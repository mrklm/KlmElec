"""Variantes des disjoncteurs et interrupteurs différentiels lues dans la désignation.

Sert au classement et aux libellés normalisés du menu « Familles ». Une variante
absente de la désignation reste vide : rien n'est deviné, sauf pour les références
vérifiées à la main (electrical.BREAKERS / DIFFERENTIALS).
"""
import re

from .electrical import (BREAKERS, CURVE, DIFFERENTIALS, RATING, RCD_TYPE, SENSITIVITY, SINGLE_PHASE,
                         THREE_PHASE, plain)

# Variantes des références d'origine, relevées sur les fiches Elec Distrib et 123 Elec (14/11/2026).
VERIFIED_BREAKERS = {ref: dict(breaking='6 kA', connection='vis', range='DNX³') for ref in BREAKERS}
VERIFIED_RESIDUALS = {'411611': 'vis', '411617': 'vis', '411633': 'auto', '411638': 'auto/vis'}

BREAKING = re.compile(r'(?<![\d.,])(\d{1,2}(?:[.,]\d)?)\s*ka\b')
# « SanVis » (Hager) et « embrochable » (Resi9 XE) : raccordement automatique.
AUTO = re.compile(r'\bauto(?:matique)?s?\b|\bsanvis\b|\bsans vis\b|\bembrochable\b')
SCREW = re.compile(r'\bvis\b')
PH_N = re.compile(r'\b(?:ph|p|u|1p)\s*\+\s*n\b|\bphase\s*\+?\s*neutre\b|\buni\s*\+?\s*neutre\b')
FOUR_POLE = re.compile(r'\b4\s*p\b|\b4\s*poles\b|\btetrapolaire\b')
THREE_N = re.compile(r'\b3\s*p\s*\+\s*n\b')
# « 30mA A » sans le mot « type » (Hager) ; superimmunisé « Asi », « A-SI », « Fsi ».
TYPE_AFTER_MA = re.compile(r'\d\s*ma\s+(ac|a)(?:\s*-?\s*si)?\b')
SUPER = re.compile(r'\b(?:type\s*)?[af]\s*-?\s*si\b')
# Gammes : Legrand DNX³ / DX³, Schneider Resi9 et Acti9.
RANGES = [(re.compile(r'\bdnx'), 'DNX³'), (re.compile(r'\bdx\s*3?\b|\bdx3'), 'DX³'),
          (re.compile(r'\bresi9\s*xp\b'), 'Resi9 XP'), (re.compile(r'\bresi9\s*xe\b'), 'Resi9 XE'),
          (re.compile(r'\bic60'), 'iC60'), (re.compile(r'\bic40'), 'iC40'), (re.compile(r'\bidt40'), 'iDT40'),
          (re.compile(r'\bidd40'), 'iDD40'), (re.compile(r'\bresi9\b'), 'Resi9')]


def _one(pattern, words):
    found = set(pattern.findall(words))
    return found.pop() if len(found) == 1 else None


def connection(words):
    auto, screw = bool(AUTO.search(words)), bool(SCREW.search(words))
    return 'auto/vis' if auto and screw else 'auto' if auto else 'vis' if screw else None


def poles(words):
    if FOUR_POLE.search(words):
        return '4P'
    if THREE_N.search(words):
        return '3P+N'
    if THREE_PHASE.search(words):
        return '3P'
    if PH_N.search(words):
        return 'Ph+N'
    if SINGLE_PHASE.search(words):
        return '2P'
    return None


def breaker(product):
    """Variantes d'un disjoncteur : pôles, calibre, courbe, pouvoir de coupure, raccordement, gamme."""
    words = plain(product['name'])
    amps = _one(RATING, words)
    curve = CURVE.search(words)
    found = sorted(set(BREAKING.findall(words)), key=lambda v: float(v.replace(',', '.')))
    kiloamps = ' / '.join(found) if found else None
    if kiloamps is None:
        # « DNX³ 4500 », « DX³ 6000 » : pouvoir de coupure en ampères.
        kiloamps = '4,5' if re.search(r'\b4500\b', words) else '6' if re.search(r'\b6000\b', words) else None
    info = dict(poles=poles(words), amps=int(amps) if amps else None,
                curve=curve.group(1).upper() if curve else None,
                breaking=f"{kiloamps.replace('.', ',')} kA" if kiloamps else None,
                connection=connection(words),
                range=next((name for pattern, name in RANGES if pattern.search(words)), None))
    if product['reference'] in BREAKERS:
        info.update(amps=BREAKERS[product['reference']], curve=info['curve'] or 'C', poles=info['poles'] or 'Ph+N')
        info.update({key: info[key] or value for key, value in VERIFIED_BREAKERS[product['reference']].items()})
    return info


def residual(product):
    """Variantes d'un interrupteur différentiel : type, sensibilité, calibre, pôles, raccordement."""
    words = plain(product['name'])
    kind = RCD_TYPE.search(words) or TYPE_AFTER_MA.search(words)
    amps = _one(RATING, words)
    sensitivity = _one(SENSITIVITY, words)
    info = dict(type={'hpi': 'Hpi'}.get(kind.group(1), kind.group(1).upper()) if kind else None,
                sensitivity=int(sensitivity) if sensitivity else None, amps=int(amps) if amps else None,
                poles='4P' if THREE_PHASE.search(words) else '2P', connection=connection(words))
    if product['reference'] in DIFFERENTIALS:
        amps, kind, sensitivity = DIFFERENTIALS[product['reference']]
        info.update(amps=amps, type=kind, sensitivity=sensitivity,
                    connection=info['connection'] or VERIFIED_RESIDUALS.get(product['reference']))
    return info


def breaker_kind(product):
    """Sous-famille : branchement, différentiel, monophasé / bipolaire ou tétrapolaire / triphasé."""
    words = plain(product['name'])
    # Un disjoncteur d'abonné est aussi « différentiel » : tester le branchement d'abord.
    if 'abonne' in words or 'branchement' in words:
        return 'Disjoncteurs de branchement'
    if 'differentiel' in words:
        return 'Disjoncteurs différentiels'
    return 'Tétrapolaires / triphasés' if THREE_PHASE.search(words) else 'Monophasés / bipolaires'


def breaker_label(product):
    info, kind, words = breaker(product), breaker_kind(product), plain(product['name'])
    plain_breaker = kind in ('Monophasés / bipolaires', 'Tétrapolaires / triphasés')
    curve = f"courbe {info['curve']}" if info['curve'] else 'courbe non indiquée' if plain_breaker else None
    parts = [info['poles'], curve, info['breaking'], info['connection'], info['range']]
    if not plain_breaker:
        sensitivity, rcd = _one(SENSITIVITY, words), RCD_TYPE.search(words)
        parts[2:2] = [f'{sensitivity} mA' if sensitivity else 'sensibilité non indiquée',
                      f"type {rcd.group(1).upper()}{' SI' if SUPER.search(words) else ''}" if rcd else None,
                      'sélectif' if 'selectif' in words else 'instantané' if 'instantane' in words else None]
    return ' · '.join(part for part in parts if part)


def range_of(words):
    return next((name for pattern, name in RANGES if pattern.search(words)), None)


def residual_kind(product):
    kind = residual(product)['type']
    return f'Type {kind}' if kind else 'Type non indiqué'


def residual_label(product):
    info, words = residual(product), plain(product['name'])
    parts = [f"{info['sensitivity']} mA" if info['sensitivity'] else 'sensibilité non indiquée',
             'SI' if SUPER.search(words) else None, info['poles'], info['connection'], range_of(words)]
    return ' · '.join(part for part in parts if part)
