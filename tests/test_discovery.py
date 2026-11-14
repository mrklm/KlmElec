import json
from html import escape

import httpx
import pytest

from klmelec.comparison import compare
from klmelec.data import Store
from klmelec.discovery import discover

SITEMAP = 'https://www.123elec.com/media/sitemap/sitemap.xml'
CATEGORY = 'https://www.elecdistrib.fr/132-disjoncteurs-legrand'
E123 = 'https://www.123elec.com/'
ED = 'https://www.elecdistrib.fr/tableaux-composants/'


def page(sku, ean, title, brand='Legrand', price='12.40'):
    product = {'@type': 'Product', 'name': title, 'sku': sku, 'brand': {'@type': 'Brand', 'name': brand},
               'gtin13': ean, 'offers': {'@type': 'Offer', 'price': price, 'priceCurrency': 'EUR',
                                         'availability': 'https://schema.org/InStock'}}
    data = {'reference': sku, 'ecotax': 0, 'minimal_quantity': '1'}
    return (f'<h1>{title}</h1><script type="application/ld+json">{json.dumps(product)}</script>'
            f'<meta property="product:price:amount" content="{price}">'
            f'<span class="pricettcproduct" content="{price}">{price} € TTC</span>'
            '<input id="quantity_wanted" min="1">'
            f'<div data-product="{escape(json.dumps(data), quote=True)}"></div>')


PAGES = {
    SITEMAP: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
        'legrand-dnx3-disjoncteur-16a-auto.html', 'legrand-disjoncteur-electrique-dnx3-uni-neutre-16a.html',
        'legrand-prise-de-courant.html', 'legrand-lot-disjoncteur.html', 'legrand-drivia-platine-disjoncteur-401181.html', 'legrand-tableau-pre-cable-8-disjoncteurs.html', 'schneider-disjoncteur.html')) + '</urlset>',
    E123 + 'legrand-dnx3-disjoncteur-16a-auto.html':
        page('LEG406783', '3245064067836', 'LEGRAND DNX3 Disjoncteur 16A auto PH+N courbe C - 406783', 'LEGRAND'),
    E123 + 'legrand-disjoncteur-electrique-dnx3-uni-neutre-16a.html':
        page('LEG406774', '3245064067744', 'Legrand Disjoncteur 16A 406774'),
    E123 + 'legrand-drivia-platine-disjoncteur-401181.html':
        page('LEG401181', '3245064011815', 'LEGRAND Drivia Platine pour disjoncteur de branchement - 401181'),
    E123 + 'legrand-tableau-pre-cable-8-disjoncteurs.html':
        page('LEG200882', '3245062008824', 'LEGRAND Drivia Tableau électrique pré-câblé 8 disjoncteurs - 200882'),
    E123 + 'legrand-lot-disjoncteur.html':
        page('LEG406700', '3245064067003', 'Legrand Lot de 10 disjoncteurs 406700'),
    CATEGORY: f'<a href="{ED}2102-disjoncteur-4p-25a-legrand-406921-3245064069212.html">x</a>'
              f'<a href="{CATEGORY}?page=2">2</a>',
    CATEGORY + '?page=2': f'<a href="{ED}2103-disjoncteur-16a-auto-legrand-ref-406783-3245064067836.html">x</a>',
    ED + '2102-disjoncteur-4p-25a-legrand-406921-3245064069212.html':
        page('LEG-406921', '3245064069212', 'Disjoncteur 4P 25A Courbe C DX3 Legrand Réf. 406921'),
    ED + '2103-disjoncteur-16a-auto-legrand-ref-406783-3245064067836.html':
        page('LEG-406783', '3245064067836', 'Disjoncteur 16A auto Legrand Réf. 406783'),
}


def run(handler=None, **kwargs):
    calls = []

    def default(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nDisallow: /catalogsearch/')
        text = PAGES.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler or default)) as client:
        return discover('disjoncteurs-legrand', client=client, pause=lambda _: None, **kwargs), calls


def test_discovers_validated_breakers_from_both_suppliers():
    result, calls = run(known={('123elec', '406774')})
    assert sorted((key, ref) for key, ref, _, _ in result.links) == [
        ('123elec', '406783'), ('elecdistrib', '406783'), ('elecdistrib', '406921')]
    reasons = {url.rsplit('/', 1)[-1]: reason for _, url, reason in result.rejected}
    assert reasons == {'legrand-lot-disjoncteur.html': 'Lot de 10 : exclu de la comparaison unitaire',
                       'legrand-drivia-platine-disjoncteur-401181.html': 'Hors famille',
                       'legrand-tableau-pre-cable-8-disjoncteurs.html': 'Hors famille'}
    # Filtered by the sitemap address, never opened.
    assert not any('prise' in url or 'schneider' in url for url in calls)
    assert sum(url.endswith('/robots.txt') for url in calls) == 2
    assert not result.errors


def test_discovered_links_are_saved_and_used_for_prices(tmp_path):
    result, _ = run()
    store = Store(tmp_path / 'db.sqlite3')
    existing = next(p for p in store.products() if p['reference'] == '406774')
    added = store.save_discovery(result.links, '2026-11-14T00:00:00+00:00')
    assert added == 2  # 406783 and 406921; 406774 already in the bundled catalog
    assert next(p for p in store.products() if p['reference'] == '406774')['name'] == existing['name']
    links = store.product_links()
    assert links['elecdistrib']['406921'].sku == 'LEG-406921'
    product = next(p for p in store.products() if p['reference'] == '406783')
    store.add_item(product['id'], 2)
    suppliers = [dict(s) for s in store.suppliers() if s['connector']]

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nAllow: /')
        return httpx.Response(200, text=PAGES[str(request.url)])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        offers = compare([dict(r) for r in store.items()], suppliers, client=client,
                         pause=lambda _: None, links=links)
    assert [o['status'] for o in offers] == ['ok', 'ok']
    # Running the discovery again updates links without duplicating products.
    assert store.save_discovery(result.links, '2026-11-15T00:00:00+00:00') == 0
    store.close()


def test_conflicting_ean_is_rejected():
    pages = dict(PAGES)
    pages[ED + '2103-disjoncteur-16a-auto-legrand-ref-406783-3245064067836.html'] = page(
        'LEG-406783', '3245064000000', 'Disjoncteur 16A auto Legrand Réf. 406783')

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    result, _ = run(handler)
    assert ('elecdistrib', '406783') not in {(k, r) for k, r, _, _ in result.links}
    assert 'EAN différent selon le fournisseur' in {reason for *_, reason in result.rejected}


def test_access_limit_stops_site_and_cancel_stops_everything():
    def limited(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        if request.url.host == 'www.123elec.com' and str(request.url) != SITEMAP:
            return httpx.Response(429)
        text = PAGES.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    result, _ = run(limited)
    assert 'www.123elec.com : accès limité, recherche interrompue' in result.errors
    assert sum(key == '123elec' for key, *_ in result.rejected) == 1  # stops at the first refusal
    assert {key for key, *_ in result.links} == {'elecdistrib'}

    result, calls = run(cancelled=lambda: True)
    assert result.errors == ['Recherche annulée'] and not result.links and not calls


def test_differential_family_keeps_only_residual_current_switches():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/135-interrupteurs-differentiels-legrand'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-interrupteur-differentiel-40a-type-a.html', 'legrand-disjoncteur-differentiel-16a.html',
            'legrand-dnx3-disjoncteur-16a-auto.html')) + '</urlset>',
        E123 + 'legrand-interrupteur-differentiel-40a-type-a.html':
            page('LEG411617', '3245064116176', 'LEGRAND DX3 Interrupteur différentiel 40A 30mA type A 230V - 411617', 'LEGRAND'),
        E123 + 'legrand-disjoncteur-differentiel-16a.html':
            page('LEG410705', '3245064107051', 'LEGRAND DX3 Disjoncteur différentiel bipolaire 16A 30mA type AC - 410705'),
        category: f'<a href="{ED}69-dx3-40a-type-a-legrand-ref-411560-3245064115605.html">x</a>',
        ED + '69-dx3-40a-type-a-legrand-ref-411560-3245064115605.html':
            page('LEG-411560', '3245064115605', 'Interrupteur DIFFERENTIEL 2P 40A Type A 30mA TX3 Legrand Réf. 411560'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('differentiels-legrand', client=client, pause=lambda _: None)
    assert sorted((key, ref) for key, ref, _, _ in result.links) == [('123elec', '411617'), ('elecdistrib', '411560')]
    assert [(url.rsplit('/', 1)[-1], reason) for _, url, reason in result.rejected] == [
        ('legrand-disjoncteur-differentiel-16a.html', 'Hors famille')]
    assert not result.errors


def test_remote_switch_family_skips_dimmers_in_same_category():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/140-telerupteurs-legrand'
    pages = {
        sitemap: f'<urlset><url><loc>{E123}legrand-cx3-telerupteur-16a-2f.html</loc></url></urlset>',
        E123 + 'legrand-cx3-telerupteur-16a-2f.html':
            page('LEG412412', '3245064124126', 'LEGRAND CX3 Télérupteur 16A 2F monophasé - 412412', 'LEGRAND'),
        category: f'<a href="{ED}1-televariateur-lexic-legrand-ref-003659-3245060036591.html">x</a>',
        ED + '1-televariateur-lexic-legrand-ref-003659-3245060036591.html':
            page('LEG-003659', '3245060036591', 'Télévariateur Lexic pour charges incandescentes 60-600W Legrand Réf: 003659'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('telerupteurs-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '412412')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']


def test_comb_family_skips_accessories_for_combs():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/138-accessoires-modulaires-legrand'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-hx3-peigne-tetrapolaire-18-modules.html', 'legrand-hx-isolant-pour-peigne.html')) + '</urlset>',
        E123 + 'legrand-hx3-peigne-tetrapolaire-18-modules.html':
            page('LEG405202', '3245064052023', 'LEGRAND HX3 Peigne d\'alimentation électrique tétrapolaire 18 modules - 405202', 'LEGRAND'),
        E123 + 'legrand-hx-isolant-pour-peigne.html':
            page('LEG404988', '3245064049887', 'LEGRAND HX Isolant pour peigne horizontal 12 modules découplable - 404988'),
        category: (f'<a href="{ED}1-peigne-vx3-legrand-ref-405003-3245064050036.html">x</a>'
                   f'<a href="{ED}2-module-raccordement-legrand-ref-406300-3245064063005.html">x</a>'),
        ED + '1-peigne-vx3-legrand-ref-405003-3245064050036.html':
            page('LEG-405003', '3245064050036', 'Peigne d\'alimentation vertical VX3 monophasée pour coffret 2 rangées Legrand Réf: 405003'),
        ED + '2-module-raccordement-legrand-ref-406300-3245064063005.html':
            page('LEG-406300', '3245064063005', 'Module de raccordement par peigne pour DX³ 2P jusqu\'à 63A Legrand Réf. 406300'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('peignes-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '405202'), ('elecdistrib', '405003')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille', 'Hors famille']


def test_contactor_family():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    pages = {
        sitemap: f'<urlset><url><loc>{E123}legrand-cx3-contacteur-jour-nuit-25a.html</loc></url></urlset>',
        E123 + 'legrand-cx3-contacteur-jour-nuit-25a.html':
            page('LEG412501', '3245064125017', 'LEGRAND CX3 Contacteur Jour / Nuit 25A 2F/NO monophasé - 412501', 'LEGRAND'),
        'https://www.elecdistrib.fr/139-contacteurs-legrand':
            f'<a href="{ED}1-contacteur-legrand-ref-412541-3245064125413.html">x</a>',
        ED + '1-contacteur-legrand-ref-412541-3245064125413.html':
            page('LEG-412541', '3245064125413', 'Contacteur de puissance CX³ 4 pôles 400V~ 63A contact 4F Legrand Réf: 412541'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('contacteurs-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '412501'), ('elecdistrib', '412541')]
    assert not result.rejected and not result.errors


def test_surge_protector_family_skips_spare_cartridges():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-parafoudre-monophase-type-2.html', 'legrand-cassette-rechange-parafoudre.html')) + '</urlset>',
        E123 + 'legrand-parafoudre-monophase-type-2.html':
            page('LEG003971', '3245060039714', 'LEGRAND Parafoudre monophasé autoprotégé type 2 12kA 230V - 003971', 'LEGRAND'),
        E123 + 'legrand-cassette-rechange-parafoudre.html':
            page('LEG003954', '3245060039547', 'LEGRAND Cassette de rechange pour parafoudre secteur - 003954'),
        'https://www.elecdistrib.fr/143-parafoudre-legrand': '',
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text is not None else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('parafoudres-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '003971')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']
    assert not result.errors


def test_isolating_switch_family_in_mixed_category():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/138-accessoires-modulaires-legrand'
    pages = {
        sitemap: f'<urlset><url><loc>{E123}legrand-dx3-interrupteur-sectionneur-bipolaire-40a.html</loc></url></urlset>',
        E123 + 'legrand-dx3-interrupteur-sectionneur-bipolaire-40a.html':
            page('LEG406440', '3245064064408', 'LEGRAND DX3 Interrupteur sectionneur bipolaire 400V 40A - 406440', 'LEGRAND'),
        category: (f'<a href="{ED}1-interrupteur-sectionneur-legrand-ref-406441-3245064064415.html">x</a>'
                   f'<a href="{ED}2-sonnerie-legrand-ref-004107-3245060041076.html">x</a>'),
        ED + '1-interrupteur-sectionneur-legrand-ref-406441-3245064064415.html':
            page('LEG-406441', '3245064064415', 'Interrupteur-Sectionneur 2P 63A DX3 Legrand Réf. 406441'),
        ED + '2-sonnerie-legrand-ref-004107-3245060041076.html':
            page('LEG-004107', '3245060041076', 'Sonnerie modulaire 230V~ - 83dB - 1 module Legrand Réf. 004107'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('sectionneurs-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '406440'), ('elecdistrib', '406441')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']


def test_time_switch_family_accepts_both_designations():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/142-horloge-modulaire-legrand'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-interrupteur-horaire-16a-journalier-412790.html', 'legrand-minuterie-412602.html')) + '</urlset>',
        E123 + 'legrand-interrupteur-horaire-16a-journalier-412790.html':
            page('LEG412790', '3245064127905', 'LEGRAND Interrupteur horaire 16A monophasé journalier 1 module - 412790', 'LEGRAND'),
        category: ''.join(f'<a href="{ED}{slug}">x</a>' for slug in (
            '1-horloge-digitale-legrand-ref-412641-3245064126410.html',
            '2-interrupteur-crepusculaire-legrand-ref-412623-3245064126236.html')),
        ED + '1-horloge-digitale-legrand-ref-412641-3245064126410.html':
            page('LEG-412641', '3245064126410', 'Horloge digitale programmable Legrand Réf: 412641'),
        ED + '2-interrupteur-crepusculaire-legrand-ref-412623-3245064126236.html':
            page('LEG-412623', '3245064126236', 'Interrupteur crépusculaire standard Legrand Réf: 412623'),
    }
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('horloges-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '412790'), ('elecdistrib', '412641')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']
    assert not any('minuterie' in url for url in calls)  # filtered by the sitemap address


def test_distribution_block_family_skips_terminal_strips():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/138-accessoires-modulaires-legrand'
    pages = {
        sitemap: f'<urlset><url><loc>{E123}legrand-repartiteur-tetrapolaire-100a-400405.html</loc></url></urlset>',
        E123 + 'legrand-repartiteur-tetrapolaire-100a-400405.html':
            page('LEG400405', '3245064004053', 'LEGRAND Répartiteur tétrapolaire modulaire 100A - 400405', 'LEGRAND'),
        category: ''.join(f'<a href="{ED}{slug}">x</a>' for slug in (
            '1-repartiteur-bipolaire-40a-legrand-ref-400400-3245064004008.html',
            '2-bornier-repartition-neutre-legrand-ref-004850-3245060048501.html')),
        ED + '1-repartiteur-bipolaire-40a-legrand-ref-400400-3245064004008.html':
            page('LEG-400400', '3245064004008', 'Répartiteur modulaire à barreaux étagés bipolaire 40A 12 départs Legrand Réf. 400400'),
        ED + '2-bornier-repartition-neutre-legrand-ref-004850-3245060048501.html':
            page('LEG-004850', '3245060048501', 'Bornier répartition neutre Legrand Réf: 004850'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('repartiteurs-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '400405'), ('elecdistrib', '400400')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']


def test_terminal_strip_family_is_distinct_from_distribution_blocks():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/138-accessoires-modulaires-legrand'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-drivia-bornier-de-terre-405055.html', 'legrand-support-universel-pour-borniers-004811.html')) + '</urlset>',
        E123 + 'legrand-drivia-bornier-de-terre-405055.html':
            page('LEG405055', '3245064050555', 'LEGRAND Drivia Bornier de terre pour tableau électrique - 405055', 'LEGRAND'),
        E123 + 'legrand-support-universel-pour-borniers-004811.html':
            page('LEG004811', '3245060048112', 'LEGRAND Support universel pour borniers sur rails DIN - 004811'),
        category: ''.join(f'<a href="{ED}{slug}">x</a>' for slug in (
            '1-repartiteur-bipolaire-40a-legrand-ref-400400-3245064004008.html',
            '2-bornier-repartition-neutre-legrand-ref-004850-3245060048501.html')),
        ED + '1-repartiteur-bipolaire-40a-legrand-ref-400400-3245064004008.html':
            page('LEG-400400', '3245064004008', 'Répartiteur modulaire à barreaux étagés bipolaire 40A 12 départs Legrand Réf. 400400'),
        ED + '2-bornier-repartition-neutre-legrand-ref-004850-3245060048501.html':
            page('LEG-004850', '3245060048501', 'Bornier répartition neutre Legrand Réf: 004850'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('borniers-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '405055'), ('elecdistrib', '004850')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille', 'Hors famille']


def test_gtl_family_keeps_complete_ducts_only():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/141-gtl-gaine-technique-de-logement-legrand'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-drivia-goulotte-gtl-13-modules-030037.html',
            'legrand-drivia-embout-pour-gaine-technique-logement-gtl-030087.html')) + '</urlset>',
        E123 + 'legrand-drivia-goulotte-gtl-13-modules-030037.html':
            page('LEG030037', '3245060300371', 'LEGRAND Drivia Goulotte GTL 13 modules 2 compartiments avec couvercle complet - 030037', 'LEGRAND'),
        E123 + 'legrand-drivia-embout-pour-gaine-technique-logement-gtl-030087.html':
            page('LEG030087', '3245060300876', 'LEGRAND Drivia Embout pour gaine technique logement GTL 13 modules - 030087'),
        category: f'<a href="{ED}1-cornet-gtl-legrand-ref-030071-3245060300715.html">x</a>',
        ED + '1-cornet-gtl-legrand-ref-030071-3245060300715.html':
            page('LEG-030071', '3245060300715', 'Cornet d\'épanouissement pour jonction goulotte avec plafond et sol pour GTL DRIVIA 18 modules Legrand Réf: 030071'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('gtl-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '030037')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille', 'Hors famille']


def test_gtl_and_accessory_families_split_the_same_pages():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/141-gtl-gaine-technique-de-logement-legrand'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-drivia-goulotte-gtl-13-modules-030037.html',
            'legrand-drivia-jonction-sol-plafond-pour-gaine-technique-030095.html')) + '</urlset>',
        E123 + 'legrand-drivia-goulotte-gtl-13-modules-030037.html':
            page('LEG030037', '3245060300371', 'LEGRAND Drivia Goulotte GTL 13 modules 2 compartiments avec couvercle complet - 030037', 'LEGRAND'),
        E123 + 'legrand-drivia-jonction-sol-plafond-pour-gaine-technique-030095.html':
            page('LEG030095', '3245060300951', 'LEGRAND Drivia Jonction sol/plafond pour gaine technique logement GTL 13 modules - 030095'),
        category: f'<a href="{ED}1-embout-gtl-legrand-ref-030087-3245060300876.html">x</a>',
        ED + '1-embout-gtl-legrand-ref-030087-3245060300876.html':
            page('LEG-030087', '3245060300876', 'Embout d\'extrémité pour goulotte GTL DRIVIA 13 modules Legrand Réf: 030087'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    found = {}
    for family in ('gtl-legrand', 'accessoires-gtl-legrand'):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = discover(family, client=client, pause=lambda _: None)
        found[family] = {ref for _, ref, _, _ in result.links}
    assert found == {'gtl-legrand': {'030037'}, 'accessoires-gtl-legrand': {'030095', '030087'}}


def test_drivia_family_keeps_bare_enclosures_only():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/130-tableaux-vides-portes'
    slugs = {
        'legrand-drivia-tableau-electrique-nu-2-rangees-13-modules-401212.html':
            ('LEG401212', '3245064012126', 'LEGRAND Drivia Tableau électrique nu 2 rangées 13 modules - 401212'),
        'legrand-drivia-porte-blanche-pour-tableau-electrique-2-rangees-401332.html':
            ('LEG401332', '3245064013321', 'LEGRAND Drivia Porte blanche pour tableau électrique 2 rangées 13 modules - 401332'),
        'legrand-drivia-tableau-pre-cable-200880.html':
            ('LEG200880', '3245062008800', 'LEGRAND Drivia Tableau électrique pré-câblé à vis 1 rangée 1ID 63A 3 disjoncteurs - 200880'),
        'legrand-drivia-coffret-de-communication-413248.html':
            ('LEG413248', '3245064132480', 'LEGRAND Drivia Coffret de communication Grade 2TV 13 modules - 413248'),
        'legrand-drivia-peigne-vertical-405002.html':
            ('LEG405002', '3245064050029', 'LEGRAND Drivia Peigne vertical 4 rangées entraxe 125mm - 405002'),
    }
    pages = {sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in slugs) + '</urlset>',
             category: f'<a href="{ED}1-coffret-drivia-legrand-ref-401213-3245064012133.html">x</a>',
             ED + '1-coffret-drivia-legrand-ref-401213-3245064012133.html':
                 page('LEG-401213', '3245064012133', 'Coffret Drivia 3 rangées 13 modules IP30 IK05 nu Legrand Réf: 401213')}
    pages.update({E123 + slug: page(*data) for slug, data in slugs.items()})

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('coffrets-drivia-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '401212'), ('elecdistrib', '401213')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille'] * 4


DRIVIA_PAGES = {
    'legrand-drivia-porte-blanche-pour-tableau-electrique-2-rangees-401332.html':
        ('LEG401332', '3245064013321', 'LEGRAND Drivia Porte blanche pour tableau électrique 2 rangées 13 modules - 401332'),
    'legrand-drivia-rehausse-pour-coffret-electrique-2-rangees-401372.html':
        ('LEG401372', '3245064013727', 'LEGRAND Drivia Rehausse pour coffret électrique 2 rangées 13 modules - 401372'),
    'legrand-drivia-tableau-electrique-nu-2-rangees-401212.html':
        ('LEG401212', '3245064012126', 'LEGRAND Drivia Tableau électrique nu 2 rangées 13 modules - 401212'),
}


@pytest.mark.parametrize('family,expected', [
    ('portes-drivia-legrand', [('123elec', '401332'), ('elecdistrib', '401342')]),
    ('rehausses-drivia-legrand', [('123elec', '401372')]),
])
def test_drivia_doors_and_spacers_are_separate_families(family, expected):
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/130-tableaux-vides-portes'
    pages = {sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in DRIVIA_PAGES) + '</urlset>',
             category: ''.join(f'<a href="{ED}{slug}">x</a>' for slug in (
                 '1-porte-drivia-transparente-legrand-ref-401342-3245064013420.html',
                 '2-porte-reversible-pour-bac-legrand-ref-401454-3414971234567.html')),
             ED + '1-porte-drivia-transparente-legrand-ref-401342-3245064013420.html':
                 page('LEG-401342', '3245064013420', 'Porte Drivia transparente IP40 - IK07 2 rangées 13 modules Legrand Réf: 401342'),
             ED + '2-porte-reversible-pour-bac-legrand-ref-401454-3414971234567.html':
                 page('LEG-401454', '3414971234567', 'Porte réversible pour bac 1 travée DRIVIA 18 modules Legrand Réf: 401454')}
    pages.update({E123 + slug: page(*data) for slug, data in DRIVIA_PAGES.items()})
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover(family, client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == expected
    assert not any('tableau-electrique-nu' in url for url in calls)  # filtered by the sitemap address


def test_pre_equipped_boards_family():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/131-tableaux-pre-equipes-portes'
    pages = {
        sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in (
            'legrand-drivia-tableau-electrique-pre-cable-a-vis-1-rangee-200880.html',
            'legrand-celiane-prise-de-courant-precablee-2x2p-t-cm0112.html')) + '</urlset>',
        E123 + 'legrand-drivia-tableau-electrique-pre-cable-a-vis-1-rangee-200880.html':
            page('LEG200880', '3245062008800', 'LEGRAND Drivia Tableau électrique pré-câblé à vis 1 rangée 1ID 63A 3 disjoncteurs - 200880', 'LEGRAND'),
        category: ''.join(f'<a href="{ED}{slug}">x</a>' for slug in (
            '1-tableau-prequipe-legrand-ref-093060-3414971930604.html',
            '2-porte-drivia-transparente-legrand-ref-401342-3245064013420.html')),
        ED + '1-tableau-prequipe-legrand-ref-093060-3414971930604.html':
            page('LEG-093060', '3414971930604', 'Tableau 1 rangée 9 modules prééquipé Legrand Réf: 093060'),
        ED + '2-porte-drivia-transparente-legrand-ref-401342-3245064013420.html':
            page('LEG-401342', '3245064013420', 'Porte Drivia transparente IP40 - IK07 2 rangées 13 modules Legrand Réf: 401342'),
    }
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('tableaux-pre-equipes-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '200880'), ('elecdistrib', '093060')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']
    assert not any('prise' in url for url in calls)  # filtered by the sitemap address


def test_communication_enclosure_family_skips_modules():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/24-coffret-de-communication-legrand-portes'
    pages = {
        sitemap: f'<urlset><url><loc>{E123}legrand-drivia-coffret-de-communication-grade-2tv-413248.html</loc></url></urlset>',
        E123 + 'legrand-drivia-coffret-de-communication-grade-2tv-413248.html':
            page('LEG413248', '3245064132480', 'LEGRAND Drivia Coffret de communication Grade 2TV 13 modules - 4RJ45 - 413248', 'LEGRAND'),
        category: ''.join(f'<a href="{ED}{slug}">x</a>' for slug in (
            '1-coffret-drivia-multimedia-legrand-ref-413261-3245064132619.html',
            '2-dti-modulaire-rj45-pour-coffret-multimedia-legrand-ref-413008-3245064130080.html')),
        ED + '1-coffret-drivia-multimedia-legrand-ref-413261-3245064132619.html':
            page('LEG-413261', '3245064132619', 'Coffret Drivia multimédia 13 modules Double Play Legrand Réf: 413261'),
        ED + '2-dti-modulaire-rj45-pour-coffret-multimedia-legrand-ref-413008-3245064130080.html':
            page('LEG-413008', '3245064130080', 'DTI modulaire RJ45 pour coffret multimédia Legrand Réf: 413008'),
    }

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('coffrets-communication-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '413248'), ('elecdistrib', '413261')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']


def test_communication_modules_exclude_enclosures_with_patch_panel():
    category = 'https://www.elecdistrib.fr/24-coffret-de-communication-legrand-portes'
    slugs = {
        '1-module-de-brassage-rj45-legrand-ref-413003-3245064130035.html':
            ('LEG-413003', '3245064130035', 'Module de brassage RJ45 pour réseau multimédia Legrand Réf: 413003'),
        '2-repartiteur-tv-legrand-ref-413013-3245064130134.html':
            ('LEG-413013', '3245064130134', 'Répartiteur TV Hertzien TNT 6 sorties 4 modules Legrand Réf: 413013'),
        '3-coffret-avec-brassage-legrand-ref-413218-3245064132183.html':
            ('LEG-413218', '3245064132183', 'Coffret de communication basique avec brassage Legrand Réf: 413218'),
        '4-porte-drivia-legrand-ref-401342-3245064013420.html':
            ('LEG-401342', '3245064013420', 'Porte Drivia transparente IP40 - IK07 2 rangées 13 modules Legrand Réf: 401342'),
    }
    pages = {'https://www.123elec.com/media/sitemap/sitemap.xml': '<urlset></urlset>',
             category: ''.join(f'<a href="{ED}{slug}">x</a>' for slug in slugs)}
    pages.update({ED + slug: page(*data) for slug, data in slugs.items()})

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    found = {}
    for family in ('modules-communication-legrand', 'coffrets-communication-legrand'):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            found[family] = {ref for _, ref, _, _ in discover(family, client=client, pause=lambda _: None).links}
    assert found == {'modules-communication-legrand': {'413003', '413013'},
                     'coffrets-communication-legrand': {'413218'}}


def test_twilight_switch_family_skips_spare_cells():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/142-horloge-modulaire-legrand'
    slugs = {
        'legrand-interrupteur-crepusculaire-16a-412623.html':
            ('LEG412623', '3245064126236', 'LEGRAND Interrupteur crépusculaire 16A avec cellule extérieure - 412623', 'LEGRAND'),
        'legrand-cellule-photoelectrique-pour-interrupteur-crepusculaire-412860.html':
            ('LEG412860', '3245064128605', 'LEGRAND Cellule photoélectrique IP65 pour interrupteur crépusculaire modulaire - 412860'),
    }
    pages = {sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in slugs) + '</urlset>',
             category: f'<a href="{ED}1-horloge-digitale-legrand-ref-412641-3245064126410.html">x</a>',
             ED + '1-horloge-digitale-legrand-ref-412641-3245064126410.html':
                 page('LEG-412641', '3245064126410', 'Horloge digitale programmable Legrand Réf: 412641')}
    pages.update({E123 + slug: page(*data) for slug, data in slugs.items()})

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('crepusculaires-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '412623')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille', 'Hors famille']


def test_yokis_family_reads_commercial_reference_on_123elec_only():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    slugs = {
        'yokis-micro-module-telerupteur-encastre.html':
            ('YOKMTR500E', '3760054540507', 'YOKIS Télérupteur 2.2A 500VA micro-module encastré - MTR500E', 'YOKIS'),
        'yokis-up-kit-radio-va-et-vient-1-telerupteur-et-2-emetteurs-radio-kitvv-up.html':
            ('YOK-KITVV-UP', '3760248204604', 'YOKIS UP Kit radio va et vient 1 télérupteur et 2 émetteurs radio - KITVV-UP', 'YOKIS'),
        'legrand-telerupteur-16a.html': ('LEG412408', '3245064124089', 'LEGRAND Télérupteur 16A - 412408'),
    }
    pages = {sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in slugs) + '</urlset>'}
    pages.update({E123 + slug: page(*data) for slug, data in slugs.items()})
    requested = []

    def handler(request):
        requested.append(request.url.host)
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('yokis', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', 'MTR500E'), ('123elec', 'KITVV-UP')]
    assert result.links[0][3].brand == 'Yokis'
    assert 'www.elecdistrib.fr' not in requested


def test_energy_meter_family_skips_meter_mounting_plates():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/144-ecocompteur-legrand'
    slugs = {
        'legrand-emdx-compteur-d-energie-45a-monophase-certifie-mid-412069.html':
            ('LEG412069', '3245064120692', 'LEGRAND EMDX³ Compteur d\'énergie 45A monophasé certifié MID - 412069', 'LEGRAND'),
        'legrand-drivia-platine-pour-compteur-linky-et-cbe-et-ou-disjoncteur-de-branchement-401182.html':
            ('LEG401182', '3245064011822', 'LEGRAND Drivia Platine pour compteur Linky et CBE et/ou disjoncteur de branchement - 401182'),
    }
    pages = {sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in slugs) + '</urlset>',
             category: f'<a href="{ED}1-ecocompteur-modulaire-ip-legrand-ref-412000-3245064120005.html">x</a>',
             ED + '1-ecocompteur-modulaire-ip-legrand-ref-412000-3245064120005.html':
                 page('LEG-412000', '3245064120005', 'Ecocompteur modulaire IP pour mesure consommation 6 postes Legrand Réf. 412000')}
    pages.update({E123 + slug: page(*data) for slug, data in slugs.items()})

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('compteurs-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [('123elec', '412069'), ('elecdistrib', '412000')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']


def test_emergency_lighting_family_ignores_satin_plates():
    sitemap = 'https://www.123elec.com/media/sitemap/sitemap.xml'
    category = 'https://www.elecdistrib.fr/214-baes'
    slugs = {
        'legrand-baes-d-evacuation-sati-connecte-45lm-a-led-062525.html':
            ('LEG062525', '3245060625252', 'LEGRAND BAES d\'évacuation SATI connecté 45lm à LED - 062525', 'LEGRAND'),
        'legrand-telecommande-baes-multifonctions-sati-connecte-062520.html':
            ('LEG062520', '3245060625207', 'LEGRAND Télécommande BAES multifonctions SATI connecté - 062520', 'LEGRAND'),
        'legrand-baes-celiane-plaque-simple-acier-satine-cp1801.html':
            ('LEGCP1801', '3245060718015', 'LEGRAND Céliane Plaque simple acier satiné - CP1801'),
    }
    pages = {sitemap: '<urlset>' + ''.join(f'<url><loc>{E123}{slug}</loc></url>' for slug in slugs) + '</urlset>',
             category: f'<a href="{ED}1-baes-encastre-kickspot-legrand-ref-062524-3245060625245.html">x</a>',
             ED + '1-baes-encastre-kickspot-legrand-ref-062524-3245060625245.html':
                 page('LEG-062524', '3245060625245', 'BAES d\'évacuation encastré à LEDs Kickspot SATI connecté Legrand Réf: 062524')}
    pages.update({E123 + slug: page(*data) for slug, data in slugs.items()})

    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='')
        text = pages.get(str(request.url))
        return httpx.Response(200, text=text) if text else httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = discover('securite-legrand', client=client, pause=lambda _: None)
    assert [(key, ref) for key, ref, _, _ in result.links] == [
        ('123elec', '062525'), ('123elec', '062520'), ('elecdistrib', '062524')]
    assert [reason for *_, reason in result.rejected] == ['Hors famille']
