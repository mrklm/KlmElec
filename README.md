# KlmElec — v1.0.0

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
La version est centralisée dans `VERSION`, utilisée par le paquet Python et le titre de fenêtre.

## Fonctions

- **Matériel** : catalogue de 27 articles, recherche par désignation ou référence, quantités et lieux par exemplaire.
- **Prix** : comparaison TTC, choix manuel du fournisseur par article et total selon les quantités, hors livraison. Les comparaisons peuvent être périodiques.
- **Calcul électrique** : rangées d’un logement monophasé, affectation des circuits, usages et caractéristiques des différentiels. Vérifications amont/aval, calibre, nombre de circuits, type et sensibilité ; données manquantes signalées.
- **Paramètres** : fournisseurs, historique, seuils de livraison offerte saisis manuellement, TVA, colonne HT optionnelle et 16 thèmes.
- **Listes** : enregistrement JSON et accès aux fichiers depuis le raccourci disquette.

## Conserver ses listes

**L’application démarre avec une liste vide.** Les fichiers JSON conservent les références, quantités, lieux et rangées électriques, sans les choix d’offres fournisseurs. Les anciennes listes restent chargeables.

Charger une liste remplace la liste actuelle après confirmation si elle n’est pas vide, puis lance la comparaison si un fournisseur est actif. À la fermeture, l’application propose d’enregistrer une liste non vide et demande confirmation avant abandon.

Catalogue, fournisseurs, lieux, préférences et historique sont conservés dans une base SQLite locale. Son chemin est indiqué au lancement dans la barre d’état.

## Périmètre et limites

**123 Elec et Elec Distrib** disposent de connecteurs pour huit références Legrand : **406771, 406773, 406774, 406775, 406777, 411617, 411633, 411638**. Le minimum automatique exige des offres unitaires disponibles et comparables chez tous les fournisseurs actifs. Les relevés récents peuvent être réutilisés pendant cinq minutes ; une nouvelle comparaison rétablit les choix automatiques.

Les prix dépendent des sites fournisseurs. Les frais de livraison ne sont pas ajoutés au total. **YESSS Électrique** est proposé désactivé, sans connecteur ; **Leroy Merlin** n’est pas intégré. Ajouter un fournisseur ne crée pas de connecteur.

Le calcul électrique reconnaît les cinq références de disjoncteurs ci-dessus. Il vérifie des critères renseignés et **ne valide pas la conformité globale de l’installation**. Voir le [périmètre détaillé et les sources](docs/calcul-electrique.md).

## Tests et documentation

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Les tests utilisent des bases temporaires.

- [Historique des versions](CHANGELOG.md)
- [Étude des fournisseurs](docs/faisabilite.md)
- [Vérifications YESSS](docs/yesss.md) et [Leroy Merlin](docs/leroy-merlin.md)
- [Origine des références](docs/import-braise-samia.md)
