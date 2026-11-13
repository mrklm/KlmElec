"""Récupération HTTP, cache explicite et calculs monétaires sans Qt ni SQLite."""
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from .suppliers import CONNECTORS
from .suppliers.base import OfferError

CACHE_SECONDS = 300
MAX_BYTES = 5_000_000


def now():
    return datetime.now(timezone.utc).isoformat()


def rounded(value):
    return value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def amounts(price, quantity, vat):
    ttc = Decimal(price)
    rate = Decimal(vat)
    if not rate.is_finite() or not 0 <= rate <= 100:
        raise ValueError('Taux de TVA invalide')
    ht = ttc / (1 + rate / 100)
    return rounded(ht), rounded(ttc), rounded(ht * quantity), rounded(ttc * quantity)


def is_recent(offer):
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(offer['checked_at'])).total_seconds()
    return 0 <= age < CACHE_SECONDS


def best_offer(offers):
    # Every enabled supplier must have a verified, comparable result.
    if not offers or any(o['status'] != 'ok' or not is_recent(o) for o in offers):
        return None
    return min(offers, key=lambda o: Decimal(o['ttc']))


def cache_lookup(previous, supplier, item, url):
    for offer in reversed(previous):
        if (offer['product_id'] == item['id'] and offer['supplier_id'] == supplier['id']
                and offer.get('connector') == supplier['connector'] and offer['url'] == url
                and offer['status'] == 'ok'):
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(offer['checked_at'])).total_seconds()
            if 0 <= age < CACHE_SECONDS:
                return offer
    return None


def read_html(client, url):
    # No automatic redirect: do not silently follow a changed product or access challenge.
    with client.stream('GET', url) as response:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise OfferError('Réponse trop volumineuse')
        return data.decode('utf-8', errors='replace')


def compare(items, suppliers, previous=(), progress=lambda text: None,
            cancelled=lambda: False, client=None, pause=time.sleep):
    """Return one explicit result per item and enabled supplier, including failures."""
    if client is None:
        with httpx.Client(timeout=15, follow_redirects=False,
                          headers={'User-Agent': 'KlmElec/0.2 (comparaison personnelle)'}) as owned:
            return compare(items, suppliers, previous, progress, cancelled, owned, pause)
    results, robots, blocked = [], {}, set()
    for item in items:
        for supplier in suppliers:
            if not supplier['active']:
                continue
            connector = CONNECTORS.get(supplier['connector'])
            link = connector.links.get(item['reference']) if connector and item['brand'].casefold() == 'legrand' else None
            result = dict(product_id=item['id'], reference=item['reference'], quantity=item['quantity'],
                          supplier_id=supplier['id'], supplier=supplier['name'], connector=supplier['connector'],
                          url=link.url if link else '', checked_at=now(), status='error', detail='', ttc=None, cached=False)
            progress(f"{item['reference']} — {supplier['name']}")
            try:
                if cancelled():
                    raise OfferError('Recherche annulée')
                if not connector or urlsplit(supplier['url']).hostname != connector.host:
                    raise OfferError('Connecteur non disponible pour ce site')
                if not link:
                    raise OfferError('URL non configurée pour cette référence')
                if link.pack != 1:
                    raise OfferError(f'Lot de {link.pack} : exclu de la comparaison unitaire')
                cached = cache_lookup(previous, supplier, item, link.url)
                if cached:
                    result.update(ttc=cached['ttc'], status='ok', checked_at=cached['checked_at'], cached=True,
                                  detail='En stock au relevé — cache de moins de 5 minutes')
                else:
                    if connector.host in blocked:
                        raise OfferError('Site suspendu après un refus ou une limitation d’accès')
                    if connector.host not in robots:
                        policy = RobotFileParser()
                        policy.parse(read_html(client, f'https://{connector.host}/robots.txt').splitlines())
                        robots[connector.host] = policy
                        pause(1)
                    if not robots[connector.host].can_fetch('KlmElec', link.url):
                        raise OfferError('Consultation exclue par les règles du site')
                    if cancelled():
                        raise OfferError('Recherche annulée')
                    html = read_html(client, link.url)
                    price, availability = connector.parse(html, item['reference'], link)
                    result.update(ttc=str(price), checked_at=now())
                    if availability == 'InStock':
                        result.update(status='ok', detail='En stock — prix TTC relevé')
                    else:
                        result.update(status='unavailable', detail='Produit indisponible à la commande')
                    pause(1)
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                if code in (403, 429):
                    blocked.add(connector.host)
                result['detail'] = ('Produit introuvable (404)' if code == 404 else f'Accès impossible (HTTP {code})')
            except httpx.TimeoutException:
                result['detail'] = 'Délai réseau dépassé'
            except httpx.RequestError:
                result['detail'] = 'Erreur réseau — site inaccessible'
            except (OfferError, ValueError, TypeError, ArithmeticError, AttributeError) as exc:
                result['detail'] = str(exc) if isinstance(exc, OfferError) else 'Données de la fiche non exploitables'
            results.append(result)
    return results
