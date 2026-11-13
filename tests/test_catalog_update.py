import json
from importlib.resources import files

from klmelec.data import Store


def test_catalog_references_are_preserved():
    catalog = json.loads(files('klmelec').joinpath('catalog.json').read_text())
    assert len(catalog) == 28
    keys = {(p['brand'], p['reference']) for p in catalog}
    assert len(keys) == 28
    assert ('Legrand', '405001') in keys
    assert ('Legrand', '080251') in keys
    assert ('Legrand', '078802') in keys
    assert ('Legrand', '278011L') in keys
    assert ('À confirmer', 'cap036819') in keys
    assert not any(p['reference'] == '824302' for p in catalog)


def test_enrichment_existing_database_is_idempotent(tmp_path):
    path = tmp_path / 'catalog.sqlite3'
    store = Store(path)
    product = next(p for p in store.products() if p['reference'] == '406774')
    store.add_item(product['id'], 13)
    supplier = store.suppliers()[0]
    store.save_supplier(supplier['name'], supplier['url'], False, supplier['id'])
    snapshot = {'date': '2026-11-13T08:00:00+00:00', 'vat': '20', 'items': [], 'offers': []}
    store.save_comparison(snapshot)
    # Recreate a pre-update database, retaining a manually entered new reference.
    with store.db:
        store.db.execute("DELETE FROM settings WHERE key='catalog_2026_11_braise_samia'")
        store.db.execute('DELETE FROM products WHERE id>18 AND reference<>?', ('406777',))
        store.db.execute("UPDATE products SET name='Nom personnel' WHERE reference='406777'")
    existing_id = next(p['id'] for p in store.products() if p['reference'] == '406777')
    store.close()
    for _ in range(2):
        store = Store(path)
        assert len(store.products()) == 28
        assert store.items()[0]['id'] == product['id']
        assert store.items()[0]['quantity'] == 13
        assert not next(s for s in store.suppliers() if s['id'] == supplier['id'])['active']
        assert store.comparisons()[0][1] == snapshot
        preserved = next(p for p in store.products() if p['reference'] == '406777')
        assert preserved['id'] == existing_id
        assert preserved['name'] == 'Nom personnel'
        store.close()


def test_three_row_busbar_added_to_existing_catalog_without_replacing_two_row(tmp_path):
    path = tmp_path / 'existing.sqlite3'
    store = Store(path)
    old = next(p for p in store.products() if p['reference'] == '405000')
    store.add_item(old['id'], 2)
    with store.db:
        store.db.execute("DELETE FROM products WHERE reference='405001'")
        store.db.execute("DELETE FROM settings WHERE key='catalog_405001_v1'")
    before = store.export_list()
    store.close()
    for _ in range(2):
        store = Store(path)
        found = [p for p in store.products() if p['reference'] == '405001']
        assert len(found) == 1
        assert '3 rangées' in found[0]['name']
        assert store.export_list() == before
        assert len(store.products()) == 28
        store.close()
