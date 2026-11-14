"""Paramètres → Catalogue : recherche automatique d'une famille de produits."""
from collections import Counter
from html import escape

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                               QPushButton, QTextBrowser)

from .comparison import now
from .discovery import FAMILIES, discover
from .suppliers import CONNECTORS


class DiscoveryWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, family, known, parent=None):
        super().__init__(parent)
        self.family, self.known = family, known

    def run(self):
        try:
            self.completed.emit(discover(self.family, self.known, self.progress.emit,
                                         self.isInterruptionRequested))
        except Exception:
            self.failed.emit('La recherche a échoué. Le catalogue n’a pas été modifié.')


class CatalogPage(QWidget):
    changed = Signal()
    finished = Signal()

    def __init__(self, store, can_start=lambda: True):
        super().__init__()
        self.store, self.can_start = store, can_start
        self.worker = None
        layout = QVBoxLayout(self)
        note = QLabel('Recherchez automatiquement les produits d’une famille chez 123 Elec et Elec Distrib. '
                      'Chaque fiche est ouverte et contrôlée (référence, EAN, marque, prix TTC, conditionnement) '
                      'avant d’être ajoutée au catalogue. Les lots sont exclus.\n'
                      'Une requête par seconde : comptez quelques minutes. Les articles existants ne sont pas modifiés.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.family = QComboBox()
        for key, family in FAMILIES.items():
            self.family.addItem(family.label, key)
        controls.addWidget(self.family, 1)
        self.start_button = QPushButton('Rechercher')
        self.start_button.clicked.connect(self.start)
        controls.addWidget(self.start_button)
        self.cancel_button = QPushButton('Annuler')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        controls.addWidget(self.cancel_button)
        layout.addLayout(controls)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.report = QTextBrowser()
        self.report.setOpenExternalLinks(True)
        layout.addWidget(self.report, 1)
        self.show_counts()

    def busy(self):
        return self.worker is not None

    def show_counts(self):
        counts = Counter({key: len(links) for key, links in self.store.product_links().items()})
        text = ' · '.join(f'{CONNECTORS[key].host} : {counts[key]}' for key in CONNECTORS)
        self.status.setText(f'Fiches découvertes enregistrées — {text}')

    def start(self):
        if self.busy():
            return
        if not self.can_start():
            self.status.setText('Une comparaison des prix est en cours. Veuillez patienter avant de lancer la recherche.')
            return
        known = {(key, ref) for key, connector in CONNECTORS.items() for ref in connector.links}
        self.start_button.setEnabled(False)
        self.family.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.report.clear()
        self.worker = DiscoveryWorker(self.family.currentData(), known, self)
        self.worker.progress.connect(self.status.setText)
        self.worker.completed.connect(self.ready)
        self.worker.failed.connect(self.status.setText)
        self.worker.finished.connect(self.done)
        self.worker.start()

    def cancel(self):
        if self.worker:
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.status.setText('Annulation demandée — attente de la requête en cours.')

    def ready(self, result):
        try:
            added = self.store.save_discovery(result.links, now())
        except Exception:
            self.status.setText('Impossible d’enregistrer le résultat. Vérifiez l’espace disque et les droits du dossier de données.')
            return
        self.report.setHtml(render_discovery(result, added))
        self.show_counts()
        self.changed.emit()

    def done(self):
        self.start_button.setEnabled(True)
        self.family.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker.deleteLater()
        self.worker = None
        self.finished.emit()


def render_discovery(result, added):
    per_site = Counter(key for key, *_ in result.links)
    parts = [f'<h3>{added} nouvelle(s) référence(s) au catalogue</h3>',
             '<p>' + ' · '.join(f'{escape(CONNECTORS[key].host)} : {per_site[key]} fiche(s) validée(s)'
                                for key in CONNECTORS) + '</p>']
    parts.extend(f'<p><b>{escape(message)}</b></p>' for message in result.errors)
    if result.links:
        parts.append('<h4>Fiches retenues</h4><ul>')
        parts.extend(f'<li>{escape(ref)} — {escape(name)} · <a href="{escape(link.url, quote=True)}">'
                     f'{escape(CONNECTORS[key].host)}</a></li>' for key, ref, name, link in result.links)
        parts.append('</ul>')
    if result.rejected:
        parts.append('<h4>Fiches écartées</h4><ul>')
        parts.extend(f'<li><a href="{escape(url, quote=True)}">{escape(url.rsplit("/", 1)[-1])}</a> — {escape(reason)}</li>'
                     for _, url, reason in result.rejected)
        parts.append('</ul>')
    return ''.join(parts)
