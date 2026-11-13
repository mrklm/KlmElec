"""Contrat commun de récupération des offres unitaires sur des URL validées."""
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ProductLink:
    url: str
    sku: str
    ean: str
    pack: int = 1


class OfferError(ValueError):
    pass


def json_objects(value):
    if isinstance(value, list):
        for child in value:
            yield from json_objects(child)
    elif isinstance(value, dict):
        yield value
        if '@graph' in value:
            yield from json_objects(value['@graph'])


def money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result <= 0:
            raise InvalidOperation
        return result
    except (InvalidOperation, ValueError):
        raise OfferError('Prix absent ou invalide') from None


class Connector:
    host = ''
    links = {}

    def parse(self, html, reference, link):
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('h1')
        if not title or not re.search(rf'(?<!\d){re.escape(reference)}(?!\d)', title.get_text()):
            raise OfferError('Référence de la fiche non confirmée')
        if link.pack != 1 or re.search(r'\b(lot|pack)\b', title.get_text(), re.I):
            raise OfferError('Conditionnement non comparable')
        products = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                objects = json_objects(json.loads(script.get_text(), parse_float=Decimal))
                for obj in objects:
                    types = obj.get('@type', [])
                    if isinstance(types, str):
                        types = [types.rsplit('/', 1)[-1]]
                    if 'Product' in types:
                        products.append(obj)
            except (ValueError, TypeError):
                continue
        candidates = [p for p in products if p.get('sku') == link.sku]
        if len(candidates) != 1:
            raise OfferError('Référence ambiguë ou données produit absentes')
        product = candidates[0]
        brand = product.get('brand', {})
        brand = brand.get('name', '') if isinstance(brand, dict) else brand
        if str(brand).casefold() != 'legrand' or str(product.get('gtin13')) != link.ean:
            raise OfferError('Marque ou EAN non confirmé')
        offer = product.get('offers')
        if isinstance(offer, list) and len(offer) == 1:
            offer = offer[0]
        if not isinstance(offer, dict) or offer.get('@type', '').rsplit('/', 1)[-1] != 'Offer':
            raise OfferError('Offre absente ou ambiguë')
        if offer.get('priceCurrency') != 'EUR':
            raise OfferError('Devise non comparable')
        if any(offer.get(key) for key in ('eligibleQuantity', 'eligibleCustomerType', 'priceSpecification')):
            raise OfferError('Conditions tarifaires à vérifier')
        if offer.get('priceValidUntil'):
            try:
                if date.fromisoformat(str(offer['priceValidUntil'])[:10]) < datetime.now(timezone.utc).date():
                    raise OfferError('Prix expiré')
            except (TypeError, ValueError) as exc:
                if isinstance(exc, OfferError):
                    raise
                raise OfferError('Validité du prix inconnue') from None
        availability = str(offer.get('availability', '')).rsplit('/', 1)[-1]
        if availability not in ('InStock', 'OutOfStock', 'Discontinued', 'SoldOut'):
            raise OfferError('Disponibilité non confirmée')
        price = money(offer.get('price'))
        self.validate_page(soup, price, link)
        return price, availability

    def validate_page(self, soup, price, link):
        """Vérifications propres au site : taxes, conditionnement, suppléments."""
        raise NotImplementedError
