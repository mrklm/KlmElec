"""Paramètres → Catalogue : recherche automatique d'une famille de produits."""
import json
from collections import Counter
from html import escape
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QSaveFile, QIODevice, QStandardPaths
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                               QPushButton, QTextBrowser, QFileDialog, QMessageBox)

from .comparison import now
from .discovery import FAMILIES, discover
from .suppliers import CONNECTORS


ALL = '*'


def blocked(result):
    """Un site a refusé l'accès (403/429) : inutile d'enchaîner les familles suivantes."""
    return any('accès limité' in message or 'HTTP 403' in message or 'HTTP 429' in message
               for message in result.errors)


class DiscoveryWorker(QThread):
    completed = Signal(object, str)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, families, known, parent=None):
        super().__init__(parent)
        self.families, self.known = list(families), set(known)

    def run(self):
        total = len(self.families)
        for number, family in enumerate(self.families, 1):
            if self.isInterruptionRequested():
                return
            prefix = f'Famille {number}/{total} — ' if total > 1 else ''
            try:
                result = discover(family, self.known, lambda text: self.progress.emit(prefix + text),
                                  self.isInterruptionRequested)
            except Exception:
                self.failed.emit(f'La recherche « {FAMILIES[family].label} » a échoué. '
                                 'Les familles déjà terminées restent enregistrées.' if number > 1 else
                                 'La recherche a échoué. Le catalogue n’a pas été modifié.')
                return
            self.known.update((key, ref) for key, ref, *_ in result.links)
            self.completed.emit(result, family)
            if blocked(result):
                return


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
                      'Une requête par seconde : comptez quelques minutes par famille, une heure environ pour toutes. '
                      'Les articles existants ne sont pas modifiés.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.family = QComboBox()
        self.family.addItem(f'Toutes les familles ({len(FAMILIES)})', ALL)
        self.family.setItemData(0, 'Enchaîne la recherche de chaque famille ; comptez une heure environ.',
                                Qt.ToolTipRole)
        for key, family in FAMILIES.items():
            self.family.addItem(family.label, key)
        self.family.setCurrentIndex(1)  # évite de lancer par mégarde une recherche d'une heure
        controls.addWidget(self.family, 1)
        self.start_button = QPushButton('Rechercher')
        self.start_button.clicked.connect(self.start)
        controls.addWidget(self.start_button)
        self.cancel_button = QPushButton('Annuler')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        controls.addWidget(self.cancel_button)
        self.export_button = QPushButton('Exporter les références…')
        self.export_button.setToolTip('Enregistrer les fiches découvertes dans un fichier JSON')
        self.export_button.clicked.connect(self.export)
        controls.addWidget(self.export_button)
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
        self.reports = []
        choice = self.family.currentData()
        self.worker = DiscoveryWorker(list(FAMILIES) if choice == ALL else [choice], known, self)
        self.worker.progress.connect(self.status.setText)
        self.worker.completed.connect(self.ready)
        self.worker.failed.connect(self.status.setText)
        self.worker.finished.connect(self.done)
        self.worker.start()

    def export(self, *, path=None):
        if path is None:
            folder = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            path, _ = QFileDialog.getSaveFileName(self, 'Exporter les références',
                                                  str(Path(folder) / 'references-klmelec.json'),
                                                  'Références KLM Elec (*.json)')
            if not path:
                return False
        if not Path(path).suffix:
            path += '.json'
        exported = self.store.export_discovery(now())
        data = json.dumps(exported, ensure_ascii=False, indent=2).encode('utf-8')
        output = QSaveFile(path)
        if not (output.open(QIODevice.WriteOnly) and output.write(data) == len(data) and output.commit()):
            output.cancelWriting()
            QMessageBox.warning(self, 'Export impossible', output.errorString())
            return False
        self.status.setText(f'{len(exported["references"])} fiche(s) exportée(s) : {path}')
        return True

    def cancel(self):
        if self.worker:
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.status.setText('Annulation demandée — attente de la requête en cours.')

    def ready(self, result, family=None):
        try:
            added = self.store.save_discovery(result.links, now())
        except Exception:
            if self.worker:
                self.worker.requestInterruption()
            self.status.setText('Impossible d’enregistrer le résultat. Vérifiez l’espace disque et les droits du dossier de données.')
            return
        if not self.worker or len(self.worker.families) == 1:
            self.report.setHtml(render_discovery(result, added))
        else:
            self.reports.append((FAMILIES[family].label, result, added))
            self.report.setHtml(render_all(self.reports, len(self.worker.families)))
        self.show_counts()
        self.changed.emit()

    def done(self):
        self.start_button.setEnabled(True)
        self.family.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker.deleteLater()
        self.worker = None
        self.finished.emit()


def render_all(reports, total):
    """Rapport de « Toutes les familles » : résumé puis détail de chaque famille terminée."""
    added = sum(count for _, _, count in reports)
    parts = [f'<h3>{added} nouvelle(s) référence(s) au catalogue — {len(reports)}/{total} famille(s) parcourue(s)</h3><ul>']
    parts.extend(f'<li>{escape(label)} : {count} ajoutée(s), {len(result.rejected)} écartée(s)'
                 + ''.join(f' — <b>{escape(message)}</b>' for message in result.errors) + '</li>'
                 for label, result, count in reports)
    parts.append('</ul>')
    parts.extend(f'<hr><h2>{escape(label)}</h2>' + render_discovery(result, count) for label, result, count in reports)
    return ''.join(parts)


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
