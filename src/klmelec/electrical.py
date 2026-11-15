"""Vérifications limitées aux rangées d'un logement monophasé."""
import json
import re
import unicodedata
from decimal import Decimal

# Références vérifiées à la main (DNX3 phase + neutre, courbe C) : prioritaires sur la désignation.
BREAKERS = {'406771': 2, '406773': 10, '406774': 16, '406775': 20, '406777': 32}
# « 16A » ; un espace confondrait « 230 à 400V » (accent retiré) avec un calibre.
RATING = re.compile(r'(?<![\d.,/])(\d{1,3})a\b')
CURVE = re.compile(r'\bcourbe\s*([bcd])\b')
SINGLE_PHASE = re.compile(r'\b(?:ph|p|u|1p)\s*\+\s*n\b|\bphase\s*\+?\s*neutre\b|\buni\s*\+?\s*neutre\b'
                          r'|\b2\s*p\b|\b2\s*poles\b|\bbipolaire\b')
THREE_PHASE = re.compile(r'\b[34]\s*p\b|\b[34]\s*poles\b|\btetrapolaire\b|\btripolaire\b')
# Produits qui citent les disjoncteurs sans en être un.
NOT_BREAKER = ('tableau', 'cordon', 'platine', 'prise', 'peigne', 'embout')


def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text).casefold())
                   if not unicodedata.combining(c))


def classify(item):
    """(caractéristiques, None) pour un disjoncteur évalué ; (None, motif) s'il est écarté ;
    (None, None) si l'article n'est pas un disjoncteur."""
    if item['brand'] != 'Legrand':
        return None, None
    if item['reference'] in BREAKERS:
        return dict(amps=BREAKERS[item['reference']], curve='C'), None
    name = plain(item['name'] if 'name' in item.keys() else '')  # dict ou sqlite3.Row
    if 'disjoncteur' not in name or any(word in name for word in NOT_BREAKER):
        return None, None
    if 'differentiel' in name:
        return None, 'disjoncteur différentiel : protection différentielle intégrée, hors rangée'
    if "d'abonne" in name or 'abonne' in name or 'branchement' in name:
        return None, 'disjoncteur de branchement : en tête d’installation, hors rangée'
    if THREE_PHASE.search(name):
        return None, 'disjoncteur triphasé : hors logement monophasé'
    if not SINGLE_PHASE.search(name):
        return None, 'pôles non indiqués dans la désignation'
    ratings = set(RATING.findall(name))
    if len(ratings) != 1:
        return None, 'calibre non identifié dans la désignation'
    curve = CURVE.search(name)
    return dict(amps=int(ratings.pop()), curve=curve.group(1).upper() if curve else None), None


# Interrupteurs différentiels vérifiés à la main (fiches 123 Elec du 14/11/2026).
DIFFERENTIALS = {'411611': (40, 'AC', 30), '411617': (40, 'A', 30),
                 '411633': (63, 'AC', 30), '411638': (40, 'A', 30)}
# « TypeAC », « type A » ; Hpi = type A à immunité renforcée chez Legrand.
# « type A », « type Asi », « type A-SI », « type Fsi » (superimmunisé : rangé avec A ou F).
RCD_TYPE = re.compile(r'\btype\s*(ac|hpi|a|f|b)(?:\s*-?\s*si)?\b')
SENSITIVITY = re.compile(r'(?<![\d.,])(\d{2,3})\s*ma\b')


def differential(item):
    """Calibre, type et sensibilité d'un interrupteur différentiel Legrand monophasé de la liste ;
    0 / « À préciser » pour ce que la désignation n'indique pas. None pour les autres articles."""
    if item['brand'] != 'Legrand':
        return None
    if item['reference'] in DIFFERENTIALS:
        rating, kind, sensitivity = DIFFERENTIALS[item['reference']]
        return dict(rating=rating, type=kind, sensitivity=sensitivity)
    name = plain(item['name'] if 'name' in item.keys() else '')
    if ('interrupteur differentiel' not in name and 'inter diff' not in name) or THREE_PHASE.search(name):
        return None
    ratings = {int(r) for r in RATING.findall(name)}
    kind = RCD_TYPE.search(name)
    kind = {'hpi': 'A'}.get(kind.group(1), kind.group(1).upper()) if kind else 'À préciser'
    sensitivities = {int(s) for s in SENSITIVITY.findall(name)}
    rating = ratings.pop() if len(ratings) == 1 else 0
    sensitivity = sensitivities.pop() if len(sensitivities) == 1 else 0
    return dict(rating=rating if rating in (25, 40, 63, 80, 100, 125) else 0, type=kind,
                sensitivity=sensitivity if sensitivity in (30, 100, 300, 500) else 0)


def unrecognized(items):
    """Disjoncteurs de la liste que le calcul n'évalue pas, avec le motif."""
    for item in items:
        info, reason = classify(item)
        if reason:
            yield item, reason
USES = ['À préciser', 'Éclairage', 'Prises', 'Chauffage électrique', 'Chauffe-eau',
        'Plaques de cuisson', 'Lave-linge', 'Recharge véhicule', 'Équipement à variateur', 'Autre / à vérifier']
FULL = {'Chauffage électrique', 'Chauffe-eau', 'Recharge véhicule'}
SPECIAL = {'Recharge véhicule', 'Équipement à variateur', 'Autre / à vérifier'}


def empty_plan():
    return dict(method='aval', upstream=0, rows=[], circuits={})


def circuit_key(item, ordinal):
    return json.dumps([item['brand'], item['reference'], ordinal], ensure_ascii=False)


def circuits(items):
    for item in items:
        info, _ = classify(item)
        if info:
            for ordinal in range(item['quantity']):
                yield circuit_key(item, ordinal), item, ordinal, info['amps']


def curve(item):
    info, _ = classify(item)
    return info['curve'] if info else None


def validate_plan(plan, items):
    def invalid():
        raise ValueError('Configuration des rangées électriques invalide.')
    if not isinstance(plan, dict) or plan.get('method') not in ('amont', 'aval'):
        invalid()
    if type(plan.get('upstream')) is not int or not 0 <= plan['upstream'] <= 125:
        invalid()
    if not isinstance(plan.get('rows'), list) or not isinstance(plan.get('circuits'), dict):
        invalid()
    ids = set()
    for row in plan['rows']:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                or not row['id'] or row['id'] in ids or not isinstance(row.get('name'), str)
                or not 1 <= len(row['name'].strip()) <= 80
                or type(row.get('rating')) is not int or row['rating'] not in (0, 25, 40, 63, 80, 100, 125)
                or row.get('type') not in ('À préciser', 'AC', 'A', 'F', 'B')
                or type(row.get('sensitivity')) is not int or row['sensitivity'] not in (0, 30, 100, 300, 500)):
            invalid()
        ids.add(row['id'])
    keys = {key for key, *_ in circuits(items)}
    for key, value in plan['circuits'].items():
        if (key not in keys or not isinstance(value, dict)
                or (value.get('row') is not None and not isinstance(value.get('row'), str))
                or value.get('row') not in ids | {None}
                or value.get('use') not in USES):
            invalid()
    return plan


def prune_plan(plan, items):
    keys = {key for key, *_ in circuits(items)}
    plan['circuits'] = {key: value for key, value in plan['circuits'].items() if key in keys}
    return plan


def evaluate(row, assigned, method='aval', upstream=0):
    """assigned = [(calibre, usage)] ou [(calibre, usage, courbe)] ; résultat par critère,
    jamais conformité globale."""
    curves = {entry[2] for entry in assigned if len(entry) > 2}
    assigned = [entry[:2] for entry in assigned]
    failures, missing = [], []
    count = len(assigned)
    if not count:
        missing.append('Aucun circuit affecté')
    if count > 8:
        failures.append(f'{count} circuits : maximum 8 par différentiel')
    uses = {use for _, use in assigned}
    if 'À préciser' in uses:
        missing.append('Usage de certains circuits à préciser')
    full = sum(amps for amps, use in assigned if use in FULL)
    half = sum(amps for amps, use in assigned if use not in FULL and use != 'À préciser')
    required = None
    if method == 'aval':
        formula = f'{full} + 0,5 × {half}'
        if 'À préciser' not in uses and count:
            required = Decimal(full) + Decimal(half) / 2
            formula += f' = {required} A'
        else:
            formula = 'Aval : usages incomplets ou rangée vide'
    else:
        formula = f'Amont : protection amont {upstream} A' if upstream else 'Amont : calibre de la protection amont manquant'
        if upstream:
            required = Decimal(upstream)
        else:
            missing.append('Calibre de protection amont à renseigner (pas la puissance souscrite)')
    if not row['rating']:
        missing.append('Calibre du différentiel à préciser')
    elif required is not None and row['rating'] < required:
        failures.append(f"Calibre {row['rating']} A insuffisant selon la règle {method}")
    if row['sensitivity'] == 0:
        missing.append('Sensibilité à préciser')
    elif row['sensitivity'] != 30:
        failures.append('Prévoir une sensibilité de 30 mA pour ces circuits de logement')
    if row['type'] == 'À préciser':
        missing.append('Type du différentiel à préciser')
    elif uses & {'Plaques de cuisson', 'Lave-linge'} and row['type'] == 'AC':
        failures.append('Type AC inadapté aux plaques / lave-linge ; type A requis au minimum')
    if 'D' in curves:
        missing.append('Disjoncteur courbe D : réservé aux forts courants d’appel, usage à vérifier')
    if None in curves:
        missing.append('Courbe de certains disjoncteurs non indiquée dans la désignation')
    if uses & SPECIAL or row['type'] == 'B':
        missing.append('Type / protection dédiée à vérifier avec la notice de l’équipement (IRVE, variateur ou usage particulier)')
    suggested = next((rating for rating in (25, 40, 63, 80, 100, 125)
                      if required is not None and rating >= required), None)
    suggestion = ('Calibre à étudier : ' + str(suggested) + ' A (critère d’intensité uniquement)'
                  if suggested and count <= 8 else 'Répartir les circuits / revoir le dimensionnement' if required else '')
    status = 'À corriger' if failures else 'Données manquantes / à vérifier' if missing else 'Critères contrôlés satisfaits'
    return dict(status=status, formula=formula, suggestion=suggestion, details=failures + missing)
