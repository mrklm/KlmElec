import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from klmelec.app import MainWindow
from klmelec.data import Store
from klmelec.family_menu import family_of, grouped


def product(name, brand='Legrand', reference='999999', id=1):
    return dict(id=id, name=name, brand=brand, reference=reference)


def test_products_classified_like_the_catalogue_search():
    assert family_of(product('LEGRAND DNX3 Disjoncteur 16A auto PH+N courbe C - 406783')) == 'disjoncteurs-legrand'
    assert family_of(product('inter diff 63A')) == 'differentiels-legrand'
    assert family_of(product('Telerupteur 16A')) == 'telerupteurs-legrand'
    assert family_of(product('LEGRAND Drivia Tableau électrique nu 2 rangées 13 modules')) == 'coffrets-drivia-legrand'
    assert family_of(product('LEGRAND Drivia Porte blanche pour tableau électrique 2 rangées')) == 'portes-drivia-legrand'
    # Complementary families: an enclosure "with patch panel" is not a module.
    assert family_of(product('Coffret de communication basique avec brassage')) == 'coffrets-communication-legrand'
    assert family_of(product('Module de brassage RJ45 pour réseau multimédia')) == 'modules-communication-legrand'
    assert family_of(product('Disjoncteur 16A', brand='Hager')) == 'disjoncteurs-hager'
    assert family_of(product('Disjoncteur 16A', brand='ABB')) is None
    assert family_of(product('Borne Wago 6mm2 Gris', brand='Wago')) == 'wago'
    families, others = grouped([product('Peigne 13u'), product('Embouts isolants', brand='IKEPE')])
    assert list(families) == ['peignes-legrand'] and list(others) == ['IKEPE']


def menu_tree(menu):
    return {action.text(): menu_tree(action.menu()) if action.menu() else action.data()
            for action in menu.actions()}


def test_family_button_adds_clicked_product(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = Store(tmp_path / 'db.sqlite3')
    window = MainWindow(store, 'test')
    tree = menu_tree(window.family_button.menu())
    assert list(tree) == ['Protection', 'Commande', 'Répartition', 'Boîtes et connexion', 'Appareillage',
                          'Autres articles']
    assert list(tree['Boîtes et connexion']) == ['Boîtes (encastrement, DCL, dérivation) (1)', 'Bornes de connexion (4)']
    assert list(tree['Boîtes et connexion']['Bornes de connexion (4)']) == ['Wago (4)']
    assert list(tree['Commande']) == ['Télérupteurs (1)']
    assert list(tree['Commande']['Télérupteurs (1)']) == ['Legrand (1)']
    assert list(tree['Appareillage']) == ['Legrand (3)']
    assert list(tree['Appareillage']['Legrand (3)']) == ['Mosaic (3)']
    assert set(tree['Appareillage']['Legrand (3)']['Mosaic (3)']) == {
        'Prises de courant (1)', 'Interrupteurs et va-et-vient (1)', 'Accessoires et supports (1)'}
    assert list(tree['Protection']) == ['Disjoncteurs (5)', 'Interrupteurs différentiels (4)']
    assert list(tree['Protection']['Disjoncteurs (5)']) == ['Legrand (5)']
    assert 'Wago (4)' not in tree['Autres articles']
    # Bundled references: verified variants (DNX³ Ph+N curve C, differentials 411611/411617/411633/411638).
    breakers = tree['Protection']['Disjoncteurs (5)']['Legrand (5)']['Monophasés / bipolaires (5)']
    assert list(breakers) == ['2 A (1)', '10 A (1)', '16 A (1)', '20 A (1)', '32 A (1)']
    product_id = breakers['16 A (1)']['Ph+N · courbe C · 6 kA · vis · DNX³ · 406774']
    rcds = tree['Protection']['Interrupteurs différentiels (4)']['Legrand (4)']
    assert rcds == {'Type AC (2)': {'40 A (1)': {'30 mA · 2P · vis · 411611': rcds['Type AC (2)']['40 A (1)']['30 mA · 2P · vis · 411611']},
                                    '63 A (1)': {'30 mA · 2P · auto · 411633': rcds['Type AC (2)']['63 A (1)']['30 mA · 2P · auto · 411633']}},
                    'Type A (2)': {'40 A (2)': rcds['Type A (2)']['40 A (2)']}}
    assert list(rcds['Type A (2)']['40 A (2)']) == ['30 mA · 2P · auto/vis · 411638', '30 mA · 2P · vis · 411617']
    window.quantity.setValue(3)
    menus = [window.family_button.menu()]
    while menus:
        menu = menus.pop()
        for action in menu.actions():
            if action.menu():
                menus.append(action.menu())
            elif action.data() == product_id:
                action.trigger()
    assert [(row['reference'], row['quantity']) for row in store.items()] == [('406774', 3)]
    assert window.search.maximumWidth() == 380
    window.close()
    app.processEvents()
    store.close()


def test_breaker_and_rcd_variants_from_designation():
    from klmelec.variants import breaker, breaker_label, residual, residual_label
    p = product('LEGRAND DNX3 Disjoncteur 16A auto PH+N courbe C 4.5kA 230V - 406783', reference='406783')
    assert breaker(p) == dict(poles='Ph+N', amps=16, curve='C', breaking='4,5 kA', connection='auto', range='DNX³')
    assert breaker_label(product('Disjoncteur DX³ 6000 10kA arrivée haute et départ bas à vis 2 pôles 230 à 400V~ 20A Courbe C')) == \
        '2P · courbe C · 10 kA · vis · DX³'
    assert breaker_label(product('Disjoncteur tétrapolaire 4P 20A courbe C 6kA 10kA DX3')) == '4P · courbe C · 6 / 10 kA · DX³'
    assert breaker_label(product('Disjoncteur DNX³ 4500 automatique/vis - tripolaire 400V~ 16A Courbe C')) == \
        '3P · courbe C · 4,5 kA · auto/vis · DNX³'
    assert breaker_label(product('Disjoncteur 6A arrivée et sortie borne automatique')) == 'courbe non indiquée · auto'
    assert breaker_label(product('Disjoncteur Différentiel U+N 16A 30mA Type F DX3')) == 'Ph+N · 30 mA · type F · DX³'
    assert breaker_label(product("Disjoncteur d'abonné monophasé 45A 500mA différentiel sélectif")) == '500 mA · sélectif'
    r = product('Interrupteur différentiel DX³-ID 40A TypeAC 300mA - 2 modules - 2P 230V~ à vis')
    assert residual(r) == dict(type='AC', sensitivity=300, amps=40, poles='2P', connection='vis')
    assert residual(product('LEGRAND DX3 Interrupteur différentiel 40A 30MA type HPI auto 230V'))['type'] == 'Hpi'
    assert residual_label(product('Interrupteur différentiel tétrapolaire 63A 30mA type F')) == '30 mA · 4P'
    assert residual_label(product('Interrupteur différentiel DX³ 25A type A')) == 'sensibilité non indiquée · 2P · DX³'


def test_breaker_and_rcd_menus_split_by_kind_then_rating():
    from klmelec.family_menu import FamilyButton, short_name
    app = QApplication.instance() or QApplication([])
    assert short_name(product('LEGRAND DNX3 Disjoncteur 16A auto PH+N courbe C - 406783', reference='406783')) == \
        'DNX3 Disjoncteur 16A auto PH+N courbe C'
    assert short_name(product('Bornier répartition neutre Legrand Réf: 004850', reference='004850')) == \
        'Bornier répartition neutre'
    names = ['Disjoncteur Ph+N 32A courbe C', 'Disjoncteur Ph+N 2A courbe D', 'Disjoncteur Ph+N 2A courbe C',
             'Disjoncteur tétrapolaire 16A courbe C', 'Disjoncteur différentiel U+N 16A 30mA type A',
             "Disjoncteur d'abonné monophasé 45A 500mA différentiel sélectif", 'Disjoncteur Ph+N courbe C',
             'Interrupteur différentiel 40A 30mA type A', 'Interrupteur différentiel 63A 30mA type B',
             'Interrupteur différentiel 40A 30mA type AC', 'Interrupteur différentiel 63A 300mA']
    button = FamilyButton()
    others = [product('Disjoncteur 1P+N 16A courbe C iC60N', brand='Schneider Electric', reference='A9F77616', id=50),
              product('Disjoncteur 1P+N 10A courbe C', brand='Hager', reference='MFN710', id=51)]
    button.set_products([product(n, reference=str(400000 + i), id=i) for i, n in enumerate(names)] + others)
    tree = menu_tree(button.menu())['Protection']
    assert list(tree) == ['Disjoncteurs (9)', 'Interrupteurs différentiels (4)']
    assert list(tree['Disjoncteurs (9)']) == ['Legrand (7)', 'Schneider (1)', 'Hager (1)']
    assert list(tree['Interrupteurs différentiels (4)']) == ['Legrand (4)']
    tree = {'Disjoncteurs Legrand (7)': tree['Disjoncteurs (9)']['Legrand (7)'],
            'Interrupteurs différentiels Legrand (4)': tree['Interrupteurs différentiels (4)']['Legrand (4)']}
    breakers = tree['Disjoncteurs Legrand (7)']
    assert list(breakers) == ['Disjoncteurs de branchement (1)', 'Disjoncteurs différentiels (1)',
                              'Monophasés / bipolaires (4)', 'Tétrapolaires / triphasés (1)']
    mono = breakers['Monophasés / bipolaires (4)']
    assert list(mono) == ['2 A (2)', '32 A (1)', 'Calibre non indiqué (1)']
    assert list(mono['2 A (2)']) == ['Ph+N · courbe C · 400002', 'Ph+N · courbe D · 400001']
    assert list(breakers['Disjoncteurs différentiels (1)']['16 A (1)']) == ['Ph+N · 30 mA · type A · 400004']
    rcds = tree['Interrupteurs différentiels Legrand (4)']
    assert list(rcds) == ['Type AC (1)', 'Type A (1)', 'Type B (1)', 'Type non indiqué (1)']
    assert list(rcds['Type non indiqué (1)']['63 A (1)']) == ['300 mA · 2P · 400010']


def test_yokis_menu_split_by_function():
    from klmelec.family_menu import FamilyButton, short_name
    app = QApplication.instance() or QApplication([])
    names = [('YOKIS Télérupteur 2.2A 500VA micro-module encastré - MTR500E', 'MTR500E'),
             ('YOKIS UP Kit radio va et vient 1 télérupteur et 2 émetteurs radio - KITVV-UP', 'KITVV-UP'),
             ('YOKIS Power Micromodule radio volet roulant 2A 250VA encastré - MVR500ERP', 'MVR500ERP'),
             ('YOKIS UP Emetteur encastré 2 canaux Zigbee - E2BP-UP', 'E2BP-UP'),
             ('YOKIS Diode pour centralisation des micromodules - D600V', 'D600V')]
    products = [product(n, brand='Yokis', reference=r, id=i) for i, (n, r) in enumerate(names)]
    assert family_of(products[0]) == 'yokis'
    assert short_name(products[0]) == 'Télérupteur 2.2A 500VA micro-module encastré'
    button = FamilyButton()
    button.set_products(products * 5)  # au-delà de 20 articles : découpage par fonction
    tree = menu_tree(button.menu())
    assert list(tree) == ['Domotique']
    assert list(tree['Domotique']['Yokis (25)']) == [
        'Kits radio (5)', 'Volets roulants (5)', 'Télérupteurs (5)', 'Émetteurs (5)', 'Passerelles et accessoires (5)']


def test_legrand_boxes_menu_split_by_use():
    from klmelec.family_menu import FamilyButton
    app = QApplication.instance() or QApplication([])
    names = ['LEGRAND Batibox Boite encastrement simple pour cloison sèche D67 P40',
             'LEGRAND EcoBatibox Boite encastrement simple étanche à l\'air D67 P40',
             'LEGRAND Batibox Boite encastrement simple à sceller P40',
             'LEGRAND Batibox Boite de dérivation placo® 115x115x40',
             'LEGRAND Batibox Point de centre DCL D67 P50',
             'LEGRAND Batibox Support simple pour fixation à vis',
             'LEGRAND Batibox Couvercle universel pour boite encastrement simple']
    button = FamilyButton()
    button.set_products([product(n, reference=str(80000 + i), id=i) for i, n in enumerate(names * 3)])
    boxes = menu_tree(button.menu())['Boîtes et connexion']['Boîtes (encastrement, DCL, dérivation) (21)']['Legrand (21)']
    assert list(boxes) == ['Encastrement cloison sèche (3)', 'Encastrement à sceller (3)',
                           'Encastrement étanche à l’air (Ecobatibox) (3)', 'Boîtes de dérivation (3)', 'DCL (3)',
                           'Supports (3)', 'Couvercles et accessoires (3)']


def test_schneider_and_hager_variants():
    from klmelec.variants import breaker_label, residual_kind, residual_label
    assert residual_kind(product('Interrupteur différentiel 2P 40A 30mA A à bornes décalées SanVis Hager', brand='Hager')) == 'Type A'
    assert residual_label(product('Interrupteur différentiel 2P 40A 30mA A à bornes décalées SanVis Hager', brand='Hager')) == \
        '30 mA · 2P · auto'
    fsi = product('SCHNEIDER Resi9 XE Interrupteur différentiel 63A 30mA type Fsi auto 230V - R9ERF263',
                  brand='Schneider Electric', reference='R9ERF263')
    assert residual_kind(fsi) == 'Type F' and residual_label(fsi) == '30 mA · SI · 2P · auto · Resi9 XE'
    assert breaker_label(product('SCHNEIDER Acti9 iDT40T Disjoncteur 10A 3P+N courbe C 6kA 400V - A9P22710')) == \
        '3P+N · courbe C · 6 kA · iDT40'
    assert breaker_label(product('Disjoncteur Différentiel Acti9 iDD40T 1P+N 10A Courbe C 4500A/6kA 30mA Type A-SI')) == \
        'Ph+N · courbe C · 30 mA · type A SI · 6 kA · iDD40'
    from klmelec.family_menu import short_name
    assert short_name(fsi) == 'Resi9 XE Interrupteur différentiel 63A 30mA type Fsi auto 230V'
