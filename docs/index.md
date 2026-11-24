# Menu Famille

**Menu Famille** planifie les déjeuners et dîners de la semaine pour toute la famille :
des repas **équilibrés**, **de saison** et à **faible empreinte carbone**, avec une liste de
courses **adaptée aux paquets vendus en magasin**.

## Le scénario du vendredi soir

1. On indique **qui mange à la maison** à chaque repas de la semaine suivante (et les invités),
   et on choisit un ou plusieurs repas **joker** pour se faire plaisir.
2. L'application **génère les 14 repas** (plat + dessert) en respectant les repères
   nutritionnels de l'ANSES et du PNNS, en privilégiant les produits de saison, les plats
   appréciés de la famille et les recettes peu émettrices de CO₂.
3. Chaque repas peut être **remplacé** : l'application propose les meilleures alternatives
   compte tenu du reste de la semaine.
4. La **liste de courses** est calculée selon les portions de chacun, déduit ce qui reste dans
   le **placard**, arrondit aux conditionnements réels (350 g de pâtes → un paquet de 500 g)
   et s'imprime en **PDF**.
5. Après les repas, chacun **note** les plats : les préférences guident les semaines suivantes.

## Points forts

| | |
|---|---|
| 🥦 **Nutrition d'abord** | Énergie, protéines, lipides, graisses saturées, fibres, sel, fruits et légumes, poisson, légumineuses, viande rouge et charcuterie sont contrôlés chaque semaine. |
| 👪 **Portions individuelles** | Besoins énergétiques calculés selon l'âge, le poids, le sexe et l'activité physique (équations de Henry). |
| 🧮 **Vraie optimisation** | Le choix des repas est un problème d'optimisation sous contraintes, résolu par OR-Tools ([détails](technique/algorithme.md)). |
| 🍲 **Cuisine en lot** | Soupes et mijotés cuisinés une fois et servis sur plusieurs repas. |
| 🎉 **Jokers** | Des repas plaisir choisis par la famille, compensés par le reste de la semaine. |
| 🌍 **Données ouvertes** | CIQUAL, Agribalyse, Impact CO2, Open Food Facts, Open Prices ([sources](technique/donnees-ouvertes.md)). |
| 🥫 **Placard** | Les restes de paquets sont suivis et réutilisés : moins de gaspillage. |
| 🤖 **Recettes par IA, sans IA** | Un [fichier d'instructions](guide/recettes-ia.md) permet de faire générer des recettes par l'IA de son choix, puis de les importer, avec validation. |

## Aperçu technique

- **Backend** : Python 3.13, FastAPI, SQLModel/SQLite, OR-Tools, géré avec **uv** ;
- **Interface** : SvelteKit (Svelte 5), installable sur téléphone ;
- **Déploiement** : une image Docker (amd64 / arm64 pour Raspberry Pi).

Pour commencer : [Démarrer](guide/demarrage.md).
