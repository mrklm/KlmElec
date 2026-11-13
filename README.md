# KlmElec

Application de bureau Python/PySide6 pour préparer et comparer une liste de matériel électrique.
Version actuelle : **0.4.1**, définie dans `VERSION` et affichée dans la barre de titre.

## Installation et lancement

Python **3.11 ou supérieur**.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m klmelec
```

Pour les lancements suivants : `.venv/bin/python -m klmelec`.

## Utilisation

- **Matériel** : recherche par mots, marque ou référence dans un catalogue de 27 articles ; quantités modifiables, regroupement par référence et affectation des lieux par exemplaire.
- **Comparer les prix** : prix unitaires TTC par fournisseur actif, minimum confirmé encadré en rouge, TVA configurable pour le calcul du HT. Les montants sont hors livraison.
- **Paramètres** : sections Apparence, Lieux, Fournisseurs, Offres et historique et Listes.
- **Apparence** : 16 thèmes ; options de persistance et de sélection aléatoire au lancement, décochées par défaut. Le mode aléatoire est prioritaire si les deux sont activés.
- **?** : aide détaillée sur les fonctions de l’application.

## Listes et données

**Chaque lancement ouvre une liste vide**, y compris après une mise à jour depuis une ancienne version.
Enregistrez la liste dans un fichier pour la conserver.

Dans **Paramètres → Listes**, les boutons d’enregistrement et de chargement utilisent des fichiers JSON contenant les références, quantités et lieux. Le chargement valide le fichier et demande confirmation avant de remplacer une liste non vide. Les références doivent exister dans le catalogue.

À la fermeture, une liste non vide déclenche une proposition d’enregistrement. Un refus demande confirmation ; annuler l’enregistrement ou rencontrer une erreur laisse l’application ouverte.

Le catalogue, les fournisseurs, les lieux, les préférences et les relevés restent dans une base SQLite locale. Son emplacement est indiqué au bas de la fenêtre au lancement.

## Comparaison : périmètre actuel

123 Elec et Elec Distrib prennent en charge **huit références Legrand chacun** :

- Disjoncteurs : **406771** (2A), **406773** (10A), **406774** (16A), **406775** (20A), **406777** (32A).
- Interrupteurs différentiels : **411617, 411633, 411638**.

Ajouter un fournisseur ne crée pas de connecteur ; les autres références peuvent afficher « URL non configurée ».

Le minimum exige des offres unitaires disponibles et comparables chez tous les fournisseurs actifs. Les lots sont exclus. Un relevé récent peut être réutilisé pendant cinq minutes, sauf actualisation forcée. L’historique conserve les relevés sans garantir leurs prix actuels. La récupération dépend de la disponibilité et de la structure des sites.

## Vérification et documentation

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Les tests utilisent des bases temporaires.

- [Historique des versions](CHANGELOG.md)
- [Étude des fournisseurs](docs/faisabilite.md)
- [Origine des références ajoutées](docs/import-braise-samia.md)
