import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from copy import deepcopy
import pytest
from PySide6.QtWidgets import QApplication
from klmelec.data import Store
from klmelec.electrical import empty_plan, circuits, evaluate
from klmelec.app import MainWindow


def row(**changes):
    return dict(dict(id='r1', name='Cuisine', rating=40, type='A', sensitivity=30), **changes)


def test_downstream_weighting_and_rating_boundary():
    result = evaluate(row(), [(20, 'Chauffe-eau'), (20, 'Prises'), (20, 'Éclairage')])
    assert result['status'] == 'Critères contrôlés satisfaits'
    assert '= 40 A' in result['formula']
    assert '40 A' in result['suggestion']
    result = evaluate(row(), [(32, 'Chauffage électrique'), (20, 'Prises')])
    assert result['status'] == 'À corriger'
    assert '63 A' in result['suggestion']


def test_upstream_alternative_and_circuit_limit():
    assigned = [(32, 'Chauffage électrique')] * 8
    assert evaluate(row(rating=63), assigned, 'amont', 60)['status'] == 'Critères contrôlés satisfaits'
    assert evaluate(row(), assigned, 'amont', 60)['status'] == 'À corriger'
    assert evaluate(row(rating=63), assigned, 'aval')['status'] == 'À corriger'
    assert evaluate(row(rating=63), assigned + [(2, 'Éclairage')], 'amont', 60)['status'] == 'À corriger'
    assert 'manquantes' in evaluate(row(), assigned, 'amont', 0)['status']


@pytest.mark.parametrize('changes,use,status', [
    ({'type': 'AC'}, 'Plaques de cuisson', 'À corriger'),
    ({'sensitivity': 300}, 'Prises', 'À corriger'),
    ({'type': 'À préciser'}, 'Prises', 'Données manquantes / à vérifier'),
    ({}, 'Recharge véhicule', 'Données manquantes / à vérifier'),
    ({}, 'Équipement à variateur', 'Données manquantes / à vérifier'),
    ({}, 'À préciser', 'Données manquantes / à vérifier'),
])
def test_missing_or_special_inputs_never_pass(changes, use, status):
    assert evaluate(row(**changes), [(20, use)])['status'] == status


def test_empty_or_unknown_usage_has_no_downstream_suggestion():
    assert not evaluate(row(), [])['suggestion']
    assert not evaluate(row(), [(32, 'À préciser')])['suggestion']


@pytest.fixture
def store(tmp_path):
    db = Store(tmp_path / 'electrical.sqlite3')
    product = next(p for p in db.products() if p['reference'] == '406774')
    db.add_item(product['id'], 3)
    yield db
    db.close()


def configured(store):
    plan = empty_plan()
    plan['rows'] = [row()]
    for (key, *_), use in zip(circuits(store.items()), ['Prises', 'Éclairage', 'Chauffage électrique']):
        plan['circuits'][key] = dict(row='r1', use=use)
    store.save_electrical_plan(plan)
    return plan


def test_json_roundtrip_and_legacy_list_reset(store, tmp_path):
    configured(store)
    payload = store.export_list()
    other = Store(tmp_path / 'other.sqlite3')
    other.import_list(payload)
    assert other.export_list() == payload
    other.close()
    legacy = deepcopy(payload)
    legacy.pop('electrical')
    store.import_list(legacy)
    assert store.electrical_plan() == empty_plan()


@pytest.mark.parametrize('bad', [None, [], {'method': []}, {'row': []}])
def test_invalid_plan_preserves_current_list(store, bad):
    configured(store)
    before = store.export_list()
    payload = deepcopy(before)
    if bad == {'row': []}:
        key = next(iter(payload['electrical']['circuits']))
        payload['electrical']['circuits'][key]['row'] = []
    else:
        payload['electrical'] = bad
    with pytest.raises(ValueError):
        store.import_list(payload)
    assert store.export_list() == before


def test_remove_exemplar_keeps_remaining_assignments(store):
    configured(store)
    product_id = store.items()[0]['id']
    store.remove_unit(product_id, 1)
    assert [v['use'] for v in store.electrical_plan()['circuits'].values()] == ['Prises', 'Chauffage électrique']
    store.set_quantity(product_id, 1)
    store.set_quantity(product_id, 3)
    assert len(store.electrical_plan()['circuits']) == 1
    store.remove_item(product_id)
    store.add_item(product_id, 3)
    assert not store.electrical_plan()['circuits']
    store.clear_list()
    assert store.electrical_plan() == empty_plan()


def test_ui_assignment_report_and_list_sync(store):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(store, 'test')
    page = window.electrical_page
    assert page.table.rowCount() == 3
    page.add_row()
    page.rating.setCurrentIndex(page.rating.findData(40))
    page.kind.setCurrentText('A')
    page.sensitivity.setCurrentIndex(page.sensitivity.findData(30))
    page.table.cellWidget(0, 2).setCurrentIndex(1)
    page.table.cellWidget(0, 3).setCurrentText('Prises')
    assert 'Critères contrôlés satisfaits' in page.report.toPlainText()
    assert len(store.export_list()['electrical']['circuits']) == 1
    page.method.setCurrentIndex(1)
    page.upstream.setValue(60)
    assert 'À corriger' in page.report.toPlainText()
    page.remove_row()
    assert not store.electrical_plan()['rows']
    assert next(iter(store.electrical_plan()['circuits'].values()))['row'] is None
    store.clear_list()
    window.material_model.refresh()
    assert page.table.rowCount() == 0
    assert not page.plan['rows']
    window.close()
    app.processEvents()


@pytest.mark.parametrize('name,expected', [
    ('LEGRAND DNX3 Disjoncteur 16A auto PH+N courbe C 4.5kA 230V - 406783', (dict(amps=16, curve='C'), None)),
    ('LEGRAND DNX3 Disjoncteur 20A Ph+N courbe D 6kA 230V - 406803', (dict(amps=20, curve='D'), None)),
    ('Disjoncteur DX³ 6000 10kA arrivée haute et départ bas vis U+N 230V~ - 40A courbe C Legrand Réf: 407704',
     (dict(amps=40, curve='C'), None)),
    ('Disjoncteur Phase+Neutre DNX ³4500 6kA - 25A courbe C - auto/vis 1P+N 230V~ 1 module Legrand Réf. 406785',
     (dict(amps=25, curve='C'), None)),
    # « 230 à 400V » must not be read as a 230 A rating.
    ('Disjoncteur 2A DX3 6000 10kA vis / vis 2 pôles 230 à 400V~ courbe C Legrand Réf: 407777',
     (dict(amps=2, curve='C'), None)),
    ('Disjoncteur DX³ 6000 10kA 2P 230V 16A', (dict(amps=16, curve=None), None)),
    ('Disjoncteur Différentiel U+N 16A 30mA Type F DX3 Legrand Réf. 410753',
     (None, 'disjoncteur différentiel : protection différentielle intégrée, hors rangée')),
    ('LEGRAND DX3 Disjoncteur tétrapolaire 16A courbe C 6kA 400V - 406910',
     (None, 'disjoncteur triphasé : hors logement monophasé')),
    ('Disjoncteur DX³6000 10kA - 40A Courbe C - 4P 400V~ Legrand Réf. 407932',
     (None, 'disjoncteur triphasé : hors logement monophasé')),
    ('LEGRAND Disjoncteur d\'abonné monophasé 45A 500mA différentiel sélectif - 401003',
     (None, 'disjoncteur différentiel : protection différentielle intégrée, hors rangée')),
    ('Disjoncteur 6A courbe C arrivée et sortie borne automatique 4500 - 6kA Legrand Réf: 406781',
     (None, 'pôles non indiqués dans la désignation')),
    ('Disjoncteur U+N 10A ou 16A', (None, 'calibre non identifié dans la désignation')),
    ('LEGRAND Drivia Tableau électrique pré-câblé auto 2 rangées 1ID 40A 8 disjoncteurs - 200882', (None, None)),
    ('Différentiel 40A type A', (None, None)),
])
def test_breakers_recognized_from_designation(name, expected):
    from klmelec.electrical import classify
    assert classify(dict(brand='Legrand', reference='999999', name=name, quantity=1)) == expected


def test_reference_override_and_other_brands():
    from klmelec.electrical import classify
    assert classify(dict(brand='Legrand', reference='406774', name='Disjoncteur 16A'))[0] == dict(amps=16, curve='C')
    assert classify(dict(brand='Hager', reference='MFN716', name='Disjoncteur Ph+N 16A courbe C')) == (None, None)


def test_curve_d_or_unknown_needs_checking():
    assigned = [(16, 'Prises', 'C'), (20, 'Lave-linge', 'D')]
    result = evaluate(row(), assigned)
    assert result['status'] == 'Données manquantes / à vérifier'
    assert any('courbe D' in detail for detail in result['details'])
    assert evaluate(row(), [(16, 'Prises', 'C')])['status'] == 'Critères contrôlés satisfaits'
    assert any('Courbe' in d for d in evaluate(row(), [(16, 'Prises', None)])['details'])


def add_discovered(db, reference, name):
    db.db.execute('INSERT INTO products(name,brand,reference) VALUES (?,?,?)', (name, 'Legrand', reference))
    product = next(p for p in db.products() if p['reference'] == reference)
    return product['id']


def test_discovered_breakers_in_ui_and_saved_list(store, tmp_path):
    app = QApplication.instance() or QApplication([])
    db_id = add_discovered(store, '406803', 'LEGRAND DNX3 Disjoncteur 20A Ph+N courbe D 6kA 230V - 406803')
    dd_id = add_discovered(store, '410753', 'Disjoncteur Différentiel U+N 16A 30mA Type F DX3 Legrand Réf. 410753')
    store.add_item(db_id, 1)
    store.add_item(dd_id, 1)
    window = MainWindow(store, 'test')
    page = window.electrical_page
    assert page.table.rowCount() == 4  # 3 × 406774 + 1 × 406803
    texts = [page.table.item(i, 1).text() for i in range(page.table.rowCount())]
    assert '20 A · courbe D' in texts and '16 A · courbe C' in texts
    assert '410753 non évalué : disjoncteur différentiel' in page.coverage.text()
    page.add_row()
    index = next(i for i in range(4) if page.table.item(i, 0).text().startswith('406803'))
    page.table.cellWidget(index, 2).setCurrentIndex(1)
    page.table.cellWidget(index, 3).setCurrentText('Lave-linge')
    assert 'courbe D' in page.report.toPlainText()
    # A saved list with a discovered breaker reloads with its assignment.
    payload = store.export_list()
    other = Store(tmp_path / 'other.sqlite3')
    add_discovered(other, '406803', 'LEGRAND DNX3 Disjoncteur 20A Ph+N courbe D 6kA 230V - 406803')
    add_discovered(other, '410753', 'Disjoncteur Différentiel U+N 16A 30mA Type F DX3 Legrand Réf. 410753')
    other.import_list(payload)
    assert other.export_list()['electrical'] == payload['electrical']
    other.close()
    window.close()


@pytest.mark.parametrize('reference,name,expected', [
    ('411591', 'Interrupteur Différentiel DX³-ID Arrivée haute et départ bas à vis 2P 230V 40A Type F 30mA 2 modules',
     dict(rating=40, type='F', sensitivity=30)),
    ('411525', 'Interrupteur différentiel DX³-ID 40A TypeAC 300mA - 2 modules - 2P 230V~', dict(rating=40, type='AC', sensitivity=300)),
    ('411644', 'LEGRAND DX3 Interrupteur différentiel 40A 30MA type HPI auto 230V - 411644', dict(rating=40, type='A', sensitivity=30)),
    ('411631', 'Interrupteur différentiel DX³ 25A type AC Legrand Réf: 411631', dict(rating=25, type='AC', sensitivity=0)),
    ('411506', 'Interrupteur différentiel 63A Legrand Réf. 411506', dict(rating=63, type='À préciser', sensitivity=0)),
    ('411633', 'inter diff 63A', dict(rating=63, type='AC', sensitivity=30)),
    ('411662', 'LEGRAND DX3 Interrupteur différentiel tétrapolaire 63A 30mA type AC 4 modules 400V - 411662', None),
    ('411658', 'Interrupteur Différentiel 4P 40A 30mA Type F DX3 Legrand Réf. 411658', None),
    ('410754', 'Disjoncteur différentiel U+N 230V~ - 20A TypeF 30mA - courbe C', None),
])
def test_differential_read_from_designation(reference, name, expected):
    from klmelec.electrical import differential
    assert differential(dict(brand='Legrand', reference=reference, name=name)) == expected
    assert differential(dict(brand='Hager', reference=reference, name=name)) is None


def test_row_prefilled_from_listed_differential(store):
    app = QApplication.instance() or QApplication([])
    store.add_item(add_discovered(store, '411591', 'Interrupteur Différentiel 2P 230V 40A Type F 30mA'), 1)
    store.add_item(add_discovered(store, '411526', 'Interrupteur Différentiel 2P 63A DX3 Legrand Réf. 411526'), 1)
    window = MainWindow(store, 'test')
    page = window.electrical_page
    assert not page.device.isEnabled()  # no row yet
    page.add_row()
    labels = [page.device.itemText(i) for i in range(1, page.device.count())]
    assert [label.split(' — ')[0] for label in labels] == ['411591', '411526']
    page.device.activated.emit(1)
    saved = store.electrical_plan()['rows'][0]
    assert (saved['rating'], saved['type'], saved['sensitivity']) == (40, 'F', 30)
    assert (page.rating.currentData(), page.kind.currentText(), page.sensitivity.currentData()) == (40, 'F', 30)
    assert page.device.currentIndex() == 0
    page.device.activated.emit(2)
    assert (page.rating.currentData(), page.kind.currentText(), page.sensitivity.currentData()) == (63, 'À préciser', 0)
    assert 'type, sensibilité' in page.device_note.text()
    window.close()
    app.processEvents()
