"""Interface de préparation et de comparaison de matériel électrique."""
import sys
from decimal import Decimal
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QStandardPaths, QStringListModel, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCompleter, QSpinBox, QPushButton, QTableView, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QCheckBox, QTabWidget, QAbstractItemView, QStyledItemDelegate,
    QTextBrowser, QDoubleSpinBox,
)

from .data import Store, matches
from .comparison import best_offer, amounts, now
from .comparison_ui import ComparisonWorker, euros, local_date, render_report
from .suppliers import CONNECTORS


class MaterialModel(QAbstractTableModel):
    HEADERS = ['Désignation', 'Marque', 'Référence', 'Quantité', 'PU HT', 'PU TTC',
               'Fournisseur retenu', 'Total HT', 'Total TTC']

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.rows = store.items()
        self.offers = []
        self.vat = store.vat()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.HEADERS[section] if orientation == Qt.Horizontal else section + 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            row = self.rows[index.row()]
            offers = [o for o in self.offers if o['product_id'] == row['id']]
            winner = best_offer(offers)
            prices = ['—', '—', 'Comparaison incomplète' if offers else 'Non comparé', '—', '—']
            if winner:
                ht, ttc, total_ht, total_ttc = amounts(winner['ttc'], row['quantity'], self.vat)
                names = [o['supplier'] for o in offers if Decimal(o['ttc']) == Decimal(winner['ttc'])]
                prices = [euros(ht), euros(ttc), ', '.join(names), euros(total_ht), euros(total_ttc)]
            return [row['name'], row['brand'], row['reference'], row['quantity'], *prices][index.column()]

    def flags(self, index):
        flags = super().flags(index)
        if index.isValid() and index.column() == 3:
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or index.column() != 3:
            return False
        try:
            # The spin delegate provides integers, never rounded fractional values.
            self.store.set_quantity(self.rows[index.row()]['id'], value)
        except ValueError:
            return False
        self.refresh()
        return True

    def refresh(self):
        self.beginResetModel()
        self.rows = self.store.items()
        self.endResetModel()


class QuantityDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QSpinBox(parent)
        editor.setRange(1, 99999)
        return editor

    def setEditorData(self, editor, index):
        editor.setValue(index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        editor.interpretText()
        model.setData(index, editor.value())


class SupplierModel(QAbstractTableModel):
    HEADERS = ['Nom', 'Adresse du site', 'Activé', 'Récupération des prix']

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.rows = store.suppliers()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 4

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.HEADERS[section] if orientation == Qt.Horizontal else section + 1

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            row = self.rows[index.row()]
            return [row['name'], row['url'], 'Oui' if row['active'] else 'Non',
                    '3 références configurées' if row['connector'] in CONNECTORS else 'Connecteur nécessaire'][index.column()]

    def refresh(self):
        self.beginResetModel()
        self.rows = self.store.suppliers()
        self.endResetModel()


class SupplierDialog(QDialog):
    def __init__(self, parent, supplier=None):
        super().__init__(parent)
        self.setWindowTitle('Modifier le fournisseur' if supplier else 'Ajouter un fournisseur')
        self.setMinimumWidth(480)
        layout = QFormLayout(self)
        self.name = QLineEdit(supplier['name'] if supplier else '')
        self.url = QLineEdit(supplier['url'] if supplier else 'https://')
        self.active = QCheckBox('Activer ce fournisseur')
        self.active.setChecked(bool(supplier['active']) if supplier else True)
        layout.addRow('Nom', self.name)
        layout.addRow('Adresse du site', self.url)
        layout.addRow(self.active)
        note = QLabel('L’ajout du site ne rend pas la récupération des prix disponible.\nUn connecteur compatible sera nécessaire.')
        note.setWordWrap(True)
        layout.addRow(note)
        buttons = QDialogButtonBox()
        buttons.addButton('Enregistrer', QDialogButtonBox.AcceptRole)
        buttons.addButton('Annuler', QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def validate(self):
        from .data import validate_supplier
        try:
            validate_supplier(self.name.text(), self.url.text())
        except ValueError as exc:
            QMessageBox.warning(self, 'Fournisseur incomplet', str(exc))
            return
        self.accept()


def table_for(model):
    table = QTableView()
    table.setModel(model)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    return table


class MainWindow(QMainWindow):
    def __init__(self, store, location):
        super().__init__()
        self.store = store
        self.worker = None
        self.close_pending = False
        self.current_payload = None
        self.setWindowTitle('KLM Elec — Préparation du matériel')
        self.resize(1200, 700)
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        material = QWidget()
        layout = QVBoxLayout(material)
        heading = QLabel('Votre liste de matériel')
        heading.setStyleSheet('font-size: 22px; font-weight: 600;')
        layout.addWidget(heading)
        note = QLabel('Recherchez une désignation, une marque ou une référence. Les mots peuvent être saisis dans n’importe quel ordre.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.search = QComboBox()
        self.search.setEditable(True)
        self.search.setInsertPolicy(QComboBox.NoInsert)
        self.products = store.products()
        self.labels = {f"{p['name']} · {p['brand']} · {p['reference']}": p['id'] for p in self.products}
        self.search.addItems(list(self.labels))
        self.search.setCurrentIndex(-1)
        self.search.lineEdit().setPlaceholderText('Exemple : disj 16, legrand, 406774…')
        self.search.setMinimumWidth(420)
        self.suggestions = QStringListModel(list(self.labels), self)
        self.completer = QCompleter(self.suggestions, self)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.search.setCompleter(self.completer)
        self.search.lineEdit().textEdited.connect(self.filter_products)
        controls.addWidget(self.search, 1)
        controls.addWidget(QLabel('Quantité'))
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 99999)
        controls.addWidget(self.quantity)
        add = QPushButton('Ajouter')
        add.clicked.connect(self.add_item)
        controls.addWidget(add)
        layout.addLayout(controls)
        self.material_model = MaterialModel(store)
        self.material_table = table_for(self.material_model)
        self.material_table.setItemDelegateForColumn(3, QuantityDelegate(self.material_table))
        layout.addWidget(self.material_table)
        bottom = QHBoxLayout()
        self.remove = QPushButton('Supprimer la ligne sélectionnée')
        self.remove.clicked.connect(self.remove_item)
        bottom.addWidget(self.remove)
        self.compare_button = QPushButton('Comparer les prix')
        self.compare_button.clicked.connect(self.start_comparison)
        bottom.addWidget(self.compare_button)
        self.cancel_button = QPushButton('Annuler la recherche')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_comparison)
        bottom.addWidget(self.cancel_button)
        bottom.addStretch()
        layout.addLayout(bottom)
        settings = QHBoxLayout()
        settings.addWidget(QLabel('TVA pour le HT calculé (%)'))
        self.vat = QDoubleSpinBox()
        self.vat.setRange(0, 100)
        self.vat.setDecimals(2)
        self.vat.setValue(float(store.vat()))
        self.vat.valueChanged.connect(self.change_vat)
        settings.addWidget(self.vat)
        self.force_refresh = QCheckBox('Actualiser même si un relevé date de moins de 5 minutes')
        settings.addWidget(self.force_refresh)
        settings.addStretch()
        layout.addLayout(settings)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        layout.addWidget(QLabel('Double-cliquez sur une quantité pour la modifier. Votre liste est enregistrée automatiquement.'))
        layout.addWidget(QLabel('Catalogue initial : 18 articles du tableur. Les marques « À confirmer » et les préfixes IKE/WAG restent à vérifier.'))
        tabs.addTab(material, 'Matériel')

        suppliers = QWidget()
        supplier_layout = QVBoxLayout(suppliers)
        supplier_note = QLabel('123 Elec et Elec Distrib : références Legrand 406774, 411617 et 411638 configurées.\nUn fournisseur ajouté nécessite un connecteur compatible. Les lots sont exclus du minimum unitaire.')
        supplier_note.setWordWrap(True)
        supplier_layout.addWidget(supplier_note)
        self.supplier_model = SupplierModel(store)
        self.supplier_table = table_for(self.supplier_model)
        supplier_layout.addWidget(self.supplier_table)
        supplier_buttons = QHBoxLayout()
        for text, action in [('Ajouter un fournisseur', self.add_supplier),
                             ('Modifier', self.edit_supplier), ('Retirer', self.remove_supplier)]:
            button = QPushButton(text)
            button.clicked.connect(action)
            supplier_buttons.addWidget(button)
        supplier_buttons.addStretch()
        supplier_layout.addLayout(supplier_buttons)
        tabs.addTab(suppliers, 'Fournisseurs')
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self.history = QComboBox()
        self.history.currentIndexChanged.connect(self.show_report)
        detail_layout.addWidget(self.history)
        self.report = QTextBrowser()
        self.report.setOpenExternalLinks(True)
        detail_layout.addWidget(self.report)
        tabs.addTab(detail, 'Offres et historique')
        self.tabs = tabs
        self.busy_widgets = [self.search, self.quantity, add, self.remove,
                             self.material_table, suppliers, self.vat, self.force_refresh,
                             self.compare_button]
        self.load_history()
        self.statusBar().showMessage(f'Données locales : {location}')
        self.material_model.modelReset.connect(self.update_summary)
        self.update_summary()
        self.freshness_timer = QTimer(self)
        self.freshness_timer.setInterval(30000)
        self.freshness_timer.timeout.connect(self.refresh_freshness)
        self.freshness_timer.start()

    def refresh_freshness(self):
        if self.material_model.offers and self.worker is None:
            self.material_model.refresh()
            self.show_report()

    def invalidate_comparison(self):
        self.material_model.offers = []
        self.current_payload = None
        self.material_model.refresh()
        self.load_history()

    def change_vat(self):
        value = str(self.vat.value())
        self.store.save_vat(value)
        self.material_model.vat = value
        self.invalidate_comparison()

    def load_history(self):
        self.history.blockSignals(True)
        self.history.clear()
        if self.current_payload:
            self.history.addItem('Relevé de cette session — voir les dates et le cache', self.current_payload)
        for run_id, payload in self.store.comparisons():
            self.history.addItem(f'Historique #{run_id} — {local_date(payload["date"])}', payload)
        self.history.blockSignals(False)
        self.show_report()

    def show_report(self):
        payload = self.history.currentData()
        if payload:
            current = self.current_payload is not None and self.history.currentIndex() == 0
            self.report.setHtml(render_report(payload, historical=not current))
        else:
            self.report.setPlainText('Aucun relevé enregistré. Ajoutez du matériel puis lancez une comparaison.')

    def start_comparison(self):
        if self.worker and self.worker.isRunning():
            return
        items = [dict(row) for row in self.store.items()]
        suppliers = [dict(row) for row in self.store.suppliers() if row['active']]
        if not items or not suppliers:
            QMessageBox.information(self, 'Comparaison', 'Veuillez ajouter du matériel et activer au moins un fournisseur.')
            return
        previous = []
        if not self.force_refresh.isChecked():
            # Newest observations first: cache_lookup scans in reverse.
            for _, payload in reversed(self.store.comparisons()):
                previous.extend(payload['offers'])
        self.material_model.offers = []
        self.material_model.refresh()
        self.pending_payload = dict(date=now(), vat=str(self.vat.value()), items=items, offers=[])
        for widget in self.busy_widgets:
            widget.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker = ComparisonWorker(items, suppliers, previous, self)
        self.worker.progress.connect(self.statusBar().showMessage)
        self.worker.completed.connect(self.comparison_ready)
        self.worker.failed.connect(self.comparison_failed)
        self.worker.finished.connect(self.comparison_finished)
        self.worker.start()

    def comparison_ready(self, offers):
        if self.worker.isInterruptionRequested():
            # Cancelled runs are retained as history, never promoted as current minima.
            for offer in offers:
                offer['status'] = 'cancelled'
                offer['detail'] += ' — comparaison annulée'
        self.pending_payload['offers'] = offers
        try:
            self.store.save_comparison(self.pending_payload)
        except Exception:
            self.comparison_failed('Impossible d’enregistrer le relevé. Vérifiez l’espace disque et les droits du dossier de données.')
            return
        self.current_payload = self.pending_payload
        self.material_model.offers = offers
        self.material_model.vat = self.pending_payload['vat']
        self.material_model.refresh()
        self.load_history()
        self.tabs.setCurrentIndex(2)
        self.statusBar().showMessage('Relevé terminé — consultez les statuts et les dates des offres.')

    def comparison_failed(self, message):
        self.material_model.offers = []
        self.current_payload = None
        self.material_model.refresh()
        self.load_history()
        self.statusBar().showMessage(message)

    def comparison_finished(self):
        for widget in self.busy_widgets:
            widget.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker.deleteLater()
        self.worker = None
        if self.close_pending:
            self.close()

    def cancel_comparison(self):
        if self.worker:
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage('Annulation demandée — attente de la requête en cours (délai réseau : 15 s).')

    def closeEvent(self, event):
        if self.worker is not None:
            self.close_pending = True
            self.cancel_comparison()
            event.ignore()
        else:
            event.accept()

    def filter_products(self, query):
        self.suggestions.setStringList([label for label in self.labels if matches(query, label)])

    def update_summary(self):
        rows = self.material_model.rows
        totals = []
        for row in rows:
            winner = best_offer([o for o in self.material_model.offers if o['product_id'] == row['id']])
            if winner:
                totals.append(amounts(winner['ttc'], row['quantity'], self.material_model.vat)[2:])
        if rows and len(totals) == len(rows):
            ht = sum((t[0] for t in totals), Decimal(0))
            ttc = sum((t[1] for t in totals), Decimal(0))
            text = f'Total HT calculé : {euros(ht)} · Total TTC : {euros(ttc)}'
        else:
            text = f'Total non disponible — {len(totals)}/{len(rows)} référence(s) comparée(s) intégralement'
        self.summary.setText(f'{len(rows)} référence(s) · {text}. Hors livraison.')

    def add_item(self):
        product_id = self.labels.get(self.search.currentText())
        if product_id is None:
            QMessageBox.information(self, 'Choisissez un article', 'Veuillez sélectionner un article proposé avant de l’ajouter.')
            return
        old = next((r for r in self.material_model.rows if r['id'] == product_id), None)
        if old:
            box = QMessageBox(self)
            box.setWindowTitle('Article déjà présent')
            box.setText(f'La liste contient déjà {old["quantity"]} unité(s). Voulez-vous ajouter {self.quantity.value()} unité(s) ?')
            yes = box.addButton('Augmenter la quantité', QMessageBox.AcceptRole)
            box.addButton('Annuler', QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() != yes:
                return
        try:
            self.store.add_item(product_id, self.quantity.value())
        except ValueError as exc:
            QMessageBox.warning(self, 'Quantité incorrecte', str(exc))
            return
        self.material_model.refresh()

    def remove_item(self):
        index = self.material_table.currentIndex()
        if index.isValid():
            self.store.remove_item(self.material_model.rows[index.row()]['id'])
            self.material_model.refresh()

    def supplier_dialog(self, supplier=None):
        dialog = SupplierDialog(self, supplier)
        if dialog.exec() == QDialog.Accepted:
            self.store.save_supplier(dialog.name.text(), dialog.url.text(), dialog.active.isChecked(),
                                     supplier['id'] if supplier else None)
            self.supplier_model.refresh()
            self.invalidate_comparison()

    def add_supplier(self):
        self.supplier_dialog()

    def edit_supplier(self):
        index = self.supplier_table.currentIndex()
        if index.isValid():
            self.supplier_dialog(self.supplier_model.rows[index.row()])

    def remove_supplier(self):
        index = self.supplier_table.currentIndex()
        if index.isValid():
            self.store.archive_supplier(self.supplier_model.rows[index.row()]['id'])
            self.supplier_model.refresh()
            self.invalidate_comparison()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('KlmElec')
    app.setOrganizationName('KlmElec')
    pixmap = QPixmap()
    pixmap.loadFromData(files('klmelec').joinpath('assets/klmelec.png').read_bytes())
    app.setWindowIcon(QIcon(pixmap))
    directory = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / 'klmelec.sqlite3')
    window = MainWindow(store, directory)
    window.show()
    try:
        return app.exec()
    finally:
        store.close()
