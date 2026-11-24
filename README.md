# 🥗 Menu Famille

[![CI](https://github.com/Skitourer/familly_meals_planner/actions/workflows/ci.yml/badge.svg)](https://github.com/Skitourer/familly_meals_planner/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-2f6b40)](https://skitourer.github.io/familly_meals_planner/)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue)](LICENSE)

Planificateur de repas pour la famille : **équilibrés**, **de saison**, **bas carbone**, avec
une **liste de courses adaptée aux paquets du magasin**.

Le vendredi soir, on indique qui mange à la maison à chaque repas de la semaine suivante et
on choisit ses jokers ; l'application compose les 14 repas (plat + dessert) en respectant les
repères de l'ANSES et du PNNS, puis produit la liste de courses imprimable.

## Fonctionnalités

- **Portions individuelles** : besoins énergétiques selon l'âge, le poids, le sexe et
  l'activité physique (équations de Henry).
- **Optimisation sous contraintes** (OR-Tools CP-SAT) : nutrition d'abord, puis goûts de la
  famille, saison, carbone, budget, temps de préparation.
- **Repas modifiables** un par un, avec les meilleures alternatives calculées.
- **Jokers** pour les repas plaisir, **cuisine en lot** (soupes, mijotés servis plusieurs jours).
- **Notes après les repas**, par membre : elles guident les semaines suivantes ; les
  répétitions sont évitées.
- **Liste de courses** par rayon, arrondie aux conditionnements réels (350 g de pâtes →
  paquet de 500 g), **PDF** imprimable, budget estimé.
- **Placard** : les restes de paquets sont suivis et réutilisés.
- **Données ouvertes** : CIQUAL (ANSES), Agribalyse et Impact CO2 (ADEME), Open Food Facts,
  Open Prices.
- **Recettes générées par IA, sans IA dans l'application** : un fichier d'instructions à
  donner à l'IA de son choix, puis un import JSON validé.
- Interface utilisable sur téléphone, **un seul mot de passe** pour la famille.

## Démarrage rapide

Prérequis : [uv](https://docs.astral.sh/uv/) et Node.js ≥ 24.

```bash
# API (http://127.0.0.1:8000, documentation sur /api/docs)
cd backend && uv sync && uv run poe dev

# Interface (http://localhost:5173), dans un second terminal
cd frontend && npm ci && npm run dev
```

Mot de passe par défaut en développement : `famille`. Détails :
[docs/guide/demarrage.md](docs/guide/demarrage.md).

## Organisation du dépôt

```text
backend/     API Python (FastAPI, OR-Tools, SQLite) — projet uv
frontend/    Interface SvelteKit
donnees/     Référentiel d'ingrédients, données ouvertes importées, recettes (YAML)
docs/        Documentation (MkDocs) : guide, algorithme, données, architecture, ADR
.github/     CI, versions automatiques, documentation, données mensuelles, Dependabot
```

## Documentation

- [Utiliser l'application](docs/guide/utilisation.md)
- [Ajouter des recettes avec une IA](docs/guide/recettes-ia.md)
- [Algorithme de planification](docs/technique/algorithme.md)
- [Données ouvertes](docs/technique/donnees-ouvertes.md)
- [Architecture](docs/technique/architecture.md) et [décisions (ADR)](docs/adr/index.md)
- [Déploiement](docs/exploitation/deploiement.md) (Raspberry Pi ou VPS)
- [Contribuer](docs/contribuer.md)

## Licences

Code sous licence [MIT](LICENSE). Données : CIQUAL, Agribalyse et Impact CO2 sous licence
ouverte Etalab 2.0 ; données dérivées d'Open Food Facts et d'Open Prices sous ODbL. Police
DejaVu (PDF) sous licence libre Bitstream Vera.

Projet développé avec l'aide de [Claude Code](https://claude.com/claude-code) : les
consignes suivies par l'agent sont dans [AGENTS.md](AGENTS.md).

La première maquette TypeScript est archivée sous le tag `v0-maquette`.
