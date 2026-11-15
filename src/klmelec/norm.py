"""Onglet « Norme » : lecture des PDF de l'utilisateur (norme, guides fabricants).

Aucun document n'est fourni avec l'application : la NF C 15-100 est protégée par le droit d'auteur.
Seuls les chemins des fichiers choisis et la dernière page lue sont enregistrés dans la base locale.
"""
import json
from pathlib import Path

from PySide6.QtCore import QPointF, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtPdf import QPdfBookmarkModel, QPdfDocument, QPdfSearchModel
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QFileDialog, QSplitter, QTreeView, QSpinBox, QLineEdit,
                               QToolButton, QMessageBox)

ERRORS = {
    QPdfDocument.Error.FileNotFound: 'Fichier introuvable : il a peut-être été déplacé ou supprimé.',
    QPdfDocument.Error.InvalidFileFormat: 'Ce fichier n’est pas un PDF lisible.',
    QPdfDocument.Error.IncorrectPassword: 'Ce PDF est protégé par un mot de passe.',
    QPdfDocument.Error.UnsupportedSecurityScheme: 'Ce PDF est protégé (DRM) et ne peut être lu que par le lecteur '
                                                  'prévu par l’éditeur.',
}
HINT = ('Ajoutez vos documents PDF : la norme NF C 15-100 que vous avez achetée, ou des guides gratuits '
        '(Promotelec, Consuel, guides NF C 15-100 des fabricants). Les fichiers restent à leur place sur votre '
        'disque ; aucun document n’est fourni avec KlmElec.')
ZOOMS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0)


class NormPage(QWidget):
    def __init__(self, store):
        super().__init__()
        self.store = store
        try:
            self.documents = [entry for entry in json.loads(store.setting('norm_documents', '[]'))
                              if isinstance(entry, dict) and isinstance(entry.get('path'), str)]
        except (ValueError, TypeError):
            self.documents = []
        self.current = None
        layout = QVBoxLayout(self)
        heading = QLabel('Norme')
        heading.setStyleSheet('font-size: 22px; font-weight: 600;')
        layout.addWidget(heading)

        splitter = QSplitter()
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(QLabel('Documents'))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.open_row)
        side_layout.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        self.add_button = QPushButton('Ajouter un PDF…')
        self.add_button.clicked.connect(self.add)
        buttons.addWidget(self.add_button)
        self.remove_button = QPushButton('Retirer')
        self.remove_button.setToolTip('Retire le document de la liste, sans supprimer le fichier')
        self.remove_button.clicked.connect(self.remove)
        buttons.addWidget(self.remove_button)
        side_layout.addLayout(buttons)
        self.external_button = QPushButton('Ouvrir avec le lecteur du système')
        self.external_button.setToolTip('Pour les PDF protégés que la visionneuse intégrée ne peut pas lire')
        self.external_button.clicked.connect(self.open_external)
        side_layout.addWidget(self.external_button)
        self.outline_label = QLabel('Sommaire')
        side_layout.addWidget(self.outline_label)
        self.outline = QTreeView()
        self.outline.setHeaderHidden(True)
        self.outline.clicked.connect(self.jump_to_bookmark)
        side_layout.addWidget(self.outline, 2)
        splitter.addWidget(side)

        viewer = QWidget()
        viewer_layout = QVBoxLayout(viewer)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        tools.addWidget(QLabel('Page'))
        self.page = QSpinBox()
        self.page.setMinimum(1)
        self.page.editingFinished.connect(lambda: self.go_to(self.page.value() - 1))
        tools.addWidget(self.page)
        self.page_count = QLabel()
        tools.addWidget(self.page_count)
        tools.addSpacing(16)
        for text, tip, step in (('−', 'Réduire', -1), ('+', 'Agrandir', 1)):
            button = QToolButton()
            button.setText(text)
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, step=step: self.zoom(step))
            tools.addWidget(button)
        fit = QPushButton('Pleine largeur')
        fit.clicked.connect(lambda: self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth))
        tools.addWidget(fit)
        tools.addSpacing(16)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Rechercher dans le document (Entrée : résultat suivant)')
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(lambda: self.find(1))
        tools.addWidget(self.search, 1)
        for text, tip, step in (('▲', 'Résultat précédent', -1), ('▼', 'Résultat suivant', 1)):
            button = QToolButton()
            button.setText(text)
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, step=step: self.find(step))
            tools.addWidget(button)
        self.results = QLabel()
        tools.addWidget(self.results)
        viewer_layout.addLayout(tools)
        self.message = QLabel(HINT)
        self.message.setWordWrap(True)
        viewer_layout.addWidget(self.message)
        self.document = QPdfDocument(self)
        self.view = QPdfView()
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.view.setDocument(self.document)
        self.search_model = QPdfSearchModel(self)
        self.search_model.setDocument(self.document)
        # Le modèle n'est confié à la vue qu'une fois un résultat sélectionné : QPdfView (Qt 6.12)
        # plante en dessinant des résultats sans résultat courant.
        self.search_model.countChanged.connect(self.results_changed)  # la recherche est progressive
        self.pending = False
        self.bookmarks = QPdfBookmarkModel(self)
        self.bookmarks.setDocument(self.document)
        self.outline.setModel(self.bookmarks)
        self.view.pageNavigator().currentPageChanged.connect(self.page_changed)
        viewer_layout.addWidget(self.view, 1)
        splitter.addWidget(viewer)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 900])
        layout.addWidget(splitter, 1)

        for entry in self.documents:
            self.list.addItem(self.item(entry))
        last = store.setting('norm_current', '')
        rows = [entry['path'] for entry in self.documents]
        self.list.setCurrentRow(rows.index(last) if last in rows else 0 if rows else -1)
        self.update_buttons()

    @staticmethod
    def item(entry):
        item = QListWidgetItem(Path(entry['path']).stem)
        item.setToolTip(entry['path'])
        return item

    def save(self):
        self.store.save_setting('norm_documents', json.dumps(self.documents, ensure_ascii=False))
        self.store.save_setting('norm_current', self.current['path'] if self.current else '')

    def update_buttons(self):
        selected = self.current is not None
        self.remove_button.setEnabled(selected)
        self.external_button.setEnabled(selected)

    def add(self, *, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, 'Ajouter un document PDF', str(Path.home()),
                                                  'Documents PDF (*.pdf)')
            if not path:
                return
        path = str(Path(path).resolve())
        rows = [entry['path'] for entry in self.documents]
        if path in rows:
            self.list.setCurrentRow(rows.index(path))
            return
        self.documents.append({'path': path, 'page': 0})
        self.list.addItem(self.item(self.documents[-1]))
        self.list.setCurrentRow(len(self.documents) - 1)
        self.save()

    def remove(self):
        row = self.list.currentRow()
        if row < 0:
            return
        name = Path(self.documents[row]['path']).name
        if QMessageBox.question(self, 'Retirer le document',
                                f'Retirer « {name} » de la liste ? Le fichier n’est pas supprimé.') != QMessageBox.Yes:
            return
        self.current = None
        del self.documents[row]
        self.list.takeItem(row)
        if not self.documents:
            self.document.close()
            self.show_message(HINT)
        self.save()
        self.update_buttons()

    def open_row(self, row):
        if row < 0 or row >= len(self.documents):
            return
        self.current = None  # pas d'enregistrement de page pendant le chargement
        entry = self.documents[row]
        self.search.clear()
        self.view.setSearchModel(None)
        self.search_model.setSearchString('')
        self.results.clear()
        self.document.close()
        error = self.document.load(entry['path'])
        self.current = entry
        self.update_buttons()
        if error != QPdfDocument.Error.None_:
            self.show_message(ERRORS.get(error, 'Impossible d’ouvrir ce PDF.') +
                              ' Utilisez « Ouvrir avec le lecteur du système ».')
            self.page_count.clear()
            self.save()
            return
        self.message.hide()
        self.view.show()
        count = self.document.pageCount()
        self.page.setMaximum(max(1, count))
        self.page_count.setText(f'/ {count}')
        has_outline = self.bookmarks.rowCount() > 0
        self.outline_label.setVisible(has_outline)
        self.outline.setVisible(has_outline)
        self.outline.expandToDepth(0)
        self.go_to(min(entry.get('page', 0), count - 1))
        self.save()

    def show_message(self, text):
        self.message.setText(text)
        self.message.show()
        self.view.hide()

    def go_to(self, page):
        if self.document.pageCount():
            self.view.pageNavigator().jump(max(0, page), QPointF(), self.view.pageNavigator().currentZoom())

    def page_changed(self, page):
        self.page.setValue(page + 1)
        if self.current is not None and self.current.get('page') != page:
            self.current['page'] = page
            self.save()

    def zoom(self, step):
        current = self.view.zoomFactor()
        if self.view.zoomMode() != QPdfView.ZoomMode.Custom:
            current = 1.0
        bigger = [z for z in ZOOMS if z > current + 1e-6]
        smaller = [z for z in ZOOMS if z < current - 1e-6]
        target = (bigger[0] if bigger else ZOOMS[-1]) if step > 0 else (smaller[-1] if smaller else ZOOMS[0])
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(target)

    def find(self, step):
        text = self.search.text().strip()
        if not text or not self.document.pageCount():
            self.view.setSearchModel(None)
            self.search_model.setSearchString('')
            self.results.clear()
            return
        if self.search_model.searchString() != text:
            self.view.setSearchModel(None)
            self.pending = True
            self.search_model.setSearchString(text)
            self.results_changed()
            return
        count = self.search_model.count()
        if count:
            self.show_result((self.view.currentSearchResultIndex() + step) % count)

    def results_changed(self):
        count = self.search_model.count()
        if self.pending and count:
            self.pending = False
            self.show_result(0)
        elif not count:
            self.results.setText('Aucun résultat' if self.search_model.searchString() else '')
        else:
            self.results.setText(f'{self.view.currentSearchResultIndex() + 1} / {count}')

    def show_result(self, index):
        if self.view.searchModel() is None:
            self.view.setSearchModel(self.search_model)
        self.view.setCurrentSearchResultIndex(index)
        self.view.pageNavigator().jump(self.search_model.resultAtIndex(index))
        self.results.setText(f'{index + 1} / {self.search_model.count()}')

    def jump_to_bookmark(self, index):
        page = index.data(int(QPdfBookmarkModel.Role.Page))
        if isinstance(page, int):
            self.go_to(page)

    def open_external(self):
        if self.current:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current['path']))
