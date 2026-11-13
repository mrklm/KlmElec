import json
from decimal import Decimal
from .base import Connector, ProductLink, OfferError, money

class ElecDistrib(Connector):
    host = 'www.elecdistrib.fr'
    links = {
        '406774': ProductLink('https://www.elecdistrib.fr/disjoncteurs-legrand/372-lot-de-10-x-16a-legrand-ref-406774-3245064067744.html', 'LEG-406774x10', '3245064067744', 10),
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
