# Historique

## 0.4.1 — 2026-11-13

- Configure les fiches unitaires Legrand 406771 (2A), 406773 (10A), 406775 (20A) et 406777 (32A) chez 123 Elec et Elec Distrib, portant la couverture à huit références par fournisseur.
- Conserve les contrôles de référence, EAN, prix TTC et conditionnement ; teste le rejet des lots pour ces quatre références.
- Actualise la liste des références prises en charge dans Paramètres et le README.
- Vérifie les cinq disjoncteurs 2A, 10A, 16A, 20A et 32A en conditions réelles : dix offres récupérées auprès des deux fournisseurs lors du contrôle du 13 novembre 2026. Les 64 tests automatisés passent.

## 0.4.0 — 2026-11-13

- Regroupe Apparence, Lieux, Fournisseurs, Offres et historique et Listes dans Paramètres.
- Ajoute les 16 thèmes Garage avec application immédiate et deux options désactivées par défaut : persistance du thème et choix aléatoire au lancement. Le mode aléatoire est prioritaire si les deux sont activés.
- Permet d’enregistrer et de charger les références, quantités et lieux dans un fichier JSON. Vérifie le fichier avant chargement et confirme le remplacement d’une liste existante.
- Ouvre une liste vide à chaque démarrage, tout en conservant catalogue, fournisseurs, lieux, paramètres et historique. Les listes doivent être enregistrées dans un fichier pour être réutilisées.
- Propose l’enregistrement à la fermeture d’une liste non vide ; demande confirmation en cas de refus et garde l’application ouverte si l’enregistrement est annulé ou échoue.
- Affiche le logo rond en 96 px au-dessus des onglets centrés et l’utilise comme icône de l’application.
- Affiche la version du projet dans le titre « KlmElec v0.4.0 ».
- Déplace l’aide dans l’onglet « ? » à droite et la structure en six rubriques défilables.
- Ajoute les tests des thèmes, de la navigation, des fichiers de listes et de la fermeture ; actualise le README.

## 0.3.1 — 2026-11-13

- Corrige l’association Elec Distrib de la référence 406774 : utilise la fiche unitaire au lieu du lot de dix.
- Maintient les contrôles de conditionnement et la protection contre la confusion unité/lot.

## 0.3.0 — 2026-11-13

- Affiche une colonne de prix TTC par fournisseur actif et encadre les minima confirmés en rouge, égalités comprises.
- Regroupe automatiquement les ajouts d'une même référence et permet de déplier ses exemplaires.
- Permet d'affecter un lieu à tous les exemplaires ou individuellement par ComboBox.
- Ajoute dix lieux initiaux et la création de lieux dans Paramètres.
- Conserve les affectations lors des ajouts ; retire les derniers exemplaires lors d'une diminution de quantité.
- Préserve les listes, fournisseurs et relevés existants avec une extension additive de la base.
- Garde le tableau Matériel affiché après la comparaison ; les détails restent dans Offres et historique.

## 0.2.2 — 2026-11-13

- Configure la référence Legrand 411633 chez 123 Elec et Elec Distrib.
- Affiche le nombre réel de références configurées par connecteur.

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
