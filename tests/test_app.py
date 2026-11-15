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
    assert len(db.suppliers()) == 3
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
    assert db.db.execute('SELECT count(*) FROM suppliers').fetchone()[0] == 4
    db.close()


def test_yesss_added_once_to_existing_database(tmp_path):
    path = tmp_path / 'suppliers.sqlite3'
    db = Store(path)
    with db.db:
        db.db.execute("DELETE FROM settings WHERE key='supplier_yesss_v1'")
        db.db.execute("DELETE FROM suppliers WHERE name='YESSS Électrique'")
    db.close()
    db = Store(path)
    yesss = next(s for s in db.suppliers() if s['name'] == 'YESSS Électrique')
    assert yesss['url'] == 'https://www.yesss-fr.com/'
    assert not yesss['active'] and yesss['connector'] is None
    db.archive_supplier(yesss['id'])
    # An existing archived entry is respected even during the one-time upgrade.
    with db.db:
        db.db.execute("DELETE FROM settings WHERE key='supplier_yesss_v1'")
    db.close()
    db = Store(path)
    assert all(s['id'] != yesss['id'] for s in db.suppliers())
    assert db.db.execute("SELECT count(*) FROM suppliers WHERE name='YESSS Électrique'").fetchone()[0] == 1
    db.close()


@pytest.mark.parametrize('url', ['example.org','file:///tmp/data','https://','https://user:secret@example.org'])
def test_invalid_supplier(store, url):
    with pytest.raises(ValueError):
        store.save_supplier('Test', url)


def test_window_workflow(app, store, monkeypatch):
    window = MainWindow(store, 'test')
    comparisons = []
    monkeypatch.setattr(window, 'start_comparison', lambda **kwargs: comparisons.append(kwargs))
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
    # Each addition launches the comparison without clicking the button.
    assert len(comparisons) == 2
    index = window.material_model.index(0, 3)
    assert window.material_model.setData(index, 8, Qt.EditRole)
    assert store.items()[0]['quantity'] == 8
    assert window.material_model.data(window.material_model.index(0, 5)) == '—'
    window.material_table.setCurrentIndex(window.material_model.index(0, 0))
    window.remove_item()
    assert not store.items()
    assert window.supplier_model.rowCount() == 3
    window.close()


def test_settings_sections_and_theme_persistence(app, tmp_path):
    from PySide6.QtGui import QPalette
    from klmelec.themes import THEMES, DEFAULT_THEME

    path = tmp_path / 'themes.sqlite3'
    db = Store(path)
    window = MainWindow(db, 'test')
    window.show()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ['Matériel', 'Paramètres', 'Calcul électrique', '?']
    assert [window.settings_sections.tabText(i) for i in range(window.settings_sections.count())] == [
        'Apparence', 'Lieux', 'Fournisseurs', 'Offres et historique', 'Listes', 'Affichage et TVA', 'Comparaison', 'Livraison', 'Catalogue']
    assert window.theme_selector.currentText() == DEFAULT_THEME
    assert window.theme_selector.count() == 16
    assert not window.persistent_themes.isChecked()
    assert not window.random_themes.isChecked()
    assert not window.header_icon.pixmap().isNull()
    app.processEvents()
    bar = window.tabs.tabBar()
    assert abs(bar.geometry().center().x() - window.tabs.rect().center().x()) <= 2
    window.persistent_themes.setChecked(True)
    for name, colors in THEMES.items():
        window.theme_selector.setCurrentText(name)
        app.processEvents()
        assert window.palette().color(QPalette.Window).name().upper() == colors['BG']
        assert window.search.palette().color(QPalette.Base).name().upper() == colors['FIELD']
        assert window.report.palette().color(QPalette.Text).name().upper() == colors['FIELD_FG']
    chosen = window.theme_selector.currentText()
    window.close()
    db.close()

    db = Store(path)
    window = MainWindow(db, 'test')
    assert window.theme_selector.currentText() == chosen
    assert db.theme() == chosen
    window.close()
    db.save_theme('Thème inconnu')
    window = MainWindow(db, 'test')
    assert window.theme_selector.currentText() == DEFAULT_THEME
    window.close()
    db.close()


def test_save_and_load_list_buttons(app, store, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    path = tmp_path / 'liste.json'
    store.add_item(store.products()[0]['id'], 3, store.locations()[0]['id'])
    expected = store.export_list()
    window = MainWindow(store, 'test')
    comparisons = []
    monkeypatch.setattr(window, 'start_comparison', lambda: comparisons.append(store.export_list()))
    assert max(window.header_icon.pixmap().width(), window.header_icon.pixmap().height()) == 96
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(path), ''))
    window.save_list_button.click()
    assert path.exists()
    store.set_quantity(store.products()[0]['id'], 7)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(path), ''))
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.No)
    window.load_list_button.click()
    assert store.items()[0]['quantity'] == 7
    assert not comparisons
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    window.load_list_button.click()
    assert store.export_list() == expected
    assert comparisons == [expected]
    assert window.material_model.rowCount() == 1
    assert window.tabs.currentIndex() == 0
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    path.write_text('invalid json')
    window.load_list_button.click()
    assert warnings
    assert store.export_list() == expected
    assert comparisons == [expected]
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: ('', ''))
    window.load_list_button.click()
    assert comparisons == [expected]
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(path), ''))
    import json
    path.write_text(json.dumps(expected))
    for supplier in store.suppliers():
        store.save_supplier(supplier['name'], supplier['url'], False, supplier['id'])
    window.load_list_button.click()
    assert comparisons == [expected]
    path.write_text(json.dumps(dict(expected, items=[])))
    window.load_list_button.click()
    assert not store.items()
    assert comparisons == [expected]
    window.close()


@pytest.mark.parametrize('answers,saved,accepted', [
    ([QMessageBox.Yes], True, True),
    ([QMessageBox.Yes], False, False),
    ([QMessageBox.No, QMessageBox.Yes], False, True),
    ([QMessageBox.No, QMessageBox.No], False, False),
])
def test_close_save_or_confirm_discard(app, store, monkeypatch, answers, saved, accepted):
    from PySide6.QtGui import QCloseEvent

    store.add_item(store.products()[0]['id'], 2)
    window = MainWindow(store, 'test')
    replies = iter(answers)
    prompts, saves = [], []

    def question(*args):
        prompts.append(args[1])
        return next(replies)

    def save():
        saves.append(True)
        return saved

    monkeypatch.setattr(QMessageBox, 'question', question)
    monkeypatch.setattr(window, 'save_list', save)
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted() == accepted
    assert len(prompts) == len(answers)
    assert bool(saves) == (answers[0] == QMessageBox.Yes)
    assert store.items()[0]['quantity'] == 2
    store.clear_list()
    window.close()


def test_cancel_save_file_keeps_window_open(app, store, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    store.add_item(store.products()[0]['id'], 1)
    window = MainWindow(store, 'test')
    window.show()
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: ('', ''))
    assert not window.close()
    assert window.isVisible()
    assert store.items()
    store.clear_list()
    window.close()


def test_shipping_thresholds_per_supplier(app, store):
    window = MainWindow(store, 'test')
    panel = window.shipping_panel
    assert 'non renseigné' in panel.message.text()
    first = panel.edit_supplier.currentData()
    panel.known.setChecked(True)
    panel.threshold.setValue(250)
    panel.basis.setCurrentText('HT')
    panel.conditions.setText('Point relais uniquement')
    panel.save_button.click()
    assert '250,00 € HT' in panel.message.text()
    assert panel.message.toolTip() == 'Point relais uniquement'
    assert window.total_label.text() == 'Total TTC\n0,00 €'
    panel.supplier.setCurrentIndex(1)
    assert 'non renseigné' in panel.message.text()
    panel.edit_supplier.setCurrentIndex(1)
    assert not panel.known.isChecked()
    panel.known.setChecked(True)
    panel.threshold.setValue(150)
    panel.save_button.click()
    assert '150,00 € TTC' in panel.message.text()
    window.close()
    window = MainWindow(store, 'test')
    panel = window.shipping_panel
    assert panel.rule(first)['threshold'] == '250.0'
    assert '250,00 € HT' in panel.message.text()
    panel.known.setChecked(False)
    panel.save_button.click()
    assert 'non renseigné' in panel.message.text()
    for supplier in store.suppliers():
        store.archive_supplier(supplier['id'])
    window.supplier_model.refresh()
    assert panel.message.text() == 'Aucun fournisseur'
    assert not panel.save_button.isEnabled()
    window.close()


def test_list_shortcut_and_file_grid(app, store, tmp_path, monkeypatch):
    import json
    from PySide6.QtTest import QTest

    store.add_item(store.products()[0]['id'], 3)
    payload = store.export_list()
    (tmp_path / 'fred.json').write_text(json.dumps(payload))
    (tmp_path / 'isa.JSON').write_text(json.dumps(payload))
    (tmp_path / 'notes.txt').write_text('not a list')
    (tmp_path / 'directory.json').mkdir()
    store.clear_list()
    store.save_setting('lists_directory', tmp_path)
    window = MainWindow(store, 'test')
    calls = []
    monkeypatch.setattr(window, 'start_comparison', lambda: calls.append(True))
    window.show()
    window.lists_shortcut.click()
    app.processEvents()
    assert window.tabs.currentIndex() == 1
    assert window.settings_sections.currentWidget() == window.lists_page
    assert not window.lists_shortcut.icon().isNull()
    assert window.save_list_button.width() < 300
    assert window.save_list_button.y() == window.load_list_button.y()
    assert [window.list_files.item(i).text() for i in range(window.list_files.count())] == ['fred', 'isa']
    item = window.list_files.item(0)
    QTest.mouseClick(window.list_files.viewport(), Qt.LeftButton,
                     pos=window.list_files.visualItemRect(item).center())
    assert store.export_list() == payload
    assert calls == [True]
    assert window.tabs.currentIndex() == 0
    assert store.setting('lists_directory', '') == str(tmp_path)
    window.open_lists()
    (tmp_path / 'fred.json').unlink()
    window.open_lists()
    assert window.list_files.count() == 1
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    (tmp_path / 'isa.JSON').write_text('invalid')
    window.load_list_item(window.list_files.item(0))
    assert warnings and store.export_list() == payload
    assert calls == [True]
    store.clear_list()
    window.close()


def test_ht_and_periodic_comparison_settings(app, store, monkeypatch):
    window = MainWindow(store, 'test')
    window.show()
    model = window.material_model
    assert window.show_ht.isChecked()
    assert not window.auto_compare.isChecked()
    assert not window.comparison_timer.isActive()
    window.show_ht.setChecked(False)
    assert window.material_table.isColumnHidden(model.columnCount()-2)
    store.save_supplier('Autre', 'https://example.org')
    model.refresh()
    assert window.material_table.isColumnHidden(model.columnCount()-2)
    assert not window.material_table.isColumnHidden(model.columnCount()-3)
    window.auto_compare.setChecked(True)
    window.comparison_minutes.setValue(12)
    assert window.comparison_timer.interval() == 720000
    assert window.comparison_timer.isActive()
    window.force_refresh.setChecked(True)
    calls = []
    monkeypatch.setattr(window, 'start_comparison', lambda **kwargs: calls.append(kwargs))
    window.run_periodic_comparison()
    assert not calls
    store.add_item(store.products()[0]['id'], 2)
    window.run_periodic_comparison()
    assert calls == [{'force': True}]
    window.worker = object()
    window.run_periodic_comparison()
    assert len(calls) == 1
    window.worker = None
    window.close_pending = True
    window.run_periodic_comparison()
    assert len(calls) == 1
    window.close_pending = False
    store.clear_list()
    window.close()
    assert not window.comparison_timer.isActive()
    window = MainWindow(store, 'test')
    assert not window.show_ht.isChecked()
    assert window.auto_compare.isChecked()
    assert window.comparison_minutes.value() == 12
    assert window.force_refresh.isChecked()
    window.auto_compare.setChecked(False)
    assert not window.comparison_timer.isActive()
    window.close()


def test_optional_and_random_themes(app, store, monkeypatch):
    from klmelec.themes import THEMES, DEFAULT_THEME

    chosen = '[Clair] Latte Vanille'
    store.save_theme(chosen)
    window = MainWindow(store, 'test')
    assert window.theme_selector.currentText() == DEFAULT_THEME
    window.theme_selector.setCurrentText('[Clair] Matin Brumeux')
    assert store.theme() == chosen
    window.random_themes.setChecked(True)
    window.close()

    def choose_theme(names):
        assert names == list(THEMES)
        return chosen

    monkeypatch.setattr('klmelec.app.random.choice', choose_theme)
    window = MainWindow(store, 'test')
    assert window.random_themes.isChecked()
    assert not window.persistent_themes.isChecked()
    assert window.theme_selector.currentText() == chosen
    window.persistent_themes.setChecked(True)
    window.theme_selector.setCurrentText('[Clair] Matin Brumeux')
    window.close()
    window = MainWindow(store, 'test')
    assert window.persistent_themes.isChecked()
    assert window.theme_selector.currentText() == chosen
    window.random_themes.setChecked(False)
    window.persistent_themes.setChecked(False)
    window.close()
    window = MainWindow(store, 'test')
    assert window.theme_selector.currentText() == DEFAULT_THEME
    assert not window.random_themes.isChecked()
    assert not window.persistent_themes.isChecked()
    window.close()


def test_background_comparison_and_history(app, store, monkeypatch):
    import time
    from threading import Event
    from PySide6.QtTest import QTest
    from klmelec.comparison import now
    from klmelec import comparison_ui
    entered, release = Event(), Event()

    def fake_compare(items, suppliers, previous, progress, cancelled, **kwargs):
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
    assert not window.load_list_button.isEnabled()
    assert window.cancel_button.isEnabled()
    # Qt can still process events while HTTP is pending.
    window.tabs.setCurrentIndex(1)
    window.settings_sections.setCurrentIndex(3)
    assert window.settings_sections.currentWidget().isEnabled()
    assert window.history.isVisible()
    assert window.theme_selector.isEnabled()
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
    # Changing VAT recomputes HT without discarding the collected prices.
    assert window.material_model.offers
    assert 'Total HT calculé : 21,82' in window.summary.text()
    assert 'Total TTC : 24,00' in window.summary.text()
    assert len(store.comparisons()) == 1
    window.close()


@pytest.mark.parametrize('answer, archived', [(QMessageBox.No, False), (QMessageBox.Yes, True)])
def test_remove_supplier_asks_confirmation(app, store, monkeypatch, answer, archived):
    asked = []
    original = QMessageBox.question

    def question(parent, title, *args):
        if title == 'Retirer le fournisseur':
            asked.append(args[0])
            return answer
        return original(parent, title, *args)

    monkeypatch.setattr(QMessageBox, 'question', question)
    window = MainWindow(store, 'test')
    before = len(store.suppliers())
    first = window.supplier_model.rows[0]
    window.supplier_table.setCurrentIndex(window.supplier_model.index(0, 0))
    window.remove_supplier()
    assert len(asked) == 1 and first['name'] in asked[0]
    assert len(store.suppliers()) == before - archived
    window.close()


def test_close_cancels_worker_without_destroying_running_thread(app, store, monkeypatch):
    import time
    from PySide6.QtTest import QTest
    from klmelec import comparison_ui

    def wait_for_cancel(items, suppliers, previous, progress, cancelled, **kwargs):
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


def test_add_item_without_active_supplier_does_not_compare(app, store, monkeypatch):
    for supplier in store.suppliers():
        store.archive_supplier(supplier['id'])
    window = MainWindow(store, 'test')
    calls = []
    monkeypatch.setattr(window, 'start_comparison', lambda **kwargs: calls.append(kwargs))
    window.search.setCurrentIndex(0)
    window.add_item()
    assert store.items() and not calls
    window.close()


def test_standard_buttons_in_french(app):
    from PySide6.QtCore import QCoreApplication
    from klmelec.app import install_translations
    translator = install_translations(app)
    try:
        assert translator is not None
        assert QCoreApplication.translate('QPlatformTheme', '&Yes') == '&Oui'
        assert QCoreApplication.translate('QPlatformTheme', '&No') == '&Non'
    finally:
        app.removeTranslator(translator)


def test_checkbox_outline_follows_theme(app):
    from pathlib import Path
    from klmelec.themes import THEMES, apply_theme
    for name in ('[Sombre] Midnight Garage', '[Clair] Matin Brumeux'):
        apply_theme(app, name)
        style = app.styleSheet()
        assert f"border: 2px solid {THEMES[name]['ACCENT']}" in style
        check = style.split('url("')[1].split('")')[0]
        assert Path(check).is_file()


def test_catalog_page_adds_references_to_search(app, store):
    from klmelec.discovery import Discovery
    from klmelec.suppliers.base import ProductLink
    window = MainWindow(store, 'test')
    link = ProductLink('https://www.elecdistrib.fr/x-406921-3245064069212.html', 'LEG-406921',
                       '3245064069212', expected_title='Disjoncteur 4P 25A Legrand Réf. 406921')
    before = window.supplier_model.configured('elecdistrib')
    window.catalog_page.ready(Discovery([('elecdistrib', '406921', 'Disjoncteur 4P 25A Legrand', link)],
                                        [('123elec', 'https://www.123elec.com/y.html', 'Hors famille')], []))
    assert any(label.endswith('· Legrand · 406921') for label in window.labels)
    assert window.supplier_model.configured('elecdistrib') == before + 1
    assert '1 nouvelle(s) référence(s)' in window.catalog_page.report.toPlainText()
    assert 'Hors famille' in window.catalog_page.report.toPlainText()
    assert 'www.elecdistrib.fr : 1' in window.catalog_page.status.text()
    window.close()


def test_catalog_all_families_chained(app, store, monkeypatch):
    from klmelec import catalog_ui
    from klmelec.discovery import Discovery, FAMILIES
    from klmelec.suppliers.base import ProductLink
    calls = []

    def fake(family, known, progress, cancelled):
        calls.append((family, set(known)))
        link = ProductLink('https://www.123elec.com/x.html', 'LEG406774', '3245064067742', brand='Legrand')
        links = [('123elec', '406774', 'Disjoncteur', link)] if len(calls) == 1 else []
        errors = ['www.elecdistrib.fr : accès limité, recherche interrompue'] if len(calls) == 3 else []
        return Discovery(links, [], errors)

    monkeypatch.setattr(catalog_ui, 'discover', fake)
    page = catalog_ui.CatalogPage(store)
    assert page.family.itemData(0) == catalog_ui.ALL and page.family.currentIndex() == 1
    page.family.setCurrentIndex(0)
    page.start()
    page.worker.wait()
    app.processEvents()
    # Arrêt après la 3e famille (accès limité) ; la référence trouvée n'est plus cherchée ensuite.
    assert [family for family, _ in calls] == list(FAMILIES)[:3]
    assert ('123elec', '406774') in calls[1][1]
    assert '3/%d famille(s)' % len(FAMILIES) in page.report.toPlainText()
    assert 'accès limité' in page.report.toPlainText()
    assert page.worker is None and page.start_button.isEnabled()
