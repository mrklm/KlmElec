# Leroy Merlin : faisabilité de la comparaison

Vérification du 13 novembre 2026.

La [fiche Legrand 406775](https://www.leroymerlin.fr/produits/dnx3-1p-ng-c20-4500a-6ka-406775-83327853.html) affiche un prix public dans la consultation web. L’offre principale observée est vendue et expédiée par Elec Distrib ; d’autres vendeurs partenaires sont également proposés. Un prix affiché sur ce site n’est donc pas nécessairement une offre vendue par Leroy Merlin.

Test avec `httpx`, sans connexion, avec un User-Agent KlmElec :

- `https://www.leroymerlin.fr/robots.txt` répond HTTP 200 et autorise le chemin de la fiche testée.
- La fiche répond HTTP 403 et demande l’exécution de JavaScript. Le client HTTP actuel ne reçoit pas les données du produit.
- Aucun contournement ni nouvelle tentative sur les fiches après ce refus.

Aucun connecteur ajouté : l’accès direct utilisé par l’application ne fonctionne pas dans ce test. Il faudrait une source de données accessible et autorisée (API, export ou autre accès documenté), puis vérifier référence fabricant, EAN, vendeur, prix TTC, disponibilité et conditionnement. Les offres de vendeurs partenaires doivent rester distinctes des offres de l’enseigne et de celles vendues sur les sites propres des partenaires.

Ce constat porte sur la fiche et le mode d’accès testés ; il ne signifie pas que tous les accès au site sont impossibles.
