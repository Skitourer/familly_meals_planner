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

Un membre ajouté, ou de nouveau marqué comme mangeant à la maison, rejoint aussi les repas
d'aujourd'hui et des jours suivants des semaines déjà ouvertes (sauf ceux où il est noté
« repas à l'extérieur ») : les portions et la liste de courses en tiennent compte. Les jours
passés ne changent pas.

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
    - **Dehors** : sous les initiales, chaque membre absent a une pastille en pointillés.
      Un clic indique ce qu'il a mangé dehors (les cantines publient leurs menus chaque
      semaine) : **?** inconnu (par défaut) → 🐟 poisson → 🍖 viande → 🥕 végétarien.
      C'est facultatif ; à la génération suivante, l'application évite un second poisson (ou
      une seconde viande) le même jour pour ce membre et compte ses poissons dans le repère
      de la semaine.
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
- le **budget estimé** utilise les prix médians relevés par Open Prices ;
- un ingrédient mis de côté avec 🛒 apparaît dans son rayon, marqué « 🛒 à racheter » (✕ pour
  y renoncer) ;
- la section **À racheter** reprend les autres produits finis au placard (un paquet chacun,
  au dernier prix payé s'il est connu). Ils se cochent comme le reste et se retirent avec ✕ ;
  scanner l'un d'eux le reconnaît par son code-barres. À la validation, un produit coché (ou
  « Tout a été acheté ») rejoint les autres produits du placard ;
- la section **Autres articles** accueille ce qui ne vient pas des repas (chaussures des
  enfants, produits nettoyants...) : un libellé, une quantité facultative, **Ajouter**. Ils se
  cochent comme le reste ; une fois coché, un champ facultatif garde le **prix payé**, compté à
  part (« autres articles ») et jamais dans le coût des repas du bilan. Ils ne vont pas au
  placard. **↪ Reporter** déplace les articles non cochés sur la liste de la semaine suivante,
  même après « Courses faites » ; un libellé déjà prévu là-bas n'est pas doublé.

Les cases cochées sont **partagées entre appareils** : à deux au magasin, chacun voit ce que
l'autre a déjà pris (en rechargeant la page ou en revenant sur l'application). Sans réseau, les
coches restent sur le téléphone, un bandeau indique combien sont en attente, et elles partent
dès le retour de la connexion ; pour un même article, la plus récente l'emporte. **Courses
faites** demande le réseau. Le bouton **Imprimer (PDF)** produit une liste à cocher. Le **Menu PDF** (onglet Semaine) s'affiche
sur le frigo.

### Au magasin sans réseau

La liste de courses s'ouvre même sans réseau, telle qu'elle était à la dernière connexion :

1. **Installer l'application** sur le téléphone, une fois : sur Android (Chrome), menu ⋮ puis
   **Installer l'application** ; sur iPhone (Safari), bouton Partager puis **Sur l'écran
   d'accueil**. Elle s'ouvre alors comme une application, depuis son icône.
2. Avant de partir, **ouvrir la liste de la semaine avec le réseau** : c'est cette version qui
   est gardée sur le téléphone, pour chaque semaine ouverte.
3. Au magasin, ouvrir l'application : la liste s'affiche avec un bandeau « Hors ligne » et se
   coche normalement ; les coches partent au retour du réseau.

Les autres onglets demandent le réseau. La **déconnexion** efface la liste gardée sur le
téléphone. Hors ligne, l'application nécessite HTTPS (c'est le cas avec Tailscale) ; une
nouvelle version est prise en compte quand l'application a été complètement fermée.

### Scanner les produits achetés

Au magasin (avec le réseau) ou au retour, **📷 Scanner** lit le code-barres d'un produit mis
dans le caddie. L'article correspondant de la liste est proposé (des penne complètes →
« Pâtes complètes » ou « Pâtes sèches », selon la liste), avec la quantité du paquet et un
prix : le dernier prix payé pour ce produit, sinon l'estimation. Corrigez le prix selon
l'étiquette, puis **Enregistrer** : l'article est coché et la ligne affiche « ✓ acheté 1 kg ·
2,35 € ». Deux paquets scannés pour le même article s'additionnent ; ✕ annule.

**Produit qui n'est pas sur la liste** : choisissez l'ingrédient dans « Hors liste »
(correspondances proposées, puis tous les ingrédients). Il apparaît dans la section **Hors
liste** et rejoint **en entier** le placard quand les courses sont validées, même un produit
frais : le cadre « Frigo à vider » le signalera à temps. Un produit que les repas n'utilisent
pas (Nutella, céréales, boissons) est proposé comme **Autre produit (hors repas)** : il compte
dans le budget et rejoint les « Autres produits » du placard à la validation. Décochez
**Ranger au placard** pour ce qui est consommé tout de suite (un sandwich).

Le total « avec les prix payés » s'affiche à côté du budget estimé. Le scan n'est pas
obligatoire : les articles non scannés gardent leur estimation.

Une fois les courses faites, **Courses faites** met à jour le placard : les restes des paquets
entamés (si le produit se conserve au moins 7 jours) y sont ajoutés avec une date limite.
Pour un article scanné, le reste est calculé à partir de la quantité vraiment achetée (un
paquet de 1 kg au lieu de 500 g laisse 650 g au placard au lieu de 150 g).

S'il reste des articles ni cochés ni scannés, l'application les liste et demande :

- **Tout a été acheté** : ils sont cochés, puis les courses validées ;
- **Ils n'ont pas été achetés** : rien n'est ajouté au placard ni au budget pour eux (ce
  que les repas prennent déjà dans le placard reste déduit) ;
- **Annuler**.

Une fois les courses validées, les cases sont verrouillées. **↩ Rouvrir les courses** défait
ce que la validation a changé dans le placard et le budget (les corrections faites depuis à
la main sont gardées) : on peut alors corriger les coches ou les scans, puis revalider.

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
    Les repas où un membre est absent (cantine, travail, restaurant) sont **supposés
    équilibrés**. Ils ne comptent ni dans les repères de la semaine (ramenés au nombre de
    repas pris à la maison), ni dans la couverture des besoins (moyenne par repas pris à la
    maison). Quand leur catégorie est indiquée (poisson, viande, végétarien), ils
    s'ajoutent aux **sources de protéines** du bilan, un repas par membre.

Le budget d'une semaine est estimé tant que les courses ne sont pas validées. À la
validation, il retient les prix payés des articles scannés, les achats hors liste et les
« autres achats », et l'estimation des articles non scannés.

## Le placard

L'onglet **Placard** liste les restes avec leur date limite estimée. Les quantités et les
dates sont modifiables (vous avez fini le riz ? mettez 0). On peut aussi ajouter un produit à
la main : tapez les premières lettres de son nom et choisissez-le dans la liste, puis sa date
limite si on la connaît. L'algorithme favorise les plats qui utilisent le placard.

Le bouton **🛒** d'un ingrédient le met sur la liste de courses de la semaine suivante :
le plus petit conditionnement vendu (un paquet de beurre, une boîte de 6 œufs…), en plus de
ce que demandent les repas, rangé au placard à la validation. Il est aussi proposé quand on
retire un ingrédient avec 🗑.

### Modifier un article

Le bouton **✏️** d'un ingrédient ou d'un autre produit ouvre le même formulaire que le scan,
pré-rempli, pour corriger une erreur sans retirer puis rajouter l'article :

- un ingrédient : changer l'ingrédient (le « lait » était de la crème), la quantité ou la
  date limite ; s'il rejoint un ingrédient déjà au placard, les quantités s'additionnent et
  la date la plus proche est gardée ;
- un autre produit : changer le nom, la catégorie, le nombre de paquets ou la date limite ;
- passer d'ingrédient à **Autre produit (hors repas)**, ou l'inverse (des céréales rangées
  comme ingrédient alors que les repas ne s'en servent pas).

Les notes du produit (Nutri-Score, NOVA, Green-Score) le suivent. La catégorie d'un
ingrédient est celle du catalogue et ne se change pas ici.

### Notes des produits

À côté du nom de chaque ingrédient et de chaque autre produit, trois pastilles résument :

- le **Nutri-Score** (A à E, qualité nutritionnelle) ;
- le groupe **NOVA** (1 à 4, du produit brut à l'ultra-transformé) ;
- le **Green-Score** (A à E, impact environnemental).

Pour un produit scanné, ce sont les notes d'Open Food Facts, enregistrées au scan : ouvrir le
placard ne consulte pas Internet. Pour un ingrédient ajouté à la main, le Nutri-Score est
calculé à partir de sa composition CIQUAL (ingrédient brut) et les deux autres notes restent
inconnues. **?** signale une note inconnue. Survolez ou touchez les pastilles pour le détail.

### Retrouver un produit

Au-dessus de la liste :

- **Rechercher** filtre les ingrédients et les autres produits, sans tenir compte des
  accents ni des majuscules (« creme » trouve « Crème fraîche légère ») ;
- **Trier par** date limite (par défaut, les produits sans date en dernier), nom ou
  quantité ; sur ordinateur, on peut aussi toucher l'en-tête d'une colonne ;
- **Par rayon** regroupe les ingrédients dans l'ordre des rayons de la liste de courses ;
- **À vider seulement** ne garde que les produits marqués « à vider » (leur nombre est
  indiqué).

Le tri et le regroupement sont retenus sur l'appareil. Sur téléphone, chaque ingrédient
s'affiche comme une carte plutôt que comme une ligne de tableau.

### Scanner un produit

**📷 Scanner un produit** ouvre la caméra du téléphone : visez le code-barres. Le produit est
cherché dans [Open Food Facts](https://world.openfoodfacts.org/) et l'ingrédient
correspondant est proposé (des penne complètes → « Pâtes complètes »), avec la quantité du
paquet. Vérifiez, ajoutez la date limite si vous la connaissez, puis **Ajouter au placard** ;
la caméra se rouvre pour le produit suivant.

- Sur Firefox, la lecture par la caméra passe par un lecteur intégré, chargé à l'ouverture
  du scanner (quelques secondes la première fois).
- Si la caméra n'est pas disponible (autorisation refusée, page sans HTTPS), tapez les
  chiffres imprimés sous le code-barres.
- Produit inconnu d'Open Food Facts ou réseau absent : ajoutez-le à la main.
- Sans date saisie, un produit déjà au placard garde sa date limite (le plus ancien d'abord).
- Les produits de fond de placard (huile, sel, épices) ne sont pas suivis.

### Autres produits

La section **Autres produits** suit le stock de ce que les repas n'utilisent pas : petit-déjeuner,
biscuits et goûters, apéritif, boissons, conserves… Chaque produit est compté **en paquets**,
regroupé par catégorie (déduite d'Open Food Facts, modifiable) :

- **−** et **+** corrigent le nombre de paquets ; à 0, le produit est retiré et
  **🛒 À racheter** le remet sur la liste de courses de la semaine suivante (voir plus bas) ;
- le bouton **🛒** de chaque produit l'y met à tout moment, sans le retirer du placard ;
- une date limite facultative le fait apparaître dans « Frigo à vider » ;
- au scan, un produit sans ingrédient correspondant est proposé comme « Autre produit » ;
  rescanner le même produit ajoute un paquet ;
- un produit sans code-barres s'ajoute à la main en bas de la section.

Les autres produits ne sont utilisés ni par l'algorithme des repas ni par le bilan
nutritionnel.

### Frigo à vider

Un produit dont la date limite tombe dans les 7 jours est marqué **à vider**. Le cadre
**Frigo à vider** apparaît alors en haut de l'onglet :

- les **plats qui utilisent le mieux** ces produits, à consulter pour s'en inspirer ;
- **Réajuster la semaine en cours** : les repas d'aujourd'hui à dimanche sont recalculés en
  vidant le frigo avant les dates limites ; les jours passés et les repas verrouillés sont
  gardés.

À la génération d'une semaine, les produits à vider sont aussi fortement favorisés.

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
