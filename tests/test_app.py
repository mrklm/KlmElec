import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from klmelec.data import Store, matches
from klmelec.app import MainWindow


@pytest.fixture
def store(tmp_path):
    db = Store(tmp_path / 'test.sqlite3')
    yield db
    db.close()


@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])


def test_search():
    assert matches('DISJ 16', 'Disjoncteur 16A · Legrand · 406774')
    assert matches('diff inter', 'Interrupteur différentiel')
    assert matches('differentiel', 'Différentiel')
    assert not matches('disj 20', 'Disjoncteur 16A')


def test_list_roundtrip(tmp_path):
    path = tmp_path / 'test.sqlite3'
    db = Store(path)
    product_id = db.products()[0]['id']
    db.add_item(product_id, 2)
    db.add_item(product_id, 3)
    assert len(db.items()) == 1
    assert db.items()[0]['quantity'] == 5
    for quantity in (0, -1, 1.5, 100000):
        with pytest.raises(ValueError):
            db.set_quantity(product_id, quantity)
    with pytest.raises(ValueError):
        db.add_item(product_id, 99999)
    assert db.items()[0]['quantity'] == 5
    db.set_quantity(product_id, 7)
    db.close()
    db = Store(path)
    assert db.items()[0]['quantity'] == 7
    db.remove_item(product_id)
    assert not db.items()
    db.close()


def test_supplier_lifecycle(tmp_path):
    path = tmp_path / 'test.sqlite3'
    db = Store(path)
    assert len(db.suppliers()) == 2
    db.save_supplier('Nouveau', 'https://example.org', False)
    supplier = next(s for s in db.suppliers() if s['name'] == 'Nouveau')
    assert not supplier['active']
    assert supplier['connector'] is None
    db.save_supplier('Modifié', 'https://example.org/catalogue', True, supplier['id'])
    db.archive_supplier(supplier['id'])
    original = db.suppliers()[0]
    db.save_supplier(original['name'], 'https://example.net', True, original['id'])
    assert next(s for s in db.suppliers() if s['id'] == original['id'])['connector'] is None
    for s in db.suppliers():
        db.archive_supplier(s['id'])
    db.close()
    db = Store(path)
    assert not db.suppliers()  # Initial suppliers must not reappear after removal.
    assert db.db.execute('SELECT count(*) FROM suppliers').fetchone()[0] == 3
    db.close()


@pytest.mark.parametrize('url', ['example.org','file:///tmp/data','https://','https://user:secret@example.org'])
def test_invalid_supplier(store, url):
    with pytest.raises(ValueError):
        store.save_supplier('Test', url)


def test_window_workflow(app, store, monkeypatch):
    window = MainWindow(store, 'test')
    window.show()
    app.processEvents()
    window.filter_products('disj 16')
    suggestions = window.suggestions.stringList()
    assert len(suggestions) == 1
    window.search.setEditText(suggestions[0])
    window.quantity.setValue(3)
    window.add_item()
    assert window.material_model.rowCount() == 1
    assert store.items()[0]['quantity'] == 3
    # Repeated additions now merge automatically.
    window.add_item()
    assert store.items()[0]['quantity'] == 6
    index = window.material_model.index(0, 3)
    assert window.material_model.setData(index, 8, Qt.EditRole)
    assert store.items()[0]['quantity'] == 8
    assert window.material_model.data(window.material_model.index(0, 5)) == '—'
    window.material_table.setCurrentIndex(window.material_model.index(0, 0))
    window.remove_item()
    assert not store.items()
    assert window.supplier_model.rowCount() == 2
    window.close()


def test_background_comparison_and_history(app, store, monkeypatch):
    import time
    from threading import Event
    from PySide6.QtTest import QTest
    from klmelec.comparison import now
    from klmelec import comparison_ui
    entered, release = Event(), Event()

    def fake_compare(items, suppliers, previous, progress, cancelled):
        entered.set()
        while not release.is_set() and not cancelled():
            time.sleep(.005)
        return [dict(product_id=items[0]['id'], reference=items[0]['reference'], quantity=2,
                     supplier_id=s['id'], supplier=s['name'], connector=s['connector'],
                     checked_at=now(), url='', status='ok', detail='Test', ttc='12.00', cached=False)
                for s in suppliers]

    monkeypatch.setattr(comparison_ui, 'compare', fake_compare)
    product = next(p for p in store.products() if p['reference'] == '411617')
    store.add_item(product['id'], 2)
    window = MainWindow(store, 'test')
    window.show()
    window.start_comparison()
    for _ in range(100):
        if entered.is_set():
            break
        QTest.qWait(10)
    assert entered.is_set()
    assert window.worker.isRunning()
    assert not window.material_table.isEnabled()
    assert window.cancel_button.isEnabled()
    # Qt can still process events while HTTP is pending.
    window.tabs.setCurrentIndex(2)
    assert window.tabs.currentIndex() == 2
    release.set()
    for _ in range(200):
        QTest.qWait(10)
        if window.worker is None:
            break
    assert window.worker is None
    assert '24,00' in window.summary.text()
    assert len(store.comparisons()) == 1
    assert window.material_table.isEnabled()
    window.history.setCurrentIndex(1)
    assert 'prix non revérifiés' in window.report.toPlainText()
    window.vat.setValue(10)
    assert not window.material_model.offers
    assert len(store.comparisons()) == 1
    window.close()


def test_close_cancels_worker_without_destroying_running_thread(app, store, monkeypatch):
    import time
    from PySide6.QtTest import QTest
    from klmelec import comparison_ui

    def wait_for_cancel(items, suppliers, previous, progress, cancelled):
        while not cancelled():
            time.sleep(.005)
        return []

    monkeypatch.setattr(comparison_ui, 'compare', wait_for_cancel)
    store.add_item(store.products()[0]['id'], 1)
    window = MainWindow(store, 'test')
    window.show()
    window.start_comparison()
    window.close()
    assert window.close_pending
    for _ in range(200):
        QTest.qWait(10)
        if window.worker is None:
            break
    assert window.worker is None
    assert not window.isVisible()
