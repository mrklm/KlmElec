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

    def products(self):
        return self.db.execute('SELECT * FROM products ORDER BY name,reference').fetchall()

    def items(self):
        return self.db.execute('SELECT p.*,i.quantity FROM items i JOIN products p ON p.id=i.product_id ORDER BY p.name,p.reference').fetchall()

    def add_item(self, product_id, quantity):
        if type(quantity) is not int or quantity < 1:
            raise ValueError('Veuillez saisir une quantité entière positive.')
        with self.db:
            old = self.db.execute('SELECT quantity FROM items WHERE product_id=?', (product_id,)).fetchone()
            total = quantity + (old['quantity'] if old else 0)
            if total > 99999:
                raise ValueError('La quantité totale ne doit pas dépasser 99 999.')
            self.db.execute('INSERT INTO items VALUES (?,?) ON CONFLICT(product_id) DO UPDATE SET quantity=excluded.quantity', (product_id, total))

    def set_quantity(self, product_id, quantity):
        if type(quantity) is not int or not 1 <= quantity <= 99999:
            raise ValueError('Veuillez saisir une quantité entre 1 et 99 999.')
        with self.db:
            self.db.execute('UPDATE items SET quantity=? WHERE product_id=?', (quantity, product_id))

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
