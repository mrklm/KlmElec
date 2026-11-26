"""Exécution réseau en arrière-plan et présentation des relevés datés."""
from datetime import datetime
from decimal import Decimal
from html import escape

from PySide6.QtCore import QThread, Signal

from .comparison import compare, best_offer, is_recent


def euros(value):
    return f'{value:.2f} €'.replace('.', ',')


def local_date(value):
    return datetime.fromisoformat(value).astimezone().strftime('%d/%m/%Y %H:%M:%S')


def render_report(payload, historical=False):
    heading = 'Historique — prix non revérifiés' if historical else 'Résultats du relevé'
    parts = [f'<h3>{heading}</h3>', f'<p>{escape(local_date(payload["date"]))} · TVA utilisée : {escape(payload["vat"])} % · Hors livraison.</p>',
             '<p>HT calculé à partir du TTC avec le taux indiqué. Un résultat incomplet ne désigne aucun fournisseur gagnant.</p>']
    for item in payload['items']:
        offers = [o for o in payload['offers'] if o['product_id'] == item['id']]
        winner = best_offer(offers) if not historical else None
        parts.append(f'<h4>{escape(item["name"])} — {escape(item["reference"])} × {item["quantity"]}</h4>')
        if not offers:
            parts.append('<p>Aucun fournisseur actif.</p>')
        for offer in offers:
            price = euros(Decimal(offer['ttc'])) if offer['ttc'] is not None else '—'
            delta = ''
            if winner and offer['status'] == 'ok':
                delta = f' · Écart au minimum : {euros(Decimal(offer["ttc"]) - Decimal(winner["ttc"]))}'
            if not is_recent(offer):
                delta += ' · Relevé ancien, à actualiser'
            source = f' · <a href="{escape(offer["url"], quote=True)}">Fiche produit</a>' if offer['url'] else ''
            parts.append(f'<p><b>{escape(offer["supplier"])}</b> : {price} TTC{delta}<br>'
                         f'{escape(offer["detail"])} · {escape(local_date(offer["checked_at"]))}{source}</p>')
        if winner:
            tied = [o['supplier'] for o in offers if o['ttc'] is not None and Decimal(o['ttc']) == Decimal(winner['ttc'])]
            parts.append(f'<p>Minimum parmi les fournisseurs actifs : {escape(", ".join(tied))}.</p>')
        elif not historical:
            parts.append('<p>Comparaison incomplète ou offres non comparables : aucun minimum validé.</p>')
    return ''.join(parts)


class ComparisonWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)
    step = Signal(int, int)  # requêtes traitées, total (articles × fournisseurs actifs)

    def __init__(self, items, suppliers, previous, parent=None, links=None):
        super().__init__(parent)
        self.items, self.suppliers, self.previous, self.links = items, suppliers, previous, links

    def run(self):
        total = len(self.items) * sum(1 for s in self.suppliers if s['active'])
        done = 0

        def progress(text):
            nonlocal done
            self.step.emit(done, total)
            done += 1
            self.progress.emit(text)

        try:
            self.step.emit(0, total)
            offers = compare(self.items, self.suppliers, self.previous,
                             progress, self.isInterruptionRequested, links=self.links)
            self.completed.emit(offers)
        except Exception:
            self.failed.emit('La comparaison a échoué. Les anciens relevés sont conservés.')
