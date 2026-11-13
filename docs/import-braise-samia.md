# Enrichissement du catalogue — 13 novembre 2026

Les trois documents ont été lus comme données de référence, sans modification.
Seule Feuille1 contient des données ; Feuille2 et Feuille3 sont vides dans chacun.
Aucun prix ni quantité historique n'est ajouté à la liste de travail.

## Neuf ajouts

| Référence conservée | Marque | Désignation | Source / ligne |
| --- | --- | --- | --- |
| 406777 | Legrand | Disjoncteur 32A | Commande Braise/Musse, 9 et 24 ; Samia, 23 |
| 411611 | Legrand | Interrupteur différentiel 40A | Commande Braise/Musse, 11 et 25 |
| PHN820961 | À confirmer | Tableau électrique 1 rangée | Commande Braise/Musse, 13 et 27 |
| 080251 | Legrand | Batibox | Samia, 7 |
| 278111 | Legrand | Prise murale Mosaic | Samia, 8 |
| 278011L | Legrand | Interrupteur 2 positions Mosaic | Samia, 9 |
| PHN847140 | À confirmer | Douille E27 | Samia, 10 |
| 078802 | Legrand | Enjoliveur Mosaic | Samia, 11 |
| cap036819 | À confirmer | Boîtier encastrable placo | Samia, 12 |

Sources : `230418 - Commande 123elec Braise Musse.ods` et `Elec Samia.ods`.
Les valeurs des références restent des chaînes : zéros initiaux, suffixe L et
préfixes PHN/cap conservés. La mention « 123 Elec » est un fournisseur, pas une
preuve de marque fabricant. Les marques manquantes restent donc à confirmer.

La référence 411611 est confirmée comme Legrand par la
[fiche fabricant](https://www.legrand.fr/pro/catalogue/interrupteur-differentiel-dx3-id-arrivee-haute-et-depart-haut-a-vis-2p-230v-40a-typeac-30ma-2-modules).
La mention « courbe C–6KA » du tableur n'est pas reprise dans sa désignation.
Les autres caractéristiques ne sont pas enrichies par supposition.

## Doublons et éléments à confirmer

Les répétitions entre les commandes Braise et Musse et entre Samia et le catalogue
Lille ne créent pas de nouveaux articles. Les articles dont la quantité vaut zéro
restent des références valables pour le catalogue.

Les embouts `824302` (modèle « Ike », lignes 14/28 de Braise/Musse) pourraient
correspondre à `IKE824302`, déjà présent. Aucun second article n'est ajouté pour
cette correspondance probable, qui reste à confirmer, notamment parce que Braise
mentionne « 5embouts ». La marque et le conditionnement ne sont pas modifiés.

La désignation Armoire 3R / IKE821023 de Samia a un modèle « 2x13 » contradictoire.
L'article existant est conservé sans correction automatique.

## Lignes sans référence

`Achat Elec Braise .ods` ne comporte aucune colonne de référence ni marque :

| Ligne | Désignation |
| --- | --- |
| 6 | Disjoncteur 16A |
| 7 | Disjoncteur 10A |
| 8 | Disjoncteur 40A |
| 9 | Prise IP66 |
| 10 | Inter Horaire C-E |

Aucune correspondance n'est déduite des désignations ou des prix seuls.
Dans Samia, les câbles `3G1.5mm²` et `3G2.5mm²` (lignes 30/31) n'ont pas non plus
de référence fabricant ; ils ne sont pas ajoutés comme références identifiées.

## Base existante et compatibilité

Le catalogue fourni passe de 18 à 27 articles. Au prochain démarrage, un ajout
transactionnel, marqué dans `settings`, insère les références manquantes sans
écraser celles déjà présentes pour le couple marque/référence. Les identifiants,
noms personnalisés, quantités, fournisseurs et relevés existants restent inchangés.
Le marqueur est enregistré dans la même transaction : une interruption peut être
rejouée sans doublons. Les démarrages suivants ne répètent pas cet enrichissement.

Aucun changement de schéma : l'ancienne application peut toujours lire la base
enrichie. Revenir au code précédent laisse les articles supplémentaires en place ;
un retour exact du contenu demanderait une restauration de sauvegarde, pas une
suppression automatique. Les tableurs source restent intacts.

L'ajout au catalogue ne configure aucune nouvelle URL de comparaison. Le périmètre
réseau reste limité aux trois références déjà prises en charge.
