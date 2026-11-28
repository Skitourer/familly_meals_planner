# API

La documentation interactive (OpenAPI) est servie par l'application sur **`/api/docs`**.
Toutes les routes, sauf `/api/session` et `/api/sante`, exigent d'être connecté. Un compte
enfant n'a accès qu'à la lecture du menu (`GET /api/semaines/{lundi}`, `menu.pdf`), des
membres et des plats, et aux avis ; les autres routes répondent 403.

Les requêtes `POST`, `PUT`, `PATCH` et `DELETE` doivent porter l'en-tête
`X-Menu-Famille: 1` (protection CSRF, 403 sinon) et un corps de 3 Mo au plus (413 sinon).

| Méthode | Route | Rôle |
|---|---|---|
| `GET` / `POST` / `DELETE` | `/api/session` | État, connexion (`{"identifiant": "...", "mot_de_passe": "..."}`), déconnexion |
| `PUT` | `/api/session/mot-de-passe` | Changer son mot de passe |
| `GET` / `POST` | `/api/comptes` | Lister, créer un compte (adulte) |
| `PUT` / `DELETE` | `/api/comptes/{id}` | Modifier, supprimer un compte (adulte) |
| `GET` | `/api/sante` | Santé et version |
| `GET` / `POST` | `/api/membres` | Lister, ajouter un membre (actif : ajouté aux repas à venir des semaines déjà créées) |
| `PUT` / `DELETE` | `/api/membres/{id}` | Modifier (de retour à la maison : ajouté aux repas à venir) ; supprimer définitivement (avec ses notes) |
| `GET` / `PUT` | `/api/reglages` | Réglages de l'algorithme |
| `GET` | `/api/recettes` | Catalogue avec profils (nutrition, CO₂, prix, saison, notes) |
| `DELETE` | `/api/recettes/{id}` | Supprimer une recette importée |
| `GET` | `/api/ingredients` | Référentiel d'ingrédients |
| `GET` | `/api/sources` | Attribution des données ouvertes |
| `GET` | `/api/import/instructions-ia.md` | Fichier d'instructions pour IA |
| `POST` | `/api/import/recettes?appliquer=` | Vérifier (puis importer) un fichier JSON |
| `GET` | `/api/semaines/{lundi}` | Semaine (créée si besoin avec toute la famille) |
| `PUT` | `/api/semaines/{lundi}/creneaux/{jour}/{moment}` | Présences, invités, joker, verrou, plat ou dessert |
| `POST` | `/api/semaines/{lundi}/generer?varier=&a_partir_du_jour=` | Générer (ou proposer une autre combinaison) ; `a_partir_du_jour` (0 à 6) garde les jours précédents |
| `GET` | `/api/semaines/{lundi}/creneaux/{jour}/{moment}/alternatives` | Meilleurs plats de remplacement |
| `GET` | `/api/semaines/{lundi}/bilan` | Bilan nutritionnel et carbone |
| `GET` | `/api/semaines/{lundi}/courses` | Liste de courses |
| `GET` | `/api/semaines/{lundi}/courses/coches` | Articles cochés (relus toutes les 5 s par la liste affichée) |
| `PUT` | `/api/semaines/{lundi}/courses/coches` | Envoyer des coches (liste de `{ingredient_id, cochee, modifiee_le}`, 500 au plus ; un produit à racheter a pour clé `racheter-{id}`, un article libre `libre-{id}` ; la coche d'un tel article retiré entre-temps est ignorée) ; la plus récente gagne ; renvoie les articles cochés |
| `POST` | `/api/semaines/{lundi}/courses/achats` | Produit acheté (`{ingredient_id, quantite_g, prix_eur, code?}`), prévu sur la liste ou non (hors liste : au placard à la validation) ; s'ajoute aux précédents |
| `DELETE` | `/api/semaines/{lundi}/courses/achats/{ingredient}` | Oublier les achats d'un article |
| `POST` | `/api/semaines/{lundi}/courses/autres-achats` | Autre produit acheté (fiche, `prix_eur`, `ranger`) : budget, et placard à la validation si `ranger` |
| `DELETE` | `/api/semaines/{lundi}/courses/autres-achats/{id}` | Retirer un autre produit acheté |
| `POST` | `/api/semaines/{lundi}/courses/a-racheter` | Remettre sur la liste un autre produit fini au placard (fiche) ; une seule fois par produit |
| `DELETE` | `/api/semaines/{lundi}/courses/a-racheter/{id}` | Retirer un produit à racheter de la liste (et sa coche) |
| `POST` | `/api/semaines/{lundi}/courses/ingredients-a-racheter` | Ajouter à la liste le plus petit conditionnement d'un ingrédient (`{ingredient_id}`), en plus des repas ; la ligne porte `a_racheter` |
| `DELETE` | `/api/semaines/{lundi}/courses/ingredients-a-racheter/{ingredient_id}` | Renoncer à cet achat en plus |
| `POST` | `/api/semaines/{lundi}/courses/articles` | Ajouter un article libre, hors repas et hors placard (`{libelle, quantite?}`) ; un même libellé une seule fois |
| `PUT` | `/api/semaines/{lundi}/courses/articles/{id}` | Prix payé d'un article libre (`{prix_eur}`, `null` pour l'effacer) ; hors coût des repas du bilan |
| `DELETE` | `/api/semaines/{lundi}/courses/articles/{id}` | Retirer un article libre (et sa coche) |
| `POST` | `/api/semaines/{lundi}/courses/articles/reporter` | Déplacer les articles libres non cochés sur la semaine suivante ; renvoie `{reportes}` ; permis après validation |
| `POST` | `/api/semaines/{lundi}/courses/valider` | Courses faites : mise à jour du placard ; corps facultatif `{tout_achete}` (faux : les articles ni cochés ni scannés n'ont pas été achetés) |
| `POST` | `/api/semaines/{lundi}/courses/rouvrir` | Défaire la validation (placard et budget) |
| `GET` | `/api/semaines/{lundi}/courses.pdf`, `/menu.pdf` | Documents imprimables |
| `GET` | `/api/bilan?semaines=12` | Bilan sur plusieurs semaines (onglet Bilan) |
| `GET` | `/api/notes/a-noter?jours=14&jours_a_venir=7` | Repas récents et à venir, notes déjà données |
| `PUT` | `/api/notes` | Noter un plat (crée ou met à jour ; un enfant pour lui-même) |
| `GET` | `/api/placard` | Contenu du placard, avec le rayon de chaque ingrédient (`rayon`, `rang_rayon` : ordre de la liste de courses) |
| `GET` | `/api/placard/idees` | Plats qui consomment le mieux les produits à vider |
| `PUT` | `/api/placard/{ingredient}` | Corriger une quantité ou une date limite (0 = retirer) |
| `GET` | `/api/placard/produits` | Autres produits du placard (hors repas, en paquets) |
| `POST` | `/api/placard/produits` | Ranger des paquets d'un autre produit (même code-barres ou même nom : additionnés) |
| `PUT` | `/api/placard/produits/{id}` | Corriger paquets (0 = retirer), date limite ou catégorie |
| `POST` | `/api/placard/modification` | Corriger un article en une transaction : source `ingredient_id` ou `produit_id`, `cible` ingrédient (`{type: "ingredient", ingredient_id, quantite_g, peremption?}`) ou autre produit (`{type: "produit", nom, categorie, paquets, peremption?}`) ; changer d'ingrédient ou de type regroupe avec le même article déjà au placard, les notes suivent |
| `GET` | `/api/produits/categories` | Catégories des autres produits |
| `GET` | `/api/produits/{code}` | Produit scanné (Open Food Facts), ingrédients correspondants et dernier prix payé |

`{lundi}` est une date `AAAA-MM-JJ` qui doit tomber un lundi ; `{jour}` va de 0 (lundi) à 6 ;
`{moment}` vaut `midi` ou `soir`.
