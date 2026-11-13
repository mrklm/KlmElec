# Historique

## 0.2.1 — 2026-11-13

- Ajoute neuf références des tableurs Braise/Musse et Samia, portant le catalogue fourni à 27 articles.
- Enrichit automatiquement les bases existantes sans écraser les produits, listes ni historiques.
- Conserve les zéros initiaux, suffixes et références fournisseur non confirmées.
- Documente les lignes sans référence et les correspondances à confirmer ; aucun prix ancien importé.

## 0.2.0 — 2026-11-13

- Active la comparaison en arrière-plan pour trois références Legrand chez 123 Elec et Elec Distrib.
- Vérifie les références, marques, EAN, prix TTC, disponibilités et conditionnements ; exclut les lots.
- Ajoute les offres détaillées, écarts au minimum et totaux HT/TTC en Decimal avec TVA configurable.
- Affiche les échecs sans remplacer les anciens prix par zéro ni valider un minimum incomplet.
- Conserve les relevés immuables et propose les vingt derniers dans l'historique.
- Ajoute un cache explicite de cinq minutes, une actualisation forcée et l'annulation.
- Consulte robots.txt et suspend les appels au site après HTTP 403 ou 429.
- Préserve le catalogue, les fournisseurs et la liste existants ; ajoute une table de relevés.

## 0.1.1 — 2026-11-13

- Ajoute l’icône fournie aux ressources et l’utilise comme icône de l’application Qt.

## 0.1.0 — 2026-11-13

- Ajoute la première interface PySide6 et le catalogue initial de 18 articles.
- Ajoute la recherche par mots, les quantités modifiables et la confirmation des doublons.
- Permet d’ajouter, modifier, désactiver et retirer des fournisseurs.
- Enregistre automatiquement la liste et les fournisseurs dans une base locale.
- Ajoute les tests de recherche, persistance et parcours d’interface.
- Laisse la comparaison désactivée en attendant les connecteurs.

## 0.0.1 — 2026-11-13

- Inspection du tableur source sans modification.
- Étude de six fiches produit publiques sur trois références Legrand.
- Sonde HTTP indépendante et rapport de faisabilité.
- Documentation des conditionnements, restrictions de recherche et limites restantes.
