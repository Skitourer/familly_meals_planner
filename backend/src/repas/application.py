"""Application FastAPI : API sous ``/api`` et, en production, l'interface compilée."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from repas.api import bilan, catalogue, famille, semaines, session, suivi
from repas.base import moteur
from repas.catalogue import catalogue as charger_catalogue
from repas.config import parametres

VERSION = "1.1.0"  # x-release-please-version


@asynccontextmanager
async def demarrage(_: FastAPI) -> AsyncIterator[None]:
    """Au démarrage : crée la base si besoin et valide le catalogue."""
    moteur()
    charger_catalogue()
    yield


def creer_application() -> FastAPI:
    reglages = parametres()
    app = FastAPI(
        lifespan=demarrage,
        title="Menu Famille",
        version=VERSION,
        description="Planificateur de repas équilibrés, de saison et bas carbone.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=reglages.cle_secrete,
        session_cookie="menu_famille",
        max_age=60 * 60 * 24 * 90,  # 90 jours : on ne se reconnecte pas tous les jours
        same_site="lax",
        https_only=reglages.cookie_securise,
    )

    api = APIRouter(prefix="/api")
    api.include_router(session.router)
    protege = [Depends(session.exiger_connexion)]
    for module in (famille, catalogue, semaines, suivi, bilan):
        api.include_router(module.router, dependencies=protege)

    @api.get("/sante", tags=["session"])
    def sante() -> dict[str, str]:
        return {"statut": "ok", "version": VERSION}

    app.include_router(api)

    if reglages.dossier_interface:
        _servir_interface(app, reglages.dossier_interface)
    return app


def _servir_interface(app: FastAPI, dossier: Path) -> None:
    """Sert l'application SvelteKit compilée (mode SPA : index.html par défaut)."""
    app.mount("/_app", StaticFiles(directory=dossier / "_app"), name="interface")

    @app.get("/{chemin:path}", include_in_schema=False)
    def page(chemin: str) -> FileResponse:  # pyright: ignore[reportUnusedFunction]
        fichier = (dossier / chemin).resolve()
        if chemin and fichier.is_file() and fichier.is_relative_to(dossier.resolve()):
            return FileResponse(fichier)
        return FileResponse(dossier / "index.html")
