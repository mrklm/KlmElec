# KLM Elec

Application de bureau Python pour préparer une liste de matériel électrique.

## Fonctionnalités

- Catalogue de 27 articles issus des tableurs Elec Lille, Braise/Musse et Samia.
- Recherche par mots, marque et référence, sans distinction de casse ou d'accents.
- Regroupement automatique par référence, quantités modifiables et exemplaires dépliables.
- Affectation des lieux par exemplaire ou pour toute une référence ; ajout de lieux dans Paramètres.
- Une colonne de prix unitaire TTC par fournisseur actif, minimum confirmé encadré en rouge.
- Fournisseurs : ajout, modification, activation/désactivation et retrait.
- Sauvegarde automatique de la liste et des fournisseurs dans SQLite.

123 Elec et Elec Distrib sont préconfigurés. Vous pouvez ajouter d'autres sites.
La comparaison fonctionne pour quatre références Legrand : **406774, 411617, 411633 et 411638**.
Les URL étudiées sont associées explicitement dans les connecteurs ; aucune recherche
interne ni correspondance approximative n'est utilisée. Les autres références affichent
« URL non configurée ». Ajouter un fournisseur ne suffit pas à rendre ses prix accessibles.

Cliquez sur **Comparer les prix** : les offres apparaissent directement côte à côte
dans le tableau Matériel. Le liseré rouge marque le minimum confirmé (toutes les offres
à égalité sont encadrées). Une comparaison incomplète ou ancienne n’est pas encadrée.
Survolez un prix pour sa date et son statut. Consultez **Offres et historique** pour
les anciens relevés et les liens source. La recherche s'exécute en arrière-plan ;
l'édition est temporairement désactivée pour conserver une liste cohérente. Le bouton
Annuler attend la fin de la requête en cours ; fermer la fenêtre demande aussi son arrêt.

Le minimum est validé uniquement si tous les fournisseurs activés renvoient une offre
unitaire disponible et comparable. Un fournisseur sans connecteur, un échec, une
rupture ou un lot empêche donc de déclarer un minimum pour cette ligne. La référence
406774 est associée à la fiche unitaire d'Elec Distrib, distincte du lot de dix.
Les offres obtenues restent consultables individuellement.

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

Dans l'onglet Matériel, sélectionnez une proposition, indiquez une quantité et
éventuellement un lieu, puis cliquez sur Ajouter. Les ajouts de la même référence
se regroupent automatiquement : le lieu choisi s'applique uniquement aux nouveaux
exemplaires. Les affectations existantes sont conservées.

Un triangle permet de déplier les exemplaires dès que la quantité dépasse un.
Cliquez sur la cellule Lieu de la ligne principale pour affecter tous les exemplaires,
ou sur celle d'un exemplaire pour ne modifier que lui. La ligne principale affiche
le lieu commun, « Non affecté » ou « Lieux multiples ». Les prix restent sur la ligne
principale ; les lieux n'interviennent pas dans la comparaison.

Double-cliquez sur une quantité pour la modifier. Une augmentation ajoute des
exemplaires non affectés ; une diminution retire les derniers exemplaires et leurs
affectations. Supprimer la sélection retire toute la référence si la ligne principale
est sélectionnée, ou seulement l'exemplaire si une sous-ligne est sélectionnée.

Dans **Paramètres**, ajoutez par exemple « Chambre #1 ». Les dix lieux initiaux sont
Salon, Cave, Cuisine, Garage, Chambre, Hall d’entrée, Couloir, Grenier, Salle à manger
et Escalier. Les noms identiques, même sans accents ou avec une casse différente,
ne créent pas de doublons. Le récapitulatif par lieu et l'onglet Plan restent prévus
pour une étape ultérieure.
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

## Compatibilité des lieux (0.3.0)

Deux tables sont ajoutées : `locations` et `item_locations`. La table `items` et
ses identifiants/quantités restent inchangés. Les anciens équipements ont un lieu
non affecté implicitement ; il n'est pas nécessaire de recréer votre liste.
Les affectations sont enregistrées dans la même transaction que les changements
de quantité. Les fournisseurs et les relevés antérieurs ne sont pas réécrits.

L'ancien code peut lire les quantités et les relevés de cette base, mais ne présente
pas les lieux. Revenir au code précédent conserve les tables supplémentaires ; une
restauration exacte nécessite une sauvegarde de la base. Ne pas utiliser les deux
versions simultanément. Si une ancienne version réduit une quantité, les affectations
des exemplaires retirés sont nettoyées au prochain démarrage de la nouvelle version.
