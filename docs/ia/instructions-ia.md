# Instructions pour générer des recettes « Menu Famille »

Tu es un assistant culinaire. Tu vas proposer des recettes familiales
**équilibrées**, de **saison** et à **faible empreinte carbone**, au format JSON
décrit ci-dessous, pour qu'elles soient importées dans l'application
« Menu Famille ».

## Ce que je te demande

(Remplace cette section par ta demande, par exemple : « Propose 10 plats
d'hiver rapides (moins de 30 min), dont 4 végétariens et 2 à base de poisson ».)

## Règles impératives

1. Réponds **uniquement** par un objet JSON valide, sans texte autour.
2. Utilise **seulement** les identifiants d'ingrédients de la liste plus bas
   (colonne de gauche, entre accents graves). N'invente aucun ingrédient : si
   une recette en exige un autre, choisis une autre recette.
3. Les quantités sont en **grammes (ou ml) par portion pour UN adulte de
   référence** (2 000 kcal/jour), **poids net** (épluché, égoutté, sans os).
   L'application ajuste ensuite les portions pour chaque membre de la famille.
4. Un **plat** est un plat principal complet (féculent + légumes + protéines),
   d'environ 450 à 650 kcal par portion, avec au moins 150 g de légumes. Le
   dessert est choisi séparément : ne l'inclus pas dans le plat.
5. Un **dessert** fait environ 60 à 150 kcal (fruit, laitage) ; les desserts
   riches (gâteaux...) portent `"plaisir": true`.
6. `"plaisir": true` est réservé aux repas « joker » (pizza, burger,
   raclette...). Les autres recettes doivent respecter les repères du PNNS :
   peu de sel (≤ 1,5 g par portion), peu de charcuterie, des légumineuses et
   du poisson régulièrement, des céréales complètes.
7. Pour les soupes et les plats mijotés qui se réchauffent bien, ajoute
   `"lot": {"repas_max": 3, "conservation_jours": 3}` (repas_max de 2 à 4,
   conservation de 1 à 5 jours).
8. `id` : en minuscules, mots séparés par des tirets, sans accent, unique, et
   **différent** des recettes déjà présentes (liste en fin de document).
9. Pas de sel ni de poivre dans la liste d'ingrédients sauf s'ils sont
   caractéristiques ; 3 à 6 étapes courtes et précises.
10. Privilégie les légumes et fruits **de saison** (mois indiqués dans la liste).

## Format attendu

```json
{
  "format": "menu-famille/recettes",
  "version": 1,
  "recettes": [
    {
      "id": "poelee-poireaux-pois-chiches",
      "nom": "Poêlée de poireaux et pois chiches, riz complet",
      "type": "plat",
      "temps": {
        "preparation": 15,
        "cuisson": 25
      },
      "etiquettes": [
        "vegetarien",
        "legumineuses"
      ],
      "ingredients": {
        "poireau": 180,
        "pois-chiches": 120,
        "riz-complet": 70,
        "huile-olive": 8,
        "cumin": 1
      },
      "etapes": [
        "Cuire le riz complet 25 min.",
        "Faire fondre les poireaux émincés dans l'huile avec le cumin.",
        "Ajouter les pois chiches égouttés, réchauffer 5 min et servir avec le riz."
      ],
      "source": "Proposition IA"
    }
  ]
}
```

Champs d'une recette :

| Champ | Obligatoire | Description |
|---|---|---|
| `id` | oui | identifiant unique (`a-z`, `0-9`, tirets) |
| `nom` | oui | nom affiché |
| `type` | oui | `"plat"` ou `"dessert"` |
| `ingredients` | oui | objet `{ "identifiant": grammes }` |
| `etapes` | conseillé | liste de phrases |
| `temps` | conseillé | `{"preparation": minutes, "cuisson": minutes}` |
| `etiquettes` | non | ex. `vegetarien`, `rapide`, `enfants`, `four`, `soupe` |
| `lot` | non | plat cuisiné une fois pour plusieurs repas |
| `plaisir` | non | `true` pour les repas joker uniquement |
| `source` | non | ex. `"Proposition IA"` |
| `lien` | non | adresse (https://…) d'une recette détaillée en ligne, si elle existe vraiment |

## Ingrédients autorisés

### Féculents

- `chapelure` : Chapelure
- `farine` : Farine de blé T65
- `feuilles-lasagne` : Feuilles de lasagne
- `frites-four` : Frites au four (surgelées)
- `pain` : Baguette
- `pain-burger` : Pains à burger
- `pain-de-mie` : Pain de mie
- `patate-douce` : Patate douce
- `pate-brisee` : Pâte brisée
- `pate-pizza` : Pâte à pizza
- `pates` : Pâtes sèches
- `pomme-de-terre` : Pommes de terre
- `riz` : Riz basmati
- `riz-arborio` : Riz à risotto
- `semoule` : Semoule de blé (couscous)

### Féculents complets

- `boulgour` : Boulgour
- `farine-sarrasin` : Farine de sarrasin
- `pain-complet` : Pain complet
- `pates-completes` : Pâtes complètes
- `quinoa` : Quinoa
- `riz-complet` : Riz complet

### Légumineuses

- `haricots-blancs` : Haricots blancs en conserve (égouttés)
- `haricots-rouges` : Haricots rouges en conserve (égouttés)
- `lentilles-corail` : Lentilles corail
- `lentilles-vertes` : Lentilles vertes
- `pois-chiches` : Pois chiches en conserve (égouttés)
- `tofu` : Tofu nature

### Légumes

- `asperge` : Asperges vertes — saison : avril, mai, juin
- `aubergine` : Aubergines — saison : juin, juil., août, sept.
- `betterave` : Betterave cuite — saison : janv., févr., mars, oct., nov., déc.
- `brocoli` : Brocoli — saison : sept., oct., nov.
- `brocoli-surgele` : Brocoli surgelé
- `carotte` : Carottes
- `champignons` : Champignons de Paris
- `chou-fleur` : Chou-fleur — saison : janv., févr., mars, sept., oct., nov., déc.
- `chou-vert` : Chou vert — saison : janv., févr., mars, oct., nov., déc.
- `concombre` : Concombre — saison : mai, juin, juil., août, sept., oct.
- `courge-butternut` : Courge butternut — saison : janv., sept., oct., nov., déc.
- `courgette` : Courgettes — saison : mai, juin, juil., août, sept., oct.
- `echalote` : Échalotes
- `endive` : Endives — saison : janv., févr., mars, avril, mai, oct.
- `epinards-frais` : Épinards frais — saison : janv., févr., mars, avril, mai, sept., oct., nov., déc.
- `epinards-surgeles` : Épinards surgelés
- `haricots-verts` : Haricots verts frais — saison : juin, juil., août, sept., oct.
- `haricots-verts-surgeles` : Haricots verts surgelés
- `laitue` : Laitue — saison : mai, juin, juil., août, sept.
- `mache` : Mâche — saison : janv., févr., oct., nov., déc.
- `mais` : Maïs doux en conserve
- `navet` : Navets — saison : janv., févr., mars, avril, mai, oct., nov., déc.
- `oignon` : Oignons
- `petits-pois-surgeles` : Petits pois surgelés
- `poireau` : Poireaux — saison : janv., févr., mars, avril, sept., oct., nov., déc.
- `poivron` : Poivrons — saison : juin, juil., août, sept.
- `potiron` : Potiron — saison : janv., sept., oct., nov., déc.
- `tomate` : Tomates — saison : juin, juil., août, sept.
- `tomates-concassees` : Tomates pelées en conserve

### Fruits

- `abricot` : Abricots — saison : juin, juil., août
- `banane` : Bananes — saison : janv., févr., mars, avril, mai, juin, juil., août, sept., oct., nov., déc.
- `cerise` : Cerises — saison : juin, juil.
- `citron` : Citrons
- `clementine` : Clémentines — saison : janv., févr., nov., déc.
- `compote` : Compote de pomme sans sucre ajouté
- `fraise` : Fraises — saison : mai, juin, juil.
- `framboise` : Framboises — saison : juin, juil., août
- `kiwi` : Kiwis — saison : janv., févr., mars, nov., déc.
- `melon` : Melon — saison : juin, juil., août, sept.
- `orange` : Oranges — saison : janv., févr., mars
- `peche` : Pêches — saison : juin, juil., août, sept.
- `poire` : Poires — saison : janv., févr., mars, août, sept., oct., nov., déc.
- `pomme` : Pommes — saison : janv., févr., mars, avril, août, sept., oct., nov., déc.
- `prune` : Prunes — saison : juil., août, sept.
- `raisin` : Raisin — saison : sept., oct.

### Viandes (hors volaille)

- `boeuf-hache` : Bœuf haché 5 % MG
- `boeuf-mijoter` : Bœuf à mijoter (paleron, macreuse)

### Volailles

- `dinde-escalope` : Escalopes de dinde
- `poulet-cuisse` : Cuisses de poulet
- `poulet-filet` : Filets de poulet

### Charcuterie

- `chair-saucisse` : Chair à saucisse
- `jambon` : Jambon blanc
- `lardons` : Lardons
- `saucisse-montbeliard` : Saucisse de Montbéliard

### Poissons

- `cabillaud` : Dos de cabillaud
- `lieu-surgele` : Filets de lieu noir surgelés
- `thon` : Thon au naturel

### Poissons gras

- `maquereau-fume` : Filets de maquereau fumé
- `sardines` : Sardines à l'huile d'olive
- `saumon` : Pavés de saumon

### Fruits de mer

- `moules` : Moules

### Œufs

- `oeuf` : Œufs

### Produits laitiers

- `fromage-blanc` : Fromage blanc 3 %
- `lait` : Lait demi-écrémé
- `yaourt` : Yaourt nature

### Fromages

- `chevre` : Bûche de chèvre
- `comte` : Comté
- `emmental` : Emmental râpé
- `feta` : Feta
- `mozzarella` : Mozzarella
- `parmesan` : Parmesan
- `raclette` : Fromage à raclette
- `reblochon` : Reblochon
- `ricotta` : Ricotta

### Matières grasses

- `beurre` : Beurre doux
- `creme` : Crème fraîche légère
- `huile-colza` : Huile de colza
- `huile-olive` : Huile d'olive
- `lait-coco` : Lait de coco
- `olives` : Olives noires
- `pesto` : Pesto

### Produits sucrés

- `chocolat-noir` : Chocolat noir pâtissier
- `miel` : Miel
- `sucre` : Sucre

### Condiments et épices

- `ail` : Ail
- `bouillon` : Bouillon de légumes (cube)
- `concentre-tomate` : Concentré de tomate
- `cumin` : Cumin
- `curry` : Curry en poudre
- `gingembre` : Gingembre en poudre
- `herbes-provence` : Herbes de Provence
- `levure-chimique` : Levure chimique
- `moutarde` : Moutarde
- `muscade` : Noix de muscade
- `paprika` : Paprika
- `persil` : Persil (botte)
- `poivre` : Poivre noir
- `sauce-soja` : Sauce soja
- `sel` : Sel iodé
- `vinaigre` : Vinaigre de vin

## Recettes déjà présentes (ne pas reprendre ces identifiants)

asperges-oeufs-mollets, aubergines-parmigiana, boeuf-carottes, brochettes-poulet-courgettes, burger-maison, cabillaud-poireaux, chili-con-carne, chili-sin-carne, compote, comte-pain, courgettes-farcies-quinoa, couscous-legumes-pois-chiches, crepes-jambon-fromage, crepes-sucre, croque-monsieur, curry-pois-chiches-patate-douce, dahl-lentilles-corail, dinde-moutarde-boulgour, endives-jambon, fromage-blanc-framboises, fromage-blanc-miel, fruit-abricots, fruit-banane, fruit-cerises, fruit-clementines, fruit-fraises, fruit-kiwi, fruit-melon, fruit-orange, fruit-peche, fruit-poire, fruit-pomme, fruit-prunes, fruit-raisin, galettes-sarrasin-completes, gaspacho-tartines-chevre, gateau-yaourt, gratin-chou-fleur, hachis-parmentier, hachis-patate-douce-lentilles, lasagnes-epinards-ricotta, lentilles-saucisse, lieu-papillote-riz-haricots, moules-frites, mousse-chocolat, omelette-champignons, pates-pesto-haricots, pizza-maison, pommes-au-four, potee-chou, poulet-basquaise, poulet-curry-chou-fleur, poulet-roti-legumes, raclette, ratatouille-oeufs, risotto-champignons-poireaux, riz-cantonais, salade-endives-betterave, salade-lentilles-ete, salade-lentilles-maquereau, salade-nicoise, salade-pates-thon, sardines-pommes-de-terre, saumon-brocoli-riz, saumon-courgettes-pates, saumon-quinoa-epinards, soupe-butternut-lentilles, soupe-haricots-blancs, soupe-poireaux-pommes-de-terre, spaghetti-bolognaise, taboule-pois-chiches, tarte-pommes, tartiflette, tofu-saute-legumes, tomates-farcies, veloute-potiron, yaourt-nature
