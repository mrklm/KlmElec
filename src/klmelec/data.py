"""Catalogue, liste locale et fournisseurs indépendants de l'interface."""
import json
import sqlite3
import unicodedata
from importlib.resources import files
from urllib.parse import urlsplit


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(c))


def matches(query, text):
    return all(word in normalize(text) for word in normalize(query).split())


def validate_supplier(name, url):
    name, url = name.strip(), url.strip()
    parts = urlsplit(url)
    if not name:
        raise ValueError('Veuillez renseigner le nom du fournisseur.')
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Veuillez saisir une adresse http:// ou https:// valide, sans identifiants.')
    return name, url


DEFAULT_LOCATIONS = ['Salon', 'Cave', 'Cuisine', 'Garage', 'Chambre', "Hall d’entrée",
                     'Couloir', 'Grenier', 'Salle à manger', 'Escalier']


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys = ON')
        with self.db:
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, brand TEXT NOT NULL,
                    reference TEXT NOT NULL, UNIQUE(brand, reference));
                CREATE TABLE IF NOT EXISTS items (
                    product_id INTEGER PRIMARY KEY REFERENCES products(id),
                    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 99999));
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                    url TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                    connector TEXT, archived INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, normalized TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS item_locations (
                    product_id INTEGER NOT NULL REFERENCES items(product_id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
                    location_id INTEGER NOT NULL REFERENCES locations(id),
                    PRIMARY KEY(product_id, ordinal));
                CREATE TABLE IF NOT EXISTS comparisons (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
            ''')
            if not self.db.execute("SELECT 1 FROM settings WHERE key='seeded'").fetchone():
                for product in json.loads(files('klmelec').joinpath('catalog.json').read_text()):
                    self.db.execute('INSERT OR IGNORE INTO products(name,brand,reference) VALUES (:name,:brand,:reference)', product)
                self.db.executemany('INSERT INTO suppliers(name,url,connector) VALUES (?,?,?)', [
                    ('123 Elec', 'https://www.123elec.com/', '123elec'),
                    ('Elec Distrib', 'https://www.elecdistrib.fr/', 'elecdistrib'),
                ])
                self.db.execute("INSERT INTO settings VALUES ('seeded','1')")
            # Add bundled references once per catalog revision. Existing names, IDs,
            # quantities, suppliers and historical snapshots are never overwritten.
            if not self.db.execute("SELECT 1 FROM settings WHERE key='catalog_2026_11_braise_samia'").fetchone():
                for product in json.loads(files('klmelec').joinpath('catalog.json').read_text()):
                    self.db.execute('INSERT OR IGNORE INTO products(name,brand,reference) VALUES (:name,:brand,:reference)', product)
                self.db.execute("INSERT INTO settings VALUES ('catalog_2026_11_braise_samia','1')")

            if not self.db.execute("SELECT 1 FROM settings WHERE key='locations_v1'").fetchone():
                self.db.executemany('INSERT OR IGNORE INTO locations(name,normalized) VALUES (?,?)',
                                    [(name, normalize(name)) for name in DEFAULT_LOCATIONS])
                self.db.execute("INSERT INTO settings VALUES ('locations_v1','1')")
            # Older versions can still change quantities; discard only out-of-range assignments.
            self.db.execute('DELETE FROM item_locations WHERE ordinal >= (SELECT quantity FROM items WHERE product_id=item_locations.product_id)')

    def locations(self):
        return self.db.execute('SELECT * FROM locations ORDER BY normalized').fetchall()

    def add_location(self, name):
        name = ' '.join(name.split())
        if not name or len(name) > 80:
            raise ValueError('Veuillez saisir un lieu de 1 à 80 caractères.')
        key = normalize(name)
        if key in ('non affecte', 'lieux multiples'):
            raise ValueError('Ce nom est réservé à l’affichage des affectations.')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO locations(name,normalized) VALUES (?,?)', (name, key))
        return self.db.execute('SELECT id FROM locations WHERE normalized=?', (key,)).fetchone()['id']

    def assignments(self):
        return {(row['product_id'], row['ordinal']): row['location_id']
                for row in self.db.execute('SELECT * FROM item_locations')}

    def assign_location(self, product_id, location_id, ordinal=None):
        row = self.db.execute('SELECT quantity FROM items WHERE product_id=?', (product_id,)).fetchone()
        if not row or (ordinal is not None and not 0 <= ordinal < row['quantity']):
            raise ValueError('Cet exemplaire n’existe plus.')
        if location_id is not None and not self.db.execute('SELECT 1 FROM locations WHERE id=?', (location_id,)).fetchone():
            raise ValueError('Veuillez sélectionner un lieu existant.')
        with self.db:
            if ordinal is None:
                self.db.execute('DELETE FROM item_locations WHERE product_id=?', (product_id,))
                positions = range(row['quantity'])
            else:
                self.db.execute('DELETE FROM item_locations WHERE product_id=? AND ordinal=?', (product_id, ordinal))
                positions = [ordinal]
            if location_id is not None:
                self.db.executemany('INSERT INTO item_locations VALUES (?,?,?)',
                                    ((product_id, pos, location_id) for pos in positions))

    def remove_unit(self, product_id, ordinal):
        row = self.db.execute('SELECT quantity FROM items WHERE product_id=?', (product_id,)).fetchone()
        if not row or not 0 <= ordinal < row['quantity']:
            raise ValueError('Cet exemplaire n’existe plus.')
        with self.db:
            if row['quantity'] == 1:
                self.db.execute('DELETE FROM items WHERE product_id=?', (product_id,))
            else:
                following = self.db.execute('SELECT ordinal,location_id FROM item_locations WHERE product_id=? AND ordinal>?', (product_id, ordinal)).fetchall()
                self.db.execute('DELETE FROM item_locations WHERE product_id=? AND ordinal>=?', (product_id, ordinal))
                self.db.executemany('INSERT INTO item_locations VALUES (?,?,?)',
                                    ((product_id, r['ordinal']-1, r['location_id']) for r in following))
                self.db.execute('UPDATE items SET quantity=quantity-1 WHERE product_id=?', (product_id,))

    def products(self):
        return self.db.execute('SELECT * FROM products ORDER BY name,reference').fetchall()

    def items(self):
        return self.db.execute('SELECT p.*,i.quantity FROM items i JOIN products p ON p.id=i.product_id ORDER BY p.name,p.reference').fetchall()

    def add_item(self, product_id, quantity, location_id=None):
        if type(quantity) is not int or quantity < 1:
            raise ValueError('Veuillez saisir une quantité entière positive.')
        with self.db:
            old = self.db.execute('SELECT quantity FROM items WHERE product_id=?', (product_id,)).fetchone()
            total = quantity + (old['quantity'] if old else 0)
            if total > 99999:
                raise ValueError('La quantité totale ne doit pas dépasser 99 999.')
            self.db.execute('INSERT INTO items VALUES (?,?) ON CONFLICT(product_id) DO UPDATE SET quantity=excluded.quantity', (product_id, total))
            if location_id is not None:
                self.db.executemany('INSERT INTO item_locations VALUES (?,?,?)',
                                    ((product_id, pos, location_id) for pos in range(total-quantity, total)))

    def set_quantity(self, product_id, quantity):
        if type(quantity) is not int or not 1 <= quantity <= 99999:
            raise ValueError('Veuillez saisir une quantité entre 1 et 99 999.')
        with self.db:
            self.db.execute('UPDATE items SET quantity=? WHERE product_id=?', (quantity, product_id))
            self.db.execute('DELETE FROM item_locations WHERE product_id=? AND ordinal>=?', (product_id, quantity))

    def remove_item(self, product_id):
        with self.db:
            self.db.execute('DELETE FROM items WHERE product_id=?', (product_id,))

    def suppliers(self):
        return self.db.execute('SELECT * FROM suppliers WHERE archived=0 ORDER BY name').fetchall()

    def save_supplier(self, name, url, active=True, supplier_id=None):
        name, url = validate_supplier(name, url)
        with self.db:
            if supplier_id is None:
                self.db.execute('INSERT INTO suppliers(name,url,active) VALUES (?,?,?)', (name,url,int(active)))
            else:
                # A changed domain cannot silently keep the former site's connector.
                old = self.db.execute('SELECT * FROM suppliers WHERE id=?', (supplier_id,)).fetchone()
                connector = old['connector'] if urlsplit(old['url']).hostname == urlsplit(url).hostname else None
                self.db.execute('UPDATE suppliers SET name=?,url=?,active=?,connector=? WHERE id=?', (name,url,int(active),connector,supplier_id))

    def archive_supplier(self, supplier_id):
        # Retain the identity for future historical price references.
        with self.db:
            self.db.execute('UPDATE suppliers SET archived=1,active=0 WHERE id=?', (supplier_id,))

    def save_comparison(self, payload):
        with self.db:
            self.db.execute('INSERT INTO comparisons(created_at,payload) VALUES (?,?)',
                            (payload['date'], json.dumps(payload, ensure_ascii=False)))

    def comparisons(self):
        return [(row['id'], json.loads(row['payload'])) for row in self.db.execute(
            'SELECT id,payload FROM comparisons ORDER BY id DESC LIMIT 20')]

    def vat(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='vat'").fetchone()
        return row['value'] if row else '20'

    def save_vat(self, value):
        with self.db:
            self.db.execute("INSERT INTO settings VALUES ('vat',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (value,))

    def close(self):
        self.db.close()
