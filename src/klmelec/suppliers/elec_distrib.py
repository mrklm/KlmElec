import json
from decimal import Decimal
from .base import Connector, ProductLink, OfferError, money

class ElecDistrib(Connector):
    host = 'www.elecdistrib.fr'
    links = {
        '405001': ProductLink('https://www.elecdistrib.fr/accessoires-modulaires-legrand/64-peigne-d-alimentation-verticale-vx3-optimisee-monophasee-pour-tableau-drivia-3-rangees-entraxe-125mm-legrand-ref-405001-3245064050012.html', 'LEG-405001', '3245064050012'),
        '404926': ProductLink('https://www.elecdistrib.fr/tableaux-composants/61-peigne-d-alimentation-universel-13-modules-phase-neutre-hx3-horizontal-1p-legrand-ref-404926-3245064049269.html', 'LEG-404926', '3245064049269'),
        '405000': ProductLink('https://www.elecdistrib.fr/accessoires-modulaires-legrand/63-peigne-d-alimentation-verticale-vx-optimisee-monophasee-pour-tableau-drivia-2-rangees-entraxe-125mm-legrand-ref-405000-3245064050005.html', 'LEG-405000', '3245064050005'),
        '412408': ProductLink('https://www.elecdistrib.fr/telerupteurs-legrand/111-telerupteur-cx-standard-avec-bornes-a-vis-16a-250v-1-module-legrand-ref-412408-3245064124089.html', 'LEG-412408', '3245064124089'),
        '406771': ProductLink('https://www.elecdistrib.fr/disjoncteurs-legrand/76-disjoncteur-phase-neutre-dnx3-4500-6ka-arrivee-et-sortie-borne-a-vis-1pn-230v-2a-courbe-c-legrand-ref-406771-3245064067713.html', 'LEG-406771', '3245064067713', 1),
        '406773': ProductLink('https://www.elecdistrib.fr/disjoncteurs-legrand/75-disjoncteur-phase-neutre-dnx3-4500-6ka-arrivee-et-sortie-borne-a-vis-1pn-230v-10a-courbe-c-legrand-ref-406773-3245064067737.html', 'LEG-406773', '3245064067737', 1),
        '406775': ProductLink('https://www.elecdistrib.fr/disjoncteurs-legrand/73-disjoncteur-phase-neutre-dnx3-4500-6-ka-arrivee-et-sortie-borne-a-vis-1pn-230v-20a-courbe-c-legrand-ref-406775-3245064067751.html', 'LEG-406775', '3245064067751', 1),
        '406777': ProductLink('https://www.elecdistrib.fr/disjoncteurs-legrand/72-disjoncteur-phase-neutre-dnx-4500-6ka-arrivee-et-sortie-borne-a-vis-1pn-230v-32a-courbe-c-legrand-ref-406777-3245064067775.html', 'LEG-406777', '3245064067775', 1),
        '411633': ProductLink('https://www.elecdistrib.fr/tableaux-composants/657-interrupteur-differentiel-63a-type-ac-3-modules-legrand-ref-411633-3245064116336.html', 'LEG-411633', '3245064116336', 1),
        '406774': ProductLink('https://www.elecdistrib.fr/disjoncteurs-legrand/74-disjoncteur-phase-neutre-dnx3-4500-6ka-arrivee-et-sortie-borne-a-vis-1pn-230v-16a-courbe-c-legrand-ref-406774-3245064067744.html', 'LEG-406774', '3245064067744', 1),
        '411617': ProductLink('https://www.elecdistrib.fr/interrupteurs-differentiels-legrand/69-dx3-40a-type-a-legrand-ref-411617-3245064116176.html', 'LEG-411617', '3245064116176', 1),
        '411638': ProductLink('https://www.elecdistrib.fr/interrupteurs-differentiels-legrand/71-interrupteur-differentiel-dx-id-arrivee-haut-visdepart-haut-auto-2p-230v-40a-type-a-30-ma-2-modules-legrand-ref-411638-3245064116381.html', 'LEG-411638', '3245064116381', 1),
    }
    def validate_page(self, soup, price, link):
        node = next((n for n in soup.select('.pricettcproduct') if 'TTC' in n.get_text()), None)
        if not node or money(node.get('content')) != price or 'TTC' not in node.get_text():
            raise OfferError('Prix TTC de la fiche non confirmé')
        quantity = soup.select_one('#quantity_wanted')
        if not quantity or Decimal(quantity.get('min', '0')) != 1:
            raise OfferError('Quantité minimale non confirmée')
        node = soup.select_one('[data-product]')
        if not node:
            raise OfferError('Conditions de vente absentes')
        try:
            product = json.loads(node['data-product'], parse_float=Decimal)
            if product.get('reference') != link.sku:
                raise OfferError('Référence fournisseur incohérente')
            if Decimal(str(product.get('ecotax', '0'))) != 0:
                raise OfferError('Éco-participation à vérifier')
            if int(product.get('minimal_quantity', 0)) != 1:
                raise OfferError('Quantité minimale non comparable')
        except (ValueError, TypeError, ArithmeticError):
            raise OfferError('Conditions tarifaires à vérifier') from None
