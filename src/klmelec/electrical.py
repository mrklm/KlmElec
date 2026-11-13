"""Vérifications limitées aux rangées d'un logement monophasé."""
import json
from decimal import Decimal

BREAKERS = {'406771': 2, '406773': 10, '406774': 16, '406775': 20, '406777': 32}
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
        if item['brand'] == 'Legrand' and item['reference'] in BREAKERS:
            for ordinal in range(item['quantity']):
                yield circuit_key(item, ordinal), item, ordinal, BREAKERS[item['reference']]


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
    """assigned = [(calibre, usage)]; résultat par critère, jamais conformité globale."""
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
    if uses & SPECIAL or row['type'] == 'B':
        missing.append('Type / protection dédiée à vérifier avec la notice de l’équipement (IRVE, variateur ou usage particulier)')
    suggested = next((rating for rating in (25, 40, 63, 80, 100, 125)
                      if required is not None and rating >= required), None)
    suggestion = ('Calibre à étudier : ' + str(suggested) + ' A (critère d’intensité uniquement)'
                  if suggested and count <= 8 else 'Répartir les circuits / revoir le dimensionnement' if required else '')
    status = 'À corriger' if failures else 'Données manquantes / à vérifier' if missing else 'Critères contrôlés satisfaits'
    return dict(status=status, formula=formula, suggestion=suggestion, details=failures + missing)
