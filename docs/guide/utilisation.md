# Utiliser l'application

## Connexion et comptes

Au premier démarrage, un compte adulte **`famille`** est créé avec le mot de passe
`REPAS_MOT_DE_PASSE`. Depuis l'onglet **Famille**, les adultes créent ensuite d'autres
comptes :

| Type | Peut faire |
|---|---|
| 🧑 **Adulte** | tout : planifier, courses, placard, bilan, famille, comptes, import de plats |
| 🧒 **Enfant** (relié à un membre) | consulter le menu de la semaine, les plats et leurs recettes, et **donner son avis** sur ses repas passés et à venir |

Les droits sont vérifiés par le serveur, pas seulement masqués dans l'interface. Chacun change
son mot de passe depuis **👤 Mon compte** (en haut à droite). Après 5 essais erronés, un
identifiant est bloqué une minute. La session dure 90 jours sur chaque appareil.

## La famille

Onglet **Famille**, pour chaque membre :

- date de naissance, sexe et poids ;
- **mode de vie** : sédentaire, modéré (debout, trajets actifs) ou actif (métier physique,
  enfant très actif) ;
- **heures de sport par semaine**.

L'application affiche le **besoin énergétique** estimé et le **coefficient de portion** (1,0 =
adulte de référence à 2 000 kcal/jour). Un adolescent sportif peut avoir 1,4 ; un enfant de
6 ans environ 0,7. La liste de courses en tient compte.

Un membre qui ne mange plus à la maison (études...) peut être marqué « ne mange plus à la
maison » : ses notes restent dans l'historique. Le bouton **Supprimer** du formulaire efface
au contraire définitivement le membre, ses notes et sa présence aux repas planifiés.

### Réglages de l'algorithme

- **Budget** : favorise les plats économiques (prix médians Open Prices).
- **Empreinte carbone** : favorise les plats peu émetteurs (Agribalyse).
- **Cuisine en lot** : favorise les soupes et mijotés servis sur plusieurs repas.
- **Repas de restes au plus** : limite le nombre de repas « réchauffés » par semaine.

La nutrition reste toujours prioritaire : ces réglages départagent les plats équivalents.

## Planifier la semaine (le vendredi soir)

À partir du vendredi, l'onglet **Semaine** propose automatiquement la semaine suivante.

1. **Présences** : chaque repas affiche les initiales des membres. Un clic indique une absence
   (cantine, déplacement). Le bouton **+** ajoute un invité (clic droit pour en retirer).
   Un repas sans personne n'est pas planifié.
2. **Jokers** 🎉 : sur ces repas, l'application propose des plats plaisir (pizza, raclette,
   burger maison...) et des desserts gourmands ; ils ne comptent pas dans les repères
   nutritionnels.
3. **Générer les repas** : en quelques secondes, l'application choisit un plat et un dessert
   par repas.
4. Cliquez sur un plat pour voir son **Nutri-Score** (indicatif, calculé pour le repas
   plat + dessert), ses calories, protéines, fibres, fruits et légumes, son **empreinte
   carbone** et son **coût** pour les convives, ainsi que **pourquoi** il a été choisi (de
   saison, apprécié, poisson gras, utilise le placard...).
5. **📖 Recette** ouvre la fiche du plat avec les **quantités calculées pour les convives de
   ce repas**, les étapes et le lien vers la recette détaillée en ligne.
6. **Changer** un repas : l'application calcule les meilleures alternatives compte tenu du
   reste de la semaine, ou vous laisse choisir dans tout le catalogue. Un plat choisi à la main
   est **verrouillé** 🔒 : il est conservé si vous demandez **Autre proposition**.
7. Le **bilan de la semaine** indique, pour chaque repère, si la cible est atteinte (✓), proche
   (≈) ou manquée (✗), ainsi que l'empreinte carbone comparée à des repas moyens.

### Restes et cuisine en lot

Les plats marqués « en lot » (soupes, chili, dahl, bœuf carottes...) peuvent être servies
sur 2 à 4 repas, dans leur durée de conservation. Le premier repas est celui où l'on cuisine,
les suivants affichent « ♻️ restes du lundi soir ». La liste de courses compte bien toutes les
portions.

## La liste de courses

Onglet **Courses** :

- les articles sont **regroupés par rayon**, dans l'ordre d'un parcours en magasin ;
- les quantités sont **arrondies aux conditionnements réels** (paquets, boîtes d'œufs, pièces,
  vrac) en choisissant la combinaison qui gaspille le moins ;
- ce qui est déjà au **placard** est déduit ;
- les produits de base (sel, épices, huile...) sont listés à part, « à vérifier » ;
- le **budget estimé** utilise les prix médians relevés par Open Prices.

Les cases cochées sont mémorisées sur le téléphone, même sans réseau au magasin. Le bouton
**Imprimer (PDF)** produit une liste à cocher. Le **Menu PDF** (onglet Semaine) s'affiche
sur le frigo.

Une fois les courses faites, **Courses faites** met à jour le placard : les restes des paquets
entamés (si le produit se conserve au moins 7 jours) y sont ajoutés avec une date limite.

## Le bilan

L'onglet **Bilan** résume les 4 dernières semaines, 3 mois, 6 mois ou 1 an :

- **chiffres clés** : repas planifiés, Nutri-Score moyen, CO₂ évité (et son équivalent en
  kilomètres de voiture), budget des courses et coût par repas et par personne ;
- **nutrition dans le temps** : chaque repère ANSES/PNNS semaine par semaine (✓ atteint,
  ≈ proche, ✗ hors cible), le Nutri-Score moyen et la part de semaines conformes ;
- **couverture des besoins** de chaque membre en calcium, fer, vitamine C, fibres, folates
  et oméga-3 (EPA + DHA) : apport moyen d'un repas pris à la maison comparé à 30 % de la
  référence journalière pour son âge et son sexe ;
- **carbone et budget** semaine par semaine (survolez une barre pour le détail) ;
- **goûts et variété** : plats préférés et moins aimés de chacun, part de repas
  végétariens, nombre de légumes différents, sources de protéines, plats bien notés à
  redécouvrir et plats jamais servis ;
- **saisonnalité** et **anti-gaspillage** : part des fruits et légumes de saison, quantités
  reprises dans le placard, surplus de produits frais, produits périmés.

!!! note "Repas pris à l'extérieur"
    Les repas où un membre est absent (cantine, travail, restaurant) ne sont pas saisis : ils
    sont **supposés équilibrés**. Ils ne comptent ni dans les repères de la semaine (ramenés
    au nombre de repas pris à la maison), ni dans la couverture des besoins (moyenne par
    repas pris à la maison).

Le budget d'une semaine est estimé tant que les courses ne sont pas validées ; il devient
celui de la liste réellement achetée ensuite.

## Le placard

L'onglet **Placard** liste les restes avec leur date limite estimée. Les quantités sont
modifiables (vous avez fini le riz ? mettez 0). On peut aussi ajouter un produit à la main.
L'algorithme favorise les plats qui utilisent le placard.

## Avis sur les repas

L'onglet **Avis** comporte deux parties :

- **À venir** : les repas des 7 prochains jours ; chacun dit à l'avance s'il en a envie
  (5 étoiles) ou pas du tout (1 étoile) ;
- **Comment c'était ?** : les repas des deux dernières semaines, à noter de 1 à 5 étoiles.

Un compte enfant ne donne que son propre avis ; un adulte peut noter pour toute la famille
(pratique pour les plus petits). Les notes influencent les choix suivants, **pour les membres présents** au repas :
un plat adoré par les enfants sera proposé plus volontiers quand ils sont là. Les plats déjà
servis les trois semaines précédentes sont aussi évités pour limiter la répétition.

## Le catalogue des plats

L'onglet **Plats** présente tous les plats avec leurs valeurs nutritionnelles, leur
empreinte carbone, leur coût estimé, leur saisonnalité et la note de la famille. On peut en
ajouter grâce à une IA : voir [Ajouter des recettes avec une IA](recettes-ia.md).
