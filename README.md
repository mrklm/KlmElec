# KlmElec

Application de bureau Python/PySide6 pour préparer et comparer une liste de matériel électrique.
Version **0.6.0**, centralisée dans `VERSION` et affichée dans la barre de titre.

## Installation

Python **3.11 ou supérieur**.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m klmelec
```

Lancements suivants : `.venv/bin/python -m klmelec`.

## Fonctions

- Catalogue de 27 articles, recherche par mots, marque ou référence ; quantités et lieux par exemplaire.
- Colonnes compactes, déplaçables et redimensionnables ; colonne HT optionnelle.
- Prix unitaires TTC par fournisseur. Minimum confirmé retenu par défaut ; un clic permet de choisir une autre offre valide, même plus chère.
- Total selon les offres retenues et les quantités, hors livraison ; affichage « Incomplet » si une offre manque. Les égalités ne sont comptées qu’une fois.
- TVA réglable : HT = TTC ÷ (1 + TVA / 100), multiplication par la quantité puis arrondi au centime.
- Comparaison périodique réglable de 1 à 1 440 minutes, désactivée par défaut. Chaque nouvelle comparaison rétablit les choix automatiques.
- Seuils de livraison offerte saisis manuellement par fournisseur, en HT ou TTC, avec conditions. Ils ne modifient pas le total matériel.
- 16 thèmes, préférences mémorisées et aide dans l’onglet **?**.

## Enregistrer et charger

**Chaque démarrage ouvre une liste vide.** Enregistrez vos listes en JSON pour les conserver : références, quantités et lieux, sans les choix de fournisseurs.

La disquette ouvre **Paramètres → Listes** : boutons Enregistrer/Charger et fichiers du dossier chargeables au clic. Le dernier dossier utilisé est mémorisé. Le chargement valide le fichier, confirme le remplacement d’une liste non vide et lance la comparaison si un fournisseur est actif.

À la fermeture, l’application propose d’enregistrer une liste non vide et demande confirmation avant abandon. Annuler l’enregistrement ou rencontrer une erreur laisse la fenêtre ouverte.

Catalogue, fournisseurs, lieux, préférences et historique restent dans une base SQLite locale, dont le chemin est indiqué au bas de la fenêtre au lancement.

## Fournisseurs et limites

**123 Elec et Elec Distrib** : huit références Legrand prises en charge chacun :

- Disjoncteurs : **406771, 406773, 406774, 406775, 406777**.
- Interrupteurs différentiels : **411617, 411633, 411638**.

Le minimum automatique exige des offres unitaires disponibles et comparables chez tous les fournisseurs actifs. Les lots sont exclus. Les relevés de moins de cinq minutes peuvent être réutilisés, sauf actualisation forcée ou périodique. La récupération dépend des sites fournisseurs.

**YESSS Électrique** est proposé désactivé, sans connecteur : aucun prix public sur la fiche testée. **Leroy Merlin** n’est pas intégré : refus HTTP 403 lors du test et présence de vendeurs partenaires. Ajouter un fournisseur ne crée pas de connecteur.

## Tests et documentation

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Les tests utilisent des bases temporaires.

- [Changelog](CHANGELOG.md)
- [Étude des fournisseurs](docs/faisabilite.md)
- [Vérification YESSS](docs/yesss.md) et [Leroy Merlin](docs/leroy-merlin.md)
- [Origine des références](docs/import-braise-samia.md)
