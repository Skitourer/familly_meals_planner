# 1. Python (FastAPI) et SvelteKit

*Date : 2026-11-24 — Statut : acceptée (remplace la maquette TypeScript, tag `v0-maquette`)*

## Contexte

L'application combine du **traitement de données** (bases nutritionnelles, carbone, prix), de
l'**optimisation** (choix des repas) et une **interface mobile** simple. Le code doit rester
lisible par un humain non spécialiste.

## Décision

- **Backend en Python 3.13** avec FastAPI, Pydantic/SQLModel et SQLite, géré par **uv**
  (environnement virtuel, verrouillage des versions).
- **Interface en SvelteKit** (Svelte 5), compilée en application statique servie par FastAPI.

## Conséquences

- Python offre le meilleur écosystème pour les données et l'optimisation (OR-Tools,
  openpyxl, httpx) et se lit facilement.
- Svelte produit des composants courts, proches du HTML, faciles à relire.
- Deux langages à maintenir, mais chacun dans son domaine ; une seule image Docker en sortie.
