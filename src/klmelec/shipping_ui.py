"""Seuils de livraison saisis par fournisseur, indépendants des prix comparés."""
import json
from decimal import Decimal
from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QLabel, QComboBox,
    QDoubleSpinBox, QCheckBox, QLineEdit, QPushButton, QFrame,
)

from .comparison_ui import euros


class ShippingPanel(QFrame):
    def __init__(self, store):
        super().__init__()
        self.setProperty('summaryCard', True)
        self.store = store
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(48, 60)
        icon.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap()
        pixmap.loadFromData(files('klmelec').joinpath('assets/icone-colis.png').read_bytes())
        icon.setPixmap(pixmap.scaled(48, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(icon, 0, Qt.AlignVCenter)
        content = QVBoxLayout()
        content.setSpacing(6)
        content.setAlignment(Qt.AlignVCenter)
        self.supplier = QComboBox()
        self.supplier.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.supplier.setMinimumContentsLength(12)
        self.message = QLabel()
        self.message.setWordWrap(True)
        content.addWidget(self.supplier)
        content.addWidget(self.message)
        layout.addLayout(content, 1)
        self.setMinimumWidth(300)
        self.supplier.currentIndexChanged.connect(self.update_message)

        self.settings_page = QWidget()
        settings = QFormLayout(self.settings_page)
        note = QLabel('Renseignez le seuil de livraison offerte pour chaque fournisseur.\n'
                      'Précisez HT ou TTC et les conditions (transporteur, destination, compte professionnel…).\n'
                      'Ces indications sont manuelles et ne modifient pas le total du matériel.')
        note.setWordWrap(True)
        settings.addRow(note)
        self.edit_supplier = QComboBox()
        settings.addRow('Fournisseur', self.edit_supplier)
        self.known = QCheckBox('Seuil renseigné')
        settings.addRow(self.known)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0, 1000000)
        self.threshold.setDecimals(2)
        self.threshold.setSuffix(' €')
        settings.addRow('Livraison offerte à partir de', self.threshold)
        self.basis = QComboBox()
        self.basis.addItems(['TTC', 'HT'])
        settings.addRow('Base du montant', self.basis)
        self.conditions = QLineEdit()
        self.conditions.setPlaceholderText('Exemple : en point relais, France métropolitaine')
        settings.addRow('Conditions', self.conditions)
        self.save_button = QPushButton('Enregistrer')
        self.save_button.clicked.connect(self.save_rule)
        settings.addRow(self.save_button)
        self.saved_message = QLabel()
        settings.addRow(self.saved_message)
        self.edit_supplier.currentIndexChanged.connect(self.load_rule)
        self.known.toggled.connect(self.update_fields)
        self.reload_suppliers()

    def rule(self, supplier_id):
        return json.loads(self.store.setting(f'shipping_{supplier_id}', '{}'))

    def reload_suppliers(self):
        suppliers = self.store.suppliers()
        for combo in (self.supplier, self.edit_supplier):
            selected = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            for supplier in suppliers:
                combo.addItem(supplier['name'], supplier['id'])
            combo.setCurrentIndex(max(0, combo.findData(selected)))
            combo.blockSignals(False)
        self.load_rule()
        self.update_message()

    def update_message(self):
        if self.supplier.currentData() is None:
            self.message.setText('Aucun fournisseur')
            return
        rule = self.rule(self.supplier.currentData())
        if not rule.get('known'):
            self.message.setText('Seuil non renseigné\nParamètres → Livraison')
            self.message.setToolTip('')
            return
        self.message.setText(f"Livraison offerte dès {euros(Decimal(rule['threshold']))} {rule['basis']}\nSous conditions")
        self.message.setToolTip(rule.get('conditions') or 'Seuil saisi manuellement ; à vérifier auprès du fournisseur.')

    def load_rule(self):
        rule = self.rule(self.edit_supplier.currentData())
        self.known.setChecked(rule.get('known', False))
        self.threshold.setValue(float(rule.get('threshold', '0')))
        self.basis.setCurrentText(rule.get('basis', 'TTC'))
        self.conditions.setText(rule.get('conditions', ''))
        self.saved_message.clear()
        self.update_fields()

    def update_fields(self):
        available = self.edit_supplier.currentData() is not None
        self.known.setEnabled(available)
        self.save_button.setEnabled(available)
        for widget in (self.threshold, self.basis, self.conditions):
            widget.setEnabled(available and self.known.isChecked())

    def save_rule(self):
        supplier_id = self.edit_supplier.currentData()
        if supplier_id is None:
            return
        rule = dict(known=self.known.isChecked(), threshold=str(self.threshold.value()),
                    basis=self.basis.currentText(), conditions=self.conditions.text().strip())
        self.store.save_setting(f'shipping_{supplier_id}', json.dumps(rule, ensure_ascii=False))
        self.saved_message.setText('Conditions enregistrées.')
        self.update_message()
