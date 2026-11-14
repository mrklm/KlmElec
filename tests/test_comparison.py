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
    product = {'@type': 'Product', 'sku': link.sku, 'brand': {'name': link.brand},
               'gtin13': link.ean, 'offers': {'@type': 'Offer', 'price': price,
               'priceCurrency': 'EUR', 'availability': 'https://schema.org/InStock'}}
    product.update(changes)
    data = {'reference': link.sku, 'ecotax': 0, 'minimal_quantity': '1'}
    return (f'<h1>{link.brand} {link.manufacturer_reference or ref}</h1><script type="application/ld+json">{json.dumps(product)}</script>'
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
    assert 'Référence non prise en charge' in run(handler, items=items)[0]['detail']


def test_missing_robots_allows_access_and_is_fetched_once():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        ref = '411638' if str(request.url) == CONNECTORS['123elec'].links['411638'].url else '411617'
        return httpx.Response(200, text=document(ref=ref))
    items, suppliers = inputs()
    items.append(dict(items[0], id=2, reference='411638'))
    offers = run(handler, items=items, suppliers=[suppliers[0]])
    assert [o['status'] for o in offers] == ['ok', 'ok']
    assert calls.count('/robots.txt') == 1


def test_unreadable_robots_is_not_reported_as_product_error():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(500) if request.url.path == '/robots.txt' else success(request)
    items, suppliers = inputs()
    items.append(dict(items[0], id=2, reference='411638'))
    offers = run(handler, items=items, suppliers=[suppliers[0]])
    assert all(o['status'] == 'error' for o in offers)
    assert all(o['detail'] == 'Règles d’accès du site illisibles (HTTP 500)' for o in offers)
    assert calls == ['/robots.txt']


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
    assert len(store.products()) == 29  # Personal product plus the enriched bundled catalog.
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


@pytest.mark.parametrize('ref,ean,page', [
    ('406771', '3245064067713', '76'),
    ('406773', '3245064067737', '75'),
    ('406775', '3245064067751', '73'),
    ('406777', '3245064067775', '72'),
])
def test_missing_breakers_are_compared_as_exact_units(ref, ean, page):
    items, suppliers = inputs(ref)
    seen = []

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /')
        key = '123elec' if request.url.host == 'www.123elec.com' else 'elecdistrib'
        seen.append(key)
        assert str(request.url) == CONNECTORS[key].links[ref].url
        return httpx.Response(200, text=document(key, ref=ref, price='9.00'))

    offers = run(handler, items=items, suppliers=suppliers)
    assert sorted(seen) == ['123elec', 'elecdistrib']
    assert all(o['status'] == 'ok' and o['reference'] == ref for o in offers)
    assert best_offer(offers) is not None
    for key, connector in CONNECTORS.items():
        link = connector.links[ref]
        assert link.ean == ean and link.pack == 1
        if key == 'elecdistrib':
            assert f'/{page}-' in link.url
        for html in (
            document(key, ref=ref).replace('<h1>Legrand', '<h1>Lot de 10 Legrand'),
            document(key, ref=ref, sku=link.sku + 'x10'),
            document(key, ref=ref, gtin13='3245064067744'),
        ):
            with pytest.raises(OfferError):
                connector.parse(html, ref, link)


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


@pytest.mark.parametrize('ref', ['404926', '405000', '405001', '412408'])
def test_accessories_reach_both_exact_product_pages(ref):
    items, suppliers = inputs(ref)
    called = []
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /')
        key = '123elec' if request.url.host == 'www.123elec.com' else 'elecdistrib'
        assert str(request.url) == CONNECTORS[key].links[ref].url
        called.append(key)
        return httpx.Response(200, text=document(key, ref=ref))
    offers = run(handler, items=items, suppliers=suppliers)
    assert len(called) == 2
    assert all(o['status'] == 'ok' for o in offers)
    assert best_offer(offers) is not None


@pytest.mark.parametrize('ref', ['WAG2106-5201', 'WAG2106-5204', 'WAG2106-5207', 'WAG2106-1291'])
def test_wago_supplier_alias_and_partial_comparison(ref):
    items, suppliers = inputs(ref)
    items[0]['brand'] = 'Wago'
    def handler(request):
        assert request.url.host == 'www.123elec.com'
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /')
        return httpx.Response(200, text=document(ref=ref))
    offers = run(handler, items=items, suppliers=suppliers)
    assert offers[0]['status'] == 'ok'
    assert 'non prise en charge' in offers[1]['detail']
    assert best_offer(offers) is None
    connector = CONNECTORS['123elec']
    link = connector.links[ref]
    for html in [document(ref=ref, brand={'name': 'Legrand'}),
                 document(ref=ref, gtin13='0000000000000'),
                 document(ref=ref, sku=link.sku + '-lot'),
                 document(ref=ref).replace('<h1>Wago', '<h1>Lot de 10 Wago'),
                 document(ref=ref).replace(link.manufacturer_reference, '9999-9999')]:
        with pytest.raises(OfferError):
            connector.parse(html, ref, link)
    items[0]['brand'] = 'Autre'
    offers = run(lambda request: pytest.fail('Aucune requête pour une marque incohérente'), items=items)
    assert all(o['status'] == 'error' for o in offers)


def test_recommended_products_tax_markup_is_not_main_product_tax():
    connector = CONNECTORS['123elec']
    link = connector.links['404926']
    recommended = ('<form class="product-item product_addtocart_form">'
                   '<span class="price-container price-final_price tax weee">'
                   '<span data-price-amount="7.5" data-price-type="finalPrice">7,50 € TTC</span>'
                   '</span></form>')
    html = document(ref='404926', price='3.20') + recommended
    html += ('<span class="price-container price-tier_price tax weee">'
             '<span class="price-wrapper" data-price-amount="3.00">3,00 € TTC</span></span>')
    assert connector.parse(html, '404926', link)[0] == Decimal('3.20')
    for surcharge in ('<div class="weee-tax">0,20 €</div>', '<div class="weee">0,20 €</div>',
                      '<span data-price-type="weee" data-price-amount="0.2"></span>'):
        with pytest.raises(OfferError, match='Éco-participation'):
            connector.parse(html + surcharge, '404926', link)


@pytest.mark.parametrize('ref', ['IKE821023', 'IKE821053'])
@pytest.mark.parametrize('catalog_brand', ['À confirmer', 'IKEPE'])
def test_ikepe_exact_identity_with_reference_absent_from_title(ref, catalog_brand):
    from bs4 import BeautifulSoup
    link = CONNECTORS['123elec'].links[ref]
    soup = BeautifulSoup(document(ref=ref), 'html.parser')
    soup.h1.string = link.expected_title
    html = str(soup)
    items, suppliers = inputs(ref)
    items[0]['brand'] = catalog_brand
    def handler(request):
        assert request.url.host == 'www.123elec.com'
        return httpx.Response(200, text='User-agent: *\nAllow: /' if request.url.path == '/robots.txt' else html)
    offers = run(handler, items=items, suppliers=suppliers)
    assert offers[0]['status'] == 'ok'
    assert offers[1]['status'] == 'error'
    assert best_offer(offers) is None
    connector = CONNECTORS['123elec']
    for wrong in [html.replace(link.expected_title, 'Autre tableau'),
                  html.replace(link.sku, 'IKE999999'),
                  html.replace(link.ean, '0000000000000'),
                  html.replace('"name": "IKEPE"', '"name": "Autre"')]:
        with pytest.raises(OfferError):
            connector.parse(wrong, ref, link)
    items[0]['brand'] = 'Autre'
    offers = run(lambda request: pytest.fail('Marque incohérente'), items=items)
    assert offers[0]['status'] == 'error'


def test_ikepe_end_caps_pack_not_silently_priced_as_single_piece():
    items, suppliers = inputs('IKE824302')
    items[0].update(brand='À confirmer', quantity=4)
    offers = run(lambda request: pytest.fail('Lot exclu sans requête'), items=items, suppliers=suppliers[:1])
    assert offers[0]['ttc'] is None
    assert 'Lot de 5' in offers[0]['detail']
    assert offers[0]['url'].endswith('ikepe-lot-de-5-embouts-isolants-pour-peigne-horizontal.html')
