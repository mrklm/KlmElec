"""Découverte automatique des fiches fournisseurs d'une famille de produits.

Les listes de produits proviennent du plan de site (123 Elec) ou des pages de
catégorie (Elec Distrib), seules sources autorisées par robots.txt. Chaque fiche
candidate est ouverte puis validée par le même contrôle que la comparaison des
prix : une fiche retenue ici pourra donc être relevée sans exception.
"""
import json
import re
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup

from . import __version__
from .comparison import MAX_BYTES, read_html, robots_policy
from .electrical import plain
from .suppliers import CONNECTORS
from .suppliers.base import OfferError, ProductLink, json_objects

SITEMAP_BYTES = 30_000_000
MAX_PAGES = 50


@dataclass(frozen=True)
class Family:
    label: str
    brand: str
    keyword: str | tuple[str, ...]    # présent dans la désignation retenue (sans accents) ; tuple = l'un d'eux
    excluded: tuple[str, ...]         # accessoires dont la désignation cite la famille (sans accents)
    sku_pattern: str                  # SKU fournisseur → référence fabricant
    elec123_url: tuple                # mots requis dans l'adresse du plan de site ; tuple imbriqué = l'un d'eux
    elecdistrib_categories: tuple[str, ...]
    required: tuple[str, ...] = ()    # si renseigné : l'un de ces mots doit aussi figurer (sans accents)
    others: tuple[str, ...] = ()      # familles complémentaires : leurs fiches sont écartées d'ici


GTL_ACCESSORY = ('pour gaine', 'pour goulotte', 'pour gtl', 'embout', 'jonction', 'cornet')

FAMILIES = {
    'disjoncteurs-legrand': Family(
        label='Disjoncteurs Legrand', brand='Legrand', keyword='disjoncteur',
        excluded=('platine', 'tableau', 'cordon', 'prise'),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'disjoncteur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/132-disjoncteurs-legrand',)),
    # « Interrupteur différentiel » écarte les disjoncteurs différentiels et d'abonné.
    'differentiels-legrand': Family(
        label='Interrupteurs différentiels Legrand', brand='Legrand', keyword='interrupteur differentiel',
        excluded=(), sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'differentiel'),
        elecdistrib_categories=('https://www.elecdistrib.fr/135-interrupteurs-differentiels-legrand',)),
    # La catégorie Elec Distrib contient aussi des télévariateurs : écartés par le mot-clé.
    'telerupteurs-legrand': Family(
        label='Télérupteurs Legrand', brand='Legrand', keyword='telerupteur',
        excluded=(), sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'telerupteur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/140-telerupteurs-legrand',)),
    # Pas de catégorie dédiée chez Elec Distrib : accessoires modulaires, triés par la désignation.
    'peignes-legrand': Family(
        label='Peignes d’alimentation Legrand', brand='Legrand', keyword='peigne',
        excluded=('pour peigne', 'par peigne', 'et peignes', 'isolant'),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'peigne'),
        elecdistrib_categories=('https://www.elecdistrib.fr/138-accessoires-modulaires-legrand',)),
    'contacteurs-legrand': Family(
        label='Contacteurs Legrand', brand='Legrand', keyword='contacteur', excluded=(),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'contacteur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/139-contacteurs-legrand',)),
    'parafoudres-legrand': Family(
        label='Parafoudres Legrand', brand='Legrand', keyword='parafoudre',
        excluded=('pour parafoudre', 'rechange'),  # cassettes de rechange
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'parafoudre'),
        elecdistrib_categories=('https://www.elecdistrib.fr/143-parafoudre-legrand',)),
    # « sectionneur » couvre « Interrupteur-Sectionneur » et « Interrupteur sectionneur ».
    'sectionneurs-legrand': Family(
        label='Interrupteurs-sectionneurs Legrand', brand='Legrand', keyword='sectionneur', excluded=(),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'sectionneur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/138-accessoires-modulaires-legrand',)),
    # « Interrupteur horaire » chez 123 Elec, parfois « Horloge » chez Elec Distrib ;
    # la catégorie contient aussi minuteries, sonneries, relais et interrupteurs crépusculaires.
    'horloges-legrand': Family(
        label='Horloges modulaires Legrand', brand='Legrand', keyword=('interrupteur horaire', 'horloge'),
        excluded=(), sku_pattern=r'LEG-?(\d{6})',
        elec123_url=('/legrand-', ('interrupteur-horaire', 'horloge')),
        elecdistrib_categories=('https://www.elecdistrib.fr/142-horloge-modulaire-legrand',)),
    'repartiteurs-legrand': Family(
        label='Répartiteurs Legrand', brand='Legrand', keyword='repartiteur', excluded=(),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'repartiteur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/138-accessoires-modulaires-legrand',)),
    # Barrettes de phase / neutre : famille distincte des répartiteurs.
    'borniers-legrand': Family(
        label='Borniers de répartition Legrand', brand='Legrand', keyword='bornier', excluded=('pour bornier',),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'bornier'),
        elecdistrib_categories=('https://www.elecdistrib.fr/138-accessoires-modulaires-legrand',)),
    # Goulottes GTL complètes ; embouts, cornets et jonctions sol/plafond sont des accessoires.
    'gtl-legrand': Family(
        label='GTL Legrand (gaines techniques de logement)', brand='Legrand', keyword=('gtl', 'gaine technique'),
        excluded=GTL_ACCESSORY, sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', ('gtl', 'gaine-technique')),
        elecdistrib_categories=('https://www.elecdistrib.fr/141-gtl-gaine-technique-de-logement-legrand',)),
    # Exactement ce que la famille GTL écarte.
    'accessoires-gtl-legrand': Family(
        label='Accessoires GTL Legrand', brand='Legrand', keyword=('gtl', 'gaine technique'),
        excluded=(), required=GTL_ACCESSORY,
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', ('gtl', 'gaine-technique')),
        elecdistrib_categories=('https://www.elecdistrib.fr/141-gtl-gaine-technique-de-logement-legrand',)),
    # Tableaux nus uniquement : portes, rehausses, platines, pré-équipés et communication écartés.
    'coffrets-drivia-legrand': Family(
        label='Coffrets Drivia Legrand (tableaux nus)', brand='Legrand', keyword='drivia',
        required=('tableau', 'coffret'),
        excluded=('pour coffret', 'pour tableau', 'porte', 'rehausse', 'serrure', 'platine', 'habillage',
                  'communication', 'multimedia', 'preequipe', 'pre-equipe', 'pre-cable', 'precable', 'pret-a-poser'),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'drivia'),
        elecdistrib_categories=('https://www.elecdistrib.fr/130-tableaux-vides-portes',)),
    # Portes des tableaux Drivia ; celles des bacs et platines de branchement sont d'autres produits.
    'portes-drivia-legrand': Family(
        label='Portes Drivia Legrand', brand='Legrand', keyword='drivia', required=('porte',),
        excluded=('pour bac', 'platine', 'habillage'),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'drivia', 'porte'),
        elecdistrib_categories=('https://www.elecdistrib.fr/130-tableaux-vides-portes',)),
    'rehausses-drivia-legrand': Family(
        label='Rehausses Drivia Legrand', brand='Legrand', keyword='drivia', required=('rehausse',), excluded=(),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'drivia', 'rehausse'),
        elecdistrib_categories=('https://www.elecdistrib.fr/130-tableaux-vides-portes',)),
    # « prééquipé », « pré-équipé », « pré-câblé » (sans accents).
    'tableaux-pre-equipes-legrand': Family(
        label='Tableaux pré-équipés Legrand', brand='Legrand',
        keyword=('preequipe', 'pre-equipe', 'pre equipe', 'pre-cable', 'precable', 'pre cable'),
        required=('tableau', 'coffret'), excluded=(),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'tableau', ('pre-equipe', 'preequipe', 'pre-cable', 'precable')),
        elecdistrib_categories=('https://www.elecdistrib.fr/131-tableaux-pre-equipes-portes',)),
    # Coffrets complets ; modules (brassage, DTI, filtres…) « pour coffret » écartés.
    'coffrets-communication-legrand': Family(
        label='Coffrets de communication Legrand', brand='Legrand', keyword='coffret',
        required=('communication', 'multimedia', 'play'), excluded=('pour coffret',),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'coffret', ('communication', 'multimedia')),
        elecdistrib_categories=('https://www.elecdistrib.fr/24-coffret-de-communication-legrand-portes',)),
    # Modules vendus seuls ; un « coffret … avec brassage » reste un coffret.
    'modules-communication-legrand': Family(
        label='Modules de communication Legrand', brand='Legrand',
        keyword=('brassage', 'dti', 'filtre', 'repartiteur', 'terminaison', 'support box'),
        excluded=(), others=('coffrets-communication-legrand',), sku_pattern=r'LEG-?(\d{6})',
        elec123_url=('/legrand-', ('brassage', '-dti', 'filtre-maitre', 'repartiteur-tv', 'terminaison', 'support-box')),
        elecdistrib_categories=('https://www.elecdistrib.fr/24-coffret-de-communication-legrand-portes',)),
    # Rangés avec les horloges chez Elec Distrib.
    'crepusculaires-legrand': Family(
        label='Interrupteurs crépusculaires Legrand', brand='Legrand', keyword='crepusculaire',
        excluded=('pour interrupteur',),  # cellules de rechange
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'crepusculaire'),
        elecdistrib_categories=('https://www.elecdistrib.fr/142-horloge-modulaire-legrand',)),
}

PACK = re.compile(r'\b(?:lot|pack|bo[iî]te|sachet)\s+de\s+(\d+)\b', re.I)
CATEGORY_PRODUCT = re.compile(r'href="(https://www\.elecdistrib\.fr/[^"]+-(\d{6})-(\d{13})\.html)"')
CATEGORY_PAGE = re.compile(r'\?page=(\d+)')


@dataclass
class Discovery:
    links: list          # (connector, référence, désignation, ProductLink)
    rejected: list       # (connector, url, motif)
    errors: list         # messages par site


class Session:
    """Requêtes espacées, robots.txt respecté et arrêt d'un site après un refus."""

    def __init__(self, client, pause, cancelled):
        self.client, self.pause, self.cancelled = client, pause, cancelled
        self.robots = {}

    def get(self, url, max_bytes=None):
        if self.cancelled():
            raise OfferError('Recherche annulée')
        host = urlsplit(url).hostname
        if host not in self.robots:
            self.robots[host] = robots_policy(self.client, host)
            self.pause(1)
        if not self.robots[host].can_fetch('KlmElec', url):
            raise OfferError('Consultation exclue par les règles du site')
        try:
            return read_html(self.client, url, max_bytes or MAX_BYTES)
        finally:
            self.pause(1)


def belongs(words, family):
    """Désignation (sans accents) conforme aux mots-clés, mots requis et exclusions de la famille."""
    keywords = (family.keyword,) if isinstance(family.keyword, str) else family.keyword
    return (any(word in words for word in keywords) and not any(word in words for word in family.excluded)
            and (not family.required or any(word in words for word in family.required)))


def identify(html, family):
    """SKU, EAN, titre et désignation de la fiche, sans encore valider l'offre."""
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.find('h1')
    title = title.get_text(' ', strip=True) if title else ''
    products = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            for obj in json_objects(json.loads(script.get_text())):
                types = obj.get('@type', [])
                types = [types.rsplit('/', 1)[-1]] if isinstance(types, str) else types
                if 'Product' in types:
                    products.append(obj)
        except (ValueError, TypeError):
            continue
    if len(products) != 1:
        raise OfferError('Données produit absentes ou multiples')
    product = products[0]
    brand = product.get('brand', {})
    brand = brand.get('name', '') if isinstance(brand, dict) else brand
    if str(brand).casefold() != family.brand.casefold():
        raise OfferError('Autre marque')
    name = ' '.join(str(product.get('name') or title).split())
    pack = PACK.search(f'{title} {name}')
    if pack and int(pack.group(1)) != 1:
        raise OfferError(f'Lot de {pack.group(1)} : exclu de la comparaison unitaire')
    words = plain(name)
    if not belongs(words, family) or any(belongs(words, FAMILIES[other]) for other in family.others):
        raise OfferError('Hors famille')
    match = re.fullmatch(family.sku_pattern, str(product.get('sku', '')))
    if not match:
        raise OfferError('Référence fabricant non reconnue')
    ean = str(product.get('gtin13', ''))
    if not re.fullmatch(r'\d{13}', ean):
        raise OfferError('EAN absent')
    return dict(reference=match.group(1), sku=product['sku'], ean=ean, title=title, name=name)


def elec123_candidates(session, family):
    xml = session.get('https://www.123elec.com/media/sitemap/sitemap.xml', SITEMAP_BYTES)
    urls = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', xml)
    return [u for u in dict.fromkeys(urls)
            if urlsplit(u).hostname == 'www.123elec.com'
            and all(word in u if isinstance(word, str) else any(w in u for w in word) for word in family.elec123_url)]


def elecdistrib_candidates(session, family):
    found = {}
    for category in family.elecdistrib_categories:
        html = session.get(category)
        last = min(max(map(int, CATEGORY_PAGE.findall(html)), default=1), MAX_PAGES)
        for page in range(1, last + 1):
            if page > 1:
                html = session.get(f'{category}?page={page}')
            for url, _, _ in CATEGORY_PRODUCT.findall(html):
                found.setdefault(url, None)
    return list(found)


SOURCES = {'123elec': elec123_candidates, 'elecdistrib': elecdistrib_candidates}


def discover(family_key, known=(), progress=lambda text: None, cancelled=lambda: False,
             client=None, pause=time.sleep):
    """Fiches validées pour chaque connecteur. `known` : (connector, référence) déjà configurés."""
    if client is None:
        with httpx.Client(timeout=15, follow_redirects=False,
                          headers={'User-Agent': f'KlmElec/{__version__} (comparaison personnelle)'}) as owned:
            return discover(family_key, known, progress, cancelled, owned, pause)
    family = FAMILIES[family_key]
    known = set(known)
    result = Discovery([], [], [])
    eans = {}
    session = Session(client, pause, cancelled)
    for key, candidates in SOURCES.items():
        connector = CONNECTORS[key]
        try:
            progress(f'{family.label} — liste des produits {connector.host}')
            urls = candidates(session, family)
        except (OfferError, httpx.HTTPError) as exc:
            if cancelled():
                result.errors.append('Recherche annulée')
                return result
            result.errors.append(f'{connector.host} : {describe(exc)}')
            continue
        for number, url in enumerate(urls, 1):
            progress(f'{family.label} — {connector.host} : fiche {number}/{len(urls)}')
            try:
                html = session.get(url)
                data = identify(html, family)
                if (key, data['reference']) in known:
                    continue
                if eans.setdefault(data['reference'], data['ean']) != data['ean']:
                    raise OfferError('EAN différent selon le fournisseur')
                link = ProductLink(url, data['sku'], data['ean'], brand=family.brand,
                                   expected_title=data['title'])
                # Même contrôle que lors du relevé des prix (titre, EAN, offre, taxes…).
                connector.parse(html, data['reference'], link)
                known.add((key, data['reference']))
                result.links.append((key, data['reference'], data['name'], link))
            except httpx.HTTPStatusError as exc:
                result.rejected.append((key, url, describe(exc)))
                if exc.response.status_code in (403, 429):
                    result.errors.append(f'{connector.host} : accès limité, recherche interrompue')
                    break
            except (OfferError, httpx.HTTPError, ValueError, TypeError, ArithmeticError, AttributeError) as exc:
                if cancelled():
                    result.errors.append('Recherche annulée')
                    return result
                result.rejected.append((key, url, describe(exc)))
    return result


def describe(exc):
    if isinstance(exc, httpx.HTTPStatusError):
        return f'HTTP {exc.response.status_code}'
    if isinstance(exc, httpx.TimeoutException):
        return 'Délai réseau dépassé'
    if isinstance(exc, httpx.HTTPError):
        return 'Erreur réseau'
    return str(exc) if isinstance(exc, OfferError) else 'Données de la fiche non exploitables'
