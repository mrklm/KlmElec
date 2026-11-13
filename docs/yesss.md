# YESSS Électrique : accès aux prix

Vérification du 13 novembre 2026.

- `https://www.yesss-fr.com/robots.txt` répond HTTP 200 et autorise la fiche testée.
- La [fiche Legrand 406774](https://www.yesss-fr.com/fiche/legrand-406774-disjoncteur-phase-neutre-dnx-4500-6ka-arrivee-et-sortie-borne-a-vis-1p-n-230v--16a-courbe-c-1-module) répond HTTP 200 et confirme la référence.
- La réponse publique testée ne contient aucun bloc JSON-LD, aucune balise de prix recherchée (`itemprop="price"` ou `product:price:amount`) et aucun symbole euro dans le texte visible.
- La [page de connexion](https://www.yesss-fr.com/connexion) présente la consultation et le téléchargement des tarifs dans YESSS PRO. L’espace personnalisé permet les demandes de prix auprès d’une agence.
- Le [panier public](https://www.yesss-fr.com/panier) décrit un parcours de demande de prix, puis de conversion du devis en commande.

Un connecteur de prix publics n’est pas implémenté : la fiche testée ne fournit pas de prix vérifiable. YESSS reste proposé comme fournisseur potentiel sans connecteur.

Pour poursuivre, il faut examiner un export de tarifs/devis ou les possibilités d’accès autorisé de YESSS PRO. Le format des données, les références, les prix HT/TTC, les conditionnements et la disponibilité restent à vérifier avant toute intégration. Aucun accès authentifié n’a été testé.
