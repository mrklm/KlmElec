import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from html import escape

import httpx
import pytest

from klmelec.comparison import compare, best_offer, amounts, now
from klmelec.data import Store
from klmelec.suppliers import CONNECTORS
from klmelec.suppliers.base import OfferError


def document(key='123elec', ref='411617', price='36.50', **changes):
    link = CONNECTORS[key].links[ref]
    product = {'@type': 'Product', 'sku': link.sku, 'brand': {'name': 'Legrand'},
               'gtin13': link.ean, 'offers': {'@type': 'Offer', 'price': price,
               'priceCurrency': 'EUR', 'availability': 'https://schema.org/InStock'}}
    product.update(changes)
    data = {'reference': link.sku, 'ecotax': 0, 'minimal_quantity': '1'}
    return (f'<h1>Legrand {ref}</h1><script type="application/ld+json">{json.dumps(product)}</script>'
            f'<meta property="product:price:amount" content="{price}">'
            f'<span class="pricettcproduct" content="EUR"></span>'
            f'<span class="pricettcproduct" content="{price}">{price} € TTC la pièce</span>'
            f'<input id="quantity_wanted" min="1">'
            f'<div data-product="{escape(json.dumps(data), quote=True)}"></div>')


def inputs(ref='411617'):
    return ([dict(id=1, brand='Legrand', reference=ref, quantity=3, name='Différentiel')],
            [dict(id=1, name='123 Elec', url='https://www.123elec.com/', active=True, connector='123elec'),
             dict(id=2, name='Elec Distrib', url='https://www.elecdistrib.fr/', active=True, connector='elecdistrib')])


def run(handler, items=None, suppliers=None, **kwargs):
    default_items, default_suppliers = inputs()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return compare(items or default_items, default_suppliers if suppliers is None else suppliers,
                       client=client, pause=lambda _: None, **kwargs)


def success(request):
    if request.url.path == '/robots.txt':
        return httpx.Response(200, text='User-agent: *\nAllow: /')
    key = '123elec' if '123elec' in request.url.host else 'elecdistrib'
    price = '45.95' if key == '123elec' else '36.50'
    return httpx.Response(200, text=document(key, price=price))


def test_complete_and_decimal_rounding():
    offers = run(success)
    assert [o['status'] for o in offers] == ['ok', 'ok']
    assert best_offer(offers)['supplier'] == 'Elec Distrib'
    assert amounts('36.50', 3, '20') == (Decimal('30.42'), Decimal('36.50'), Decimal('91.25'), Decimal('109.50'))
    assert amounts('0.03', 3, '20')[2] == Decimal('0.08')
    assert amounts('36.50', 3, '0')[2] == Decimal('109.50')


@pytest.mark.parametrize('price', ['0', '-1', 'NaN', 'Infinity', 'inconnu'])
def test_invalid_price(price):
    connector = CONNECTORS['123elec']
    with pytest.raises(OfferError):
        connector.parse(document(price=price), '411617', connector.links['411617'])


@pytest.mark.parametrize('changes', [
    {'sku': 'LEG411638'}, {'brand': {'name': 'Autre'}}, {'gtin13': '000'},
    {'offers': {'@type':'Offer','price':'1','priceCurrency':'USD'}},
    {'offers': [{'price':'1'}, {'price':'2'}]},
    {'offers': {'@type':'Offer','price':'1','priceCurrency':'EUR','eligibleQuantity':{'minValue':10}}},
])
def test_mismatched_or_ambiguous(changes):
    connector = CONNECTORS['123elec']
    with pytest.raises(OfferError):
        connector.parse(document(**changes), '411617', connector.links['411617'])


def test_recommended_product_not_selected():
    connector = CONNECTORS['123elec']
    html = document().replace('<h1>Legrand 411617</h1>', '<h1>Autre produit 999999</h1>')
    with pytest.raises(OfferError):
        connector.parse(html, '411617', connector.links['411617'])


@pytest.mark.parametrize('code', [403, 404, 429, 503, 302])
def test_http_failure_no_winner(code):
    def handler(request):
        if request.url.host == 'www.elecdistrib.fr':
            return httpx.Response(code)
        return success(request)
    offers = run(handler)
    assert offers[0]['ttc'] == '45.95'
    assert offers[1]['ttc'] is None
    assert best_offer(offers) is None


def test_timeout_unknown_and_disabled_supplier():
    def handler(request):
        raise httpx.ReadTimeout('test', request=request)
    assert all(o['detail'] == 'Délai réseau dépassé' for o in run(handler))
    items, suppliers = inputs()
    suppliers.append(dict(id=3, name='Autre', url='https://example.org', active=True, connector=None))
    offers = run(success, suppliers=suppliers)
    assert len(offers) == 3 and best_offer(offers) is None
    suppliers[-1]['active'] = False
    assert best_offer(run(success, suppliers=suppliers)) is not None
    assert run(success, suppliers=[]) == []


def test_lot_and_unknown_reference_never_requested(monkeypatch):
    from dataclasses import replace
    connector = CONNECTORS['elecdistrib']
    monkeypatch.setattr(connector, 'links', dict(connector.links, **{
        '406774': replace(connector.links['406774'], pack=10, sku='LEG-406774x10')}))
    items, suppliers = inputs('406774')
    def handler(request):
        raise AssertionError('Aucune requête attendue pour un lot exclu')
    offers = run(handler, items=items, suppliers=[suppliers[1]])
    assert 'Lot de 10' in offers[0]['detail']
    items[0]['reference'] = '999999'
    assert 'URL non configurée' in run(handler, items=items)[0]['detail']


def test_robots_and_stop_after_block():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text='User-agent: *\nDisallow: /')
    offers = run(handler)
    assert calls == ['/robots.txt', '/robots.txt']
    assert best_offer(offers) is None
    items, suppliers = inputs()
    items.append(dict(items[0], id=2, reference='411638'))
    calls.clear()
    def blocked(request):
        calls.append(request.url.path)
        return httpx.Response(403)
    run(blocked, items=items, suppliers=[suppliers[0]])
    assert len(calls) == 1


def test_cache_age_and_cancellation():
    offers = run(success)
    def no_network(request):
        raise AssertionError('Le cache frais doit éviter le réseau')
    cached = run(no_network, previous=offers)
    assert all(o['cached'] for o in cached)
    assert cached[0]['checked_at'] == offers[0]['checked_at']
    assert best_offer(cached)
    for offer in offers:
        offer['checked_at'] = (datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat()
    assert best_offer(offers) is None
    assert not any(o['cached'] for o in run(success, previous=offers))
    assert all('annulée' in o['detail'] for o in run(no_network, cancelled=lambda: True))


def test_unavailable_not_a_winner():
    def handler(request):
        response = success(request)
        return httpx.Response(200, text=response.text.replace('InStock', 'OutOfStock'))
    offers = run(handler)
    assert all(o['status'] == 'unavailable' and o['ttc'] for o in offers)
    assert best_offer(offers) is None


def test_history_preserved_after_failure_and_supplier_archive(tmp_path):
    path = tmp_path/'db.sqlite3'
    store = Store(path)
    items, suppliers = inputs()
    first = dict(date=now(), vat='20', items=items, offers=run(success))
    store.save_comparison(first)
    second = dict(first, offers=run(lambda r: httpx.Response(503)))
    store.save_comparison(second)
    store.archive_supplier(store.suppliers()[0]['id'])
    store.close()
    store = Store(path)
    history = store.comparisons()
    assert history[0][1]['offers'][0]['ttc'] is None
    assert history[1][1] == first
    store.close()


def test_expired_ambiguous_and_surcharge():
    connector = CONNECTORS['123elec']
    for validity in ('2000-01-01', 'incorrect'):
        html = document().replace('"priceCurrency": "EUR"', f'"priceCurrency": "EUR", "priceValidUntil": "{validity}"')
        with pytest.raises(OfferError):
            connector.parse(html, '411617', connector.links['411617'])
    with pytest.raises(OfferError):
        connector.parse(document()+document(), '411617', connector.links['411617'])
    with pytest.raises(OfferError):
        connector.parse(document()+'<div class="weee">0,20 €</div>', '411617', connector.links['411617'])


def test_existing_database_upgrade_preserves_data(tmp_path):
    import sqlite3
    path = tmp_path/'legacy.sqlite3'
    old = sqlite3.connect(path)
    old.executescript('''
        CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT,brand TEXT,reference TEXT,UNIQUE(brand,reference));
        CREATE TABLE items(product_id INTEGER PRIMARY KEY REFERENCES products(id),quantity INTEGER);
        CREATE TABLE suppliers(id INTEGER PRIMARY KEY,name TEXT,url TEXT,active INTEGER,connector TEXT,archived INTEGER DEFAULT 0);
        CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);
        INSERT INTO settings VALUES ('seeded','1');
        INSERT INTO products VALUES (42,'Produit personnel','Marque','REF');
        INSERT INTO items VALUES (42,9);
        INSERT INTO suppliers VALUES (7,'Personnel','https://example.org',0,NULL,0);
    ''')
    old.close()
    store = Store(path)
    assert store.items()[0]['quantity'] == 9
    assert len(store.products()) == 28  # Personal product plus the enriched bundled catalog.
    assert next(p for p in store.products() if p['id'] == 42)['name'] == 'Produit personnel'
    assert store.suppliers()[0]['name'] == 'Personnel'
    assert not store.suppliers()[0]['active']
    assert store.comparisons() == []
    store.close()


def test_411633_is_compared_by_exact_reference():
    items, suppliers = inputs('411633')
    seen = []
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /')
        key = '123elec' if request.url.host == 'www.123elec.com' else 'elecdistrib'
        assert str(request.url) == CONNECTORS[key].links['411633'].url
        seen.append(key)
        return httpx.Response(200, text=document(key, ref='411633', price='42.90' if key=='123elec' else '40.00'))
    offers = run(handler, items=items, suppliers=suppliers)
    assert set(seen) == {'123elec','elecdistrib'}
    assert all(o['status']=='ok' and o['reference']=='411633' for o in offers)
    assert best_offer(offers)['supplier'] == 'Elec Distrib'
    # Similar 63A models must not be accepted as the requested reference.
    connector = CONNECTORS['123elec']
    with pytest.raises(OfferError):
        connector.parse(document(ref='411633').replace('411633', '411650'), '411633', connector.links['411633'])


def test_406774_unit_offer_and_lot_rejection():
    items, suppliers = inputs('406774')
    connector = CONNECTORS['elecdistrib']
    link = connector.links['406774']
    assert link.pack == 1 and link.sku == 'LEG-406774'
    assert '/74-' in link.url and 'lot-de-10' not in link.url
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /')
        key = '123elec' if request.url.host=='www.123elec.com' else 'elecdistrib'
        assert str(request.url) == CONNECTORS[key].links['406774'].url
        return httpx.Response(200, text=document(key, ref='406774', price='7.50'))
    results = run(handler, items=items, suppliers=suppliers)
    assert all(o['status']=='ok' for o in results)
    assert best_offer(results) is not None
    lot = document('elecdistrib',ref='406774').replace('<h1>Legrand', '<h1>Lot de 10 Legrand')
    with pytest.raises(OfferError):
        connector.parse(lot, '406774', link)
    with pytest.raises(OfferError):
        connector.parse(document('elecdistrib',ref='406774',sku='LEG-406774x10'), '406774', link)
