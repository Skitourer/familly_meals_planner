# 🥗 Menu Famille

Application de planification des repas pour la famille : chaque vendredi, on définit
les repas de la semaine à venir (midi et soir), le nombre de personnes présentes,
et l'application calcule une liste de courses adaptée aux besoins de chacun.
La liste de courses s'exporte en PDF pour l'emporter au magasin.

**Aucune IA à l'exécution** : la génération des repas est un algorithme explicable
(saisonnalité, variété, adéquation aux besoins, notes passées).

## Fonctionnalités

- **Profils familiaux** : âge, taille, poids, sexe et activité de chaque membre ;
  besoin énergétique calculé (formule Mifflin-St Jeor).
- **Planning hebdomadaire** : midi/soir sur 7 jours, nombre de convives par repas,
  `0 convive` = repas hors maison (exclu de la liste de courses).
- **Génération algorithmique** : plats de saison, pas de catégorie répétée,
  couverture du besoin familial, pondérés par les notes passées.
- **Liste de courses** : agrégation des ingrédients, arrondie aux conditionnements
  du magasin (ex. 800 g de pâtes -> 1 kg), **export PDF** en un clic.
- **Notes a posteriori** : 1 à 5 étoiles par plat, moyennes cumulées ("favoris").
- **Open Food Facts** : recherche de produits pour pré-remplir les ingrédients.
- **PWA** : installable sur téléphone, tablette et ordinateur ; consultable hors
  ligne au supermarché.
- **Accès protégé** : un mot de passe partagé pour la famille (cookie de session).

## Architecture

```
menu-famille/
├── shared/              # Cœur métier pur (testé unitairement, sans dépendance)
│   ├── types.ts         # Membres, plats, repas
│   ├── besoins.ts       # Besoins énergétiques (Mifflin-St Jeor)
│   ├── generation.ts    # Algorithme de planification
│   ├── courses.ts       # Liste de courses + arrondi magasin
│   ├── saison.ts        # Fruits et légumes de saison (France)
│   ├── dates.ts         # Semaines ISO (lundi -> dimanche)
│   └── tests/           # Tests unitaires (node:test)
├── server/              # API Fastify + SQLite (better-sqlite3)
│   └── src/
│       ├── index.ts     # Point d'entrée
│       ├── db.ts        # Base + schéma + données initiales
│       ├── auth.ts      # Mot de passe partagé, cookie de session signé
│       ├── pdf.ts       # Générateur PDF minimal (sans dépendance)
│       └── routes.ts    # Routes REST (membres, plats, semaines, courses, notes)
└── web/                 # Interface React + Vite (PWA)
    └── src/
        ├── api.ts       # Client HTTP typé
        ├── App.tsx      # Navigation par onglets
        └── pages/       # Planning, Courses, Famille, Plats, Notes
```

## Démarrage (développement)

Prérequis : **Node.js 22 ou plus**.

```bash
npm install                 # installe les dépendances des workspaces
npm run dev:server          # API sur http://localhost:3000
npm run dev:web             # interface sur http://localhost:5173 (proxy /api)
```

La base SQLite se crée au premier lancement avec dix plats de démonstration,
et le mot de passe par défaut est **« menu-famille »**
(à changer dès la première connexion via `PUT /api/session/mot-de-passe`).

## Tests

```bash
npm test
```

Exécute les tests du cœur métier (besoins, génération, liste de courses, dates)
et du générateur PDF (structure, table xref, accents Latin-1, pagination).

## Export PDF de la liste de courses

Le bouton « 📄 Exporter en PDF » de la page Courses appelle
`GET /api/semaines/{id}/courses.pdf`. Le serveur construit le PDF avec un
générateur maison (aucune dépendance, ~150 lignes commentées) : liste des
articles avec « besoin -> quantité à acheter », pagination automatique.
Le fichier se télécharge (`courses-2026-11-23.pdf`).

## Mise en production (exemple self-hosting)

```bash
npm run build              # build Vite -> web/dist
npm start -w server        # API en production directe
```

Configure un reverse proxy (Caddy, Nginx) qui sert le dossier statique `web/dist/`
et transmet `/api/*` au port 3000 (avec HTTPS, ce qui active aussi l'installation
PWA sur mobile). La base est un simple fichier SQLite : sauvegarde = copie du
fichier `donnees/menu.db`.

## Source des données

- **Ingrédients et quantités du catalogue initial** : ce sont des *estimations de
  portions* (ordres de grandeur), pas des recettes copiées d'un site. Elles servent
  uniquement à calculer la liste de courses. À affiner plat par plat dans l'onglet
  **Plats**, où l'on renseigne aussi son propre lien de recette.
- **Liens de recette par défaut** : recherche Marmiton par nom du plat (plusieurs
  recettes proposées) — à remplacer par la recette familiale.
- **Besoins énergétiques** : formule de Mifflin-St Jeor (référence scientifique).
- **Saisonnalité** : fruits et légumes de saison usuels pour la France.

## Paramétrage accessible

- Conditionnements magasin : table `emballages` (modifiable via la base ou une
  future interface d'administration).
- Plats, membres, notes : tout est éditable dans l'interface.
