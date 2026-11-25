# Agent instructions

Single source of truth for every coding agent (Claude Code, Codex, Copilot…); `CLAUDE.md`
only contains `@AGENTS.md`. Copy of the general template (`agent-conventions`); the last
two sections are specific to this project. Written in English to save tokens; talk to
the user in French.

## 1. Language

- Code, comments, docstrings, file names, commits, PRs/MRs, issues: English.
- Docs are bilingual: English is the source, French a mirror translation updated in the
  same PR (same structure and headings).
- Chat with the user: French, concise, conclusion first, no recap of what is already
  known; explain the technical "why" only when it helps a decision.
- Each project keeps a glossary (Project specifics); use its terms everywhere, no synonyms.

## 2. Code conventions

Tools enforce style; this file only holds what tools cannot check. Every repo has
`.editorconfig`, pre-commit hooks, and CI running the same checks.

| Language | Format | Analysis | Tests | Notes |
|---|---|---|---|---|
| Python | ruff format | ruff, pyright strict | pytest | type hints everywhere; uv only (no pip, no global env) |
| TypeScript / Svelte | prettier | TS `strict`, svelte-check | vitest | no ESLint unless needed |
| C / C++ | clang-format | clang-tidy; `-Wall -Wextra` as errors in CI | GoogleTest + CTest | CMake; sanitizers (address, undefined) in tests |
| Shell | shfmt | shellcheck | bats | `#!/usr/bin/env bash`, `set -euo pipefail`; beyond ~100 lines, use Python |
| PHP | PHP-CS-Fixer (PER-CS) | PHPStan | PHPUnit | `declare(strict_types=1);`, Composer |
| End-to-end | | | Playwright | |

**Unlisted language**: before writing the first file, propose the community-standard
formatter, linter, dependency manager and test framework; once approved, add a row here
(in the project and in this template).

- Readable without context: explicit names, no abbreviations except universal ones
  (`id`, `url`).
- Small single-purpose functions; ~40 lines is a cue to split, not a hard limit.
- Comments explain **why** (business rule, source, workaround), never what. Numeric rules
  cite their source.
- Docstring for modules and public functions (one sentence is enough).
- No dead or commented-out code: git remembers.
- Business logic is pure (no DB, network or files) in its own module; it gets the most
  tests.
- Configuration through environment variables (12-factor), each documented in
  `.env.example`.
- Simple first: no abstraction before two real uses. Every new dependency is justified
  (maintenance, licence, weight); prefer the standard library.
- Fail early: validate inputs at boundaries; never swallow errors (no bare `except`).

## 3. Repository

Rules apply to GitHub and GitLab ("PR" also means MR).

- GitHub Flow: `main` is always releasable and protected. Short branches named
  `<type>/<short-description>`. One PR = one topic; it references its issue
  (`Closes #12`) and states why, what was verified, and what a human must test.
- Squash merge; the PR title becomes the commit message.
- Conventional Commits: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`,
  `chore`; `!` or `BREAKING CHANGE:` for breaking changes.
- Issues: clear title and acceptance criteria. Use existing labels; never create labels
  without approval.
- Standard files: README, LICENSE, CONTRIBUTING, SECURITY, CHANGELOG (generated),
  `.gitignore`, `.editorconfig`, `.gitattributes`, `.env.example`, short issue and PR/MR
  templates.
- Licence: always ask the user, never pick a default.
- Never commit secrets, `.env` files or personal data.

| | GitHub | GitLab |
|---|---|---|
| CI | Actions | GitLab CI |
| Dependency updates | Dependabot | Renovate |
| Releases and CHANGELOG | release-please | semantic-release or release-please CLI |
| Static security analysis | CodeQL | SAST template (Semgrep) |

### Repository settings

Propose them when a repository is created, apply them once approved:

- Squash merge only, PR title as message; delete branch after merge.
- Protected `main`: required CI checks, linear history, no force push, no deletion.
- Secret scanning and push protection; dependency alerts and security updates;
  CodeQL (GitHub) or SAST (GitLab).
- Private vulnerability reporting on (SECURITY.md points to it).
- CI tokens read-only by default; CI cannot approve PRs.
- Unused features off (wiki, projects…).
- GitLab: protected branches, "Pipelines must succeed", squash required, delete source
  branch.

## 4. Confidentiality

- Before the first commit of a repo, **ask whether it is personal or professional**.
  Never infer it from the folder or the forge.
- Personal: repo-local git identity, never the global one:
  `git config user.name "Skitourer"` and
  `git config user.email "149181038+Skitourer@users.noreply.github.com"`; check with
  `git config --show-origin user.email`.
- Professional: keep the machine's professional identity.
- Personal projects: no professional login, email or machine name in commits, PRs,
  issues, code, docs, screenshots or published logs. No absolute local paths
  (`C:\Users\…`) in committed files, ever.
- Tests, examples and docs use fictitious data only.
- Secrets live only in `.env` (git-ignored) and forge secrets; never printed in logs or CI.
- Secret detection in every repo: gitleaks as a pre-commit hook and in CI (full history,
  `fetch-depth: 0`); on GitHub also secret scanning and push protection.
- A committed secret is revoked immediately; rewriting history is not enough.
- No professional code or data in personal projects, and vice versa. No project data sent
  to external services (online converters, pastebins, third-party APIs) without approval.
- Professional restrictions: none yet. List here the repos, code or data agents must not
  process.
- AI use: agent commits keep the `Co-Authored-By: Claude …` trailer; the README states
  the project is developed with Claude's help.

## 5. Security

Based on OWASP Top 10 and ASVS level 1; applies to anything reachable over a network.

- Inputs: validated at boundaries with schemas (pydantic, zod…); parameterised queries or
  ORM; never build shell commands from user data.
- Outputs: rely on framework escaping (no `{@html}` or `innerHTML` with user data); errors
  returned to clients carry no stack trace or internals.
- Accounts: argon2 or scrypt hashing; rate-limited login; cookies `HttpOnly`, `Secure`,
  `SameSite`; CSRF protection; authorisation checked server-side on every route, never
  only in the UI.
- **Two-factor authentication: whenever a project manages accounts, ask the user whether
  to support 2FA (TOTP, passkeys). The user decides.**
- Web: HTTPS only; security headers (CSP, HSTS, `X-Content-Type-Options`,
  `frame-ancestors`); restrictive CORS; request and upload size limits.
- Least privilege: containers run as non-root on minimal images; CI tokens read-only by
  default; service accounts narrowly scoped.
- Logs: no passwords, tokens or personal data.
- CI: dependency audit (pip-audit, npm audit) and static security analysis (ruff `S`
  rules, CodeQL or Semgrep).
- C / C++: sanitizers in tests; no unbounded functions (`strcpy`, `sprintf`, `gets`).
- Before releasing a network-facing feature, the agent runs a security review of the diff.

## 6. Quality and tests

- New or changed business rule → unit tests. Bug fix → first a failing test that
  reproduces it.
- API or CLI → integration tests (temporary database, no network).
- End-to-end tests (Playwright) only for apps whose UI is used by others than the
  developer: a few critical paths.
- Tests are fast (under a minute in total) and deterministic: no network, fixed dates and
  seeds, fictitious data.
- Coverage is a CI floor (**80 % by default**), not a goal.
- Before saying "done": run the same checks as CI and report real results, failures
  included; check UI changes in a real browser (screenshot); review the own diff; the PR
  lists what a human must test.
- Automated dependency updates, grouped weekly; security alerts and fixes on.

## 7. Documentation

- Updated in the same PR as the code it describes.
- Light Diátaxis: Guide (install, use) · Technical (architecture, algorithms, API, data) ·
  Operations (deploy, backup, upgrade) · Contributing · Decisions (ADR).
- The agent writes an ADR for every structural choice (major dependency, architecture,
  data format): context, decision, consequences, rejected alternatives, ~10 lines.
- Diagrams in Mermaid. API references are generated (OpenAPI, docstrings), never copied
  by hand; for a new project, ask whether to generate one from docstrings (mkdocstrings).
- MkDocs Material, strict build in CI, published on GitHub or GitLab Pages. Bilingual
  with mkdocs-static-i18n (`page.md` English, `page.fr.md` mirror). C / C++: Doxygen for
  the API reference.
- README: what and for whom, a screenshot, quick start in ≤ 5 commands, links to the
  docs, licence, "developed with the help of Claude".

## 8. Environment

- Windows 11 with Git Bash and PowerShell. Documented commands work on Windows and Linux;
  tooling in Python rather than shell beyond a few lines.
- `.gitattributes` with `* text=auto eol=lf`. Pinned tool versions (`.python-version`,
  `engines` in `package.json`, compiler in CMake).
- Task runners: poe (Python), npm scripts, CMake presets. No Makefile.
- Docker and dev containers are optional.
- At the end of each coding session, restart the app's local servers and give the URLs.
  Check that a port is free first; never kill a process the agent did not start.
- Scratch files, one-off scripts, screenshots and downloads go to the session's temporary
  directory, never into the repo.

### Ask at the start of a new project

Personal or professional · Linux environments to use (access, what is allowed) ·
professional network (proxy, corporate certificates, internal mirrors) · licence ·
generated API reference · deliverables · 2FA if there are accounts · repository settings.
Record the answers in Project specifics.

## 9. Agent autonomy

**Without asking**: read, search, run tests, linters and local servers; edit code on a
work branch and commit locally; install already-declared dependencies (`uv sync`,
`npm ci`).

**Propose, then wait for approval.** The user will not think to ask: the agent proposes
at the right time ("the branch is ready, shall I push and open the PR?"), then acts once
approved. An approval covers the proposed action only.

- Push a branch, open a PR or MR; merge it.
- Create an issue.
- Add, remove or major-upgrade a dependency.
- Make a structural choice (with an ADR).
- Change CI, workflows or quality tools.
- Delete files or data the agent did not create.
- Extend the scope: extra ideas are proposed separately, never slipped into the PR.
- Sensitive actions, proposed with their consequences and what is irreversible: release,
  tag, direct push to `main`, force push, history rewrite, deleting remote branches, repo
  settings, branch protection, secrets, production or remote servers, writing outside the
  project repo (other repos, external issues, online services).

**Way of working**

- For a decision that belongs to the user, give an argued recommendation, not a neutral
  list of options.
- When blocked (permission denied, missing tool), explain and ask; never work around it.
- End of session: what was done, what was verified, what remains to test or decide.

**Token economy, without losing quality**

- Instruction files stay short and factual; nothing a tool already enforces.
- Read targeted excerpts (search, line ranges) rather than whole files; do not re-read a
  file just edited.
- Filter long outputs (logs, CI) before reading them.
- Subagents only for truly parallel or large work.
- Do not repeat what is already established in the conversation.
- Never cut verification (tests, CI, screenshots) to save tokens.

## 10. Releases and deployment

- SemVer derived from Conventional Commits (`fix` → patch, `feat` → minor, breaking →
  major). release-please (GitHub) or semantic-release (GitLab) maintains a release PR and
  the CHANGELOG; merging it publishes the release.
- The release bot uses a dedicated identity (GitHub App, GitLab project token), never the
  user's account.
- Deliverables: an app is a Docker image on the forge registry, tagged with the version
  and `latest`, multi-arch if needed; a library goes to PyPI or npm (or an internal
  mirror); anything else is defined with the user.
- Deployment documented step by step: install, upgrade, backup, restore, rollback.
  Configuration through environment variables, one `.env` per environment, never
  versioned. Automated backups; restore tested at least once. Internet exposure only
  behind HTTPS.

## Project exceptions

- **Everything is in French** (French-only project, existing code kept): code
  identifiers (no accents: `creneau`, not `créneau`), comments, docs (no English
  version), commits, PRs, issues. Only tool keywords stay English (`feat:`, `fix:`…).
  This instruction file is in English to save tokens.
- Coverage floor **90 %** in CI (95 % actual).
- Pyright in **standard** mode, not strict: switching would cost more than it brings on
  existing code.

## Project specifics

### Overview

Menu Famille: family meal planner (nutritional needs, seasons, carbon footprint,
shopping list). Backend Python (FastAPI, SQLModel, OR-Tools), frontend SvelteKit
(Svelte 5 runes). Open data: CIQUAL, Agribalyse, Open Food Facts, Open Prices. No AI
call at runtime. Full docs in `docs/` (MkDocs), especially `docs/contribuer.md`.
Personal project, MIT licence, accounts with adult and child roles.

### Repository

- GitHub `Skitourer/familly_meals_planner`; docs on GitHub Pages; no docstring-generated
  reference (the maintainer is the only technical reader).
- Labels: `bug`, `amelioration`, `documentation`, `recette`, `donnees`, `dependances`.
- Release PRs are opened by release-please through a GitHub App (variable
  `RELEASE_APP_ID`, secret `RELEASE_APP_PRIVATE_KEY`).
- Images: `ghcr.io/skitourer/familly_meals_planner` (amd64, arm64).
- Hosting: **Raspberry Pi at home, HTTPS through Tailscale**; keep everything portable to a
  VPS later (same multi-arch image, data = SQLite volume + `.env`). Manual upgrade after
  each release: `docker compose pull && docker compose up -d`.

### Code layout

- Pure business logic: `backend/src/repas/domaine/` (needs, guidelines, planner,
  shopping, report, Nutri-Score).
- API: `backend/src/repas/api/`; database models: `modeles.py`.
- Frontend: `frontend/src/lib/` (API client, shared state, components),
  `frontend/src/routes/` (pages). Internal imports via `#lib/…` with explicit `.ts`.

### Commands

```bash
cd backend && uv sync && uv run poe check   # style + types + tests, as CI
uv run poe format                           # fix style
cd frontend && npm ci && npm run lint && npm run check && npm test
```

### Local environment

- Windows only, no Linux environment.
- Servers to restart at the end of each session:
  - API on port **8010** (8000 is used by another tool), **without `--reload`** (it hangs
    on Windows): `cd backend && uv run uvicorn repas.application:creer_application --factory --port 8010`;
  - UI on port **5173**:
    `cd frontend && REPAS_API=http://127.0.0.1:8010 npm run dev -- --port 5173 --strictPort`.
- Local login: `famille`, password from `.env`.

### Glossary

Use these French terms as is in the UI, code and docs.

| Term | Meaning | Not to be confused with |
|---|---|---|
| **Plat** | What is eaten (catalogue entry, `donnees/recettes/*.yaml`); the menu is "Plats". | Recette |
| **Recette** | The link to how to cook a plat (`lien` field, mandatory). | Plat |
| **Dessert** | Plat served at the end of a meal, chosen in addition to the main plat. | |
| **Catalogue** | All hand-picked plats, plus those imported as JSON. | Database |
| **Ingrédient** | Reference food (`ingredients.yaml`), linked to CIQUAL and Agribalyse. | Produit (item bought) |
| **Membre** | Family member with age, weight, sex and activity. | Compte |
| **Compte** | Login, adult or child, optionally linked to a membre. | Membre |
| **Semaine** | Planned period, Monday to Sunday. | |
| **Créneau** | One meal of a semaine: a day and a moment (midi or soir). | Repas (generic word) |
| **Convives** | Membres present at a créneau; **invités** are added as a count. | Présences (UI action name) |
| **Joker** | "Treat" créneau: plaisir plats allowed, nutritional guidelines not applied. | |
| **Plat en lot** | Plat cooked once and served on several créneaux (soups, stews). | |
| **Restes** | Créneau served with a plat en lot cooked earlier (`restes_de`). | Placard |
| **Verrouillé** | Manual choice, kept when regenerating. | |
| **Repas à l'extérieur** | Créneau eaten outside (school canteen…), assumed balanced. | Absence |
| **Coefficient de portion** | Membre's energy need ÷ 2,000 kcal; multiplies the reference portion. | |
| **Placard** | Ingredient stock left at home after shopping. | Restes |
| **Autre produit** | Placard item not used by meals (Nutella, cereals), counted in paquets. | Ingrédient |
| **Avis** / **note** | The "Avis" menu; a 1–5 star rating given by a membre to a plat. | |
| **Bilan** | Statistics over a period (nutrition, carbon, budget, variety). | |
| **Repères** | Per-meal nutritional guidelines (ANSES, PNNS). | Références (EFSA intakes per membre) |
