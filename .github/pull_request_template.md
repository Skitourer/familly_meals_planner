## Objet

<!-- Que change cette PR, et pourquoi ? Lier l'issue : « Closes #12 » (GitHub ne reconnaît pas « Ferme »). -->

## Vérifications

- [ ] Le titre suit les [Conventional Commits](https://www.conventionalcommits.org/fr/) (`feat:`, `fix:`, `docs:`, `chore:`…)
- [ ] `uv run poe check` passe dans `backend/`
- [ ] `npm run lint && npm run check && npm test` passent dans `frontend/`
- [ ] Documentation mise à jour si le comportement change (`docs/`)
- [ ] Si le référentiel d'ingrédients a changé : `uv run repas-import` et `uv run python -m repas.catalogue.import_recettes` relancés
