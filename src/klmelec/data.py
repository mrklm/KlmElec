"""Catalogue, liste locale et fournisseurs indépendants de l'interface."""
import json
import sqlite3
import unicodedata
from importlib.resources import files
from urllib.parse import urlsplit
from .electrical import empty_plan, prune_plan, validate_plan


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
            if not self.db.execute("SELECT 1 FROM settings WHERE key='supplier_yesss_v1'").fetchone():
                existing = self.db.execute('SELECT url FROM suppliers').fetchall()
                if not any((urlsplit(row['url']).hostname or '').lower() in ('yesss-fr.com', 'www.yesss-fr.com')
                           for row in existing):
                    self.db.execute('INSERT INTO suppliers(name,url,active) VALUES (?,?,0)',
                                    ('YESSS Électrique', 'https://www.yesss-fr.com/'))
                self.db.execute("INSERT INTO settings VALUES ('supplier_yesss_v1','1')")
            # Add bundled references once per catalog revision. Existing names, IDs,
            # quantities, suppliers and historical snapshots are never overwritten.
            if not self.db.execute("SELECT 1 FROM settings WHERE key='catalog_2026_11_braise_samia'").fetchone():
                for product in json.loads(files('klmelec').joinpath('catalog.json').read_text()):
                    self.db.execute('INSERT OR IGNORE INTO products(name,brand,reference) VALUES (:name,:brand,:reference)', product)
                self.db.execute("INSERT INTO settings VALUES ('catalog_2026_11_braise_samia','1')")

            if not self.db.execute("SELECT 1 FROM settings WHERE key='catalog_405001_v1'").fetchone():
                product = next(p for p in json.loads(files('klmelec').joinpath('catalog.json').read_text())
                               if p['brand'] == 'Legrand' and p['reference'] == '405001')
                self.db.execute('INSERT OR IGNORE INTO products(name,brand,reference) VALUES (:name,:brand,:reference)', product)
                self.db.execute("INSERT INTO settings VALUES ('catalog_405001_v1','1')")

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
        product = self.db.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
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
            self._prune_electrical_plan(product, ordinal)

    def electrical_plan(self):
        return prune_plan(json.loads(self.setting('electrical_plan', json.dumps(empty_plan()))), self.items())

    def save_electrical_plan(self, plan):
        validate_plan(plan, self.items())
        self.save_setting('electrical_plan', json.dumps(plan, ensure_ascii=False))

    def _prune_electrical_plan(self, removed_product=None, ordinal=None):
        raw = self.setting('electrical_plan', None)
        if raw is None:
            return
        plan = json.loads(raw)
        if removed_product is not None:
            shifted = {}
            for key, value in plan['circuits'].items():
                brand, reference, position = json.loads(key)
                if (brand, reference) == (removed_product['brand'], removed_product['reference']):
                    if position == ordinal:
                        continue
                    if position > ordinal:
                        position -= 1
                shifted[json.dumps([brand, reference, position], ensure_ascii=False)] = value
            plan['circuits'] = shifted
        plan = prune_plan(plan, self.items())
        self.db.execute("UPDATE settings SET value=? WHERE key='electrical_plan'", (json.dumps(plan, ensure_ascii=False),))

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

    def export_list(self):
        assignments = self.assignments()
        locations = {row['id']: row['name'] for row in self.locations()}
        payload = {'format': 'klmelec-list', 'version': 1, 'items': [
            {'brand': row['brand'], 'reference': row['reference'], 'quantity': row['quantity'],
             'locations': [locations.get(assignments.get((row['id'], pos))) for pos in range(row['quantity'])]}
            for row in self.items()]}
        plan = self.electrical_plan()
        if plan != empty_plan():
            payload['electrical'] = plan
        return payload

    def clear_list(self):
        with self.db:
            self.db.execute('DELETE FROM items')
            self.db.execute("DELETE FROM settings WHERE key='electrical_plan'")

    def validate_list(self, payload):
        if (not isinstance(payload, dict) or payload.get('format') != 'klmelec-list'
                or type(payload.get('version')) is not int or payload['version'] != 1
                or not isinstance(payload.get('items'), list)):
            raise ValueError('Ce fichier n’est pas une liste KLM Elec compatible.')
        products = {(p['brand'], p['reference']): p['id'] for p in self.products()}
        validated, seen = [], set()
        for item in payload['items']:
            if not isinstance(item, dict) or not all(isinstance(item.get(key), str) for key in ('brand', 'reference')):
                raise ValueError('Une référence du fichier est invalide.')
            product_id = products.get((item['brand'], item['reference']))
            if product_id is None:
                raise ValueError(f"Référence absente du catalogue : {item['brand']} {item['reference']}.")
            quantity, places = item.get('quantity'), item.get('locations')
            if (product_id in seen or type(quantity) is not int or not 1 <= quantity <= 99999
                    or not isinstance(places, list) or len(places) != quantity):
                raise ValueError('Quantité, affectations ou référence en double invalides.')
            cleaned = []
            for place in places:
                if place is None:
                    cleaned.append(None)
                    continue
                if not isinstance(place, str):
                    raise ValueError('Un lieu du fichier est invalide.')
                place = ' '.join(place.split())
                if not 1 <= len(place) <= 80 or normalize(place) in ('non affecte', 'lieux multiples'):
                    raise ValueError('Un lieu du fichier est invalide.')
                cleaned.append(place)
            seen.add(product_id)
            validated.append((product_id, quantity, cleaned))
        validate_plan(payload.get('electrical', empty_plan()), payload['items'])
        return validated

    def import_list(self, payload):
        validated = self.validate_list(payload)
        with self.db:
            self.db.execute('DELETE FROM items')
            self.db.execute("DELETE FROM settings WHERE key='electrical_plan'")
            if 'electrical' in payload:
                self.db.execute('INSERT INTO settings VALUES (?,?)', ('electrical_plan', json.dumps(payload['electrical'], ensure_ascii=False)))
            for product_id, quantity, places in validated:
                self.db.execute('INSERT INTO items VALUES (?,?)', (product_id, quantity))
                for ordinal, place in enumerate(places):
                    if place is not None:
                        key = normalize(place)
                        self.db.execute('INSERT OR IGNORE INTO locations(name,normalized) VALUES (?,?)', (place, key))
                        location_id = self.db.execute('SELECT id FROM locations WHERE normalized=?', (key,)).fetchone()['id']
                        self.db.execute('INSERT INTO item_locations VALUES (?,?,?)', (product_id, ordinal, location_id))

    def set_quantity(self, product_id, quantity):
        if type(quantity) is not int or not 1 <= quantity <= 99999:
            raise ValueError('Veuillez saisir une quantité entre 1 et 99 999.')
        with self.db:
            self.db.execute('UPDATE items SET quantity=? WHERE product_id=?', (quantity, product_id))
            self.db.execute('DELETE FROM item_locations WHERE product_id=? AND ordinal>=?', (product_id, quantity))
            self._prune_electrical_plan()

    def remove_item(self, product_id):
        with self.db:
            self.db.execute('DELETE FROM items WHERE product_id=?', (product_id,))
            self._prune_electrical_plan()

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

    def theme(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='theme'").fetchone()
        return row['value'] if row else None

    def setting(self, key, default):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row['value'] if row else default

    def save_setting(self, key, value):
        with self.db:
            self.db.execute('INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            (key, str(value)))

    def theme_option(self, key):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return bool(row and row['value'] == '1')

    def save_theme_option(self, key, enabled):
        with self.db:
            self.db.execute('INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            (key, '1' if enabled else '0'))

    def save_theme(self, name):
        with self.db:
            self.db.execute("INSERT INTO settings VALUES ('theme',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (name,))

    def vat(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='vat'").fetchone()
        return row['value'] if row else '20'

    def save_vat(self, value):
        with self.db:
            self.db.execute("INSERT INTO settings VALUES ('vat',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (value,))

    def close(self):
        self.db.close()
