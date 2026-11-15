import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtWidgets import QApplication

from klmelec.family_menu import FamilyButton, family_of
from klmelec.fittings import function, part, plate_size


def product(name, reference='600001', id=1, brand='Legrand'):
    return dict(id=id, name=name, brand=brand, reference=reference)


@pytest.mark.parametrize('name,expected', [
    ('LEGRAND Dooxie Interrupteur va et vient blanc à voyant témoin - 600009', ('Interrupteurs et va-et-vient', 'Mécanismes')),
    ('LEGRAND Dooxie Interrupteur volets roulants blanc - 600021', ('Volets roulants', 'Mécanismes')),
    ('LEGRAND Dooxie Interrupteur variateur universel 3 fils 150W noir - 600266A', ('Variateurs', 'Mécanismes')),
    ('LEGRAND Dooxie One Transformeur 5 fonctions va et vient et poussoir complet blanc', ('Interrupteurs et va-et-vient', 'Complets')),
    ('LEGRAND Dooxie Prise de courant 2P+T surface avec prise USB TYPE C Blanc', ('Prises de courant', 'Mécanismes')),
    ('LEGRAND Dooxie Prise chargeur USB double Type A aluminium', ('Prises USB', 'Mécanismes')),
    ('Prise TV-SAT + RJ45 Cat6 STP compacte blanc Dooxie Legrand', ('Prises RJ45, TV, téléphone, HP', 'Mécanismes')),
    ('Prise de courant 2P+T à puits 16A IP44 livré avec plaque carrée blanche Dooxie', ('Prises de courant', 'Complets')),
    ('LEGRAND Mosaic Bouton poussoir étroit blanc - 077030L', ('Poussoirs', 'Mécanismes')),
    ('LEGRAND Céliane - Mosaic Voyant témoin pour interrupteur - 067688', ('Voyants et balisage', 'Mécanismes')),
    ('Prise murale Mosaic', ('Prises de courant', 'Mécanismes')),
    ('LEGRAND Mosaic Cadre saillie double blanc P40 - 080285', ('Cadres saillie', 'Mécanismes')),
    ('LEGRAND Céliane Enjoliveur prise de courant blanc', ('Prises de courant', 'Enjoliveurs')),
])
def test_function_and_part(name, expected):
    assert (function(product(name)), part(product(name))) == expected


@pytest.mark.parametrize('name,label', [
    ('LEGRAND Dooxie Plaque simple blanc - 600801', '1 poste'),
    ('Plaque de finition ronde effet bois ébène avec bague noire brillante Legrand Dooxie', '1 poste'),
    ('Plaque Carrée 4 Postes Finition Noir Effet Velours Dooxie', '4 postes'),
    ('LEGRAND Mosaic Plaque double verticale blanc E57 - 078854L', '2 postes'),
    ('LEGRAND Mosaic Plaque horizontale 6 modules blanc - 078816L', '6 modules'),
    ('LEGRAND Mosaic Plaque horizontale 2x8 modules blanc - 078837L', '2×8 modules'),
    ('LEGRAND Mosaic Plaque horizontale 2x2 postes blanc - 078838L', '2×2 postes'),
])
def test_plates_by_size(name, label):
    assert function(product(name)) == 'Plaques de finition'
    assert plate_size(product(name))[1] == label


def test_ranges_classified_and_menu_built():
    assert family_of(product('LEGRAND Dooxie Prise TV blanc - 600351')) == 'dooxie-legrand'
    assert family_of(product('Interrupteur Variateur pour Ballast 1V à 10V Blanc Mosaïc')) == 'mosaic-legrand'
    # Plexo product listed in an Elec Distrib Dooxie category stays out of Dooxie.
    assert family_of(product('Double Prise de courant étanche 2P+T Plexo composable IP55')) != 'dooxie-legrand'
    app = QApplication.instance() or QApplication([])
    names = ['LEGRAND Dooxie Prise de courant 2P+T surface blanc', 'Prise de courant 2P+T à puits 16A livré avec plaque Dooxie',
             'LEGRAND Dooxie Plaque simple blanc', 'LEGRAND Dooxie Plaque double noir', 'LEGRAND Dooxie Plaque double blanc',
             'LEGRAND Dooxie Bouton poussoir blanc', 'LEGRAND Dooxie Griffe de fixation Rapido']
    button = FamilyButton()
    button.set_products([product(n, reference=str(600100 + i), id=i) for i, n in enumerate(names)])
    menu = button.menu()

    def tree(m):
        return {a.text(): tree(a.menu()) if a.menu() else a.data() for a in m.actions()}

    dooxie = tree(menu)['Appareillage']['Legrand (7)']['Dooxie (7)']
    assert list(dooxie) == ['Prises de courant (2)', 'Poussoirs (1)', 'Plaques de finition (3)', 'Accessoires et supports (1)']
    assert list(dooxie['Prises de courant (2)']) == ['Mécanismes (1)', 'Complets (1)']
    assert list(dooxie['Plaques de finition (3)']) == ['1 poste (1)', '2 postes (2)']
    assert list(dooxie['Poussoirs (1)']) == ['Bouton poussoir blanc · 600105']  # single part: no extra level


def test_celiane_specifics():
    from klmelec.discovery import FAMILIES
    import re
    assert re.fullmatch(FAMILIES['celiane-legrand'].sku_pattern, 'LEGCB0001').group(1) == 'CB0001'
    assert re.fullmatch(FAMILIES['celiane-legrand'].sku_pattern, 'LEG-068001').group(1) == '068001'
    cases = {
        'LEGRAND Céliane Enjoliveur simple allumage blanc - CB0001': ('Interrupteurs et va-et-vient', 'Enjoliveurs'),
        'LEGRAND Céliane Enjoliveur double lumineux noir - CN3001': ('Interrupteurs et va-et-vient', 'Enjoliveurs'),
        'LEGRAND Céliane Enjoliveur écodétecteur sans dérogation blanc': ('Détecteurs', 'Enjoliveurs'),
        'LEGRAND Céliane Ecovariateur 2 fils sans neutre - 067083A': ('Variateurs', 'Mécanismes'),
        'Enjoliveur pour Variateurs blanc Céliane': ('Variateurs', 'Enjoliveurs'),
        "Thermostat d'ambiance fil pilote 230V Céliane": ('Thermostats', 'Mécanismes'),
        "Prise d'aspiration centralisée sans contact livrée avec enjoliveur Blanc Céliane": ('Autres fonctions', 'Complets'),
        'Prise téléphonique T Céliane Blanc complète': ('Prises RJ45, TV, téléphone, HP', 'Complets'),
        "LEGRAND Céliane Liseuse d'éclairage avec flexible 230V titanium": ('Voyants et balisage', 'Mécanismes'),
    }
    for name, expected in cases.items():
        assert (function(product(name)), part(product(name))) == expected, name
    assert plate_size(product('LEGRAND Céliane Plaque 4 à 5 modules noir mat - CP0108'))[1] == '4 à 5 modules'
    assert plate_size(product('LEGRAND Céliane Plaque Memories 4/5 modules Yesterday blanc'))[1] == '4 à 5 modules'
    from klmelec.family_menu import families_of
    assert families_of(product('Support à vis 2 postes pour Céliane, Mosaic ou Soliroc')) == ['mosaic-legrand', 'celiane-legrand']
    assert families_of(product('Interrupteur Horaire Programmable Céliane 230V')) == ['horloges-legrand', 'celiane-legrand']


def test_long_lists_split_by_finish():
    from klmelec.fittings import finish
    assert finish(product('LEGRAND Céliane Plaque 4 à 5 modules verre onyx noir')) == 'Verre'
    assert finish(product('Plaque de finition simple carrée effet bois ébène avec bague noire')) == 'Bois'
    assert finish(product('LEGRAND Céliane Plaque métal 4/5 modules titane')) == 'Métal'
    assert finish(product('Plaque de finition double noir velours Dooxie')) == 'Noir et graphite'
    assert finish(product('LEGRAND Céliane Plaque 6 à 8 modules jaune safran')) == 'Couleurs et matières'
    app = QApplication.instance() or QApplication([])
    names = [f'LEGRAND Céliane Plaque 2 postes {colour}' for colour in
             ['blanc'] * 8 + ['titane'] * 6 + ['verre piano'] * 4 + ['noir'] * 3 + ['chêne', 'jaune safran']]
    button = FamilyButton()
    button.set_products([product(n, reference=f'CP{i:04d}', id=i) for i, n in enumerate(names)])
    plates = button.menu().actions()[0].menu().actions()[0].menu().actions()[0].menu().actions()[0].menu()
    # A single plate size: no size level, finishes directly.
    assert [a.text() for a in plates.actions()] == ['Blanc (8)', 'Noir et graphite (3)', 'Métal (6)', 'Bois (1)',
                                                   'Verre (4)', 'Couleurs et matières (1)']


@pytest.mark.parametrize('name,expected', [
    ('LEGRAND Plexo Prise de courant 2P+T saillie complet étanche gris IP55 - 069731L', ('Prises de courant', 'Complets')),
    ('LEGRAND Plexo Interrupteur va et vient à composer étanche anthracite IP55 - 069801L',
     ('Interrupteurs et va-et-vient', 'Mécanismes')),
    ('LEGRAND Plexo Bouton poussoir porte étiquette encastré complet étanche blanc IP55 - 069864L', ('Poussoirs', 'Complets')),
    ('LEGRAND Plexo Boite de dérivation étanche IP55 80x80x45 650°C gris - 092012', ('Boîtes de dérivation', 'Mécanismes')),
    ('LEGRAND Plexo Coffret électrique étanche nu 2 rangées de 18 modules IP65 - 001925', ('Coffrets étanches', 'Mécanismes')),
    ('LEGRAND Plexo Sortie de câble encastré complet étanche blanc IP55 - 069888L', ('Sorties de câble', 'Complets')),
])
def test_plexo_function_and_part(name, expected):
    p = product(name)
    assert family_of(p) == 'plexo-legrand'
    assert (function(p), part(p)) == expected


def test_plexo_grey_and_anthracite_finishes():
    from klmelec.fittings import finish
    assert finish(product('LEGRAND Plexo Bouton poussoir à composer étanche gris IP55 - 069540L')) == 'Gris et anthracite'
    assert finish(product('LEGRAND Plexo Bouton poussoir à composer étanche anthracite IP55 - 069810L')) == 'Gris et anthracite'
    assert finish(product('LEGRAND Céliane Plaque simple gris cendré - CP1001')) == 'Gris et anthracite'
    assert finish(product('LEGRAND Plexo Bouton poussoir à composer étanche blanc IP55 - 069630L')) == 'Blanc'


def test_niloe_range():
    frame = product('LEGRAND Niloé Cadre saillie double Blanc - 664799', reference='664799')
    socket = product('Prise TV/R/SAT Blanc Niloé Legrand Réf: 664763', reference='664763')
    assert family_of(frame) == family_of(socket) == 'niloe-legrand'
    assert function(socket) == 'Prises RJ45, TV, téléphone, HP'
    from klmelec.family_menu import short_name
    assert short_name(socket) == 'Prise TV/R/SAT Blanc'


@pytest.mark.parametrize('name,expected', [
    ('Interrupteur Va-et-Vient blanc Appareillage Saillie Complet Otéo Legrand Réf. 086001', ('Interrupteurs et va-et-vient', 'Complets')),
    ('Prise de courant 2P+T à bornes automatiques saillie composable blanc Otéo Legrand Réf. 086127', ('Prises de courant', 'Mécanismes')),
    ('LEGRAND Prise TV en saillie blanc - 086040', ('Prises RJ45, TV, téléphone, HP', 'Mécanismes')),
    ('Cadre Appareillage saillie 2 postes épaisseur 20mm pose le long des moulures DLPlus blanc Legrand Réf. 031418',
     ('Cadres saillie', 'Mécanismes')),
])
def test_surface_range(name, expected):
    p = product(name)
    assert family_of(p) == 'saillie-legrand'
    assert (function(p), part(p)) == expected


@pytest.mark.parametrize('name', [
    'LEGRAND Plexo Prise de courant 2P+T saillie complet étanche gris IP55 - 069731L',
    'LEGRAND Mosaic Cadre saillie double blanc P40 - 080285',
    "LEGRAND Green'up prise de courant 2P+T étanche complet saillie gris pour recharge véhicule électrique - 090471",
])
def test_surface_range_leaves_other_ranges(name):
    from klmelec.family_menu import families_of
    assert 'saillie-legrand' not in families_of(product(name))


def test_decimal_positions_are_not_whole_positions():
    assert plate_size(product('LEGRAND Mosaic Cadre saillie 1,5 postes ou 3 modules P40 blanc - 080289'))[1] == '3 modules'
    assert plate_size(product('Cadre saillie 3 postes blanc Appareillage saillie Otéo Legrand Réf. 086093'))[1] == '3 postes'
