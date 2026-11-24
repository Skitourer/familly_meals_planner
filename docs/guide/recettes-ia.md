# Ajouter des recettes avec une IA

L'application **n'est connectée à aucune IA** : elle ne transmet aucune donnée et fonctionne
hors ligne. Pour enrichir le catalogue, vous pouvez en revanche faire générer des recettes
par l'assistant de votre choix, puis les **importer** sous forme de fichier JSON.

## Étapes

1. **Télécharger le fichier d'instructions** : onglet **Plats** → « fichier
   d'instructions » (ou [version de la documentation](../ia/instructions-ia.md)). Il est généré
   à partir du référentiel : il contient toujours la **liste à jour des ingrédients
   autorisés**, avec leurs mois de saison.
2. **Remplacer la section « Ce que je te demande »** par votre demande, par exemple :
   > Propose 8 plats d'hiver pour une famille avec deux enfants, prêts en moins de 30 minutes,
   > dont 3 végétariens, 2 à base de poisson et 2 soupes à cuisiner en lot.
3. **Donner le fichier à l'IA** (copier-coller ou pièce jointe) et enregistrer sa réponse dans
   un fichier `recettes.json`.
4. **Importer** : onglet Plats → choisir le fichier → **Vérifier**. Chaque recette est
   contrôlée :
    - ❌ **refusée** si sa structure est invalide, si son identifiant existe déjà, si elle
      utilise un ingrédient absent du référentiel, ou s'il s'agit d'un plat **sans lien vers
      sa recette** ou avec un lien qui n'existe pas (page 404 : les IA inventent parfois des
      adresses) ;
    - ⚠️ **avertissements** (non bloquants) si son profil nutritionnel est inhabituel :
      énergie, peu de légumes ou de protéines, trop de sel, pas d'étapes.
5. **Importer N recettes** pour confirmer.

Les recettes importées reçoivent automatiquement leurs valeurs nutritionnelles, leur
empreinte carbone, leur saisonnalité et leur coût à partir des bases ouvertes : l'IA ne
fournit que la composition, jamais les chiffres.

Elles sont enregistrées dans `donnees/local/recettes-importees/` (un fichier YAML lisible par
recette) et peuvent être supprimées depuis leur fiche, tant qu'elles n'ont pas été servies.

## Format du fichier

```json
{
  "format": "menu-famille/recettes",
  "version": 1,
  "recettes": [
    {
      "id": "poelee-poireaux-pois-chiches",
      "nom": "Poêlée de poireaux et pois chiches, riz complet",
      "type": "plat",
      "temps": { "preparation": 15, "cuisson": 25 },
      "etiquettes": ["vegetarien", "legumineuses"],
      "ingredients": { "poireau": 180, "pois-chiches": 120, "riz-complet": 70 },
      "etapes": ["Cuire le riz.", "Faire fondre les poireaux.", "Ajouter les pois chiches."],
      "lien": "https://www.marmiton.org/recettes/recette_…aspx"
    }
  ]
}
```

Le champ `lien` est **obligatoire pour un plat** : c'est la recette détaillée qu'ouvre le
bouton « 📖 Recette » du planning. Les champs sont ceux du
[format du catalogue](../technique/catalogue.md) ; les quantités
sont en grammes par portion pour un adulte de référence.

!!! tip "Partager une bonne recette"
    Une recette importée qui plaît à toute la famille peut rejoindre le catalogue commun :
    copiez son fichier YAML dans `donnees/recettes/` et proposez une pull request.
