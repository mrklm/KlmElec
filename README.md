# KLM Elec

Application de bureau Python pour préparer une liste de matériel électrique.

## Fonctionnalités

- Catalogue de 27 articles issus des tableurs Elec Lille, Braise/Musse et Samia.
- Recherche par mots, marque et référence, sans distinction de casse ou d'accents.
- Ajout de quantités, confirmation des doublons, modification et suppression des lignes.
- Fournisseurs : ajout, modification, activation/désactivation et retrait.
- Sauvegarde automatique de la liste et des fournisseurs dans SQLite.

123 Elec et Elec Distrib sont préconfigurés. Vous pouvez ajouter d'autres sites.
La comparaison fonctionne pour quatre références Legrand : **406774, 411617, 411633 et 411638**.
Les URL étudiées sont associées explicitement dans les connecteurs ; aucune recherche
interne ni correspondance approximative n'est utilisée. Les autres références affichent
« URL non configurée ». Ajouter un fournisseur ne suffit pas à rendre ses prix accessibles.

Cliquez sur **Comparer les prix**, puis consultez **Offres et historique** pour les
prix, statuts, dates, écarts et liens source. La recherche s'exécute en arrière-plan ;
l'édition est temporairement désactivée pour conserver une liste cohérente. Le bouton
Annuler attend la fin de la requête en cours ; fermer la fenêtre demande aussi son arrêt.

Le minimum est validé uniquement si tous les fournisseurs activés renvoient une offre
unitaire disponible et comparable. Un fournisseur sans connecteur, un échec, une
rupture ou un lot empêche donc de déclarer un minimum pour cette ligne. Le lot de dix
406774 d'Elec Distrib est exclu : aucun total complet si cette ligne figure dans la liste
avec ce fournisseur actif. Les offres obtenues restent consultables individuellement.

Le total du projet n'est affiché que lorsque toutes les lignes sont comparées. Les
calculs utilisent Decimal, avec arrondi au centime, hors livraison. Le TTC provient du
site ; le HT est **calculé** avec la TVA configurable (20 % initialement). Le total HT
est arrondi après multiplication du HT non arrondi par la quantité.

Un relevé réussi de moins de cinq minutes peut être réutilisé : son horodatage initial
et la mention cache restent visibles. Cochez « Actualiser même si… » pour refaire les
requêtes. Après cinq minutes, le minimum n'est plus validé ; la vue se met à jour au
plus tard trente secondes après. Au redémarrage, les relevés sont uniquement historiques
jusqu'à une nouvelle comparaison. Les vingt derniers sont proposés dans l'interface,
mais tous sont conservés en base. Les erreurs n'écrasent jamais les anciens relevés.

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

Les ajouts Braise/Musse et Samia sont intégrés automatiquement au prochain lancement,
sans écraser les articles déjà enregistrés ni modifier la liste de travail.
Les prix et quantités des tableurs ne sont pas importés. Consultez le
[compte rendu des références](docs/import-braise-samia.md) pour les sources,
les doublons et les lignes sans référence. Les neuf ajouts restent sans URL fournisseur
configurée : leur comparaison automatique n'est pas encore disponible.

## Vérification

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Les tests utilisent des bases temporaires, jamais votre liste personnelle.
Le stockage est isolé dans `data.py`, l'interface dans `app.py`.
Les fournisseurs sont des données en base, indépendantes du catalogue. Le champ
`connector` est un identifiant, pas du code exécutable. Il est effacé si le domaine d'un
fournisseur change. Pour ajouter un site compatible, implémentez le contrat `Connector`
dans `suppliers/`, associez les URL vérifiées et enregistrez-le dans `CONNECTORS`.
Le transport réseau et les calculs de `comparison.py` sont indépendants de Qt et SQLite.

Les requêtes sont espacées d'au moins une seconde, sans redirection automatique, avec
un délai réseau de 15 secondes et une taille maximale de réponse de 5 Mo. Les règles
robots.txt sont consultées à chaque comparaison nécessitant le réseau ; un refus
HTTP 403/429 suspend ce site pour le reste du relevé. Aucun contournement ni collecte
de catalogue n'est effectué. La récupération demeure dépendante de la structure des
sites et de leurs conditions d'accès ; voir les limites de l'étude.

## Étude des fournisseurs

Consultez [le rapport de faisabilité](docs/faisabilite.md).
La sonde ponctuelle `experiments/inspect_pages.py` n'est pas utilisée par l'application.
Elle lit six fiches publiques et conserve ses observations dans `local-study/`, exclu
 de Git. Réexaminer les règles des sites avant de la relancer.

## Versionnement

Version centralisée dans `VERSION`. Commits en français avec les préfixes
`feat:`, `fix:`, `docs:`, `test:`, `chore:`. Aucun commit ni push automatique.
