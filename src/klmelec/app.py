"""Première interface locale ; aucun prix ni connecteur réseau simulé."""
import sys
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QStandardPaths, QStringListModel
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCompleter, QSpinBox, QPushButton, QTableView, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QCheckBox, QTabWidget, QAbstractItemView, QStyledItemDelegate,
)

from .data import Store, matches


class MaterialModel(QAbstractTableModel):
    HEADERS = ['Désignation', 'Marque', 'Référence', 'Quantité', 'PU HT', 'PU TTC',
               'Fournisseur retenu', 'Total HT', 'Total TTC']

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.rows = store.items()

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
            return [row['name'], row['brand'], row['reference'], row['quantity'],
                    '—', '—', 'Non comparé', '—', '—'][index.column()]

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
                    'Connecteur prévu' if row['connector'] else 'Connecteur nécessaire'][index.column()]

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
        compare = QPushButton('Comparer les prix — prochaine étape')
        compare.setEnabled(False)
        bottom.addWidget(compare)
        bottom.addStretch()
        layout.addLayout(bottom)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        layout.addWidget(QLabel('Double-cliquez sur une quantité pour la modifier. Votre liste est enregistrée automatiquement.'))
        layout.addWidget(QLabel('Catalogue initial : 18 articles du tableur. Les marques « À confirmer » et les préfixes IKE/WAG restent à vérifier.'))
        tabs.addTab(material, 'Matériel')

        suppliers = QWidget()
        supplier_layout = QVBoxLayout(suppliers)
        supplier_note = QLabel('Ajoutez les fournisseurs de votre choix. Aucun connecteur de prix n’est encore opérationnel ;\n123 Elec et Elec Distrib sont prévus pour la prochaine étape.')
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
        self.statusBar().showMessage(f'Données locales : {location}')
        self.material_model.modelReset.connect(self.update_summary)
        self.update_summary()

    def filter_products(self, query):
        self.suggestions.setStringList([label for label in self.labels if matches(query, label)])

    def update_summary(self):
        rows = self.material_model.rows
        self.summary.setText(f'{len(rows)} référence(s) · {sum(r["quantity"] for r in rows)} unité(s) — Totaux HT / TTC : non disponibles, prix non relevés. Hors livraison.')

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
