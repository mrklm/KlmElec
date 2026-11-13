"""Sonde ponctuelle de fiches publiques connues ; aucun connecteur de production."""
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

PAGES = {
    '123elec-406774': 'https://www.123elec.com/legrand-disjoncteur-electrique-dnx3-uni-neutre-16a.html',
    '123elec-411617': 'https://www.123elec.com/legrand-interrupteur-differentiel-dx3-40a-30ma-type-a.html',
    '123elec-411638': 'https://www.123elec.com/legrand-interrupteur-differentiel-40a-30ma-typea-dx3-auto.html',
    'elecdistrib-411617': 'https://www.elecdistrib.fr/interrupteurs-differentiels-legrand/69-dx3-40a-type-a-legrand-ref-411617-3245064116176.html',
    'elecdistrib-411638': 'https://www.elecdistrib.fr/interrupteurs-differentiels-legrand/71-interrupteur-differentiel-dx-id-arrivee-haut-visdepart-haut-auto-2p-230v-40a-type-a-30-ma-2-modules-legrand-ref-411638-3245064116381.html',
    'elecdistrib-406774-lot10': 'https://www.elecdistrib.fr/disjoncteurs-legrand/372-lot-de-10-x-16a-legrand-ref-406774-3245064067744.html',
}

def main():
    output = Path('local-study')
    output.mkdir(exist_ok=True)
    results = []
    for key, url in PAGES.items():
        result = {'page': key, 'url': url, 'consultation_utc': datetime.now(timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'KlmElec-feasibility/0.0.1'})
            with urllib.request.urlopen(request, timeout=20) as response:
                html = response.read(5_000_000).decode('utf-8', errors='replace')
                result.update(status=response.status, final_url=response.url)
            (output / (key + '.html')).write_text(html)
            blocks = re.findall(r'<script\b[^>]*type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>', html, re.S | re.I)
            result['json_ld'] = []
            for block in blocks:
                try:
                    result['json_ld'].append(json.loads(block))
                except ValueError:
                    result['json_ld'].append({'erreur': 'JSON-LD invalide'})
            result['title'] = [unescape(re.sub('<[^>]+>', '', t)).strip() for t in re.findall(r'<h1\b[^>]*>(.*?)</h1>', html, re.S | re.I)]
            result['price_markers'] = re.findall(r'.{0,90}(?:itemprop="price"|data-price-amount|product-price|price-tax|priceCurrency).{0,180}', html)[:15]
        except Exception as exc:
            result['erreur'] = str(exc)
        results.append(result)
        print(key, result.get('status', result.get('erreur')), flush=True)
        time.sleep(2)
    (output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
