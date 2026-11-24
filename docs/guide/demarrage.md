# Démarrer

## Prérequis

- [uv](https://docs.astral.sh/uv/) (gère Python 3.13 et l'environnement virtuel du backend) ;
- [Node.js](https://nodejs.org/) 24 ou plus (pour l'interface).

## Installation pour le développement

```bash
git clone https://github.com/Skitourer/familly_meals_planner.git
cd familly_meals_planner

# Backend : uv crée l'environnement virtuel backend/.venv et installe tout
cd backend
uv sync

# Interface
cd ../frontend
npm ci
```

## Lancer l'application

Dans deux terminaux :

```bash
# Terminal 1 : API sur http://127.0.0.1:8000 (documentation : /api/docs)
cd backend
uv run poe dev

# Terminal 2 : interface sur http://localhost:5173 (les appels /api sont relayés)
cd frontend
npm run dev
```

Si le port 8000 est déjà utilisé : `uv run poe dev --port 8010` puis
`REPAS_API=http://127.0.0.1:8010 npm run dev`.

Ouvrez <http://localhost:5173>. Mot de passe par défaut en développement : `famille`
(variable `REPAS_MOT_DE_PASSE`, voir `.env.example`).

!!! tip "Premier lancement"
    1. Onglet **Famille** : ajoutez chaque membre (date de naissance, poids, sexe, activité).
    2. Onglet **Semaine** : ajustez les présences, puis **Générer les repas**.

## Tâches courantes (backend)

| Commande | Rôle |
|---|---|
| `uv run poe dev` | API avec rechargement automatique (`--port 8010` pour changer de port) |
| `uv run poe check` | Tout vérifier comme la CI (style, types, tests) |
| `uv run poe format` | Corriger le style automatiquement |
| `uv run poe test` | Tests avec couverture |
| `uv run repas-import` | Mettre à jour les données ouvertes ([détails](../technique/donnees-ouvertes.md)) |
| `uv run python -m repas.catalogue.import_recettes` | Régénérer le fichier d'instructions pour IA |

## Tâches courantes (interface)

| Commande | Rôle |
|---|---|
| `npm run dev` | Serveur de développement |
| `npm run check` | Vérification des types |
| `npm run lint` / `npm run format` | Style (Prettier) |
| `npm test` | Tests (Vitest) |
| `npm run build` | Compilation dans `frontend/build/` |

## Tester comme en production

```bash
cd frontend && npm run build
cd ../backend
REPAS_DOSSIER_INTERFACE=../frontend/build uv run repas
```

L'application complète est alors servie sur <http://127.0.0.1:8000>.
