# Image de production : une seule image contenant l'API Python et l'interface compilée.
#   docker build -t menu-famille .
#   docker run -p 8000:8000 -v menu-famille:/app/donnees/local -e REPAS_MOT_DE_PASSE=... menu-famille

# --- Étape 1 : compilation de l'interface SvelteKit -----------------------------------
FROM node:24-alpine AS interface
WORKDIR /interface
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Étape 2 : dépendances Python avec uv ----------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS dependances
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev

# --- Étape 3 : image finale, sans outils de compilation ---------------------------------
FROM python:3.13-slim-bookworm
RUN useradd --create-home --uid 1000 famille
WORKDIR /app
COPY --from=dependances --chown=famille /app/backend /app/backend
COPY --chown=famille donnees/referentiel /app/donnees/referentiel
COPY --chown=famille donnees/recettes /app/donnees/recettes
COPY --from=interface --chown=famille /interface/build /app/interface
RUN mkdir -p /app/donnees/local && chown famille /app/donnees/local

ENV PATH="/app/backend/.venv/bin:$PATH" \
    REPAS_DOSSIER_DONNEES=/app/donnees \
    REPAS_DOSSIER_INTERFACE=/app/interface \
    PYTHONUNBUFFERED=1
USER famille
VOLUME ["/app/donnees/local"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/sante')"
CMD ["repas", "--hote", "0.0.0.0", "--port", "8000"]
