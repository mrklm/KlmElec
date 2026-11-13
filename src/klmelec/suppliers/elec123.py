from .base import Connector, ProductLink, OfferError, money

class Elec123(Connector):
    host = 'www.123elec.com'
    links = {
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
            if node.get_text(strip=True) or node.get('data-price-amount'):
                raise OfferError('Éco-participation à vérifier')
