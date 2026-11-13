import copy

import pytest

from klmelec.data import Store


def test_clear_list_preserves_settings_catalog_and_history(tmp_path):
    store = Store(tmp_path / 'session.sqlite3')
    store.add_item(store.products()[0]['id'], 2, store.locations()[0]['id'])
    store.save_theme('test')
    store.save_comparison({'date': '2026-11-13', 'offers': []})
    before = {table: [tuple(row) for row in store.db.execute(f'SELECT * FROM {table}')]
              for table in ('products', 'suppliers', 'locations', 'settings', 'comparisons')}
    store.clear_list()
    assert not store.items()
    assert not store.assignments()
    for table, rows in before.items():
        assert [tuple(row) for row in store.db.execute(f'SELECT * FROM {table}')] == rows
    store.close()


def test_list_roundtrip_between_databases(tmp_path):
    source = Store(tmp_path / 'source.sqlite3')
    target = Store(tmp_path / 'target.sqlite3')
    product = source.products()[0]
    place = source.add_location('Atelier')
    source.add_item(product['id'], 3)
    source.assign_location(product['id'], place, 1)
    payload = source.export_list()
    target.add_location('Autre lieu')
    target.add_item(target.products()[1]['id'], 8)
    target.import_list(payload)
    assert target.export_list() == payload
    assert len(target.items()) == 1
    target.import_list({'format': 'klmelec-list', 'version': 1, 'items': []})
    assert not target.items()
    source.close()
    target.close()


@pytest.mark.parametrize('invalid', ['quantity', 'locations', 'unknown', 'duplicate', 'version'])
def test_invalid_list_preserves_current_items(tmp_path, invalid):
    store = Store(tmp_path / 'list.sqlite3')
    store.add_item(store.products()[0]['id'], 2, store.locations()[0]['id'])
    original = store.export_list()
    payload = copy.deepcopy(original)
    if invalid == 'quantity':
        payload['items'][0]['quantity'] = True
    elif invalid == 'locations':
        payload['items'][0]['locations'] = [42, None]
    elif invalid == 'unknown':
        payload['items'][0]['reference'] = 'unknown-reference'
    elif invalid == 'duplicate':
        payload['items'].append(copy.deepcopy(payload['items'][0]))
    else:
        payload['version'] = 2
    with pytest.raises(ValueError):
        store.import_list(payload)
    assert store.export_list() == original
    store.close()
