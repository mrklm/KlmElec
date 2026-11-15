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
from .suppliers.base import OfferError, ProductLink, json_objects, same_brand

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


BREAKER_EXCLUDED = ('platine', 'tableau', 'cordon', 'prise', 'telerupteur', 'contacteur', 'combine', 'repiquage',
                    'offert', 'bloc')
RCD_KEYWORDS = ('interrupteur differentiel', 'inter diff', 'inter. diff')
GTL_ACCESSORY = ('pour gaine', 'pour goulotte', 'pour gtl', 'embout', 'jonction', 'cornet')

FAMILIES = {
    'disjoncteurs-legrand': Family(
        label='Disjoncteurs Legrand', brand='Legrand', keyword='disjoncteur',
        excluded=('platine', 'tableau', 'cordon', 'prise'),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'disjoncteur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/132-disjoncteurs-legrand',)),
    # « Interrupteur différentiel » écarte les disjoncteurs différentiels et d'abonné.
    'differentiels-legrand': Family(
        label='Interrupteurs différentiels Legrand', brand='Legrand', keyword=('interrupteur differentiel', 'inter diff'),
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
    # Appareillage : une famille par gamme ; références à 6 chiffres, parfois suivies d'une lettre (600266A),
    # ou nouvelle gamme Céliane (CB0001, CT0001, CM0051, CP0108).
    'dooxie-legrand': Family(
        label='Dooxie Legrand', brand='Legrand', keyword='dooxie', excluded=(),
        sku_pattern=r'LEG-?(\d{6}[A-Z]?)', elec123_url=('/legrand-', 'dooxie'),
        elecdistrib_categories=('https://www.elecdistrib.fr/179-mecanismes-dooxie',
                                'https://www.elecdistrib.fr/180-plaques-de-finition-dooxie-rondes-carrees-accessoires',
                                'https://www.elecdistrib.fr/207-dooxie-complet')),
    'mosaic-legrand': Family(
        label='Mosaic Legrand', brand='Legrand', keyword='mosaic', excluded=(),
        sku_pattern=r'LEG-?(\d{6}[A-Z]?)', elec123_url=('/legrand-', 'mosaic'),
        elecdistrib_categories=('https://www.elecdistrib.fr/255-mecanismes-mosaic',
                                'https://www.elecdistrib.fr/68-mosaic-complet',
                                'https://www.elecdistrib.fr/69-plaques-de-finition-mosaic',
                                'https://www.elecdistrib.fr/70-accessoires-supports-mosaic')),
    'celiane-legrand': Family(
        label='Céliane Legrand', brand='Legrand', keyword='celiane', excluded=(),
        sku_pattern=r'LEG-?(\d{6}[A-Z]?|C[A-Z]\d{4})', elec123_url=('/legrand-', 'celiane'),
        elecdistrib_categories=('https://www.elecdistrib.fr/64-mecanismes-celiane',
                                'https://www.elecdistrib.fr/65-enjoliveurs-celiane',
                                'https://www.elecdistrib.fr/66-plaques-de-finition-celiane',
                                'https://www.elecdistrib.fr/63-celiane-complet',
                                'https://www.elecdistrib.fr/67-accessoires-supports-celiane')),
    # Gamme étanche : composable (mécanisme + support + boîtier) ou complet saillie.
    'plexo-legrand': Family(
        label='Plexo Legrand (étanche)', brand='Legrand', keyword='plexo', excluded=(),
        sku_pattern=r'LEG-?(\d{6}[A-Z]?)', elec123_url=('/legrand-', 'plexo'),
        elecdistrib_categories=('https://www.elecdistrib.fr/256-mecanismes-plexo',
                                'https://www.elecdistrib.fr/257-supports-et-boitiers-plexo',
                                'https://www.elecdistrib.fr/258-plexo-complet')),
    'niloe-legrand': Family(
        label='Niloé Legrand', brand='Legrand', keyword='niloe', excluded=(),
        sku_pattern=r'LEG-?(\d{6}[A-Z]?)', elec123_url=('/legrand-', 'niloe'),
        elecdistrib_categories=('https://www.elecdistrib.fr/60-niloe-complet',
                                'https://www.elecdistrib.fr/61-plaques-de-finition-niloe',
                                'https://www.elecdistrib.fr/62-mecanismes-niloe')),
    # Appareillage saillie (Oteo, cadres DLP) : « saillie » figure aussi dans les autres gammes,
    # écartées par « others », et dans des produits étanches ou de recharge.
    'saillie-legrand': Family(
        label='Appareillage saillie Legrand (Oteo)', brand='Legrand', keyword=('oteo', 'saillie'),
        excluded=('green', 'etanche', 'differentiel', 'coffret', 'tableau'),
        others=('dooxie-legrand', 'mosaic-legrand', 'celiane-legrand', 'plexo-legrand', 'niloe-legrand'),
        sku_pattern=r'LEG-?(\d{6}[A-Z]?)', elec123_url=('/legrand-', 'saillie'),
        elecdistrib_categories=('https://www.elecdistrib.fr/52-appareillage-saillie-legrand',)),
    'compteurs-legrand': Family(
        label='Compteurs d’énergie Legrand (EMDX³, Écocompteur)', brand='Legrand', keyword=('emdx', 'ecocompteur'),
        excluded=('platine', 'pour compteur'), sku_pattern=r'LEG-?(\d{6})',
        elec123_url=('/legrand-', ('compteur', 'emdx')),
        elecdistrib_categories=('https://www.elecdistrib.fr/144-ecocompteur-legrand',)),
    # « sati » seul trouverait les plaques Céliane « satiné » : repérage par BAES / BAEH.
    'securite-legrand': Family(
        label='Éclairage de sécurité Legrand (BAES Sati)', brand='Legrand', keyword=('baes', 'baeh', 'bloc autonome'),
        excluded=(), sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', 'baes'),
        elecdistrib_categories=('https://www.elecdistrib.fr/214-baes',)),
    # Boîtes d'encastrement, DCL, combles et dérivation ; Plexo et la boîte Oteo « en saillie » restent dans leur gamme.
    # Les Ecobatibox à suffixe L (autre conditionnement) sont écartées par le motif de référence.
    'boites-legrand': Family(
        label='Boîtes Legrand (Batibox, DCL, dérivation)', brand='Legrand', keyword=('batibox', 'boite', 'dcl'),
        excluded=('ip55', 'coffret', 'en saillie', 'vis longues'), others=('plexo-legrand',),
        sku_pattern=r'LEG-?(\d{6})', elec123_url=('/legrand-', ('boite', 'batibox', 'dcl')),
        elecdistrib_categories=('https://www.elecdistrib.fr/53-boites-d-encastrement',
                                'https://www.elecdistrib.fr/54-boites-dcl',
                                'https://www.elecdistrib.fr/55-boites-de-comble',
                                'https://www.elecdistrib.fr/188-boites-de-derivation')),
    # Wago : bornes à levier vendues en pot, flacon, blister… écartées (comparaison unitaire).
    # Elec Distrib ne vend que des conditionnements de 25 à 100 pièces.
    'wago': Family(
        label='Bornes Wago', brand='Wago', keyword=('borne', 'plaque d extremite', 'plaque d\'extremite', 'adaptateur',
                                                    'support de fixation', 'barre de pontage'),
        excluded=('mini bornes', 'bornes de connexion', 'flacon', 'pot de', 'pot panache', 'blister', 'sachet',
                  'panache', 'valisette', 'lot de', 'pack'),
        sku_pattern=r'(WAG\d{3,4}-\d{3,4})', elec123_url=('/wago-',), elecdistrib_categories=()),
    # Schneider Electric et Hager : disjoncteurs (dont différentiels et d'abonné) et interrupteurs différentiels.
    # Écartés : tableaux pré-équipés, combinés (télérupteur, contacteur, prises), lots promotionnels, blocs Vigi.
    'disjoncteurs-schneider': Family(
        label='Disjoncteurs Schneider', brand='Schneider Electric', keyword='disjoncteur',
        excluded=BREAKER_EXCLUDED, sku_pattern=r'SCH-?([A-Z0-9]+)', elec123_url=('/schneider-', 'disjoncteur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/147-disjoncteurs-schneider',)),
    'differentiels-schneider': Family(
        label='Interrupteurs différentiels Schneider', brand='Schneider Electric', keyword=RCD_KEYWORDS,
        excluded=BREAKER_EXCLUDED, sku_pattern=r'SCH-?([A-Z0-9]+)', elec123_url=('/schneider-', 'differentiel'),
        elecdistrib_categories=('https://www.elecdistrib.fr/150-interrupteurs-differentiels-schneider',)),
    'disjoncteurs-hager': Family(
        label='Disjoncteurs Hager', brand='Hager', keyword='disjoncteur',
        excluded=BREAKER_EXCLUDED, sku_pattern=r'HAG-?([A-Z0-9]+)', elec123_url=('/hager-', 'disjoncteur'),
        elecdistrib_categories=('https://www.elecdistrib.fr/265-disjoncteurs-hager',)),
    'differentiels-hager': Family(
        label='Interrupteurs différentiels Hager', brand='Hager', keyword=RCD_KEYWORDS,
        excluded=BREAKER_EXCLUDED, sku_pattern=r'HAG-?([A-Z0-9]+)', elec123_url=('/hager-', 'differentiel'),
        elecdistrib_categories=('https://www.elecdistrib.fr/260-interrupteurs-differentiels-hager',)),
    # Yokis : 123 Elec seulement. Elec Distrib n'en vend que 3, sans marque dans les données produit
    # et sous une autre référence (LUM-5454062 au lieu de MTV500M).
    'yokis': Family(
        label='Domotique Yokis', brand='Yokis', keyword='yokis', excluded=(),
        sku_pattern=r'YOK-?([A-Z0-9][A-Z0-9-]*)', elec123_url=('/yokis-',), elecdistrib_categories=()),
}

PACK = re.compile(r'\b(?:lot|pack|bo[iî]te|sachet)\s+de\s+(\d+)\b', re.I)
# Référence avant l'EAN : 6 chiffres (Legrand) ou alphanumérique (Schneider a9f76216, Hager mfn702).
CATEGORY_PRODUCT = re.compile(r'href="(https://www\.elecdistrib\.fr/[^"]+-([a-z0-9]+)-(\d{13})\.html)"')
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
    if not same_brand(brand, family.brand):
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
