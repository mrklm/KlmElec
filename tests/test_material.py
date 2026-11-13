import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtTest import QAbstractItemModelTester
from PySide6.QtWidgets import QApplication

from klmelec.app import MainWindow
from klmelec.comparison import now
from klmelec.data import Store
from klmelec.material import MaterialModel, BEST_PRICE_ROLE


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def store(tmp_path):
    db = Store(tmp_path/'data.sqlite3')
    yield db
    db.close()


def test_six_units_assign_together_and_individually(store, app):
    pid = store.products()[0]['id']
    garage = store.add_location('Garage')
    bedroom = store.add_location('Chambre #1')
    store.add_item(pid, 6)
    model = MaterialModel(store)
    tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)
    root = model.index(0, 0)
    assert model.rowCount(root) == 6
    assert model.parent(model.index(3, 4, root)) == root
    assert model.rowCount(model.index(0, 1)) == 0
    assert model.setData(model.index(0, 4), garage)
    assert all(model.index(i, 4, root).data() == 'Garage' for i in range(6))
    assert model.setData(model.index(2, 4, root), bedroom)
    assert model.index(0, 4).data() == 'Lieux multiples'
    assert model.index(2, 4, root).data() == 'Chambre #1'
    assert not model.flags(model.index(0, 3, root)) & Qt.ItemIsEditable
    assert model.setData(model.index(0, 4), None)
    assert model.index(0, 4).data() == 'Non affecté'
    assert not store.assignments()


def test_one_by_one_merges_and_reduction_preserves_remaining(tmp_path):
    path = tmp_path/'places.sqlite3'
    db = Store(path)
    pid = db.products()[0]['id']
    places = [db.add_location(name) for name in ('Garage', 'Couloir', 'Chambre #1', 'Salon', 'Grenier')]
    for place in places:
        db.add_item(pid, 1, place)
    assert len(db.items()) == 1 and db.items()[0]['quantity'] == 5
    db.remove_unit(pid, 1)
    assert [db.assignments()[pid,i] for i in range(4)] == [places[0], *places[2:]]
    db.set_quantity(pid, 2)
    assert db.assignments() == {(pid,0):places[0], (pid,1):places[2]}
    db.set_quantity(pid, 3)
    assert (pid,2) not in db.assignments()
    db.close()
    db = Store(path)
    assert db.items()[0]['quantity'] == 3
    assert db.assignments() == {(pid,0):places[0], (pid,1):places[2]}
    db.remove_item(pid)
    assert not db.assignments()
    db.add_item(pid, 1)
    assert not db.assignments()
    db.close()


def offers(model, prices=('42.90','40.00')):
    return [dict(product_id=model.rows[0]['id'], supplier_id=s['id'], supplier=s['name'],
                 status='ok', ttc=price, checked_at=now(), url='https://example.org',
                 detail='En stock', cached=False)
            for s,price in zip(model.suppliers, prices)]


def test_supplier_columns_ties_failures_and_age(store, app):
    store.add_item(store.products()[0]['id'], 2)
    model = MaterialModel(store)
    assert model.columnCount() == 9
    model.offers = offers(model)
    assert model.index(0,5).data() == '42,90 €'
    assert not model.index(0,5).data(BEST_PRICE_ROLE)
    assert model.index(0,6).data(BEST_PRICE_ROLE)
    assert model.index(0,8).data() == '80,00 €'
    assert model.index(0,5,model.index(0,0)).data() is None
    model.offers = offers(model, ('40.00','40.00'))
    assert all(model.index(0,c).data(BEST_PRICE_ROLE) for c in (5,6))
    model.offers[0]['status'] = 'error'
    model.offers[0]['ttc'] = None
    model.offers[0]['detail'] = 'Erreur réseau'
    assert model.index(0,5).data() == 'Erreur réseau'
    assert not model.index(0,6).data(BEST_PRICE_ROLE)
    model.offers = offers(model)
    model.offers[0]['checked_at'] = (datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat()
    assert 'ancien' in model.index(0,5).data()
    assert not model.index(0,6).data(BEST_PRICE_ROLE)
    model.offers = offers(model)
    store.save_supplier('Troisième', 'https://example.org')
    model.refresh()
    assert model.columnCount() == 10
    assert not any(model.index(0,c).data(BEST_PRICE_ROLE) for c in (5,6,7))
    third = next(s for s in store.suppliers() if s['name']=='Troisième')
    store.save_supplier(third['name'],third['url'],False,third['id'])
    model.refresh()
    assert model.columnCount() == 9


def test_locations_ui_and_tree_expansion(store, app):
    window = MainWindow(store, 'test')
    window.place_name.setText('Chambre #2')
    window.add_location()
    new_id = window.add_place.currentData()
    assert new_id == store.add_location('  CHAMBRE #2 ')
    window.search.setCurrentIndex(0)
    window.quantity.setValue(2)
    window.add_item()
    model = window.material_model
    assert model.index(0,4).data() == 'Chambre #2'
    window.material_table.expand(model.index(0,0))
    window.quantity.setValue(1)
    window.add_place.setCurrentIndex(0)
    window.add_item()
    assert model.rowCount(model.index(0,0)) == 3
    assert model.index(0,4).data() == 'Lieux multiples'
    assert window.material_table.isExpanded(model.index(0,0))
    child = model.index(0,0,model.index(0,0))
    window.material_table.setCurrentIndex(child)
    window.remove_item()
    assert model.rows[0]['quantity'] == 2
    assert model.index(0,4,model.index(0,0)).data() == 'Chambre #2'
    window.close()


def test_manual_offer_updates_frame_and_totals(store, app):
    store.add_item(store.products()[0]['id'], 3)
    window = MainWindow(store, 'test')
    model = window.material_model
    model.offers = offers(model, ('7.50', '6.85'))
    model.offers[0]['cached'] = True
    model.refresh_prices()
    assert window.total_label.text() == 'Total TTC\n20,55 €'
    assert model.index(0, 5).data() == '7,50 €'
    assert model.select_offer(model.index(0, 5))
    assert model.index(0, 5).data(BEST_PRICE_ROLE)
    assert not model.index(0, 6).data(BEST_PRICE_ROLE)
    assert model.index(0, 8).data() == '22,50 €'
    assert model.index(0, 7).data() == '18,75 €'
    assert window.total_label.text() == 'Total TTC\n22,50 €'
    assert '22,50' in window.summary.text()
    model.setData(model.index(0, 3), 4)
    assert window.total_label.text() == 'Total TTC\n30,00 €'
    # A moved supplier column still selects its logical supplier.
    header = window.material_table.header()
    assert header.sectionsMovable() and header.isFirstSectionMovable()
    header.moveSection(header.visualIndex(5), 7)
    assert header.logicalIndex(7) == 5
    header.resizeSection(5, 220)
    window.material_table.clicked.emit(model.index(0, 6))
    assert window.total_label.text() == 'Total TTC\n27,40 €'
    model.refresh()
    assert header.sectionSize(5) == 220
    assert header.visualIndex(5) == 7
    window.invalidate_comparison()
    assert not model.selected_suppliers
    assert window.total_label.text() == 'Total TTC\nIncomplet'
    window.close()


def test_manual_choice_rejects_invalid_offers_and_counts_ties_once(store, app):
    store.add_item(store.products()[0]['id'], 2)
    window = MainWindow(store, 'test')
    model = window.material_model
    model.offers = offers(model, ('10.00', '10.00'))
    model.refresh_prices()
    assert window.total_label.text() == 'Total TTC\n20,00 €'
    assert all(model.index(0, col).data(BEST_PRICE_ROLE) for col in (5, 6))
    assert model.select_offer(model.index(0, 5))
    assert not model.index(0, 6).data(BEST_PRICE_ROLE)
    assert not model.select_offer(model.index(0, 5, model.index(0, 0)))
    assert not model.select_offer(model.index(0, 3))
    model.offers[1]['status'] = 'error'
    assert not model.select_offer(model.index(0, 6))
    # Explicit choice stays usable even if the other supplier failed.
    assert model.selected_offer(model.rows[0]) == model.offers[0]
    model.offers[0]['checked_at'] = (datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat()
    model.refresh_prices()
    assert not model.select_offer(model.index(0, 5))
    assert not model.index(0, 5).data(BEST_PRICE_ROLE)
    assert window.total_label.text() == 'Total TTC\nIncomplet'
    store.clear_list()
    model.refresh()
    assert window.total_label.text() == 'Total TTC\n0,00 €'
    window.close()


def test_compact_columns_and_click_without_row_highlight(store, app):
    from PySide6.QtTest import QTest

    product = next(p for p in store.products() if p['reference'] == '406774')
    store.add_item(product['id'], 2)
    window = MainWindow(store, 'test')
    window.resize(1200, 700)
    model = window.material_model
    model.offers = offers(model, ('7.50', '6.85'))
    model.refresh_prices()
    window.show()
    app.processEvents()
    table = window.material_table
    assert table.header().length() <= table.viewport().width()
    index = model.index(0, 5)
    QTest.mouseClick(table.viewport(), Qt.LeftButton, pos=table.visualRect(index).center())
    assert table.currentIndex().row() == 0
    assert not table.selectionModel().selectedIndexes()
    assert model.index(0, 5).data(BEST_PRICE_ROLE)
    assert window.total_label.text() == 'Total TTC\n15,00 €'
    table.setColumnWidth(0, 230)
    model.refresh_prices()
    assert table.columnWidth(0) == 230
    window.remove.click()
    assert not store.items()
    window.close()


def test_old_database_gets_unassigned_units_without_changing_history(tmp_path):
    import sqlite3
    path = tmp_path/'old.sqlite3'
    db = sqlite3.connect(path)
    db.executescript('''
        CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT,brand TEXT,reference TEXT,UNIQUE(brand,reference));
        CREATE TABLE items(product_id INTEGER PRIMARY KEY REFERENCES products(id),quantity INTEGER);
        INSERT INTO products VALUES (42,'Personnel','Marque','REF');
        INSERT INTO items VALUES (42,6);
    ''')
    db.close()
    for _ in range(2):
        store = Store(path)
        assert store.items()[0]['id'] == 42
        assert store.items()[0]['quantity'] == 6
        assert len(store.locations()) == 10
        assert not store.assignments()
        store.close()
