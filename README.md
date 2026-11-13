# KLM Elec

Application de bureau Python pour préparer une liste de matériel électrique.

## Première version

- Catalogue initial de 18 articles issus du tableur Elec Lille.
- Recherche par mots, marque et référence, sans distinction de casse ou d'accents.
- Ajout de quantités, confirmation des doublons, modification et suppression des lignes.
- Fournisseurs : ajout, modification, activation/désactivation et retrait.
- Sauvegarde automatique de la liste et des fournisseurs dans SQLite.

123 Elec et Elec Distrib sont préconfigurés. Vous pouvez ajouter d'autres sites.
Les connecteurs réseau seront intégrés à l'étape suivante : ajouter un fournisseur
ne suffit pas à rendre ses prix accessibles. Le bouton de comparaison est désactivé
et les prix restent absents, sans prix fictifs ni anciens prix présentés comme actuels.

## Installation et lancement

Python 3.11 minimum ; version vérifiée sur ce Mac avec Python 3.14.5 et PySide6 6.12.0.
Les autres systèmes et versions de Python restent à tester.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m klmelec
```

L'environnement du dépôt actuel est déjà installé. Pour le relancer :

```sh
.venv/bin/python -m klmelec
```

Dans l'onglet Matériel, sélectionnez une proposition, indiquez une quantité puis
cliquez sur Ajouter. Double-cliquez sur une quantité du tableau pour la modifier.
Dans Fournisseurs, utilisez Ajouter ou Modifier ; la case « Activer ce fournisseur »
contrôle son activation. Le retrait conserve l'identité en base pour un futur historique.

La base est stockée dans le répertoire de données utilisateur choisi par Qt,
indiqué au bas de la fenêtre. Elle n'est pas dans le dépôt Git. Cette version gère
une seule liste de travail. Les projets multiples et l'import interactif viendront ensuite.
Le catalogue initial n'est pas modifiable dans l'interface à ce stade ; les références
IKE/WAG et marques non confirmées sont conservées telles quelles. Le tableur source
n'a pas été modifié et aucun ancien prix n'est importé.

## Vérification

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Les tests utilisent des bases temporaires, jamais votre liste personnelle.
Le stockage est isolé dans `data.py`, l'interface dans `app.py`.
Les fournisseurs sont des données en base, indépendantes du catalogue. Le champ
`connector` est un identifiant prévu pour les futurs connecteurs, pas du code exécutable.
Il est effacé si le domaine d'un fournisseur change. L'interface commune des
connecteurs sera définie avec la récupération effective des prix.

## Étude des fournisseurs

Consultez [le rapport de faisabilité](docs/faisabilite.md).
La sonde ponctuelle `experiments/inspect_pages.py` n'est pas utilisée par l'application.
Elle lit six fiches publiques et conserve ses observations dans `local-study/`, exclu
 de Git. Réexaminer les règles des sites avant de la relancer.

## Versionnement

Version centralisée dans `VERSION`. Commits en français avec les préfixes
`feat:`, `fix:`, `docs:`, `test:`, `chore:`. Aucun commit ni push automatique.
