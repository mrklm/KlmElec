# Calcul électrique

Cet onglet vérifie des critères pour les interrupteurs différentiels en tête de rangée d’un logement monophasé. Il ne mesure pas la consommation réelle et n’atteste pas la conformité de l’installation.

## Utilisation

1. Ajoutez les disjoncteurs dans Matériel. Les références Legrand reconnues sont 406771 (2 A), 406773 (10 A), 406774 (16 A), 406775 (20 A), 406777 (32 A). Chaque exemplaire représente un circuit ; les autres articles sont exclus.
2. Créez les rangées et renseignez le calibre, le type et la sensibilité du différentiel prévu, à partir de ses caractéristiques. Ces champs restent inconnus par défaut.
3. Affectez chaque circuit à sa rangée et indiquez son usage.
4. Choisissez la règle aval ou amont. En amont, renseignez le calibre de la protection amont, pas la puissance souscrite.

Les résultats sont détaillés par rangée. Les circuits non affectés sont comptés séparément. L’affichage des affectations est limité à 500 circuits ; fractionnez les listes plus importantes.

## Critères

- **Aval** : somme des calibres chauffage électrique, chauffe-eau et recharge véhicule, plus la moitié des autres calibres. Aucun résultat aval complet si un usage manque.
- **Amont** : calibre du différentiel au moins égal à celui de la protection amont. Cette règle est une alternative à la règle aval.
- Au maximum huit circuits par différentiel ; sensibilité de 30 mA pour les circuits considérés.
- Un type AC est signalé comme inadapté aux plaques de cuisson ou au lave-linge. Les IRVE, variateurs, autres usages particuliers et différentiels de type B nécessitent une vérification spécifique des notices.

Le calibre proposé ne concerne que le critère d’intensité. Le logiciel ne vérifie pas les sections, le câblage, les protections dédiées, le nombre minimal de différentiels du logement ni la répartition assurant la continuité de service. Un résultat satisfaisant pour une rangée ne vaut donc pas validation du tableau complet.

Les fichiers JSON conservent cette configuration. Charger une ancienne liste sans configuration électrique réinitialise les rangées. Diminuer une quantité retire les affectations des derniers exemplaires ; supprimer un exemplaire conserve celles des exemplaires restants. Le démarrage avec une liste vide réinitialise aussi les rangées.

Sources fabricant consultées le 13/11/2026 : [dimensionnement amont/aval](https://www.legrand.fr/questions-frequentes/comment-calculer-lamperage-dun-interrupteur-differentiel), [nombre et types de différentiels](https://www.legrand.fr/questions-frequentes/combien-dinterrupteurs-differentiels-dois-je-mettre-dans-mon-tableau-electrique).
