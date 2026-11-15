# KlmElec — v1.36.0

Application de bureau Python/PySide6 pour préparer une liste de matériel électrique, comparer les prix et vérifier des critères de dimensionnement des différentiels.

## Installation et lancement

Python **3.11 ou supérieur**.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m klmelec
```

Lancements suivants : `.venv/bin/python -m klmelec`.
La version est centralisée dans `VERSION` : paquet Python, titre de fenêtre et identification auprès des fournisseurs.

## Fonctions

- **Matériel** : catalogue de 28 articles extensible automatiquement, recherche par désignation ou référence, ou bouton **Familles** (domaine → type de produit → marque → sous-famille / calibre → article, ajout en un clic ; par exemple Protection → Disjoncteurs → Legrand / Schneider / Hager, Appareillage → Legrand → Dooxie, Mosaic… ; disjoncteurs et différentiels détaillés par variantes, appareillage par fonction, composition, taille de plaque ou de cadre et finition ; domaines Protection, Commande, Mesure, Répartition, Tableaux, GTL, Communication, Boîtes et connexion, Domotique, Sécurité et Appareillage), quantités et lieux par exemplaire.
- **Prix** : comparaison TTC, choix manuel du fournisseur par article et total selon les quantités, hors livraison. La comparaison se lance automatiquement à chaque ajout d’article et peut aussi être périodique.
- **Calcul électrique** : rangées d’un logement monophasé, affectation des circuits, usages et caractéristiques des différentiels. Vérifications amont/aval, calibre, nombre de circuits, type et sensibilité ; données manquantes signalées.
- **Paramètres** : fournisseurs, historique, seuils de livraison offerte saisis manuellement, TVA, colonne HT optionnelle et 16 thèmes (cases à cocher contourées à la couleur du thème).
- **Listes** : enregistrement JSON et accès aux fichiers depuis le raccourci disquette (en haut à gauche). Le bouton « ? » en haut à droite ouvre l’aide dans une fenêtre séparée.
- **Catalogue** : recherche automatique d’une famille de produits chez les deux fournisseurs (disjoncteurs, interrupteurs différentiels, télérupteurs, peignes, contacteurs, parafoudres, interrupteurs-sectionneurs, horloges modulaires, répartiteurs, borniers de répartition, GTL, accessoires GTL, coffrets, portes et rehausses Drivia, tableaux pré-équipés, coffrets et modules de communication, interrupteurs crépusculaires, compteurs d’énergie, éclairage de sécurité Sati, boîtes Legrand, bornes Wago, appareillage Dooxie, Mosaic, Céliane, Plexo, Niloé et saillie Oteo Legrand, domotique Yokis, disjoncteurs et interrupteurs différentiels Schneider et Hager pour l’instant). L’option « Toutes les familles » les enchaîne en une seule recherche (une heure environ) ; « Exporter les références… » enregistre les fiches découvertes dans un fichier JSON. Chaque fiche est contrôlée avant ajout ; les lots et accessoires sont écartés. Yokis et Wago ne sont recherchés que chez 123 Elec ; une fiche dont l’EAN diffère d’un fournisseur à l’autre est écartée.

## Conserver ses listes

**L’application démarre avec une liste vide.** Les fichiers JSON conservent les références, quantités, lieux et rangées électriques, sans les choix d’offres fournisseurs. Les anciennes listes restent chargeables.

Charger une liste remplace la liste actuelle après confirmation si elle n’est pas vide, puis lance la comparaison si un fournisseur est actif. À la fermeture, l’application propose d’enregistrer une liste non vide et demande confirmation avant abandon.

Catalogue, fournisseurs, lieux, préférences et historique sont conservés dans une base SQLite locale. Son chemin est indiqué au lancement dans la barre d’état.

## Périmètre et limites

| Fournisseurs | Références prises en charge pour les prix |
| --- | --- |
| 123 Elec et Elec Distrib | Legrand : 404926, 405000, 405001, 406771, 406773, 406774, 406775, 406777, 411617, 411633, 411638, 412408 |
| 123 Elec uniquement | Wago : WAG2106-5201, WAG2106-5204, WAG2106-5207, WAG2106-1291 |
| 123 Elec uniquement | IKEPE : IKE821023 (tableau nu 3 rangées), IKE821053 (porte blanche) |
| Selon le fournisseur | Disjoncteurs, interrupteurs différentiels, télérupteurs, peignes, contacteurs, parafoudres, interrupteurs-sectionneurs, horloges modulaires, répartiteurs, borniers de répartition, GTL, accessoires GTL, coffrets, portes et rehausses Drivia, tableaux pré-équipés, coffrets et modules de communication, interrupteurs crépusculaires, compteurs d’énergie, éclairage de sécurité Sati, boîtes Legrand, bornes Wago, appareillage Dooxie, Mosaic, Céliane, Plexo, Niloé et saillie Oteo Legrand, domotique Yokis, disjoncteurs et interrupteurs différentiels Schneider et Hager trouvés par **Paramètres → Catalogue** (environ 80 disjoncteurs, 40 différentiels, 7 télérupteurs, 12 peignes, 13 contacteurs, 4 parafoudres, 7 interrupteurs-sectionneurs, 10 horloges, 11 répartiteurs, 10 borniers, 3 GTL, 3 accessoires GTL, 8 coffrets, 16 portes et 8 rehausses Drivia, 17 tableaux pré-équipés, 17 coffrets et 6 modules de communication, 2 interrupteurs crépusculaires, 5 compteurs d’énergie, 7 BAES Sati, 59 boîtes Legrand, 18 bornes Wago (123 Elec seulement), environ 120 références Dooxie, 100 Mosaic, 480 Céliane, 116 Plexo, 2 Niloé et 38 saillie, 49 Yokis (123 Elec seulement), 168 disjoncteurs et 44 différentiels Schneider, 13 disjoncteurs et 8 différentiels Hager, références d’origine comprises, lors des relevés des 14 et 15/11/2026) |

La recherche du catalogue utilise le plan de site de 123 Elec et les pages de catégorie d’Elec Distrib : leurs moteurs de recherche sont exclus par robots.txt. Une fiche n’est retenue que si sa marque, sa référence, son EAN, son titre et son offre TTC sont confirmés ; un EAN différent selon le fournisseur l’écarte. Les fiches retenues sont conservées dans la base locale, celles configurées dans le code restent prioritaires.

Le catalogue et la couverture des prix sont distincts : un article sans fiche configurée reste utilisable dans une liste. Le minimum automatique exige des offres comparables chez tous les fournisseurs actifs ; une offre disponible seule peut être sélectionnée manuellement.

Les relevés peuvent être réutilisés pendant cinq minutes. Une nouvelle comparaison rétablit les choix automatiques. Les remises par quantité ne sont pas calculées.

- **Peignes** : 405000 correspond à 2 rangées, malgré certains anciens libellés. Pour 3 rangées avec entraxe de 125 mm, sélectionner **405001**.
- **Embouts IKE824302** : fiche identifiée, mais lot de cinq exclu du calcul unitaire tant que l’unité de la liste n’est pas définie.
- **Câble RV2-3G6mm2** : fabricant et unité de vente à préciser avant comparaison.

Les anciennes listes IKE portant la marque « À confirmer » restent compatibles. Voir le [diagnostic des références](docs/releve-2026-11-13.md).

Les prix dépendent des sites fournisseurs. Les frais de livraison ne sont pas ajoutés au total. **YESSS Électrique** est proposé désactivé, sans connecteur ; **Leroy Merlin** n’est pas intégré. Ajouter un fournisseur ne crée pas de connecteur.

Le calcul électrique reconnaît les disjoncteurs Legrand phase + neutre ou bipolaires d’après leur désignation (calibre et courbe), y compris ceux ajoutés par la recherche du catalogue ; les disjoncteurs différentiels, de branchement et triphasés sont écartés avec leur motif. Il vérifie des critères renseignés et **ne valide pas la conformité globale de l’installation**. Voir le [périmètre détaillé et les sources](docs/calcul-electrique.md).

## Tests et documentation

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Les tests utilisent des bases temporaires.

- [Historique des versions](CHANGELOG.md)
- [Étude des fournisseurs](docs/faisabilite.md)
- [Vérifications YESSS](docs/yesss.md) et [Leroy Merlin](docs/leroy-merlin.md)
- [Origine des références](docs/import-braise-samia.md)
