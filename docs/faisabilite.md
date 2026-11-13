# Faisabilité — 13 novembre 2026

## Conclusion

La récupération ponctuelle des prix par HTTP est démontrée sur six fiches
et trois références Legrand. Toutes ont répondu HTTP 200, avec un objet JSON-LD
Product contenant marque, SKU, EAN, prix EUR et disponibilité. Aucun navigateur
automatisé ni connexion à un compte n'a été nécessaire.

Cela ne valide pas encore un connecteur fiable pour tout le catalogue, la recherche
automatique des URL, ni l'autorisation d'une collecte régulière.
Aucune API publique de prix documentée n'a été identifiée dans les recherches
ciblées effectuées : ce n'est pas une preuve de son absence.

## Tableur source

Fichier étudié : `Elec Lille.ods`, sans modification.
Trois feuilles : Feuille1 contient 18 articles ; Feuille2 et Feuille3 sont vides.
Date indiquée dans le document : 10/12/2025, à conserver comme date déclarative,
non comme date de vérification individuelle des prix.

Colonnes A à K : Désignation, Cave, Cuisine, SDB, Étages, Total (quantité),
Référence, Modèle, Prix, Total (montant), fournisseur.
Trois fournisseurs sont présents : 123 Elec, Elec-distrib, Brico Depot.
Aucun hyperlien produit n'est enregistré. Brico Depot reste hors du périmètre
initial des deux connecteurs.

Prévoir la séparation de `Legr 406774` en marque Legrand et référence 406774.
Ne pas supprimer aveuglément les préfixes IKE ou WAG : confirmer la référence
fabricant sur la fiche. Conserver les références comme chaînes et les unités
(le câble est exprimé au mètre). Une ligne a une quantité nulle.

Anomalie : le total affiché 250,90 € additionne une sélection de cellules de la
colonne I (prix unitaires) au lieu de la colonne J (montants). La somme des
18 montants mémorisés dans J est 486,12 €. Ce montant est historique, pas un devis
aux prix actuels. La formule du peigne 13u contient également un double signe
égal (`of:==[.F9]*[.I9]`) : recalculer les montants à l'import plutôt que reprendre
les formules. Le tableur n'a pas été corrigé.

## Échantillon HTTP

Relevé le 13/11/2026 vers 07:34, heure de Paris. Prix des données structurées,
TTC selon l'affichage Elec Distrib et les CGV de 123elec ; hors livraison et
éventuels suppléments. Les six offres indiquaient InStock au moment du test.

| Référence Legrand | 123elec | Elec Distrib | Observation |
| --- | ---: | ---: | --- |
| 406774 | 7,50 € unité | 67,50 € lot de 10 | Ne pas comparer directement |
| 411617 | 45,95 € unité | 36,50 € unité | Écart observé : 9,45 € |
| 411638 | 45,30 € unité | 41,59 € unité | Écart observé : 3,71 € |

Les URL exactes sont dans `experiments/inspect_pages.py` et les observations
horodatées dans `local-study/results.json` (non versionnées).
Les EAN et marques coïncident entre fournisseurs pour les trois références.
Cependant, le lot de dix utilise le même EAN que l'article unitaire : l'EAN seul
ne valide donc pas le conditionnement. Pour les 13 disjoncteurs du tableur,
acheter deux lots signifierait 20 pièces et 135 €, et non 13 × 6,75 €.
Aucun fournisseur gagnant global n'est déclaré par cette étude.

## Accès et identité du fournisseur

Le domaine identifié est https://www.elecdistrib.fr/, dont les mentions légales
nomment Elecdistrib. Sa correspondance avec le fournisseur historique du tableur
a été confirmée par l'utilisateur, ainsi que 123 Elec.

Les fichiers robots.txt ont été lus directement :
- https://www.123elec.com/robots.txt exclut notamment `/catalogsearch/`.
- https://www.elecdistrib.fr/robots.txt exclut notamment les recherches internes.

Ne pas automatiser ces recherches. Commencer avec des associations produit/URL
validées manuellement ; étudier un flux fournisseur ou sitemap autorisé ensuite.
L'accès aux fiches publiques testées n'était pas exclu par ces règles.
Cela ne constitue pas une autorisation générale de réutilisation.

Sources consultées :
- https://www.123elec.com/cgv : prix TTC et frais supplémentaires éventuels,
  dont éco-participation ; vérifier ces suppléments avant de déclarer des offres comparables.
- https://www.123elec.com/mentions_legales_123elec : consultation via l'outil web
  refusée (403), sans tentative de contournement ; examen incomplet.
- https://www.elecdistrib.fr/content/3-conditions-generales-de-vente
- https://www.elecdistrib.fr/content/2-mentions-legales : restrictions générales
  de reproduction et d'exploitation ; conditions d'une collecte régulière à
  clarifier avec le fournisseur avant activation durable. Aucun message envoyé.

## Mise en œuvre proposée pour la prochaine étape

HTTP simple et extraction du JSON-LD Product, avec contrôle du contenu HTML si
nécessaire. Ne jamais lire le premier prix global de la page : les fiches
contiennent aussi des accessoires et recommandations.

Valider marque, référence exacte, unité/lot, monnaie, taxes et suppléments.
Exclure les lots de la comparaison initiale tant que leur coût pour la quantité
commandée n'est pas géré. Utiliser Decimal depuis la chaîne source pour les
calculs ; la sonde actuelle ne fait aucun calcul monétaire et son décodage JSON
n'est pas une implémentation du modèle monétaire définitif.

Conserver le TTC source ; calculer le HT avec le taux configuré seulement si
nécessaire, en indiquant qu'il est calculé. Ne pas faire d'aller-retour HT arrondi
vers TTC. Conserver date, URL, statut et prix historiques séparés des prix actuels.

Prévoir cache, limitation des requêtes, arrêt sur 403/429, erreurs explicites,
validation manuelle des correspondances ambiguës, tests HTTP simulés et travail
réseau hors du fil graphique. Tester ensuite produits absents, rupture, lots,
prix manquants, changement de structure, TVA et éco-participation.

## Validation réalisée et limites

- Six requêtes HTTP réelles : six réussites, six objets Product exploitables.
- Confrontation manuelle des SKU, marques, EAN et titres sur l'échantillon.
- Inspection des cellules et formules ODS sans modification du fichier.
- Sonde limitée à une visite par fiche ; aucune preuve de stabilité dans le temps.
- Pas encore de tests de connecteur, d'interface, de catalogue complet ni d'import.
- Pas d'installation de dépendances, de commit ou de push.
