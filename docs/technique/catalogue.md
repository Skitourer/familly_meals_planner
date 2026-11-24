# Format du catalogue

Le catalogue est fait de fichiers texte versionnés dans `donnees/`, validés au démarrage et
par les tests (voir l'[ADR 3](../adr/0003-catalogue-en-fichiers.md)).

```text
donnees/
├── referentiel/
│   ├── ingredients.yaml   # ingrédients (édité à la main)
│   └── aliments.json      # données ouvertes (généré par repas-import)
├── recettes/              # recettes du catalogue commun (YAML)
├── sources/               # cache des téléchargements (non versionné)
└── local/                 # base SQLite et recettes importées (non versionné)
```

## Ingrédients — `referentiel/ingredients.yaml`

```yaml
pates:
  nom: Pâtes sèches
  ciqual: 9810                 # code CIQUAL : nutrition, et CO2 via Agribalyse
  famille: feculent            # pour les repères PNNS
  rayon: epicerie-salee        # regroupement de la liste de courses
  conservation_jours: 365      # ≥ 7 : le surplus va au placard
  vente: {mode: paquet}        # formats déduits d'Open Food Facts
  categorie_off: en:dry-pastas # catégorie Open Food Facts (formats, prix)
  prix_kg: 1.8                 # prix de repli si Open Prices manque de relevés
```

Champs complets et valeurs possibles : voir l'en-tête du fichier. Les modes de vente sont :

- `{mode: paquet, formats: [400, 800]}` : paquets de poids fixe ; formats facultatifs ;
- `{mode: piece, poids: 60, lots: [6, 12]}` : à l'unité, éventuellement par boîtes ;
- `{mode: vrac, pas: 100}` : au poids, arrondi au pas.

Pour **ajouter un ingrédient** : trouver son code sur [ciqual.anses.fr](https://ciqual.anses.fr/),
l'ajouter au YAML, puis lancer `uv run repas-import` et
`uv run python -m repas.catalogue.import_recettes`. Les tests vérifient qu'il a bien des
données nutritionnelles, une empreinte carbone et des formats de vente.

## Recettes — `recettes/*.yaml`

Chaque fichier contient une liste de recettes, regroupées par thème
(`plats-toute-annee.yaml`, `plats-automne-hiver.yaml`, `desserts.yaml`...).

```yaml
- id: dahl-lentilles-corail            # unique, minuscules et tirets
  nom: Dahl de lentilles corail au lait de coco
  type: plat                           # plat | dessert
  plaisir: false                       # true : réservé aux jokers
  temps: {preparation: 10, cuisson: 25}
  lot: {repas_max: 3, conservation_jours: 4}   # facultatif : cuisine en lot
  etiquettes: [vegetarien, legumineuses]
  ingredients:                         # grammes par portion adulte de référence
    lentilles-corail: 70
    lait-coco: 50
    tomates-concassees: 100
  etapes:
    - Faire revenir l'oignon émincé avec le curry.
    - "Astuce : les guillemets sont nécessaires si la phrase contient « : »."
  source: Catalogue Menu Famille
```

### Règles de composition

- Quantités **nettes** (épluchées, égouttées), pour **un adulte à 2 000 kcal/jour**.
- Un **plat** est complet (féculent, légumes, protéines), environ 450 à 650 kcal, avec au
  moins 75 g (idéalement 150 g) de légumes. Le dessert est choisi à part.
- Pas de sel ajouté dans la liste ; les épices et l'huile sont des produits « basiques ».
- Les tests imposent : énergie plausible, au moins 15 g de protéines pour un plat ordinaire,
  au moins 14 plats de saison chaque mois.
