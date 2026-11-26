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


FREE = '#2e9e44'  # vert lisible sur les thèmes clairs et sombres
MISSING = '#d6453d'  # rouge lisible sur les thèmes clairs et sombres


class ShippingPanel(QFrame):
    """Carte « Livraison » : une ligne par fournisseur retenu, livraison gratuite ou montant restant."""

    def __init__(self, store):
        super().__init__()
        self.setProperty('summaryCard', True)
        self.store = store
        self.subtotals = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        icon = QLabel()
        icon.setFixedSize(32, 40)
        icon.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap()
        pixmap.loadFromData(files('klmelec').joinpath('assets/icone-colis.png').read_bytes())
        icon.setPixmap(pixmap.scaled(32, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(icon, 0, Qt.AlignVCenter)
        self.lines_layout = QVBoxLayout()
        self.lines_layout.setSpacing(2)
        self.lines_layout.setAlignment(Qt.AlignVCenter)
        layout.addLayout(self.lines_layout, 1)
        self.lines = []
        self.setMinimumWidth(360)

        self.settings_page = QWidget()
        settings = QFormLayout(self.settings_page)
        note = QLabel('Renseignez le seuil de livraison offerte pour chaque fournisseur.\n'
                      'Précisez HT ou TTC et les conditions (transporteur, destination, compte professionnel…).\n'
                      'Ces indications sont manuelles et ne modifient pas le total du matériel.')
        note.setWordWrap(True)
        settings.addRow(note)
        self.show_info = QCheckBox('Afficher les infos de livraison sur la page principale')
        self.show_info.setChecked(store.setting('show_shipping', '1') == '1')
        self.show_info.toggled.connect(self.toggle_info)
        settings.addRow(self.show_info)
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
        selected = self.edit_supplier.currentData()
        self.edit_supplier.blockSignals(True)
        self.edit_supplier.clear()
        for supplier in self.store.suppliers():
            self.edit_supplier.addItem(supplier['name'], supplier['id'])
        self.edit_supplier.setCurrentIndex(max(0, self.edit_supplier.findData(selected)))
        self.edit_supplier.blockSignals(False)
        self.load_rule()
        self.update_message()

    def toggle_info(self, checked):
        self.store.save_setting('show_shipping', int(checked))
        self.setVisible(checked)

    def set_subtotals(self, subtotals):
        """{fournisseur: (HT, TTC)} des offres retenues dans la liste."""
        self.subtotals = dict(subtotals)
        self.update_message()

    def update_message(self):
        for label in self.lines:
            self.lines_layout.removeWidget(label)
            label.hide()  # sinon l'ancienne ligne reste dessinée jusqu'à sa destruction
            label.deleteLater()
        self.lines = []
        suppliers = [s for s in self.store.suppliers() if s['active']]
        # Fournisseurs sans article retenu masqués dès qu'au moins un article est retenu ailleurs.
        if any(self.subtotals.get(s['id']) for s in suppliers):
            suppliers = [s for s in suppliers if self.subtotals.get(s['id'])]
        if not suppliers:
            self.add_line('Aucun fournisseur actif')
            return
        for supplier in suppliers:
            rule = self.rule(supplier['id'])
            name = supplier['name']
            if not rule.get('known'):
                self.add_line(f'{name} : seuil non renseigné (Paramètres → Livraison)')
                continue
            ht, ttc = self.subtotals.get(supplier['id'], (Decimal(0), Decimal(0)))
            missing = Decimal(rule['threshold']) - (ht if rule['basis'] == 'HT' else ttc)
            tip = (f"Livraison offerte dès {euros(Decimal(rule['threshold']))} {rule['basis']}. "
                   + (rule.get('conditions') or 'Seuil saisi manuellement ; à vérifier auprès du fournisseur.'))
            if missing <= 0:
                self.add_line(f'{name} : livraison gratuite', tip, FREE)
            else:
                self.add_line(f'{name} : livraison gratuite dans {euros(missing)}', tip, MISSING)

    def add_line(self, text, tip='', colour=None):
        label = QLabel(text)
        label.setToolTip(tip)
        if colour:
            label.setStyleSheet(f'color: {colour}; font-weight: 600;')
        self.lines_layout.addWidget(label)
        self.lines.append(label)

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
