"""Tableau arborescent : références, exemplaires, lieux et offres par fournisseur."""
from decimal import Decimal

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, QSize
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QComboBox, QSpinBox, QStyledItemDelegate, QStyleOptionViewItem

from .comparison import best_offer, amounts, is_recent
from .comparison_ui import euros, local_date

BEST_PRICE_ROLE = Qt.UserRole + 1


class MaterialModel(QAbstractItemModel):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.offers = []
        self.selected_suppliers = {}
        self.vat = store.vat()
        self.load()

    def load(self):
        self.rows = self.store.items()
        self.suppliers = [s for s in self.store.suppliers() if s['active']]
        self.places = {p['id']: p['name'] for p in self.store.locations()}
        self.assignments = self.store.assignments()
        self.headers = ['Désignation', 'Marque', 'Référence', 'Quantité', 'Lieu'] + [
            s['name'] + '\nPU TTC' for s in self.suppliers] + ['Total HT calculé', 'Total TTC']

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        # internalId 0 = reference; parent row + 1 = individual unit.
        return self.createIndex(row, column, parent.row()+1 if parent.isValid() else 0)

    def parent(self, index):
        if not index.isValid() or not index.internalId():
            return QModelIndex()
        return self.createIndex(index.internalId()-1, 0, 0)

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self.rows)
        if parent.column() != 0 or parent.internalId():
            return 0
        quantity = self.rows[parent.row()]['quantity']
        return quantity if quantity > 1 else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]

    def item(self, index):
        return self.rows[index.internalId()-1 if index.internalId() else index.row()]

    def location_value(self, index):
        row = self.item(index)
        if index.internalId():
            return self.assignments.get((row['id'], index.row()))
        values = {self.assignments.get((row['id'], i)) for i in range(row['quantity'])}
        return next(iter(values)) if len(values) == 1 else -1

    def offers_for(self, row):
        ids = {s['id'] for s in self.suppliers}
        return [o for o in self.offers if o['product_id'] == row['id'] and o['supplier_id'] in ids]

    def winner(self, row):
        offers = self.offers_for(row)
        if len(offers) != len(self.suppliers) or {o['supplier_id'] for o in offers} != {s['id'] for s in self.suppliers}:
            return None
        return best_offer(offers)

    def selected_offer(self, row):
        if row['id'] not in self.selected_suppliers:
            return self.winner(row)
        supplier_id = self.selected_suppliers[row['id']]
        return next((offer for offer in self.offers_for(row)
                     if offer['supplier_id'] == supplier_id and self.selectable_offer(offer)), None)

    @staticmethod
    def selectable_offer(offer):
        return offer['status'] == 'ok' and offer['ttc'] is not None and is_recent(offer)

    def select_offer(self, index):
        if (not index.isValid() or index.internalId()
                or not 5 <= index.column() < 5 + len(self.suppliers)):
            return False
        row = self.item(index)
        supplier_id = self.suppliers[index.column()-5]['id']
        offer = next((o for o in self.offers_for(row) if o['supplier_id'] == supplier_id), None)
        if not offer or not self.selectable_offer(offer):
            return False
        self.selected_suppliers[row['id']] = supplier_id
        self.dataChanged.emit(self.index(index.row(), 5), self.index(index.row(), self.columnCount()-1))
        return True

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = self.item(index), index.column()
        child = bool(index.internalId())
        if col == 4:
            value = self.location_value(index)
            if role == Qt.EditRole:
                return value
            if role == Qt.DisplayRole:
                return 'Lieux multiples' if value == -1 else self.places.get(value, 'Non affecté')
            if role == Qt.ToolTipRole:
                return 'Choisissez un lieu pour cet exemplaire.' if child else 'Choisissez un lieu pour tous les exemplaires de cette référence.'
        if role in (Qt.DisplayRole, Qt.EditRole) and col < 4:
            return [f"{row['name']} · exemplaire {index.row()+1}" if child else row['name'],
                    '' if child else row['brand'], '' if child else row['reference'],
                    1 if child else row['quantity']][col]
        if child:
            return None
        winner = self.selected_offer(row)
        if 5 <= col < 5 + len(self.suppliers):
            supplier = self.suppliers[col-5]
            offer = next((o for o in self.offers_for(row) if o['supplier_id'] == supplier['id']), None)
            if role == BEST_PRICE_ROLE:
                if row['id'] in self.selected_suppliers:
                    return bool(winner and offer and offer['supplier_id'] == winner['supplier_id'])
                return bool(winner and offer and Decimal(offer['ttc']) == Decimal(winner['ttc']))
            if role == Qt.ToolTipRole and offer:
                hint = '\nCliquez pour retenir cette offre dans le total.' if self.selectable_offer(offer) else ''
                return f"{offer['detail']}\n{local_date(offer['checked_at'])}\n{offer['url']}" + hint
            if role == Qt.DisplayRole:
                if not offer:
                    return '—'
                if offer['ttc'] is None:
                    return offer['detail']
                label = euros(Decimal(offer['ttc']))
                if offer['status'] != 'ok':
                    return label + ' · ' + offer['detail']
                if not is_recent(offer):
                    return label + ' · ancien'
                return label
        if role == Qt.DisplayRole and col >= 5 + len(self.suppliers):
            if not winner:
                return '—'
            totals = amounts(winner['ttc'], row['quantity'], self.vat)[2:]
            return euros(totals[col-5-len(self.suppliers)])

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 4 or (index.column() == 3 and not index.internalId()):
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        row = self.item(index)
        try:
            if index.column() == 4:
                self.store.assign_location(row['id'], value, index.row() if index.internalId() else None)
                self.assignments = self.store.assignments()
                root = self.parent(index) if index.internalId() else self.index(index.row(), 0)
                self.dataChanged.emit(self.index(root.row(), 4), self.index(root.row(), 4))
                if self.rowCount(root):
                    self.dataChanged.emit(self.index(0, 4, root), self.index(self.rowCount(root)-1, 4, root))
                return True
            if index.column() == 3 and not index.internalId():
                self.store.set_quantity(row['id'], value)
                self.refresh()
                return True
        except ValueError:
            return False
        return False

    def refresh(self):
        self.beginResetModel()
        self.load()
        self.selected_suppliers = {pid: sid for pid, sid in self.selected_suppliers.items()
                                   if any(row['id'] == pid for row in self.rows)
                                   and any(s['id'] == sid for s in self.suppliers)}
        self.endResetModel()

    def refresh_prices(self):
        if self.rows:
            self.dataChanged.emit(self.index(0, 5), self.index(len(self.rows)-1, self.columnCount()-1))


class MaterialDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return super().sizeHint(option, index) + QSize(24, 8)

    def createEditor(self, parent, option, index):
        if index.column() == 4:
            editor = QComboBox(parent)
            editor.addItem('Non affecté', None)
            if index.data(Qt.EditRole) == -1:
                editor.addItem('Lieux multiples', -1)
                editor.model().item(1).setEnabled(False)
            for place in index.model().store.locations():
                editor.addItem(place['name'], place['id'])
            editor.activated.connect(lambda _: self.commitData.emit(editor))
            editor.activated.connect(lambda _: self.closeEditor.emit(editor))
            return editor
        if index.column() == 3:
            editor = QSpinBox(parent)
            editor.setRange(1, 99999)
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            editor.setCurrentIndex(editor.findData(index.data(Qt.EditRole)))
        elif isinstance(editor, QSpinBox):
            editor.setValue(index.data(Qt.EditRole))
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            if editor.currentData() != -1:
                model.setData(index, editor.currentData())
        elif isinstance(editor, QSpinBox):
            editor.interpretText()
            model.setData(index, editor.value())
        else:
            super().setModelData(editor, model, index)

    def paint(self, painter, option, index):
        padded = QStyleOptionViewItem(option)
        padded.rect = option.rect.adjusted(10, 0, -10, 0)
        super().paint(painter, padded, index)
        if index.data(BEST_PRICE_ROLE):
            painter.save()
            painter.setPen(QPen(QColor('#d71920'), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(option.rect.adjusted(2, 2, -2, -2))
            painter.restore()
