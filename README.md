# KLM Elec

Application de bureau Python envisagée pour préparer des listes de matériel électrique et comparer les mêmes références fabricant chez plusieurs fournisseurs.

État : étude de faisabilité ; aucune interface ni aucun connecteur de production.

Consultez [le rapport de faisabilité](docs/faisabilite.md).

## Environnement

Python 3.11 minimum envisagé ; étude exécutée sur macOS avec Python 3.14.5.
La compatibilité PySide6 reste à vérifier lors de l'étape interface.

```sh
python3 -m venv .venv
source .venv/bin/activate
```

La sonde `experiments/inspect_pages.py` utilise uniquement la bibliothèque standard.
Elle effectue six lectures HTTP espacées de deux secondes, avec un délai de 20 secondes
par requête, et enregistre ses observations dans `local-study/` (exclu de Git).
Elle ne constitue pas un comparateur et ne valide pas automatiquement les références,
la TVA, les conditionnements ni les conditions d'accès. Réexaminer les règles des sites
avant tout nouveau lancement ; aucune exécution réseau n'est nécessaire pour lire le rapport.

## Versionnement

Version de l'étude : voir `VERSION`.
Commits en français avec préfixes `docs:`, `feat:`, `fix:`, `test:`, `chore:`.
Aucun commit ni push automatique.
