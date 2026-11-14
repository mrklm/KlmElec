"""Appareillage (prises, interrupteurs…) : fonction, composition et nombre de postes
lus dans la désignation, pour le menu « Familles »."""
import re

from .electrical import plain

# Ordre d'affichage et mots-clés (sans accents), testés dans cet ordre.
FUNCTIONS = [
    ('Thermostats', ('thermostat',)),
    ('Autres fonctions', ('aspiration', 'tuner', 'compensateur')),
    ('Variateurs', ('variateur', 'ecovariateur', 'televariateur')),
    ('Détecteurs', ('detecteur', 'ecodetecteur')),
    ('Volets roulants', ('volet', 'volets')),
    ('VMC', ('vmc',)),
    ('Prises de courant', ('prise de courant', 'prises de courant', '2p+t', '2 p+t', 'prise 2p', 'combine prise')),
    ('Prises USB', ('usb', 'chargeur')),
    ('Prises RJ45, TV, téléphone, HP', ('rj45', 'tv', 'sat', 'telephone', 'telephonique', 'hdmi', 'haut parleur',
                                        'haut-parleur', 'multimedia')),
    # Repli : une « prise » qui n'est ni USB ni communication est une prise de courant.
    ('Prises de courant', ('prise', 'prises')),
    # Transformeur « va-et-vient et poussoir » : rangé avec les interrupteurs.
    ('Interrupteurs et va-et-vient', ('transformeur', 'transformateur')),
    ('Poussoirs', ('poussoir', 'poussoirs')),
    ('Interrupteurs et va-et-vient', ('interrupteur', 'va-et-vient', 'va et vient', 'permutateur', 'transformeur',
                                      'transformateur', 'commande', 'allumage', 'double lumineux')),
    ('Voyants et balisage', ('voyant', 'balisage', 'veilleuse', 'liseuse', 'couronne')),
    ('Sorties de câble', ('sortie de cable', 'sortie cable')),
    ('Obturateurs', ('obturateur',)),
    ('Cadres saillie', ('cadre',)),
    # Plexo : boîtes et coffrets étanches vendus dans la gamme.
    ('Boîtes de dérivation', ('boite de derivation', 'boites de derivation')),
    ('Coffrets étanches', ('coffret',)),
]
PLATES = 'Plaques de finition'
FRAMES = 'Cadres saillie'
OTHERS = 'Accessoires et supports'
PARTS = ['Mécanismes', 'Enjoliveurs', 'Complets']
# « livré avec plaque », « et plaque de finition », « complet » : appareil prêt à poser.
COMPLETE = re.compile(r'\bcomplet\b|\bcomplete\b|\bkit\b|\blivre[es]? avec\b|\bavec (?:sa )?plaque\b|\bet plaque\b')
# « 1,5 postes » n'est pas « 5 postes » : chiffre précédé d'une virgule écarté.
N = r'(?<![\d,.])\b'
POSITIONS = [(1, re.compile(N + r'1\s*poste\b|\bsimple\b|\bronde\b')), (2, re.compile(N + r'2\s*postes\b|\bdouble\b')),
             (3, re.compile(N + r'3\s*postes\b|\btriple\b')), (4, re.compile(N + r'4\s*postes\b|\bquadruple\b')),
             (5, re.compile(N + r'5\s*postes\b')), (6, re.compile(N + r'6\s*postes\b'))]


def has(words, key):
    # Mot entier, pluriel admis : « sat » ne doit pas trouver « satin ».
    return re.search(r'(?<![a-z0-9])' + re.escape(key) + r's?(?![a-z0-9])', words) is not None


def words_of(product):
    return plain(product['name'])


def is_plate(words):
    return 'plaque' in words and not COMPLETE.search(words) and not any(
        word in words for word in ('prise', 'interrupteur', 'poussoir', 'va-et-vient'))


# Désignation sans marque ni gamme en tête : « Voyant … pour interrupteur » est un voyant.
LEAD = re.compile(r'^(?:legrand\s+)?(?:(?:celiane|mosaic|dooxie|plexo|niloe|oteo)\s*-?\s*)*')


def function(product):
    words = words_of(product)
    if is_plate(words):
        return PLATES
    if LEAD.sub('', words).startswith('voyant'):
        return 'Voyants et balisage'
    for name, keys in FUNCTIONS:
        if any(has(words, key) for key in keys):
            return name
    return OTHERS


def part(product):
    """Composition d'un appareil : mécanisme, enjoliveur (Céliane) ou complet."""
    words = words_of(product)
    if COMPLETE.search(words):
        return 'Complets'
    if 'enjoliveur' in words:
        return 'Enjoliveurs'
    return 'Mécanismes'


# « 6 modules », « 2x8 modules », « 2x2 postes ».
MODULES = re.compile(r'(?<![\d,.])\b((?:\d+\s*x\s*)*\d+(?:\s*(?:a|/)\s*\d+)?)\s*(modules?|postes?)\b')


def positions(product):
    words = words_of(product)
    found = {count for count, pattern in POSITIONS if pattern.search(words)}
    return found.pop() if len(found) == 1 else None


def plate_size(product):
    """(ordre, libellé) : postes (Dooxie, Céliane) ou modules (Mosaic)."""
    count = positions(product)
    if count:
        return (count, 0), f"{count} poste{'s' if count > 1 else ''}"
    modules = MODULES.search(words_of(product))
    if modules:
        text = re.sub(r'\s*(?:a|/)\s*', ' à ', re.sub(r'\s*x\s*', '×', modules.group(1)))
        total = 1
        for value in text.split(' à ')[0].split('×'):
            total *= int(value)
        unit = 'poste' if modules.group(2).startswith('poste') else 'module'
        return (total, 1 if unit == 'module' else 0), f'{text} {unit}{"s" if total > 1 else ""}'
    return (999, 0), 'Autres plaques'


# Finitions, testées dans cet ordre (« verre onyx noir » est du verre, « noir velours » du noir).
FINISHES = [
    ('Verre', ('verre',)),
    ('Bois', ('bois', 'hetre', 'chene', 'frene', 'wengue', 'noyer', 'bambou', 'ebene', 'liege')),
    ('Métal', ('metal', 'acier', 'alu', 'aluminium', 'inox', 'laiton', 'bronze', 'nickel', 'titane', 'titanium',
               'chrome', 'cuivre', 'or')),
    ('Noir et graphite', ('noir', 'graphite', 'onyx')),
    ('Gris et anthracite', ('gris', 'anthracite', 'cendre')),
    ('Blanc', ('blanc', 'blanche', 'ivoire', 'amande', 'kaolin')),
]
OTHER_FINISH = 'Couleurs et matières'


def finish(product):
    words = words_of(product)
    for name, keys in FINISHES:
        if any(has(words, key) for key in keys):
            return name
    return OTHER_FINISH
