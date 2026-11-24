# 6. Liste de courses hors ligne avec un service worker écrit à la main

*Date : 2026-11-24 — Statut : acceptée*

## Contexte

Au magasin, le réseau manque souvent. Les coches attendent déjà sur l'appareil (PR #34),
mais sans réseau la page elle-même ne s'ouvre pas.

## Décision

- Un **service worker SvelteKit** (`frontend/src/service-worker/`), sans bibliothèque :
  fichiers de l'application en cache par version, navigations « réseau puis page gardée ».
- Seules **la session et la liste de courses** sont gardées (réseau d'abord, cache sans
  réseau). Le reste de l'API demande le réseau.
- Les règles sont dans un module pur testé (`lib/hors-ligne.ts`).
- Le cache de données est **vidé à la déconnexion** et quand la session est fermée.

## Conséquences

- Aucune dépendance ; environ 100 lignes à maintenir.
- Peu de données familiales restent sur le téléphone, et seulement pendant la session.
- Une nouvelle version s'applique quand l'application a été complètement fermée.
- HTTPS obligatoire (Tailscale le fournit).

## Alternatives écartées

- **vite-plugin-pwa / Workbox** : dépendance lourde pour deux règles de cache.
- **Tout garder en cache** (menu, bilan, placard) : plus de données personnelles sur
  l'appareil, sans besoin réel hors ligne.
