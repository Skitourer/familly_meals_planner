# Algorithme de planification

Le choix des repas est formulé comme un **problème d'optimisation linéaire en nombres
entiers**, résolu par le solveur **CP-SAT** d'[OR-Tools](https://developers.google.com/optimization)
(Google, licence Apache 2.0). Le code est dans
`backend/src/repas/domaine/planificateur.py`. Ce choix est justifié dans
l'[ADR 2](../adr/0002-optimisation-cp-sat.md).

Contrairement à un tirage au sort pondéré, le solveur considère **la semaine entière** :
un dîner léger peut compenser un déjeuner riche, et le poisson est placé là où il convient le
mieux.

## 1. Portions individuelles

Fichier : `domaine/besoins.py`.

1. **Métabolisme de base** (MB) : équations de Henry (2005), version « poids seul »,
   valables à tout âge (enfants compris) :
   $\text{MB} = (a \times \text{poids} + b) \times 239$ kcal, avec $a$ et $b$ selon le sexe
   et la tranche d'âge (0-3, 3-10, 10-18, 18-30, 30-60, 60+ ans).
2. **Niveau d'activité physique** (NAP) : 1,4 (sédentaire), 1,6 (modéré) ou 1,8 (actif),
   plus la dépense sportive : $\Delta\text{NAP} = (\text{MET} - 1) \times h / 168$, avec
   MET = 7 (effort modéré à soutenu) et $h$ les heures de sport par semaine ; plafonné à 2,2.
3. **Besoin** = MB × NAP.
4. **Coefficient de portion** = besoin / 2 000 kcal (adulte de référence du règlement UE
   1169/2011), borné entre 0,3 et 1,8.

Les recettes sont écrites pour **une portion de référence** ; la quantité cuisinée pour un
repas est la portion multipliée par la somme des coefficients des convives (un invité compte
1,0).

!!! note "Limites"
    Ces équations donnent une estimation de population. Elles ne remplacent pas un avis
    médical (grossesse, sport de haut niveau, régime particulier).

## 2. Variables

Pour chaque créneau $c$ (repas où au moins une personne mange à la maison), chaque plat $r$
et chaque dessert $d$ :

- $x_{c,r} \in \{0, 1\}$ vaut 1 si le plat $r$ est servi au créneau $c$ ;
- $y_{c,d} \in \{0, 1\}$ vaut 1 si le dessert $d$ est servi au créneau $c$.

## 3. Contraintes strictes

| Contrainte | Formulation |
|---|---|
| Un plat et un dessert par repas | $\sum_r x_{c,r} = 1$, $\sum_d y_{c,d} = 1$ |
| Plats plaisir réservés aux jokers | $x_{c,r}$ n'existe pas si $r$ est « plaisir » et $c$ n'est pas un joker |
| Pas de répétition | $\sum_c x_{c,r} \le 1$ pour un plat ordinaire |
| Cuisine en lot | $\sum_c x_{c,r} \le$ `repas_max` ; deux services séparés de plus de `conservation_jours`, ou le même jour, sont interdits |
| Limite de restes | nombre total de repas de restes ≤ réglage (4 par défaut) |
| Desserts variés | chaque dessert au plus 2 fois par semaine |
| Sources de protéines variées | une même source principale (légumineuses, poisson, volaille, viande, œuf, fromage) sur au plus 35 % des repas |
| Choix de la famille | les plats verrouillés sont imposés |

## 4. Repères nutritionnels (contraintes souples prioritaires)

Fichier : `domaine/reperes.py`. Les repères s'appliquent aux créneaux **hors jokers**, pour
une portion de référence. Un repas principal (plat + dessert) couvre environ 30 % de la
journée, le petit-déjeuner et le goûter apportant le reste.

| Repère | Cible par repas (moyenne de la semaine) | Source |
|---|---|---|
| Énergie (chaque repas) | 480 à 780 kcal | 30 % de 2 000 kcal ± marge |
| Protéines | 12 à 25 % de l'énergie | ANSES (10-20 %), borne haute relevée pour les repas principaux |
| Lipides | ≤ 40 % de l'énergie | ANSES (35-40 %) |
| Acides gras saturés | ≤ 12 % de l'énergie | ANSES |
| Fibres | ≥ 9 g | ANSES : 30 g/jour |
| Sel | ≤ 1,75 g | OMS : < 5 g/jour |
| Fruits et légumes | ≥ 200 g | PNNS : ≥ 5 portions/jour |
| Poisson | ≥ 2 repas/semaine, dont 1 gras | PNNS |
| Légumineuses | ≥ 2 repas/semaine | PNNS |
| Produits laitiers | ≥ 1 par jour sur le déjeuner et le dîner (fromage ≥ 25 g dans le plat ou laitage en dessert) | PNNS : 2 par jour pour un adulte, le petit-déjeuner apportant le second |
| Viande hors volaille | ≤ 500 g/semaine | PNNS |
| Charcuterie | ≤ 150 g/semaine | PNNS |

Les repères hebdomadaires sont **ramenés au nombre de repas pris à la maison** (avec 10
repas sur 14, on vise 1 poisson au lieu de 2, et ≤ 357 g de viande).

Chaque repère est une contrainte **souple** : un écart $e \ge 0$ est autorisé mais pénalisé
par $1000 \times e / \text{cible}$ dans l'objectif. Ce poids, très supérieur aux préférences,
garantit que **la nutrition prime** : le solveur ne sacrifie un repère que s'il est impossible
à atteindre (et l'interface le signale). Les écarts relatifs aux parts d'énergie sont
linéarisés : $100 \cdot \text{kcal}_\text{protéines} - 12 \cdot \text{kcal}_\text{total} \ge 0$.

## 5. Préférences (objectif)

Pour chaque plat ou dessert servi à un créneau, un **intérêt** est ajouté à l'objectif
(maximisé) :

| Critère | Effet par défaut |
|---|---|
| Notes de la famille | + 40 × (moyenne bayésienne des convives − 3) |
| Saisonnalité | − 0,6 par gramme d'ingrédient hors saison |
| Empreinte carbone | − 25 par kg CO₂e (réglable : 0 à 50) |
| Prix | − 3 par € (réglable : 0 à 15) |
| Répétition | − 40, − 20, − 10 si servi il y a 1, 2 ou 3 semaines |
| Restes d'un plat en lot | + 6 par repas sans cuisine (réglable) |
| Placard | + 8 par ingrédient du placard utilisé |
| Joker | + 80 pour un plat ou dessert plaisir sur un joker |
| Temps en semaine | − 0,5 par minute au-delà de 45 min, du lundi au vendredi |
| Hasard | + 0 à 6, déterministe pour une « graine » donnée |

**Moyenne bayésienne** (`domaine/notes.py`) : pour un membre et un plat,
$\bar{n} = (\sum \text{notes} + C \cdot m) / (k + C)$, avec $k$ notes, $m$ la moyenne générale
du membre et $C = 2$. Un plat noté une seule fois 5/5 n'écrase pas un plat noté dix fois 4/5.

**Hasard** : le bouton « Autre proposition » change la graine, ce qui fait émerger une autre
combinaison de qualité équivalente.

## 6. Résolution et alternatives

CP-SAT trouve la solution optimale en 1 à 3 secondes (environ 700 variables binaires pour une
semaine complète ; limite fixée à 10 s).

Pour **remplacer un repas**, tous les autres repas sont figés et le créneau est re-résolu
plusieurs fois en interdisant à chaque fois les plats déjà trouvés : on obtient les 5
meilleurs plats de remplacement, classés par perte de score.

## 7. Nutri-Score d'un repas

Fichier : `domaine/nutriscore.py`. L'algorithme **2023** du Nutri-Score (aliments
généraux) est appliqué, à titre indicatif, au repas plat + dessert ramené à 100 g :

- points négatifs : énergie (0-10), sucres (0-15), acides gras saturés (0-10), sel (0-20) ;
- points positifs : protéines (0-7), fibres (0-5), fruits, légumes et légumineuses (0-5) ;
  les protéines ne comptent pas si les points négatifs atteignent 11 (sauf 5 points de
  fruits et légumes) ;
- classes : A ≤ 0, B 1-2, C 3-10, D 11-18, E ≥ 19.

Le poids du repas tient compte de l'eau absorbée par les féculents et légumes secs
(`rendement_cuisson`, ex. 2,2 pour les pâtes) ; l'eau des soupes n'est pas comptée, ce qui
rend leur score un peu sévère. Le Nutri-Score n'entre pas dans l'optimisation : les repères
nutritionnels, plus complets, la pilotent déjà.

### Couverture des besoins par membre (onglet Bilan)

Fichier : `domaine/references.py`. Pour chaque membre, l'apport moyen d'un repas pris à la
maison (plat + dessert, multiplié par son coefficient de portion) est comparé à 30 % de sa
référence journalière, selon l'âge et le sexe (RNP ou AS de l'EFSA, reprises par l'ANSES) :

| Nutriment | Pourquoi le suivre | Exemples de références journalières |
|---|---|---|
| Calcium | souvent insuffisant chez les adolescents | 800 mg (4-10 ans), 1 150 mg (11-17 ans), 950 mg (adulte) |
| Fer | souvent insuffisant chez les femmes et adolescentes | 11 mg (homme), 16 mg (femme de 18 à 49 ans), 13 mg (fille de 12 à 17 ans) |
| Vitamine C | demandé par la famille | 45 mg (7-10 ans), 110 mg (homme), 95 mg (femme) |
| Fibres | insuffisantes chez la plupart des Français | 14 g (4-6 ans), 30 g (adulte) |
| Folates (B9) | importants pour les femmes en âge d'avoir des enfants | 200 µg (7-10 ans), 330 µg (adulte) |
| Oméga-3 EPA + DHA | apportés presque uniquement par les poissons gras | 250 mg |

L'énergie et les protéines ne sont pas suivies par membre : les portions étant calculées sur
les besoins énergétiques, la couverture énergétique vaut 100 % par construction ; la part
des protéines (10-20 % de l'énergie) est contrôlée au niveau de la famille.

Limites : valeurs des aliments crus (la cuisson réduit la vitamine C et les folates) ; la
vitamine D et l'iode, qui dépendent surtout du soleil et du sel iodé, ne sont pas suivis.

## 8. Liste de courses

Fichier : `domaine/courses.py`.

1. Besoin = Σ (grammes de la recette × somme des coefficients des convives).
2. Le placard est déduit.
3. Division par la **part comestible** (épluchures, noyaux, coquilles).
4. **Arrondi au conditionnement** : recherche exhaustive de la combinaison de formats qui
   couvre le besoin avec le **moins de surplus**, puis le moins d'unités (850 g de pâtes
   → 1 kg ; 9 œufs → une boîte de 12).
5. Le surplus va au placard si l'ingrédient se conserve au moins 7 jours.

## 9. Vérification

Les tests (`backend/tests/test_planificateur.py`) vérifient notamment que :

- tous les repères sont atteints pour une semaine complète en janvier, avril, juillet et octobre ;
- aucun plat ordinaire n'est répété, les restes sont cohérents ;
- les plats plaisir n'apparaissent que sur les jokers ;
- les notes et l'historique changent effectivement les choix ;
- des verrous contradictoires sont signalés.
