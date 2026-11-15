"""Interface de préparation et de comparaison de matériel électrique."""
import sys
import random
import json
import sqlite3
from decimal import Decimal
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QStandardPaths, QStringListModel, QTimer, QSaveFile, QIODevice, QSize, QTranslator, QLocale, QLibraryInfo
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QCompleter, QSpinBox, QPushButton, QTableView, QHeaderView,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QCheckBox, QTabWidget, QAbstractItemView,
    QTextBrowser, QDoubleSpinBox, QTreeView, QListWidget, QFileDialog,
    QGridLayout, QToolButton, QListView, QListWidgetItem, QFrame,
)

from .data import Store, matches
from . import __version__
from .shipping_ui import ShippingPanel
from .electrical_ui import ElectricalPage
from .catalog_ui import CatalogPage
from .theory import TheoryPage
from .norm import NormPage
from .family_menu import FamilyButton
from .comparison import amounts, now
from .comparison_ui import ComparisonWorker, euros, local_date, render_report
from .suppliers import CONNECTORS
from .material import MaterialModel, MaterialDelegate
from .themes import THEMES, DEFAULT_THEME, apply_theme


class SupplierModel(QAbstractTableModel):
    HEADERS = ['Nom', 'Adresse du site', 'Activé', 'Récupération des prix']

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.rows = store.suppliers()
        self.discovered = store.product_links()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 4

    def configured(self, connector):
        return len(set(CONNECTORS[connector].links) | set(self.discovered.get(connector, {})))

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.HEADERS[section] if orientation == Qt.Horizontal else section + 1

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            row = self.rows[index.row()]
            return [row['name'], row['url'], 'Oui' if row['active'] else 'Non',
                    f"{self.configured(row['connector'])} références configurées" if row['connector'] in CONNECTORS else 'Connecteur nécessaire'][index.column()]

    def refresh(self):
        self.beginResetModel()
        self.rows = self.store.suppliers()
        self.discovered = self.store.product_links()
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
        self.setWindowTitle(f'KlmElec v{__version__}')
        self.resize(1200, 700)
        central = QWidget()
        central_layout = QVBoxLayout(central)
        self.header_icon = QLabel()
        pixmap = QPixmap()
        pixmap.loadFromData(files('klmelec').joinpath('assets/klmelec-rond.png').read_bytes())
        self.header_icon.setPixmap(pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.header_icon.setAlignment(Qt.AlignCenter)
        self.header_icon.setAccessibleName('KLM Elec')
        header_layout = QGridLayout()
        header_layout.addWidget(self.header_icon, 0, 0)
        disk = QPixmap()
        disk.loadFromData(files('klmelec').joinpath('assets/icone-disquette.png').read_bytes())
        self.disk_icon = QIcon(disk)
        self.lists_shortcut = QToolButton()
        self.lists_shortcut.setIcon(self.disk_icon)
        self.lists_shortcut.setIconSize(QSize(40, 40))
        self.lists_shortcut.setAutoRaise(True)
        self.lists_shortcut.setToolTip('Enregistrer / charger une liste')
        self.lists_shortcut.setAccessibleName('Enregistrer / charger une liste')
        self.lists_shortcut.clicked.connect(self.open_lists)
        header_layout.addWidget(self.lists_shortcut, 0, 0, Qt.AlignTop | Qt.AlignLeft)
        self.help_button = QToolButton()
        self.help_button.setText('?')
        self.help_button.setAutoRaise(True)
        self.help_button.setFixedSize(self.lists_shortcut.sizeHint())
        self.help_button.setStyleSheet('QToolButton { font-size: 46px; font-weight: 700; padding: 0; }')
        self.help_button.setToolTip('Aide')
        self.help_button.setAccessibleName('Aide')
        self.help_button.clicked.connect(self.show_help)
        header_layout.addWidget(self.help_button, 0, 0, Qt.AlignTop | Qt.AlignRight)
        central_layout.addLayout(header_layout)
        tabs = QTabWidget()
        central_layout.addWidget(tabs)
        self.setCentralWidget(central)
        material = QWidget()
        layout = QVBoxLayout(material)
        heading = QLabel('Votre liste de matériel')
        heading.setStyleSheet('font-size: 22px; font-weight: 600;')
        layout.addWidget(heading)
        controls = QHBoxLayout()
        self.family_button = FamilyButton()
        self.family_button.chosen.connect(self.add_product)
        controls.addWidget(self.family_button)
        controls.addStretch(1)
        self.search = QComboBox()
        self.search.setEditable(True)
        self.search.setInsertPolicy(QComboBox.NoInsert)
        self.search.lineEdit().setPlaceholderText('Exemple : disj 16, legrand, 406774…')
        self.search.setMinimumWidth(260)
        self.search.setMaximumWidth(380)
        self.suggestions = QStringListModel(self)
        self.reload_catalog()
        self.completer = QCompleter(self.suggestions, self)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.search.setCompleter(self.completer)
        self.search.lineEdit().textEdited.connect(self.filter_products)
        controls.addWidget(self.search, 2)
        controls.addStretch(1)
        controls.addWidget(QLabel('Quantité'))
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 99999)
        controls.addWidget(self.quantity)
        self.add_place = QComboBox()
        self.add_place.setMinimumWidth(130)
        self.reload_places()
        controls.addWidget(QLabel('Lieu'))
        controls.addWidget(self.add_place)
        add = QPushButton('Ajouter')
        add.clicked.connect(self.add_item)
        controls.addWidget(add)
        layout.addLayout(controls)
        self.material_model = MaterialModel(store)
        self.material_table = QTreeView()
        self.material_table.setModel(self.material_model)
        self.material_table.setUniformRowHeights(True)
        self.material_table.setAlternatingRowColors(True)
        self.material_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.material_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.material_table.header().setSectionResizeMode(QHeaderView.Interactive)
        self.material_table.header().setSectionsMovable(True)
        self.material_table.header().setFirstSectionMovable(True)
        self.material_table.header().setDefaultSectionSize(100)
        self.material_table.header().setMinimumSectionSize(45)
        self.material_table.header().setStretchLastSection(False)
        self.material_table.setItemDelegate(MaterialDelegate(self.material_table))
        self.manual_column_widths = set()
        self.sizing_columns = False
        self.size_material_columns()
        self.material_table.header().sectionResized.connect(self.remember_column_width)
        self.material_model.modelReset.connect(self.size_material_columns)
        self.material_model.dataChanged.connect(self.size_material_columns)
        self.material_table.clicked.connect(self.edit_place)
        self.material_table.clicked.connect(self.material_model.select_offer)
        self.expanded_products = set()
        self.material_model.modelAboutToBeReset.connect(self.save_expansion)
        self.material_model.modelReset.connect(self.restore_expansion)
        layout.addWidget(self.material_table)
        footer = QHBoxLayout()
        footer_controls = QVBoxLayout()
        footer.addLayout(footer_controls, 1)
        layout.addLayout(footer)
        bottom = QHBoxLayout()
        self.remove = QPushButton('Supprimer la sélection')
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
        footer_controls.addLayout(bottom)
        self.vat = QDoubleSpinBox()
        self.vat.setRange(0, 100)
        self.vat.setDecimals(2)
        self.vat.setValue(float(store.vat()))
        self.vat.valueChanged.connect(self.change_vat)
        self.force_refresh = QCheckBox('Toujours actualiser les prix, même si le relevé date de moins de 5 minutes')
        self.force_refresh.setChecked(store.setting('force_refresh', '0') == '1')
        self.force_refresh.toggled.connect(lambda checked: store.save_setting('force_refresh', int(checked)))
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        footer_controls.addWidget(self.summary)
        self.summary_cards = QWidget()
        self.summary_cards.setMinimumHeight(112)
        self.summary_cards.setStyleSheet('QFrame[summaryCard="true"] { border: 2px solid palette(mid); border-radius: 6px; }')
        cards_layout = QHBoxLayout(self.summary_cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(10)
        self.shipping_panel = ShippingPanel(store)
        cards_layout.addWidget(self.shipping_panel, 3)
        self.total_card = QFrame()
        self.total_card.setProperty('summaryCard', True)
        total_layout = QVBoxLayout(self.total_card)
        total_layout.setContentsMargins(14, 12, 14, 12)
        self.total_label = QLabel('Total TTC\n0,00 €')
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setMinimumWidth(180)
        self.total_label.setStyleSheet('font-size: 20px; font-weight: 600;')
        total_layout.addWidget(self.total_label)
        self.total_label.setToolTip('Somme des offres retenues multipliées par les quantités. Hors livraison.')
        cards_layout.addWidget(self.total_card, 2)
        footer.addWidget(self.summary_cards, 0, Qt.AlignBottom)
        tabs.addTab(material, 'Matériel')

        suppliers = QWidget()
        supplier_layout = QVBoxLayout(suppliers)
        supplier_note = QLabel('123 Elec et Elec Distrib : 12 références Legrand configurées (disjoncteurs, différentiels, peignes 404926 / 405000 / 405001 et télérupteur 412408).\n123 Elec : également les quatre références Wago 2106, le tableau IKE821023 et la porte IKE821053. IKE824302 : lot de 5 exclu du calcul unitaire.\nParamètres → Catalogue ajoute automatiquement d’autres références (disjoncteurs, interrupteurs différentiels, télérupteurs, peignes, contacteurs, parafoudres, interrupteurs-sectionneurs, horloges modulaires, répartiteurs, borniers, GTL, accessoires GTL, coffrets, portes et rehausses Drivia, tableaux pré-équipés, coffrets et modules de communication, interrupteurs crépusculaires, compteurs d’énergie, éclairage de sécurité Sati, boîtes Legrand, bornes Wago, appareillage Dooxie, Mosaic, Céliane, Plexo, Niloé et saillie Oteo Legrand, domotique Yokis, disjoncteurs et interrupteurs différentiels Schneider et Hager).\nUn fournisseur ajouté nécessite un connecteur compatible. Les lots sont exclus du minimum unitaire.')
        supplier_note.setWordWrap(True)
        supplier_layout.addWidget(supplier_note)
        self.supplier_model = SupplierModel(store)
        self.supplier_model.modelReset.connect(self.shipping_panel.reload_suppliers)
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
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self.history = QComboBox()
        self.history.currentIndexChanged.connect(self.show_report)
        detail_layout.addWidget(self.history)
        self.report = QTextBrowser()
        self.report.setOpenExternalLinks(True)
        detail_layout.addWidget(self.report)
        parameters = QWidget()
        parameters_layout = QVBoxLayout(parameters)
        self.settings_sections = QTabWidget()
        parameters_layout.addWidget(self.settings_sections)
        appearance = QWidget()
        appearance_layout = QFormLayout(appearance)
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(THEMES)
        self.persistent_themes = QCheckBox('Thèmes persistants')
        self.persistent_themes.setChecked(store.theme_option('persistent_themes'))
        self.persistent_themes.setToolTip('Retrouver le thème choisi au prochain lancement.')
        self.random_themes = QCheckBox('Thèmes aléatoires')
        self.random_themes.setChecked(store.theme_option('random_themes'))
        self.random_themes.setToolTip('Choisir un thème au hasard à chaque lancement, même si la persistance est activée.')
        saved_theme = store.theme()
        initial_theme = saved_theme if self.persistent_themes.isChecked() and saved_theme in THEMES else DEFAULT_THEME
        if self.random_themes.isChecked():
            initial_theme = random.choice(list(THEMES))
        self.theme_selector.setCurrentText(initial_theme)
        appearance_layout.addRow('Thème', self.theme_selector)
        appearance_layout.addRow(self.persistent_themes)
        appearance_layout.addRow(self.random_themes)
        self.persistent_themes.toggled.connect(self.change_theme_persistence)
        self.random_themes.toggled.connect(lambda enabled: store.save_theme_option('random_themes', enabled))
        self.theme_selector.currentTextChanged.connect(self.change_theme)
        apply_theme(QApplication.instance(), self.theme_selector.currentText())
        self.setStyleSheet('QTabWidget::tab-bar { alignment: center; }')
        self.settings_sections.addTab(appearance, 'Apparence')
        locations = QWidget()
        locations_layout = QVBoxLayout(locations)
        locations_layout.addWidget(QLabel('Lieux disponibles pour les équipements'))
        self.place_list = QListWidget()
        locations_layout.addWidget(self.place_list)
        place_controls = QHBoxLayout()
        self.place_name = QLineEdit()
        self.place_name.setPlaceholderText('Exemple : Chambre #1')
        place_controls.addWidget(self.place_name)
        add_place_button = QPushButton('Ajouter le lieu')
        add_place_button.clicked.connect(self.add_location)
        self.place_name.returnPressed.connect(self.add_location)
        place_controls.addWidget(add_place_button)
        locations_layout.addLayout(place_controls)
        locations_layout.addWidget(QLabel('Les lieux servent à préparer la répartition des équipements. Ils ne changent pas les prix.'))
        self.settings_sections.addTab(locations, 'Lieux')
        self.settings_sections.addTab(suppliers, 'Fournisseurs')
        self.settings_sections.addTab(detail, 'Offres et historique')
        lists = QWidget()
        self.lists_page = lists
        self.lists_directory = Path(store.setting('lists_directory', str(Path.cwd()))).expanduser()
        lists_layout = QVBoxLayout(lists)
        lists_note = QLabel('Enregistrez vos références, quantités et lieux dans un fichier. Charger une liste remplace la liste actuelle après confirmation.')
        lists_note.setWordWrap(True)
        lists_layout.addWidget(lists_note)
        list_buttons = QHBoxLayout()
        list_buttons.addStretch()
        self.save_list_button = QPushButton('Enregistrer')
        self.save_list_button.setMinimumSize(140, 40)
        self.save_list_button.clicked.connect(self.save_list)
        list_buttons.addWidget(self.save_list_button)
        self.load_list_button = QPushButton('Charger')
        self.load_list_button.setMinimumSize(140, 40)
        self.load_list_button.clicked.connect(self.load_list)
        list_buttons.addWidget(self.load_list_button)
        list_buttons.addStretch()
        lists_layout.addLayout(list_buttons)
        directory_row = QHBoxLayout()
        self.lists_directory_label = QLabel()
        self.lists_directory_label.setWordWrap(True)
        directory_row.addWidget(self.lists_directory_label, 1)
        choose_directory = QPushButton('Choisir le dossier…')
        choose_directory.clicked.connect(self.choose_lists_directory)
        directory_row.addWidget(choose_directory)
        lists_layout.addLayout(directory_row)
        self.list_files = QListWidget()
        self.list_files.setViewMode(QListView.IconMode)
        self.list_files.setResizeMode(QListView.Adjust)
        self.list_files.setMovement(QListView.Static)
        self.list_files.setIconSize(QSize(72, 72))
        self.list_files.setGridSize(QSize(160, 120))
        self.list_files.setSpacing(12)
        self.list_files.setWordWrap(True)
        self.list_files.itemClicked.connect(self.load_list_item)
        self.list_files.itemActivated.connect(self.load_list_item)
        lists_layout.addWidget(self.list_files, 1)
        self.refresh_list_files()
        self.settings_sections.addTab(lists, 'Listes')
        self.settings_sections.currentChanged.connect(self.refresh_list_files)
        display = QWidget()
        display_layout = QFormLayout(display)
        self.show_ht = QCheckBox('Afficher la colonne Total HT calculé')
        self.show_ht.setChecked(store.setting('show_ht', '1') == '1')
        display_layout.addRow(self.show_ht)
        display_layout.addRow('TVA (%)', self.vat)
        rule = QLabel('HT = TTC ÷ (1 + TVA / 100).\nLe total HT est calculé avec la quantité, puis arrondi au centime.\nLe prix fournisseur et le total TTC restent inchangés. Hors livraison.')
        rule.setWordWrap(True)
        display_layout.addRow(rule)
        self.settings_sections.addTab(display, 'Affichage et TVA')
        self.show_ht.toggled.connect(self.change_ht_visibility)
        self.material_model.modelReset.connect(self.apply_ht_visibility)
        self.apply_ht_visibility()
        comparison_settings = QWidget()
        comparison_layout = QFormLayout(comparison_settings)
        self.auto_compare = QCheckBox('Comparer automatiquement à intervalles réguliers')
        self.auto_compare.setChecked(store.setting('auto_compare', '0') == '1')
        self.comparison_minutes = QSpinBox()
        self.comparison_minutes.setRange(1, 1440)
        self.comparison_minutes.setSuffix(' min')
        self.comparison_minutes.setValue(int(store.setting('comparison_minutes', '5')))
        comparison_layout.addRow(self.auto_compare)
        comparison_layout.addRow('Fréquence', self.comparison_minutes)
        comparison_layout.addRow(self.force_refresh)
        note = QLabel('La comparaison périodique récupère de nouveaux prix et rétablit les choix automatiques.\nElle nécessite une liste non vide et un fournisseur actif. Aucun lancement simultané.\nSans actualisation forcée, un lancement ordinaire peut réutiliser un relevé de moins de 5 minutes.')
        note.setWordWrap(True)
        comparison_layout.addRow(note)
        self.settings_sections.addTab(comparison_settings, 'Comparaison')
        self.settings_sections.addTab(self.shipping_panel.settings_page, 'Livraison')
        self.catalog_page = CatalogPage(store, can_start=lambda: self.worker is None)
        self.catalog_page.changed.connect(self.reload_catalog)
        self.catalog_page.changed.connect(self.supplier_model.refresh)
        self.catalog_page.finished.connect(self.discovery_finished)
        self.settings_sections.addTab(self.catalog_page, 'Catalogue')
        self.comparison_timer = QTimer(self)
        self.comparison_timer.timeout.connect(self.run_periodic_comparison)
        self.auto_compare.toggled.connect(self.configure_comparison_timer)
        self.comparison_minutes.valueChanged.connect(self.configure_comparison_timer)
        self.configure_comparison_timer()
        tabs.addTab(parameters, 'Paramètres')
        self.electrical_page = ElectricalPage(store)
        tabs.addTab(self.electrical_page, 'Calcul électrique')
        self.theory_page = TheoryPage()
        tabs.addTab(self.theory_page, 'Théorie')
        self.norm_page = NormPage(store)
        tabs.addTab(self.norm_page, 'Norme')
        self.material_model.modelReset.connect(self.electrical_page.refresh)
        help_page = QWidget()
        help_layout = QVBoxLayout(help_page)
        help_heading = QLabel('Aide')
        help_heading.setStyleSheet('font-size: 22px; font-weight: 600;')
        help_layout.addWidget(help_heading)
        help_content = QTextBrowser()
        help_content.setHtml(f'''
            <p><b>À retenir :</b> l’application démarre avec une liste vide.
            Enregistrez votre liste dans un fichier pour la retrouver plus tard.</p>

            <p><b>Calcul électrique :</b> pour un logement monophasé, créez vos rangées,
            affectez chaque disjoncteur reconnu (Legrand phase + neutre ou bipolaire, calibre et courbe lus
            dans sa désignation) et précisez son usage ainsi que les caractéristiques
            du différentiel prévu. Choisissez la règle amont ou aval pour consulter les critères détaillés.
            Les rangées sont enregistrées avec la liste. Ce contrôle ne valide pas la conformité globale du tableau.</p>

            <h3>1. Préparer votre liste de matériel</h3>
            <ul>
                <li>Dans <b>Matériel</b>, recherchez une désignation, une marque ou une référence.
                Les mots peuvent être saisis dans n’importe quel ordre, par exemple « disj 16 ».</li>
                <li>Sélectionnez l’article, indiquez la quantité et éventuellement le lieu,
                puis cliquez sur <b>Ajouter</b>. Les ajouts d’une même référence sont regroupés.</li>
                <li>Vous pouvez aussi survoler le bouton <b>Familles</b> : domaine, famille, puis sous-famille
                et calibre. Les disjoncteurs et différentiels affichent leurs variantes (pôles, courbe, pouvoir de coupure,
                raccordement ; type et sensibilité). L’appareillage est classé par gamme, fonction, puis mécanisme,
                enjoliveur ou complet ; les plaques par nombre de postes ou de modules. Cliquez sur un article pour
                l’ajouter directement, avec la quantité et le lieu choisis.</li>
                <li>Double-cliquez sur une quantité pour la modifier.
                Une diminution retire les derniers exemplaires.</li>
                <li>Pour retirer un article ou un exemplaire, sélectionnez sa ligne
                puis cliquez sur <b>Supprimer la sélection</b>.</li>
            </ul>

            <h3>2. Répartir les équipements par lieu</h3>
            <ul>
                <li>Le lieu choisi sur la ligne principale s’applique à tous les exemplaires.</li>
                <li>Dépliez une référence pour affecter un lieu à chaque exemplaire.</li>
                <li>Ajoutez vos lieux dans <b>Paramètres → Lieux</b>.
                Les affectations ne changent pas les prix.</li>
            </ul>

            <h3>3. Comparer les prix</h3>
            <ul>
                <li>Gérez les fournisseurs actifs dans <b>Paramètres → Fournisseurs</b>.
                Un fournisseur ajouté nécessite un connecteur compatible pour récupérer ses prix.</li>
                <li>La comparaison se lance automatiquement à chaque ajout d’article.
                Vous pouvez aussi cliquer sur <b>Comparer les prix</b> et annuler une recherche en cours.</li>
                <li>Les colonnes affichent les prix unitaires TTC. Par défaut, le liseré rouge indique
                le minimum confirmé, égalités incluses. Cliquez sur un autre prix valide pour retenir
                cette offre, même plus chère : le cadre rouge suit votre choix.</li>
                <li>Le total TTC en bas à droite additionne les offres retenues, multipliées par les
                quantités. Les égalités ne sont comptées qu’une fois. « Incomplet » indique qu’il manque
                une offre valide. Une nouvelle comparaison rétablit les choix automatiques.</li>
                <li>Déplacez les colonnes en faisant glisser leur en-tête et ajustez leur largeur
                en tirant leurs séparations. Les lots restent exclus du minimum unitaire.</li>
                <li>Survolez une offre pour voir sa date et son statut.
                Consultez les détails des relevés dans <b>Paramètres → Offres et historique</b>.</li>
                <li>Dans <b>Paramètres → Affichage et TVA</b>, affichez ou masquez la colonne HT
                et réglez le taux : HT = TTC ÷ (1 + TVA / 100).</li>
                <li>Dans <b>Paramètres → Comparaison</b>, activez une comparaison périodique et choisissez
                sa fréquence. Chaque lancement périodique actualise les prix et rétablit les choix automatiques.
                L’option d’actualisation forcée s’applique aux autres lancements.</li>
            </ul>

            <h3>4. Enregistrer, charger et quitter</h3>
            <ul>
                <li>Dans <b>Paramètres → Listes</b>, <b>Enregistrer une liste</b> crée un fichier JSON
                contenant les références, les quantités et les lieux affectés.</li>
                <li><b>Charger une liste</b> remplace la liste actuelle après confirmation
                si elle contient du matériel.</li>
                <li>À la fermeture d’une liste non vide, choisissez <b>Oui</b> pour l’enregistrer
                ou <b>Non</b> pour quitter sans l’enregistrer, après une seconde confirmation.</li>
                <li>Si vous annulez l’enregistrement ou s’il échoue, l’application reste ouverte.
                Au prochain lancement, chargez votre fichier pour retrouver votre liste.</li>
            </ul>

            <h3>5. Choisir un thème</h3>
            <p>Ouvrez <b>Paramètres → Apparence</b> et choisissez un thème dans la liste.
            Le changement s’applique immédiatement.</p>
            <ul>
                <li><b>Thèmes persistants</b> : retrouve le thème choisi au prochain lancement.</li>
                <li><b>Thèmes aléatoires</b> : choisit un thème au hasard à chaque lancement.
                Cette option est prioritaire si les deux cases sont cochées.</li>
                <li>Les deux options sont décochées par défaut.</li>
            </ul>

            <h3>6. Vérifier les références du catalogue</h3>
            <p>Le catalogue contient <b>{len(self.products)} articles</b>.
            Les marques « À confirmer » et les références préfixées restent à vérifier.</p>
            <p>Dans <b>Paramètres → Catalogue</b>, choisissez une famille (ou « Toutes les familles ») puis cliquez sur <b>Rechercher</b>
            pour ajouter automatiquement les produits trouvés chez les fournisseurs. Chaque fiche est contrôlée
            avant ajout ; les lots et accessoires sont écartés. Les articles existants ne sont pas modifiés.</p>
        ''')
        help_layout.addWidget(help_content)
        self.help_dialog = QDialog(self)
        self.help_dialog.setWindowTitle('Aide — KlmElec')
        self.help_dialog.resize(800, 600)
        QVBoxLayout(self.help_dialog).addWidget(help_page)
        self.reload_places()
        self.tabs = tabs
        self.busy_widgets = [self.search, self.family_button, self.quantity, add, self.remove,
                             self.material_table, suppliers, self.vat, self.force_refresh,
                             self.compare_button, self.add_place, locations, self.load_list_button, self.list_files]
        self.load_history()
        self.statusBar().showMessage(f'Données locales : {location}')
        self.material_model.modelReset.connect(self.update_summary)
        self.material_model.dataChanged.connect(self.update_summary)
        self.update_summary()
        self.freshness_timer = QTimer(self)
        self.freshness_timer.setInterval(30000)
        self.freshness_timer.timeout.connect(self.refresh_freshness)
        self.freshness_timer.start()

    def apply_ht_visibility(self):
        ht_column = self.material_model.columnCount()-2
        for column in range(self.material_model.columnCount()):
            self.material_table.setColumnHidden(column, column == ht_column and not self.show_ht.isChecked())

    def change_ht_visibility(self, checked):
        self.store.save_setting('show_ht', int(checked))
        self.apply_ht_visibility()

    def configure_comparison_timer(self):
        enabled = self.auto_compare.isChecked()
        self.store.save_setting('auto_compare', int(enabled))
        self.store.save_setting('comparison_minutes', self.comparison_minutes.value())
        self.comparison_minutes.setEnabled(enabled)
        self.comparison_timer.stop()
        if enabled:
            self.comparison_timer.start(self.comparison_minutes.value() * 60000)

    def run_periodic_comparison(self):
        if (self.auto_compare.isChecked() and self.isVisible() and not self.close_pending
                and self.worker is None and QApplication.activeModalWidget() is None
                and self.store.items() and any(s['active'] for s in self.store.suppliers())):
            self.start_comparison(force=True)

    def open_lists(self):
        self.tabs.setCurrentIndex(1)
        self.settings_sections.setCurrentWidget(self.lists_page)
        self.refresh_list_files()

    def choose_lists_directory(self):
        directory = QFileDialog.getExistingDirectory(self, 'Dossier des listes', str(self.lists_directory))
        if directory:
            self.set_lists_directory(Path(directory))

    def set_lists_directory(self, directory):
        self.lists_directory = directory.resolve()
        self.store.save_setting('lists_directory', self.lists_directory)
        self.refresh_list_files()

    def refresh_list_files(self):
        self.list_files.clear()
        self.lists_directory_label.setText(f'Dossier : {self.lists_directory}')
        try:
            paths = sorted((p for p in self.lists_directory.iterdir()
                            if p.is_file() and p.suffix.lower() == '.json'), key=lambda p: p.name.casefold())
        except OSError:
            self.lists_directory_label.setText(f'Dossier inaccessible : {self.lists_directory}')
            return
        for path in paths:
            item = QListWidgetItem(self.disk_icon, path.stem)
            item.setData(Qt.UserRole, str(path))
            item.setToolTip(str(path))
            self.list_files.addItem(item)
        if not paths:
            self.lists_directory_label.setText(f'Dossier : {self.lists_directory} — aucun fichier JSON')

    def load_list_item(self, item):
        self.load_list(path=item.data(Qt.UserRole))

    def show_help(self):
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def save_list(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Enregistrer une liste', str(self.lists_directory / 'liste-klmelec.json'), 'Liste KLM Elec (*.json)')
        if not path:
            return
        if not Path(path).suffix:
            path += '.json'
        data = json.dumps(self.store.export_list(), ensure_ascii=False, indent=2).encode('utf-8')
        output = QSaveFile(path)
        if not output.open(QIODevice.WriteOnly):
            QMessageBox.warning(self, 'Enregistrement impossible', output.errorString())
            return
        if output.write(data) != len(data):
            output.cancelWriting()
            QMessageBox.warning(self, 'Enregistrement impossible', output.errorString())
            return
        if not output.commit():
            QMessageBox.warning(self, 'Enregistrement impossible', output.errorString())
            return
        self.statusBar().showMessage(f'Liste enregistrée : {path}')
        self.set_lists_directory(Path(path).parent)
        return True

    def load_list(self, *, path=None):
        if self.worker is not None:
            return
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, 'Charger une liste', str(self.lists_directory), 'Liste KLM Elec (*.json)')
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding='utf-8'))
            self.store.validate_list(payload)
            if self.store.items() and QMessageBox.question(
                    self, 'Remplacer la liste', 'Remplacer la liste actuelle par celle du fichier ?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            self.store.import_list(payload)
        except (OSError, ValueError, sqlite3.Error) as exc:
            QMessageBox.warning(self, 'Chargement impossible', str(exc))
            return
        self.set_lists_directory(Path(path).parent)
        self.reload_places()
        self.invalidate_comparison()
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage(f'Liste chargée : {path}')
        if self.material_model.rows and self.material_model.suppliers:
            self.start_comparison()

    def change_theme(self, name):
        self.setStyleSheet('')
        apply_theme(QApplication.instance(), name)
        self.setStyleSheet('QTabWidget::tab-bar { alignment: center; }')
        if self.persistent_themes.isChecked():
            self.store.save_theme(name)

    def change_theme_persistence(self, enabled):
        self.store.save_theme_option('persistent_themes', enabled)
        if enabled:
            self.store.save_theme(self.theme_selector.currentText())

    def refresh_freshness(self):
        if self.material_model.offers and self.worker is None:
            self.material_model.refresh_prices()
            self.update_summary()
            self.show_report()

    def invalidate_comparison(self):
        self.material_model.selected_suppliers.clear()
        self.material_model.offers = []
        self.current_payload = None
        self.material_model.refresh()
        self.load_history()

    def change_vat(self):
        value = str(self.vat.value())
        self.store.save_vat(value)
        self.material_model.vat = value
        # Seul le HT dépend de la TVA : conserver les prix relevés et les choix d'offres.
        self.material_model.refresh_prices()
        self.update_summary()

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

    def start_comparison(self, *, force=False):
        if self.worker and self.worker.isRunning():
            return
        if self.catalog_page.busy():
            self.statusBar().showMessage('Recherche du catalogue en cours : la comparaison sera possible ensuite.')
            return
        items = [dict(row) for row in self.store.items()]
        suppliers = [dict(row) for row in self.store.suppliers() if row['active']]
        if not items or not suppliers:
            QMessageBox.information(self, 'Comparaison', 'Veuillez ajouter du matériel et activer au moins un fournisseur.')
            return
        previous = []
        if not force and not self.force_refresh.isChecked():
            # Newest observations first: cache_lookup scans in reverse.
            for _, payload in reversed(self.store.comparisons()):
                previous.extend(payload['offers'])
        self.material_model.selected_suppliers.clear()
        self.material_model.offers = []
        self.material_model.refresh()
        self.pending_payload = dict(date=now(), vat=str(self.vat.value()), items=items, offers=[])
        for widget in self.busy_widgets:
            widget.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker = ComparisonWorker(items, suppliers, previous, self, links=self.store.product_links())
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
        self.tabs.setCurrentIndex(0)
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
            self.close_pending = False
            self.close()

    def cancel_comparison(self):
        if self.worker:
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage('Annulation demandée — attente de la requête en cours (délai réseau : 15 s).')

    def discovery_finished(self):
        if self.close_pending and self.worker is None:
            self.close_pending = False
            self.close()

    def closeEvent(self, event):
        if self.catalog_page.busy():
            self.close_pending = True
            self.catalog_page.cancel()
            event.ignore()
            return
        if self.worker is not None:
            self.close_pending = True
            self.cancel_comparison()
            event.ignore()
            return
        if self.store.items():
            answer = QMessageBox.question(
                self, 'Enregistrer avant de quitter', 'Voulez-vous enregistrer la liste avant de quitter ?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if answer == QMessageBox.Yes:
                if not self.save_list():
                    event.ignore()
                    return
            elif answer == QMessageBox.No:
                confirmation = QMessageBox.question(
                    self, 'Quitter sans enregistrer',
                    'Confirmez-vous la fermeture sans enregistrer ? La liste sera vide au prochain démarrage.',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if confirmation != QMessageBox.Yes:
                    event.ignore()
                    return
            else:
                event.ignore()
                return
        self.comparison_timer.stop()
        event.accept()

    def edit_place(self, index):
        if index.column() == 4:
            self.material_table.edit(index)

    def save_expansion(self):
        self.expanded_products = {row['id'] for i, row in enumerate(self.material_model.rows)
                                  if self.material_table.isExpanded(self.material_model.index(i, 0))}

    def restore_expansion(self):
        for i, row in enumerate(self.material_model.rows):
            if row['id'] in self.expanded_products:
                self.material_table.setExpanded(self.material_model.index(i, 0), True)

    def reload_places(self):
        selected = self.add_place.currentData()
        self.add_place.clear()
        self.add_place.addItem('Non affecté', None)
        for place in self.store.locations():
            self.add_place.addItem(place['name'], place['id'])
        self.add_place.setCurrentIndex(max(0, self.add_place.findData(selected)))
        if hasattr(self, 'place_list'):
            self.place_list.clear()
            self.place_list.addItems([p['name'] for p in self.store.locations()])

    def add_location(self):
        try:
            location_id = self.store.add_location(self.place_name.text())
        except ValueError as exc:
            QMessageBox.warning(self, 'Lieu incorrect', str(exc))
            return
        self.reload_places()
        self.material_model.refresh()
        self.add_place.setCurrentIndex(self.add_place.findData(location_id))
        self.place_name.clear()

    def reload_catalog(self):
        current = self.search.currentText()
        self.products = self.store.products()
        self.labels = {f"{p['name']} · {p['brand']} · {p['reference']}": p['id'] for p in self.products}
        self.search.clear()
        self.search.addItems(list(self.labels))
        self.search.setCurrentIndex(-1)
        self.search.setEditText(current)
        self.suggestions.setStringList(list(self.labels))
        self.family_button.set_products(self.products)

    def filter_products(self, query):
        self.suggestions.setStringList([label for label in self.labels if matches(query, label)])

    def remember_column_width(self, column, old_size, new_size):
        if not self.sizing_columns and column < len(self.material_model.headers):
            self.manual_column_widths.add(self.material_model.headers[column])

    def size_material_columns(self):
        metrics = self.material_table.fontMetrics()
        self.sizing_columns = True
        try:
            for column, heading in enumerate(self.material_model.headers):
                if heading in self.manual_column_widths:
                    continue
                header_width = max(metrics.horizontalAdvance(line) for line in heading.split('\n')) + 20
                texts = [str(self.material_model.index(row, column).data() or '')
                         for row in range(len(self.material_model.rows))]
                content_width = max((metrics.horizontalAdvance(text) for text in texts), default=0) + 20
                if column == 0:
                    content_width += self.material_table.indentation()
                # Long designations/status messages must not consume the whole table.
                cap = 280 if column == 0 else 170 if column == 4 else 140
                width = max(header_width, min(content_width, cap))
                self.material_table.setColumnWidth(column, width)
        finally:
            self.sizing_columns = False

    def update_summary(self):
        rows = self.material_model.rows
        totals = []
        for row in rows:
            winner = self.material_model.selected_offer(row)
            if winner:
                totals.append(amounts(winner['ttc'], row['quantity'], self.material_model.vat)[2:])
        if rows and len(totals) == len(rows):
            ht = sum((t[0] for t in totals), Decimal(0))
            ttc = sum((t[1] for t in totals), Decimal(0))
            text = f'Total HT calculé : {euros(ht)} · Total TTC : {euros(ttc)}'
            self.total_label.setText(f'Total TTC\n{euros(ttc)}')
        elif not rows:
            text = 'Liste vide'
            self.total_label.setText('Total TTC\n0,00 €')
        else:
            text = f'Total non disponible — {len(totals)}/{len(rows)} référence(s) avec une offre retenue'
            self.total_label.setText('Total TTC\nIncomplet')
        self.summary.setText(f'{len(rows)} référence(s) · {text}. Hors livraison.')

    def add_item(self):
        product_id = self.labels.get(self.search.currentText())
        if product_id is None:
            QMessageBox.information(self, 'Choisissez un article', 'Veuillez sélectionner un article proposé avant de l’ajouter.')
            return
        self.add_product(product_id)

    def add_product(self, product_id):
        try:
            self.store.add_item(product_id, self.quantity.value(), self.add_place.currentData())
        except ValueError as exc:
            QMessageBox.warning(self, 'Quantité incorrecte', str(exc))
            return
        self.material_model.refresh()
        # Comparaison automatique ; les relevés de moins de 5 minutes sont réutilisés.
        if self.material_model.suppliers:
            self.start_comparison()

    def remove_item(self):
        index = self.material_table.currentIndex()
        if index.isValid():
            product_id = self.material_model.item(index)['id']
            if index.internalId():
                self.store.remove_unit(product_id, index.row())
            else:
                self.store.remove_item(product_id)
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
            supplier = self.supplier_model.rows[index.row()]
            if QMessageBox.question(
                    self, 'Retirer le fournisseur',
                    f"Retirer « {supplier['name']} » de la liste des fournisseurs ?\n"
                    'Les prix relevés de la session en cours seront effacés.',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            self.store.archive_supplier(supplier['id'])
            self.supplier_model.refresh()
            self.invalidate_comparison()


def install_translations(app):
    """Boutons standard de Qt (Oui, Non, Annuler…) et boîtes de fichiers en français."""
    translator = QTranslator(app)
    if translator.load(QLocale(QLocale.French, QLocale.France), 'qtbase', '_',
                       QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
        return translator
    return None


def main():
    app = QApplication(sys.argv)
    install_translations(app)
    app.setApplicationName('KlmElec')
    app.setOrganizationName('KlmElec')
    pixmap = QPixmap()
    pixmap.loadFromData(files('klmelec').joinpath('assets/klmelec-rond.png').read_bytes())
    app.setWindowIcon(QIcon(pixmap))
    directory = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / 'klmelec.sqlite3')
    store.clear_list()
    window = MainWindow(store, directory)
    window.show()
    try:
        return app.exec()
    finally:
        store.close()
