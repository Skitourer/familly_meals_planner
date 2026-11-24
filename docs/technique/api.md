# API

La documentation interactive (OpenAPI) est servie par l'application sur **`/api/docs`**.
Toutes les routes, sauf `/api/session` et `/api/sante`, exigent d'être connecté.

| Méthode | Route | Rôle |
|---|---|---|
| `GET` / `POST` / `DELETE` | `/api/session` | État, connexion (`{"mot_de_passe": "..."}`), déconnexion |
| `GET` | `/api/sante` | Santé et version |
| `GET` / `POST` | `/api/membres` | Lister, ajouter un membre |
| `PUT` / `DELETE` | `/api/membres/{id}` | Modifier, désactiver |
| `GET` / `PUT` | `/api/reglages` | Réglages de l'algorithme |
| `GET` | `/api/recettes` | Catalogue avec profils (nutrition, CO₂, prix, saison, notes) |
| `DELETE` | `/api/recettes/{id}` | Supprimer une recette importée |
| `GET` | `/api/ingredients` | Référentiel d'ingrédients |
| `GET` | `/api/sources` | Attribution des données ouvertes |
| `GET` | `/api/import/instructions-ia.md` | Fichier d'instructions pour IA |
| `POST` | `/api/import/recettes?appliquer=` | Vérifier (puis importer) un fichier JSON |
| `GET` | `/api/semaines/{lundi}` | Semaine (créée si besoin avec toute la famille) |
| `PUT` | `/api/semaines/{lundi}/creneaux/{jour}/{moment}` | Présences, invités, joker, verrou, plat ou dessert |
| `POST` | `/api/semaines/{lundi}/generer?varier=` | Générer (ou proposer une autre combinaison) |
| `GET` | `/api/semaines/{lundi}/creneaux/{jour}/{moment}/alternatives` | Meilleurs plats de remplacement |
| `GET` | `/api/semaines/{lundi}/bilan` | Bilan nutritionnel et carbone |
| `GET` | `/api/semaines/{lundi}/courses` | Liste de courses |
| `POST` | `/api/semaines/{lundi}/courses/valider` | Courses faites : mise à jour du placard |
| `GET` | `/api/semaines/{lundi}/courses.pdf`, `/menu.pdf` | Documents imprimables |
| `GET` | `/api/notes/a-noter?jours=14` | Repas récents et notes déjà données |
| `PUT` | `/api/notes` | Noter un plat (crée ou met à jour) |
| `GET` | `/api/placard` | Contenu du placard |
| `PUT` | `/api/placard/{ingredient}` | Corriger une quantité (0 = retirer) |

`{lundi}` est une date `AAAA-MM-JJ` qui doit tomber un lundi ; `{jour}` va de 0 (lundi) à 6 ;
`{moment}` vaut `midi` ou `soir`.
