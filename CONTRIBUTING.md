# Contribuer

Merci de votre intérêt ! Le processus (branches, Conventional Commits, CI, versions) est
décrit dans la documentation : [docs/contribuer.md](docs/contribuer.md).

En bref :

```bash
git switch -c feat/ma-fonctionnalite
cd backend && uv run poe check          # style, types, tests
cd ../frontend && npm run lint && npm run check && npm test
```

Puis ouvrez une pull request dont le titre suit les Conventional Commits (`feat: …`, `fix: …`).
