"""Bouton « Familles » : domaine → famille → (sous-famille) → article, ouvert au survol."""
import re

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu, QToolButton

from .discovery import FAMILIES, belongs
from .suppliers.base import same_brand
from .electrical import RATING, THREE_PHASE, plain
from . import fittings
from .variants import breaker, breaker_kind, breaker_label, residual, residual_kind, residual_label

LARGE = 20         # au-delà, la famille est découpée en sous-familles
LABEL_LENGTH = 70

# Regroupement des familles du catalogue pour le menu.
DOMAINS = [
    ('Protection', ('disjoncteurs-legrand', 'differentiels-legrand', 'disjoncteurs-schneider', 'differentiels-schneider',
                    'disjoncteurs-hager', 'differentiels-hager', 'parafoudres-legrand', 'sectionneurs-legrand')),
    ('Commande', ('telerupteurs-legrand', 'contacteurs-legrand', 'horloges-legrand', 'crepusculaires-legrand')),
    ('Mesure', ('compteurs-legrand',)),
    ('Répartition', ('peignes-legrand', 'repartiteurs-legrand', 'borniers-legrand')),
    ('Tableaux', ('coffrets-drivia-legrand', 'portes-drivia-legrand', 'rehausses-drivia-legrand',
                  'tableaux-pre-equipes-legrand')),
    ('GTL', ('gtl-legrand', 'accessoires-gtl-legrand')),
    ('Communication', ('coffrets-communication-legrand', 'modules-communication-legrand')),
    ('Boîtes et connexion', ('boites-legrand', 'wago')),
    ('Domotique', ('yokis',)),
    ('Sécurité', ('securite-legrand',)),
    ('Appareillage', ('dooxie-legrand', 'mosaic-legrand', 'celiane-legrand', 'plexo-legrand', 'niloe-legrand',
                      'saillie-legrand')),
]
RANGES = {'dooxie-legrand', 'mosaic-legrand', 'celiane-legrand', 'plexo-legrand', 'niloe-legrand', 'saillie-legrand'}
OTHERS = 'Autres articles'


# Familles toujours découpées : (sous-famille, libellé des variantes, ordre des sous-familles).
RCD_ORDER = ['Type AC', 'Type A', 'Type Hpi', 'Type F', 'Type B', 'Type non indiqué']
VARIANTS = {key: (breaker_kind, breaker_label, None) for key in ('disjoncteurs-legrand', 'disjoncteurs-schneider',
                                                                  'disjoncteurs-hager')}
VARIANTS.update({key: (residual_kind, residual_label, RCD_ORDER) for key in ('differentiels-legrand',
                                                                             'differentiels-schneider', 'differentiels-hager')})


# Domotique Yokis : sous-familles par fonction, testées dans cet ordre (un kit contient un télérupteur).
YOKIS = [('Kits radio', ('kit',)), ('Volets roulants', ('volet',)), ('Télérupteurs', ('telerupteur',)),
         ('Minuteries', ('minuterie',)), ('Télévariateurs', ('televariateur',)), ('Émetteurs', ('emetteur',)),
         ('Télécommandes', ('telecommande',))]
YOKIS_OTHERS = 'Passerelles et accessoires'
# Boîtes Legrand : sous-familles testées dans cet ordre (« couvercle pour boîte DCL » est un accessoire).
# Boîtes d'encastrement réparties par type de pose (Ecobatibox d'abord : elle est aussi « pour cloison sèche »).
BOXES = [('Couvercles et accessoires', ('couvercle', 'vis longue')), ('Supports', ('support',)),
         ('DCL', ('dcl',)), ('Boîtes de dérivation', ('derivation',)), ('Boîtes de combles', ('comble',)),
         ('Encastrement étanche à l’air (Ecobatibox)', ('ecobatibox', 'etanche')),
         ('Encastrement multimatériaux', ('multimateriaux',)), ('Encastrement pour sol', ('sol',)),
         ('Encastrement à sceller', ('sceller', 'maconnerie')),
         ('Encastrement cloison sèche', ('cloison', 'placo', 'encastrement', 'boite', 'monoposte'))]
BOXES_OTHERS = 'Autres'
ORDERS = {'yokis': [name for name, _ in YOKIS] + [YOKIS_OTHERS],
          'boites-legrand': ['Encastrement cloison sèche', 'Encastrement à sceller', 'Encastrement multimatériaux',
                             'Encastrement étanche à l’air (Ecobatibox)', 'Encastrement pour sol', 'Boîtes de dérivation',
                             'Boîtes de combles', 'DCL', 'Supports', 'Couvercles et accessoires', BOXES_OTHERS]}


def subfamily(key, words):
    """Sous-famille d'un article, pour les autres familles volumineuses."""
    if key == 'yokis':
        return next((name for name, keys in YOKIS if any(k in words for k in keys)), YOKIS_OTHERS)
    if key == 'boites-legrand':
        return next((name for name, keys in BOXES if any(k in words for k in keys)), BOXES_OTHERS)
    return 'Tétrapolaires / triphasés' if THREE_PHASE.search(words) else 'Monophasés / bipolaires'


def rating(product):
    found = RATING.findall(plain(product['name']))
    return int(found[0]) if len(set(found)) == 1 else 999


def amps(key, product):
    """Calibre pour le menu, références vérifiées comprises."""
    if key.startswith('disjoncteurs-'):
        return breaker(product)['amps'] or 999
    if key.startswith('differentiels-'):
        return residual(product)['amps'] or 999
    return rating(product)


def families_of(product):
    """Familles dont la désignation relève : la première hors gammes d'appareillage, plus chaque gamme
    citée (« support pour Mosaic, Céliane ou Soliroc » figure dans les deux gammes)."""
    words = plain(product['name'])
    found = [key for key, family in FAMILIES.items()
             if same_brand(product['brand'], family.brand) and belongs(words, family)
             and not any(belongs(words, FAMILIES[other]) for other in family.others)]
    main = [key for key in found if key not in RANGES][:1]
    return main + [key for key in found if key in RANGES]


def family_of(product):
    """Clé de la première famille dont la désignation relève, sinon None."""
    found = families_of(product)
    return found[0] if found else None


def grouped(products):
    """({famille: [articles]}, {marque: [articles]}) pour les articles hors familles."""
    families, others = {}, {}
    for product in products:
        keys = families_of(product)
        for key in keys:
            families.setdefault(key, []).append(product)
        if not keys:
            others.setdefault(product['brand'], []).append(product)
    return families, others


def short_name(product):
    """Désignation sans la marque, la gamme ni la référence répétées, abrégée pour le menu."""
    brand = re.escape(product['brand'].split()[0]) if product['brand'].strip() else 'legrand'
    name = re.sub(r'^\s*(?:legrand|' + brand + r')\s+', '', product['name'], flags=re.I)
    name = re.sub(r'^\s*(?:dooxie|mosaic|c[ée]liane|plexo|nilo[ée]|oteo)\s+|\s+(?:dooxie|mosaic|c[ée]liane|plexo|nilo[ée]|oteo)(?=\s)', '', name, flags=re.I)
    name = re.sub(r'\s*[-–]?\s*(?:legrand\s*)?r[ée]f\s*[.:]?\s*:?\s*\w+.*$', '', name, flags=re.I)
    name = re.sub(r'\s*[-–]\s*' + re.escape(product['reference']) + r'\s*$', '', name)
    name = re.sub(r'\s+legrand\s*$', '', name, flags=re.I).strip(' -–') or product['name']
    return name if len(name) <= LABEL_LENGTH else name[:LABEL_LENGTH - 1].rstrip() + '…'


def label(product, describe=None):
    # « & » introduirait un raccourci clavier dans un menu Qt.
    text = describe(product) if describe else short_name(product)
    return f"{text or short_name(product)} · {product['reference']}".replace('&', '&&')


class FamilyButton(QToolButton):
    chosen = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText('Familles')
        self.setToolTip('Parcourir le catalogue par famille ; cliquez sur un article pour l’ajouter à la liste.')
        self.setPopupMode(QToolButton.InstantPopup)
        self.setMenu(QMenu(self))
        self.menu().setToolTipsVisible(True)
        self.menu().triggered.connect(lambda action: action.data() is not None and self.chosen.emit(action.data()))

    def set_products(self, products):
        menu = self.menu()
        menu.clear()
        families, others = grouped(products)
        for domain, keys in DOMAINS:
            present = [key for key in keys if key in families]
            if not present:
                continue
            domain_menu = menu.addMenu(domain)
            for key in present:
                family_menu = domain_menu.addMenu(f'{FAMILIES[key].label} ({len(families[key])})')
                if key in VARIANTS:
                    self.fill_variants(family_menu, key, families[key])
                    continue
                if key in RANGES:
                    self.fill_fittings(family_menu, families[key])
                    continue
                if len(families[key]) <= LARGE:
                    self.fill(family_menu, families[key])
                    continue
                groups = {}
                for product in families[key]:
                    groups.setdefault(subfamily(key, plain(product['name'])), []).append(product)
                order = ORDERS.get(key, [])
                for name in sorted(groups, key=lambda n: (order.index(n) if n in order else len(order), n)):
                    self.fill_by_rating(family_menu.addMenu(f'{name} ({len(groups[name])})'), groups[name])
        if others:
            others_menu = menu.addMenu(OTHERS)
            for brand in sorted(others, key=str.casefold):
                self.fill(others_menu.addMenu(f'{brand} ({len(others[brand])})'), others[brand])
        if not families:
            hint = menu.addAction('Recherchez d’autres familles dans Paramètres → Catalogue')
            hint.setEnabled(False)

    @classmethod
    def fill_variants(cls, menu, key, products):
        """Sous-famille → calibre → libellé normalisé des variantes."""
        kind_of, describe, order = VARIANTS[key]
        groups = {}
        for product in products:
            groups.setdefault(kind_of(product), []).append(product)
        for name in sorted(groups, key=lambda n: (order.index(n) if order and n in order else len(order or ()), n)):
            group_menu = menu.addMenu(f'{name} ({len(groups[name])})')
            ratings = {}
            for product in groups[name]:
                ratings.setdefault(amps(key, product), []).append(product)
            for value in sorted(ratings):
                title = f'{value} A' if value != 999 else 'Calibre non indiqué'
                cls.fill(group_menu.addMenu(f'{title} ({len(ratings[value])})'), ratings[value], describe)

    @classmethod
    def fill_fittings(cls, menu, products):
        """Gamme d'appareillage : fonction → composition (si plusieurs) → article ;
        plaques par nombre de postes."""
        groups = {}
        for product in products:
            groups.setdefault(fittings.function(product), []).append(product)
        order = [name for name, _ in fittings.FUNCTIONS] + [fittings.PLATES, fittings.OTHERS]
        for name in sorted(groups, key=order.index):
            group_menu = menu.addMenu(f'{name} ({len(groups[name])})')
            if name in (fittings.PLATES, fittings.FRAMES):
                key, title = fittings.plate_size, lambda size: size[1]
            elif name == fittings.OTHERS:
                cls.fill_by_finish(group_menu, groups[name])
                continue
            else:
                key, title = fittings.part, str
            sub = {}
            for product in groups[name]:
                sub.setdefault(key(product), []).append(product)
            if len(sub) == 1:
                cls.fill_by_finish(group_menu, groups[name])
                continue
            for value in sorted(sub, key=lambda v: fittings.PARTS.index(v) if v in fittings.PARTS else v):
                cls.fill_by_finish(group_menu.addMenu(f'{title(value)} ({len(sub[value])})'), sub[value])

    @classmethod
    def fill_by_finish(cls, menu, products):
        """Niveau « finition » quand la liste reste trop longue (plaques et enjoliveurs Céliane)."""
        finishes = {}
        for product in products:
            finishes.setdefault(fittings.finish(product), []).append(product)
        if len(products) <= LARGE or len(finishes) == 1:
            cls.fill(menu, products)
            return
        order = [name for name, _ in fittings.FINISHES][::-1] + [fittings.OTHER_FINISH]
        for name in sorted(finishes, key=order.index):
            cls.fill(menu.addMenu(f'{name} ({len(finishes[name])})'), finishes[name])

    @classmethod
    def fill_by_rating(cls, menu, products):
        """Niveau supplémentaire par calibre quand la sous-famille reste volumineuse."""
        if len(products) <= LARGE:
            cls.fill(menu, products)
            return
        ratings = {}
        for product in products:
            ratings.setdefault(rating(product), []).append(product)
        for amps in sorted(ratings):
            title = f'{amps} A' if amps != 999 else 'Calibre non indiqué'
            cls.fill(menu.addMenu(f'{title} ({len(ratings[amps])})'), ratings[amps])

    @staticmethod
    def fill(menu, products, describe=None):
        menu.setToolTipsVisible(True)
        for product in sorted(products, key=lambda p: (rating(p), label(p, describe), p['reference'])):
            action = menu.addAction(label(product, describe))
            action.setData(product['id'])
            action.setToolTip(f"{product['name']} — {product['brand']} {product['reference']}")

    def enterEvent(self, event):
        super().enterEvent(event)
        if not self.menu().isVisible() and not self.menu().isEmpty():
            self.menu().popup(self.mapToGlobal(self.rect().bottomLeft()))
