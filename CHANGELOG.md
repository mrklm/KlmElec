# Historique

## 1.39.0 — 2026-11-15

- Page principale : cartes Livraison et Total réduites d’un tiers en hauteur.
- Carte Livraison sans liste déroulante : une ligne par fournisseur (123 Elec en haut, Elec Distrib en bas), « livraison gratuite » en vert ou « livraison gratuite dans XX,XX € » d’après les offres retenues et le seuil HT ou TTC saisi ; un fournisseur sans article retenu n’est pas affiché.
- Paramètres → Livraison : case « Afficher les infos de livraison sur la page principale », cochée par défaut et mémorisée. Valide ces changements avec 217 tests automatisés.

## 1.38.0 — 2026-11-15

- Nouvel onglet « Norme » : liste de PDF choisis sur le disque (norme NF C 15-100, guides), lecture intégrée avec pages, zoom, recherche surlignée et sommaire ; document et page retrouvés au lancement suivant. Aucun PDF n’est fourni ni copié : seuls les chemins sont enregistrés dans la base locale.
- PDF protégé ou illisible : message explicite et bouton « Ouvrir avec le lecteur du système ». Valide ces changements avec 217 tests automatisés.

## 1.37.0 — 2026-11-15

- Nouvel onglet « Théorie » : règles amont / aval et sélectivité, principe des disjoncteurs, courbes de déclenchement, différentiels et leurs types, sectionneurs et interrupteurs, calculs de base (intensité, section, chute de tension) et foisonnement, avec sommaire cliquable et exemples chiffrés. Valide ces changements avec 216 tests automatisés.

## 1.36.0 — 2026-11-15

- Menu « Familles » : niveau marque pour toutes les familles (domaine → type de produit → marque), même quand une seule marque est proposée ; Appareillage → Legrand → gamme, Domotique → Yokis. Valide ces changements avec 215 tests automatisés.

## 1.35.0 — 2026-11-15

- Menu « Familles » : les disjoncteurs et les interrupteurs différentiels sont regroupés par type puis par marque (Protection → Disjoncteurs → Legrand / Schneider / Hager), au lieu d’une entrée par marque. Valide ces changements avec 215 tests automatisés.

## 1.34.0 — 2026-11-15

- Paramètres → Catalogue : bouton « Exporter les références… » qui enregistre en JSON les fiches découvertes (fournisseur, référence, marque, désignation, adresse, SKU, EAN, date).
- L’aide n’est plus un onglet : le bouton « ? », de la taille de la disquette, l’ouvre dans une fenêtre séparée depuis le coin supérieur droit ; la disquette passe à gauche. Valide ces changements avec 215 tests automatisés.

## 1.33.0 — 2026-11-15

- Paramètres → Catalogue : option « Toutes les familles » qui enchaîne la recherche de chaque famille (une heure environ). Chaque famille terminée est enregistrée aussitôt ; le rapport résume les ajouts par famille. Annuler conserve les familles déjà parcourues, et un refus d’accès (403/429) arrête l’enchaînement.
- La liste s’ouvre toujours sur la première famille, pour éviter un lancement par mégarde. Valide ces changements avec 214 tests automatisés.

## 1.32.0 — 2026-11-15

- Ajoute à Paramètres → Catalogue les disjoncteurs et interrupteurs différentiels Schneider Electric (Acti9, Resi9) et Hager ; tableaux pré-équipés, combinés (télérupteur, contacteur, prises), blocs Vigi et lots promotionnels sont écartés.
- Reconnaît une marque à son premier mot (« Schneider Electric » chez Elec Distrib, « SCHNEIDER » chez 123 Elec), à la recherche comme au relevé des prix.
- Lit chez Elec Distrib les références alphanumériques (Schneider A9F77210, Hager MFN702), en plus des références Legrand à 6 chiffres.
- Menu « Familles » : mêmes niveaux que Legrand (sous-famille ou type, calibre, variantes) ; lit les types Asi / Fsi (mention SI), « 30mA A » sans le mot « type », le 3P+N, les raccordements SanVis et embrochables, et les gammes Resi9 XP / XE, iC60, iC40, iDT40, iDD40 ; la gamme s’affiche aussi pour les différentiels.
- Vérifié en conditions réelles le 15/11/2026 : 233 références validées (168 disjoncteurs et 44 différentiels Schneider, 13 disjoncteurs et 8 différentiels Hager), dont 70 chez les deux fournisseurs. Deux fiches Elec Distrib (R9EFD620, R9PFC632) sont écartées car leur EAN diffère de celui de 123 Elec. Valide ces changements avec 213 tests automatisés.

## 1.31.0 — 2026-11-15

- Ajoute la famille « Boîtes Legrand » à Paramètres → Catalogue : Batibox, Ecobatibox, boîtes de dérivation, DCL, combles, supports et couvercles ; Plexo, la boîte Oteo en saillie et les lots de vis sont écartés.
- Ajoute la famille « Bornes Wago » (123 Elec seulement) : bornes de passage TopJob S, plaques d’extrémité, barres de pontage, adaptateurs rail DIN, bornes KNX ; les bornes vendues en pot, flacon, blister, sachet ou panaché sont écartées, comme toute la gamme Elec Distrib (conditionnements de 25 à 100).
- Ajoute le domaine « Boîtes et connexion » au menu « Familles » ; boîtes classées par type de pose (cloison sèche, à sceller, multimatériaux, étanche à l’air, sol), dérivation, DCL, supports et couvercles.
- Vérifié en conditions réelles le 15/11/2026 : 59 références de boîtes (53 chez 123 Elec, 15 chez Elec Distrib, dont 9 chez les deux) et 18 références Wago validées. Les Ecobatibox à suffixe L de 123 Elec sont écartées par prudence (autre conditionnement). Valide ces changements avec 209 tests automatisés.

## 1.30.1 — 2026-11-14

- Met à jour le README : numéro de version du titre (resté à 1.3.0), domaines du menu « Familles », recherche Yokis limitée à 123 Elec et rejet des fiches à EAN différent.

## 1.30.0 — 2026-11-14

- Ajoute la famille « Éclairage de sécurité Legrand (BAES Sati) » à Paramètres → Catalogue : BAES d’évacuation et d’ambiance, BAES+BAEH, télécommande ; les plaques Céliane « satiné » sont écartées.
- Ajoute le domaine « Sécurité » au menu « Familles ».
- Vérifié en conditions réelles le 14/11/2026 : 7 références validées (3 chez 123 Elec, 5 chez Elec Distrib, 062525 chez les deux). La fiche Elec Distrib du 062565 est écartée car son EAN diffère de celui de 123 Elec. Valide ces changements avec 206 tests automatisés.

## 1.29.0 — 2026-11-14

- Ajoute la famille « Compteurs d’énergie Legrand » (EMDX³ et Écocompteur) à Paramètres → Catalogue ; les platines Drivia « pour compteur » sont écartées.
- Ajoute le domaine « Mesure » au menu « Familles ».
- Vérifié en conditions réelles le 14/11/2026 : 5 références validées (4 EMDX³ chez 123 Elec, Écocompteur 412000 chez Elec Distrib). Valide ces changements avec 205 tests automatisés.

## 1.28.0 — 2026-11-14

- Ajoute la domotique Yokis à Paramètres → Catalogue (micro-modules filaires, Power radio et UP Zigbee : télérupteurs, minuteries, télévariateurs, volets roulants, émetteurs, télécommandes, kits, passerelle).
- Recherche limitée à 123 Elec : Elec Distrib ne vend que 3 articles Yokis, sans marque dans les données produit et sous une autre référence.
- Ajoute le domaine « Domotique » au menu « Familles », découpé par fonction.
- Vérifié en conditions réelles le 14/11/2026 : 49 références validées (prix, quantité minimale, disponibilité), aucune rejetée. Valide ces changements avec 204 tests automatisés.

## 1.27.0 — 2026-11-14

- Ajoute l’appareillage saillie Legrand (Oteo, cadres pour moulures DLP) à Paramètres → Catalogue ; les articles saillie des gammes Dooxie, Mosaic, Céliane, Plexo et Niloé restent dans leur gamme, les prises Green’up et les articles étanches sont écartés.
- Ajoute la rubrique « Cadres saillie » au menu « Familles », classée par nombre de postes, dans toutes les gammes.
- Corrige le classement du cadre Mosaic « 1,5 postes ou 3 modules », qui était rangé dans « 5 postes ».
- Relevé du 14/11/2026 : 38 références (123 Elec et Elec Distrib, catégorie « Appareillage saillie Legrand ») ; les lots assemblés par le revendeur, sans référence Legrand, sont écartés. Valide ces changements avec 202 tests automatisés.

## 1.26.0 — 2026-11-14

- Ajoute la gamme Niloé Legrand à Paramètres → Catalogue et au menu « Familles » (domaine « Appareillage »).
- Relevé du 14/11/2026 : gamme en fin de vie, 2 références seulement chez les deux fournisseurs (cadre saillie double 664799, prise TV/R/SAT 664763). Valide ces changements avec 194 tests automatisés.

## 1.25.0 — 2026-11-14

- Ajoute la gamme Plexo Legrand (étanche) à Paramètres → Catalogue : mécanismes à composer, appareils complets en saillie ou encastrés, supports, boîtes de dérivation et coffrets étanches.
- Ajoute au menu « Familles » les rubriques « Boîtes de dérivation » et « Coffrets étanches », ainsi que la finition « Gris et anthracite ».
- Relevé du 14/11/2026 : 116 références Plexo identifiées sur 123 Elec et Elec Distrib. Valide ces changements avec 193 tests automatisés.

## 1.24.0 — 2026-11-14

- Ajoute l’appareillage à Paramètres → Catalogue : familles Dooxie, Mosaic et Céliane Legrand (mécanismes, enjoliveurs, plaques, complets, supports), y compris les références de la nouvelle gamme Céliane (CB0001, CP0108…).
- Ajoute le domaine « Appareillage » au menu « Familles » : gamme, fonction (prises de courant, USB, RJ45/TV/HP, interrupteurs, poussoirs, variateurs, détecteurs, volets roulants, VMC, thermostats…), puis mécanisme, enjoliveur ou complet.
- Classe les plaques par nombre de postes ou de modules, puis par finition (blanc, noir, métal, bois, verre, couleurs) quand la liste dépasse 20 articles.
- Affiche dans chaque gamme concernée les accessoires communs (supports « pour Mosaic, Céliane ou Soliroc »).
- Écarte les lots assemblés par le revendeur, sans référence Legrand.
- Vérifié en conditions réelles le 14/11/2026 sur 1 000 fiches environ ; recherche Mosaic complète : 97 références (83 fiches 123 Elec, 23 Elec Distrib). Valide ces changements avec 186 tests automatisés.

## 1.23.0 — 2026-11-14

- Détaille les disjoncteurs dans le menu « Familles » : sous-famille (phase + neutre / bipolaires, tétrapolaires / triphasés, différentiels, branchement), puis calibre, puis variantes normalisées (pôles, courbe, pouvoir de coupure, raccordement, gamme DNX³ / DX³).
- Détaille les interrupteurs différentiels : type (AC, A, Hpi, F, B), puis calibre, puis sensibilité, pôles et raccordement.
- Lit ces variantes dans la désignation, sans les deviner ; les références d’origine reprennent les caractéristiques relevées sur les fiches fournisseurs.
- Vérifie que les sous-catégories Elec Distrib (automatiques, à vis) n’apportent pas de fiche supplémentaire. Valide ces changements avec 163 tests automatisés.

## 1.22.0 — 2026-11-14

- Ajoute un bouton « Familles » à gauche de la recherche : il s’ouvre au survol et présente le catalogue par domaine, famille, puis sous-famille et calibre pour les familles de plus de 20 articles ; un clic sur un article l’ajoute à la liste avec la quantité et le lieu choisis.
- Classe les articles du catalogue avec les règles de la recherche automatique ; les autres sont regroupés par marque dans « Autres articles ».
- Abrège les désignations dans le menu (marque et référence répétées retirées), désignation complète en info-bulle.
- Réduit et centre la barre de recherche.
- Reconnaît « inter diff » comme interrupteur différentiel. Valide ces changements avec 162 tests automatisés.

## 1.21.0 — 2026-11-14

- Ajoute la famille « Interrupteurs crépusculaires Legrand » à Paramètres → Catalogue ; les cellules de rechange sont écartées.
- Vérifié en conditions réelles le 14/11/2026 : 2 nouvelles références (2 fiches 123 Elec, 1 Elec Distrib). Valide ces changements avec 159 tests automatisés.

## 1.20.0 — 2026-11-14

- Ajoute la famille « Modules de communication Legrand » (brassage, DTI, filtre, répartiteur TV, DTIO, support box) à Paramètres → Catalogue.
- Permet de déclarer des familles complémentaires : une fiche retenue par l’une est écartée de l’autre (un coffret « avec brassage » reste un coffret).
- Vérifié en conditions réelles le 14/11/2026 : 6 nouvelles références, toutes chez Elec Distrib (123 Elec n’en propose pas). Valide ces changements avec 158 tests automatisés.

## 1.19.0 — 2026-11-14

- Ajoute la famille « Coffrets de communication Legrand » (communication, multimédia, double ou triple play) à Paramètres → Catalogue ; les modules pour coffret (brassage, DTI, filtres, répartiteur TV, DTIO, support box) et les portes sont écartés.
- Vérifié en conditions réelles le 14/11/2026 : 17 nouvelles références (3 fiches 123 Elec, 15 Elec Distrib, 1 refusée faute de disponibilité confirmée). Valide ces changements avec 157 tests automatisés.

## 1.18.0 — 2026-11-14

- Ajoute la famille « Tableaux pré-équipés Legrand » (pré-équipés ou pré-câblés) à Paramètres → Catalogue ; les prises précâblées et les portes de la catégorie sont écartées.
- Vérifié en conditions réelles le 14/11/2026 : 17 nouvelles références (4 fiches 123 Elec, 13 Elec Distrib, aucune en commun). Valide ces changements avec 156 tests automatisés.

## 1.17.0 — 2026-11-14

- Ajoute les familles « Portes Drivia Legrand » (blanches et transparentes) et « Rehausses Drivia Legrand » à Paramètres → Catalogue ; les portes de bacs, de platines et XL³ sont écartées.
- Vérifié en conditions réelles le 14/11/2026 : 16 portes (8 fiches 123 Elec, 14 Elec Distrib, 2 refusées faute de quantité minimale confirmée) et 8 rehausses (123 Elec uniquement). Valide ces changements avec 155 tests automatisés.

## 1.16.0 — 2026-11-14

- Ajoute la famille « Coffrets Drivia Legrand (tableaux nus) » à Paramètres → Catalogue : 13 et 18 modules, 1 à 4 rangées.
- Écarte les portes, rehausses, serrures, platines, habillages, tableaux pré-équipés ou pré-câblés et coffrets de communication, ainsi que les GTL, peignes et borniers de la gamme Drivia.
- Vérifié en conditions réelles le 14/11/2026 : 8 nouvelles références (8 fiches 123 Elec, 7 Elec Distrib), 64 autres fiches Drivia écartées. Valide ces changements avec 153 tests automatisés.

## 1.15.0 — 2026-11-14

- Ajoute la famille « Accessoires GTL Legrand » (embouts, cornets, jonctions sol/plafond), complémentaire de la famille GTL : chaque fiche relève de l’une ou de l’autre.
- Permet d’exiger, en plus du mot-clé, l’un de plusieurs mots dans la désignation d’une famille.
- Vérifié en conditions réelles le 14/11/2026 : 3 nouvelles références (2 fiches 123 Elec, 2 Elec Distrib), les goulottes renvoyées à la famille GTL. Valide ces changements avec 152 tests automatisés.

## 1.14.0 — 2026-11-14

- Ajoute la famille « GTL Legrand (gaines techniques de logement) » à Paramètres → Catalogue : goulottes GTL complètes ; embouts, cornets et jonctions sol/plafond sont écartés.
- Vérifié en conditions réelles le 14/11/2026 : 3 nouvelles références (3 fiches 123 Elec, 2 Elec Distrib), 5 accessoires écartés. Valide ces changements avec 151 tests automatisés.

## 1.13.0 — 2026-11-14

- Ajoute la famille « Borniers de répartition Legrand » (phase, neutre, terre, 3P+N), distincte des répartiteurs ; les supports pour borniers sont écartés.
- Vérifié en conditions réelles le 14/11/2026 : 10 nouvelles références (7 fiches 123 Elec, 5 Elec Distrib), 1 support écarté. Valide ces changements avec 150 tests automatisés.

## 1.12.0 — 2026-11-14

- Ajoute la famille « Répartiteurs Legrand » à Paramètres → Catalogue (catégorie accessoires modulaires chez Elec Distrib, triée par la désignation) ; les borniers de répartition ne sont pas retenus.
- Vérifié en conditions réelles le 14/11/2026 : 11 nouvelles références (2 fiches 123 Elec, 11 Elec Distrib), 66 autres articles de la catégorie écartés. Valide ces changements avec 149 tests automatisés.

## 1.11.0 — 2026-11-14

- Ajoute la famille « Horloges modulaires Legrand » à Paramètres → Catalogue : « interrupteur horaire » ou « horloge » dans la désignation ; minuteries, sonneries, relais et interrupteurs crépusculaires de la catégorie sont écartés.
- Permet plusieurs mots-clés par famille, dans la désignation comme dans l’adresse du plan de site.
- Vérifié en conditions réelles le 14/11/2026 : 10 nouvelles références (6 fiches 123 Elec, 7 Elec Distrib), 5 fiches écartées. Valide ces changements avec 148 tests automatisés.

## 1.10.0 — 2026-11-14

- Ajoute la famille « Interrupteurs-sectionneurs Legrand » à Paramètres → Catalogue (catégorie accessoires modulaires chez Elec Distrib, triée par la désignation).
- Vérifié en conditions réelles le 14/11/2026 : 7 nouvelles références (4 fiches 123 Elec, 6 Elec Distrib), 71 autres articles de la catégorie écartés. Valide ces changements avec 147 tests automatisés.

## 1.9.0 — 2026-11-14

- Ajoute la famille « Parafoudres Legrand » à Paramètres → Catalogue ; les cassettes de rechange sont écartées.
- Vérifié en conditions réelles le 14/11/2026 : 4 nouvelles références (4 fiches 123 Elec, 1 Elec Distrib), 1 fiche écartée. Valide ces changements avec 146 tests automatisés.

## 1.8.0 — 2026-11-14

- Ajoute la famille « Contacteurs Legrand » à Paramètres → Catalogue (plan de site 123 Elec, catégorie Elec Distrib).
- Vérifié en conditions réelles le 14/11/2026 : 13 nouvelles références (12 fiches 123 Elec, 5 Elec Distrib), aucune fiche écartée. Valide ces changements avec 145 tests automatisés.

## 1.7.0 — 2026-11-14

- Ajoute la famille « Peignes d’alimentation Legrand » à Paramètres → Catalogue (catégorie accessoires modulaires chez Elec Distrib, triée par la désignation).
- Écarte les accessoires pour peignes : modules d’alimentation ou de raccordement, isolants, dispositifs de raccordement.
- Vérifié en conditions réelles le 14/11/2026 : 8 nouvelles références (5 fiches 123 Elec, 6 Elec Distrib), 7 accessoires pour peignes et 65 autres articles écartés. Valide ces changements avec 144 tests automatisés.

## 1.6.0 — 2026-11-14

- Ajoute la famille « Télérupteurs Legrand » à Paramètres → Catalogue ; les télévariateurs et relais variateurs de la même catégorie sont écartés.
- Vérifié en conditions réelles le 14/11/2026 : 6 nouvelles références (5 fiches 123 Elec, 4 Elec Distrib), 3 fiches écartées. Valide ces changements avec 143 tests automatisés.

## 1.5.0 — 2026-11-14

- Pré-remplit le différentiel d’une rangée (calibre, type, sensibilité) à partir d’un interrupteur différentiel Legrand monophasé de la liste ; les valeurs restent modifiables.
- Laisse « À préciser » ce que la désignation n’indique pas et le signale ; les quatre références d’origine sont reconnues d’office.
- Vérifié sur les 40 interrupteurs différentiels trouvés le 14/11/2026 : 20 complets, 5 partiels, 15 tétrapolaires écartés. Valide ces changements avec 142 tests automatisés.

## 1.4.0 — 2026-11-14

- Ajoute la famille « Interrupteurs différentiels Legrand » à Paramètres → Catalogue (plan de site 123 Elec, catégorie Elec Distrib), avec les mêmes contrôles que les disjoncteurs.
- Écarte de cette famille les disjoncteurs différentiels, disjoncteurs d’abonné et prises qui citent un différentiel.
- Compare les désignations sans tenir compte des accents.
- Vérifié en conditions réelles le 14/11/2026 : 37 nouvelles références (27 fiches 123 Elec, 28 Elec Distrib), 12 fiches écartées (hors famille ou autre marque). Valide ces changements avec 132 tests automatisés.

## 1.3.0 — 2026-11-14

- Étend le calcul électrique aux disjoncteurs Legrand reconnus d’après leur désignation : phase + neutre ou bipolaires, calibre et courbe lus dans le libellé. Les cinq références d’origine restent reconnues d’office.
- Affiche la courbe dans l’onglet et signale les courbes D ou non indiquées comme à vérifier.
- Indique les disjoncteurs non évalués et leur motif : différentiels, branchement, triphasés, pôles ou calibre non identifiés.
- Écarte de la recherche du catalogue les tableaux pré-câblés, cordons et prises dont la désignation cite des disjoncteurs.
- Vérifié sur les 78 disjoncteurs Legrand du catalogue après recherche : 34 évalués, 44 écartés avec motif. Valide ces changements avec 131 tests automatisés.

## 1.2.0 — 2026-11-14

- Ajoute Paramètres → Catalogue : recherche automatique des disjoncteurs Legrand chez 123 Elec (plan de site) et Elec Distrib (pages de catégorie), robots.txt respecté et une requête par seconde.
- Ouvre et contrôle chaque fiche (marque, référence, EAN, titre, offre TTC) avant de l’ajouter ; écarte les lots, les accessoires et les EAN discordants entre fournisseurs.
- Conserve les fiches trouvées dans la base locale et les utilise pour la comparaison des prix ; les fiches configurées dans le code restent prioritaires et les articles existants ne sont pas modifiés.
- Vérifié en conditions réelles le 14/11/2026 : 80 nouvelles références (48 fiches 123 Elec, 54 Elec Distrib), prix relevés sur un échantillon.
- Accélère les tests en détruisant les fenêtres entre deux tests. Valide ces changements avec 114 tests automatisés.

## 1.1.0 — 2026-11-14

- Rend les cases à cocher visibles dans tous les thèmes : contour et coche à la couleur d’accent du thème.
- Lance automatiquement la comparaison des prix à chaque ajout d’article, si un fournisseur est actif ; les relevés de moins de 5 minutes restent réutilisés.
- Traduit en français les boutons standard (Oui, Non, Annuler…) des boîtes de dialogue, dont la confirmation à la fermeture.
- Valide ces changements avec 109 tests automatisés.

## 1.0.3 — 2026-11-14

- Traite un robots.txt absent (404/410) comme une absence de restriction et ne le redemande plus pour chaque article ; une autre erreur sur ce fichier est signalée comme telle, et non plus comme une fiche produit introuvable.
- Conserve les prix relevés et les choix d’offres lors d’un changement de TVA : seul le HT est recalculé.
- Demande confirmation avant de retirer un fournisseur.
- Valide ces changements avec 106 tests automatisés.

## 1.0.2 — 2026-11-13

- Configure les fiches IKEPE IKE821023 (tableau nu 3 rangées) et IKE821053 (porte blanche) chez 123 Elec. Accepte la marque historique « À confirmer » uniquement pour les références IKE explicitement vérifiées, sans modifier les listes existantes.
- Vérifie leur titre exact, SKU, marque et EAN même lorsque la référence est absente du titre.
- Identifie IKE824302 comme un lot de cinq embouts : conserve la fiche accessible mais exclut son prix de la comparaison unitaire tant que l’unité de la liste n’est pas définie.
- Valide ces changements avec 102 tests automatisés et les fiches publiques 123 Elec.

## 1.0.1 — 2026-11-13

- Ajoute le peigne vertical Legrand 405001 (3 rangées, entraxe 125 mm) au catalogue et aux deux connecteurs. Enrichit les bases existantes sans remplacer les articles ni les quantités des listes.
- Étend la récupération aux peignes Legrand 404926 / 405000 et au télérupteur 412408 chez les deux fournisseurs, ainsi qu’aux quatre références Wago 2106 chez 123 Elec, avec correspondance explicite des références fabricant et fournisseur.
- Corrige les faux rejets d’éco-participation dus aux produits recommandés et aux prix dégressifs de 123 Elec ; conserve les contrôles des taxes du produit et utilise le prix unitaire standard.
- Remplace « URL non configurée » par un message indiquant clairement qu’une référence n’est pas prise en charge chez le fournisseur.
- Documente les références restant non couvertes et le libellé historique « Peigne 3r » associé à la référence 405000 (2 rangées).
- Aligne la version annoncée aux fournisseurs sur la version centralisée de l’application.
- Valide les changements avec 97 tests automatisés ; les nouvelles fiches fournisseurs ont également été vérifiées en ligne.

## 1.0.0 — 2026-11-13

- Ajoute l’onglet Calcul électrique pour préparer les rangées d’un logement monophasé à partir des cinq références de disjoncteurs Legrand reconnues.
- Permet d’affecter chaque exemplaire à une rangée, de préciser son usage et les caractéristiques du différentiel prévu.
- Détaille les critères amont/aval, le calibre à étudier, la limite de huit circuits, la sensibilité et les restrictions de type. Signale les données manquantes et les équipements particuliers sans attester la conformité globale.
- Conserve les rangées et affectations dans les listes JSON ; accepte les anciennes listes et ajuste les affectations lors des suppressions d’exemplaires.
- Passe la version centralisée à 1.0.0 pour le titre de fenêtre et le paquet Python ; actualise le README et documente le périmètre des calculs.
- Valide les changements avec 87 tests automatisés, incluant les calculs, la sauvegarde des rangées et leur interface.

## 0.6.0 — 2026-11-13

- Harmonise les blocs Livraison et Total TTC : hauteur commune, cadres identiques, marges régulières et typographie plus compacte.
- Ajoute YESSS Électrique aux fournisseurs potentiels, désactivé par défaut et sans connecteur de prix ; enrichit les bases existantes sans doublon.
- Ajoute un bloc Livraison avec icône colis et choix du fournisseur près du total TTC.
- Ajoute Paramètres → Livraison pour mémoriser les seuils de gratuité par fournisseur, en HT ou TTC, et leurs conditions. Les montants restent indicatifs et exclus du total matériel.
- Ajoute un raccourci disquette en haut à droite vers Paramètres → Listes, avec deux boutons compacts et une grille de fichiers JSON chargeables au clic.
- Mémorise le dossier des listes, permet de le choisir et actualise la grille à l’ouverture de la section ainsi qu’après un enregistrement ou un chargement.
- Ajoute Affichage et TVA dans Paramètres : visibilité mémorisée de la colonne HT, taux de TVA et formule de calcul explicitée.
- Ajoute Comparaison dans Paramètres : fréquence automatique de 1 à 1 440 minutes, désactivée par défaut, et option d’actualisation forcée mémorisées. Les lancements périodiques renouvellent les prix et rétablissent les choix automatiques.
- Lance automatiquement la comparaison après le chargement réussi d’une liste non vide, si un fournisseur est actif.
- Supprime la surbrillance des lignes au clic, tout en conservant le choix des offres et la suppression de la ligne courante.
- Dimensionne les colonnes selon leur contenu avec des plafonds pour les textes longs ; réduit les marges et conserve les largeurs ajustées manuellement.

- Documente les limites de YESSS (aucun prix public sur la fiche testée) et de Leroy Merlin (refus HTTP 403 et vendeurs partenaires) ; aucun connecteur supplémentaire activé.
- Valide les changements avec 71 tests automatisés.

## 0.5.0 — 2026-11-13

- Aère les cellules du tableau Matériel et rend les colonnes déplaçables et redimensionnables.
- Permet de retenir une offre par clic, même plus chère, avec déplacement du cadre rouge et recalcul des totaux HT/TTC selon les quantités.
- Affiche un total TTC en bas à droite, adapté au thème ; signale les listes incomplètes et évite le double comptage des égalités.
- Retire la mention du cache après les prix ; conserve les informations de date et de statut au survol.
- Rétablit la sélection automatique à chaque nouvelle comparaison ; refuse la sélection d’une offre en erreur ou périmée.
- Met à jour l’aide et vérifie le choix manuel, les quantités, les égalités et le déplacement des colonnes : 66 tests automatisés passent.

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
