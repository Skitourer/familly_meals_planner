# 3. Catalogue en fichiers versionnés, données familiales en SQLite

*Date : 2026-11-24 — Statut : acceptée*

## Contexte

Il n'existe pas de base ouverte de recettes françaises avec des ingrédients structurés et
reliés aux tables nutritionnelles. Le catalogue doit donc être rédigé, puis **relu et
contrôlé**. Les données de la famille (membres, notes, placard) sont privées.

## Décision

- Recettes et ingrédients en **YAML** dans `donnees/`, données ouvertes dérivées en JSON
  généré (`aliments.json`), le tout versionné et validé par les tests.
- Données de la famille dans **SQLite** (`donnees/local/`, jamais versionné).
- Les recettes importées par la famille sont des YAML locaux dans `donnees/local/`.

## Conséquences

- Chaque modification du catalogue passe par une revue de code lisible (diff de texte).
- Pas d'interface d'édition de recettes dans l'application (l'import JSON couvre le besoin).
- Une seule base fichier, facile à sauvegarder ; pas de serveur de base de données.
