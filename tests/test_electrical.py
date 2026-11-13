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
