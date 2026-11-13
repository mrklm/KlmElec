"""Préparation des rangées et détail des critères électriques contrôlés."""
from html import escape
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
                             QPushButton, QComboBox, QSpinBox, QLineEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QTextBrowser)

from .electrical import USES, circuits, evaluate


class ElectricalPage(QWidget):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.loading = False
        layout = QVBoxLayout(self)
        note = QLabel('Logement monophasé — un exemplaire de disjoncteur = un circuit. '
                      'Affectez chaque circuit à une rangée et précisez son usage. '
                      'Vérification de critères uniquement : câblage, sections, notices et conformité globale restent à contrôler.')
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.method = QComboBox()
        self.method.addItem('Règle de l’aval', 'aval')
        self.method.addItem('Règle de l’amont', 'amont')
        controls.addWidget(self.method)
        controls.addWidget(QLabel('Calibre de protection amont'))
        self.upstream = QSpinBox()
        self.upstream.setRange(0, 125)
        self.upstream.setSpecialValueText('À préciser')
        self.upstream.setSuffix(' A')
        controls.addWidget(self.upstream)
        controls.addStretch()
        layout.addLayout(controls)
        self.method.currentIndexChanged.connect(self.change_method)
        self.upstream.valueChanged.connect(self.change_method)
        row_controls = QHBoxLayout()
        self.row_choice = QComboBox()
        row_controls.addWidget(self.row_choice, 1)
        add = QPushButton('Ajouter une rangée')
        add.clicked.connect(self.add_row)
        row_controls.addWidget(add)
        remove = QPushButton('Retirer la rangée')
        remove.clicked.connect(self.remove_row)
        row_controls.addWidget(remove)
        layout.addLayout(row_controls)
        form = QFormLayout()
        self.row_name = QLineEdit()
        self.rating = QComboBox()
        for rating in (0, 25, 40, 63, 80, 100, 125):
            self.rating.addItem(f'{rating} A' if rating else 'À préciser', rating)
        self.kind = QComboBox()
        self.kind.addItems(['À préciser', 'AC', 'A', 'F', 'B'])
        self.sensitivity = QComboBox()
        for sensitivity in (0, 30, 100, 300, 500):
            self.sensitivity.addItem(f'{sensitivity} mA' if sensitivity else 'À préciser', sensitivity)
        form.addRow('Nom de la rangée', self.row_name)
        differential = QHBoxLayout()
        for widget in (self.rating, self.kind, self.sensitivity):
            differential.addWidget(widget)
        form.addRow('Différentiel prévu (à lire sur l’appareil)', differential)
        layout.addLayout(form)
        self.row_name.setMaxLength(80)
        self.row_name.editingFinished.connect(self.change_row)
        for combo in (self.rating, self.kind, self.sensitivity):
            combo.currentIndexChanged.connect(self.change_row)
        self.row_choice.currentIndexChanged.connect(self.show_row)
        self.coverage = QLabel()
        self.coverage.setWordWrap(True)
        layout.addWidget(self.coverage)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Disjoncteur / exemplaire', 'Calibre', 'Rangée', 'Usage'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(150)
        layout.addWidget(self.table, 1)
        self.report = QTextBrowser()
        self.report.setOpenExternalLinks(True)
        layout.addWidget(self.report, 1)
        self.refresh()

    def refresh(self):
        self.loading = True
        selected = self.row_choice.currentData()
        self.plan = self.store.electrical_plan()
        self.method.setCurrentIndex(self.method.findData(self.plan['method']))
        self.upstream.setValue(self.plan['upstream'])
        self.upstream.setEnabled(self.plan['method'] == 'amont')
        self.row_choice.clear()
        for row in self.plan['rows']:
            self.row_choice.addItem(row['name'], row['id'])
        self.row_choice.setCurrentIndex(max(0, self.row_choice.findData(selected)))
        self.units = list(circuits(self.store.items()))
        # Keep very large procurement lists from creating thousands of widgets.
        shown = self.units[:500]
        self.table.setRowCount(len(shown))
        for index, (key, item, ordinal, amps) in enumerate(shown):
            for col, text in enumerate((f"{item['reference']} · exemplaire {ordinal+1}", f'{amps} A')):
                cell = QTableWidgetItem(text)
                cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(index, col, cell)
            entry = self.plan['circuits'].get(key, dict(row=None, use=USES[0]))
            group = QComboBox()
            group.addItem('Non affecté', None)
            for row in self.plan['rows']:
                group.addItem(row['name'], row['id'])
            group.setCurrentIndex(max(0, group.findData(entry['row'])))
            use = QComboBox()
            use.addItems(USES)
            use.setCurrentText(entry['use'])
            self.table.setCellWidget(index, 2, group)
            self.table.setCellWidget(index, 3, use)
            group.currentIndexChanged.connect(lambda _, k=key, g=group, u=use: self.change_circuit(k, g, u))
            use.currentIndexChanged.connect(lambda _, k=key, g=group, u=use: self.change_circuit(k, g, u))
        self.loading = False
        self.show_row()
        self.update_report()

    def persist(self):
        self.store.save_electrical_plan(self.plan)
        self.update_report()

    def add_row(self):
        self.plan['rows'].append(dict(id=uuid4().hex, name=f"Rangée {len(self.plan['rows'])+1}",
                                      rating=0, type='À préciser', sensitivity=0))
        self.persist()
        self.refresh()
        self.row_choice.setCurrentIndex(self.row_choice.count()-1)

    def remove_row(self):
        key = self.row_choice.currentData()
        if key is None:
            return
        self.plan['rows'] = [row for row in self.plan['rows'] if row['id'] != key]
        for entry in self.plan['circuits'].values():
            if entry['row'] == key:
                entry['row'] = None
        self.persist()
        self.refresh()

    def show_row(self):
        if self.loading:
            return
        row = next((r for r in self.plan['rows'] if r['id'] == self.row_choice.currentData()), None)
        self.loading = True
        for widget in (self.row_name, self.rating, self.kind, self.sensitivity):
            widget.setEnabled(row is not None)
        self.row_name.setText(row['name'] if row else '')
        self.rating.setCurrentIndex(self.rating.findData(row['rating'] if row else 0))
        self.kind.setCurrentText(row['type'] if row else 'À préciser')
        self.sensitivity.setCurrentIndex(self.sensitivity.findData(row['sensitivity'] if row else 0))
        self.loading = False

    def change_row(self):
        if self.loading:
            return
        row = next((r for r in self.plan['rows'] if r['id'] == self.row_choice.currentData()), None)
        if row is None:
            return
        row.update(name=self.row_name.text().strip() or row['name'], rating=self.rating.currentData(),
                   type=self.kind.currentText(), sensitivity=self.sensitivity.currentData())
        self.persist()
        self.refresh()

    def change_method(self):
        if self.loading:
            return
        self.plan.update(method=self.method.currentData(), upstream=self.upstream.value())
        self.upstream.setEnabled(self.plan['method'] == 'amont')
        self.persist()

    def change_circuit(self, key, group, use):
        if self.loading:
            return
        self.plan['circuits'][key] = dict(row=group.currentData(), use=use.currentText())
        self.persist()

    def update_report(self):
        unassigned = sum(not self.plan['circuits'].get(key, {}).get('row') for key, *_ in self.units)
        self.coverage.setText(f'{len(self.units)} circuits reconnus · {unassigned} non affectés. '
                             'Références reconnues : Legrand 406771, 406773, 406774, 406775, 406777. '
                             'Les autres articles ne sont pas évalués.' +
                             (' Affichage limité à 500 circuits : fractionnez la liste.' if len(self.units) > 500 else ''))
        parts = []
        for row in self.plan['rows']:
            assigned = [(amps, self.plan['circuits'][key]['use']) for key, _, _, amps in self.units
                        if self.plan['circuits'].get(key, {}).get('row') == row['id']]
            result = evaluate(row, assigned, self.plan['method'], self.plan['upstream'])
            parts.append(f"<h3>{escape(row['name'])} — {result['status']}</h3><p>{len(assigned)} circuit(s) / 8 · {escape(result['formula'])}</p>")
            parts.append(f"<p>{escape(result['suggestion'])}</p>")
            parts.extend(f'<p>{escape(detail)}</p>' for detail in result['details'])
        if not parts:
            parts.append('<p>Ajoutez une rangée et renseignez son différentiel pour commencer.</p>')
        parts.append('<p>Résultat limité aux critères renseignés. La répartition globale du logement, '
                     'le nombre minimal de différentiels, la continuité de service, les câbles et les équipements particuliers ne sont pas validés.</p>'
                     '<p><a href="https://www.legrand.fr/questions-frequentes/comment-calculer-lamperage-dun-interrupteur-differentiel">Règles amont / aval — Legrand</a> · Vérifiées le 13/11/2026.</p>')
        self.report.setHtml(''.join(parts))
