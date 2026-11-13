from .base import Connector, ProductLink, OfferError, money

class Elec123(Connector):
    host = 'www.123elec.com'
    links = {
        '405001': ProductLink('https://www.123elec.com/legrand-drivia-peigne-vertical-pour-tableau-electrique-drivia-3-rangees-entraxe-125-mm.html', 'LEG405001', '3245064050012'),
        '412408': ProductLink('https://www.123elec.com/legrand-cx3-telerupteur-16a.html', 'LEG412408', '3245064124089'),
        '404926': ProductLink('https://www.123elec.com/legrand-peigne-universel-d-alimentation-electrique-13-modules.html', 'LEG404926', '3245064049269'),
        '405000': ProductLink('https://www.123elec.com/legrand-drivia-peigne-vertical-pour-tableau-electrique-drivia-2-rangees-entraxe-125-mm.html', 'LEG405000', '3245064050005'),
        'WAG2106-5201': ProductLink('https://www.123elec.com/wago-topjobrs-borne-de-passage-a-levier-2-fils-6mm-gris-2106-5201.html', 'WAG2106-5201', '4055143742450', brand='Wago', manufacturer_reference='2106-5201'),
        'WAG2106-5204': ProductLink('https://www.123elec.com/wago-topjobrs-borne-de-passage-a-levier-2-fils-6mm-bleu-2106-5204.html', 'WAG2106-5204', '4055143742467', brand='Wago', manufacturer_reference='2106-5204'),
        'WAG2106-5207': ProductLink('https://www.123elec.com/wago-topjobrs-borne-de-passage-a-levier-2-fils-6mm-vert-jaune-2106-5207.html', 'WAG2106-5207', '4055143742474', brand='Wago', manufacturer_reference='2106-5207'),
        'WAG2106-1291': ProductLink('https://www.123elec.com/wago-topjobrs-plaque-d-extremite-pour-borne-de-passage-2106-2106-1291.html', 'WAG2106-1291', '4055143745383', brand='Wago', manufacturer_reference='2106-1291'),
        '406771': ProductLink('https://www.123elec.com/legrand-disjoncteur-electrique-dnx3-uni-neutre-2a.html', 'LEG406771', '3245064067713', 1),
        '406773': ProductLink('https://www.123elec.com/legrand-disjoncteur-electrique-dnx3-uni-neutre-10a.html', 'LEG406773', '3245064067737', 1),
        '406775': ProductLink('https://www.123elec.com/legrand-disjoncteur-electrique-dnx3-uni-neutre-20a.html', 'LEG406775', '3245064067751', 1),
        '406777': ProductLink('https://www.123elec.com/legrand-disjoncteur-electrique-dnx3-uni-neutre-32a.html', 'LEG406777', '3245064067775', 1),
        '411633': ProductLink('https://www.123elec.com/legrand-interrupteur-differentiel-63a-30ma-type-ac-dx3-auto.html', 'LEG411633', '3245064116336', 1),
        '406774': ProductLink('https://www.123elec.com/legrand-disjoncteur-electrique-dnx3-uni-neutre-16a.html', 'LEG406774', '3245064067744', 1),
        '411617': ProductLink('https://www.123elec.com/legrand-interrupteur-differentiel-dx3-40a-30ma-type-a.html', 'LEG411617', '3245064116176', 1),
        '411638': ProductLink('https://www.123elec.com/legrand-interrupteur-differentiel-40a-30ma-typea-dx3-auto.html', 'LEG411638', '3245064116381', 1),
    }
    def validate_page(self, soup, price, link):
        # These unit references were checked against the supplier's TTC terms.
        # A second product-specific price must agree with the structured offer.
        meta = soup.find('meta', attrs={'property': 'product:price:amount'})
        if not meta or money(meta.get('content')) != price:
            raise OfferError('Prix de la fiche et offre incohérents')
        # Fail closed if a product-specific environmental surcharge appears.
        for node in soup.select('.weee, .weee-tax, .price-including-tax .weee, [data-price-type="weee"]'):
            # Recommended products have their own price/tax markup, unrelated
            # to the product identified by the SKU and EAN above.
            if node.find_parent(class_='product-item'):
                continue
            # Magento also adds "weee" to ordinary quantity-discount prices.
            # Keep the standard unit price; explicit tax nodes are checked below.
            classes = node.get('class', [])
            if ('price-container' in classes and 'price-tier_price' in classes
                    and node.select_one('.price-wrapper[data-price-amount]')
                    and 'weee-tax' not in classes and node.get('data-price-type') != 'weee'):
                continue
            if node.get_text(strip=True) or node.get('data-price-amount'):
                raise OfferError('Éco-participation à vérifier')
