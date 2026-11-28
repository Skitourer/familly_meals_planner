"""Protections HTTP communes (OWASP ASVS niveau 1) : en-têtes, CSRF et taille des requêtes.

Middlewares ASGI purs, appliqués à toutes les réponses (API et interface) :

* **en-têtes de sécurité** : CSP, ``X-Content-Type-Options``, ``frame-ancestors``,
  ``Referrer-Policy`` et, derrière HTTPS, HSTS ;
* **CSRF** : les requêtes qui modifient des données (POST, PUT, PATCH, DELETE) sous
  ``/api`` doivent porter l'en-tête ``X-Menu-Famille``. Un site tiers ne peut pas
  l'ajouter sans autorisation CORS (que l'application ne donne jamais) ; c'est une
  défense en plus du cookie ``SameSite=Lax`` ;
* **taille maximale** du corps des requêtes (413 au-delà).
"""

import base64
import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ENTETE_CSRF = "x-menu-famille"
METHODES_SURES = frozenset({"GET", "HEAD", "OPTIONS"})

# L'import JSON de recettes est limité à 2 Mo (api/catalogue.py) ; marge pour l'enveloppe
# multipart.
TAILLE_MAX_OCTETS = 3_000_000

# Pages de documentation OpenAPI de FastAPI : leurs scripts viennent du CDN jsdelivr.
CHEMINS_DOCUMENTATION = ("/api/docs", "/api/redoc")
CSP_DOCUMENTATION = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
)

# HSTS : un an, recommandation OWASP (HTTP Strict Transport Security Cheat Sheet).
HSTS = "max-age=31536000"


def politique_contenu(empreintes_scripts: Iterable[str] = ()) -> str:
    """Content-Security-Policy de l'application : tout vient de la même origine.

    ``style-src 'unsafe-inline'`` : Svelte écrit des attributs ``style`` dynamiques.
    Les scripts en ligne ne sont acceptés que par leur empreinte (``index.html``).
    """
    scripts = " ".join(["'self'", *(f"'{e}'" for e in empreintes_scripts)])
    return (
        f"default-src 'self'; script-src {scripts}; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'"
    )


def empreintes_scripts_en_ligne(html: str) -> list[str]:
    """Empreintes CSP (``sha256-…``) des balises ``<script>`` sans ``src`` d'une page."""
    contenus = re.findall(r"<script>(.*?)</script>", html, flags=re.DOTALL)
    return [
        "sha256-" + base64.b64encode(hashlib.sha256(c.encode()).digest()).decode() for c in contenus
    ]


def empreintes_interface(dossier: Path | None) -> list[str]:
    """Empreintes des scripts en ligne de l'interface compilée (aucune sans interface)."""
    index = dossier / "index.html" if dossier else None
    if index is None or not index.is_file():
        return []
    return empreintes_scripts_en_ligne(index.read_text(encoding="utf-8"))


class EntetesSecurite:
    """Ajoute les en-têtes de sécurité à chaque réponse HTTP."""

    def __init__(self, app: ASGIApp, csp: str, hsts: bool) -> None:
        self.app = app
        self.csp = csp
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        documentation = str(scope["path"]).startswith(CHEMINS_DOCUMENTATION)

        async def envoyer(message: Message) -> None:
            if message["type"] == "http.response.start":
                entetes = MutableHeaders(scope=message)
                csp = CSP_DOCUMENTATION if documentation else self.csp
                entetes["Content-Security-Policy"] = csp
                entetes["X-Content-Type-Options"] = "nosniff"
                entetes["X-Frame-Options"] = "DENY"
                entetes["Referrer-Policy"] = "same-origin"
                if self.hsts:
                    entetes["Strict-Transport-Security"] = HSTS
            await send(message)

        await self.app(scope, receive, envoyer)


class ProtectionCsrf:
    """Refuse (403) les requêtes modifiantes de l'API sans l'en-tête ``X-Menu-Famille``."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] not in METHODES_SURES
            and str(scope["path"]).startswith("/api/")
            and ENTETE_CSRF not in Headers(scope=scope)
        ):
            reponse = JSONResponse({"detail": "Requête refusée (en-tête manquant)"}, 403)
            await reponse(scope, receive, send)
            return
        await self.app(scope, receive, send)


class TailleMaximale:
    """Refuse (413) les corps de requête de plus de ``taille_max`` octets."""

    def __init__(self, app: ASGIApp, taille_max: int = TAILLE_MAX_OCTETS) -> None:
        self.app = app
        self.taille_max = taille_max

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        longueur = Headers(scope=scope).get("content-length", "0")
        if not longueur.isdigit() or int(longueur) > self.taille_max:
            await self._refuser(scope, receive, send)
            return

        # Corps envoyé sans Content-Length (transfert par morceaux) : on compte les octets
        # reçus. Au-delà de la limite, on répond 413 et l'application voit une déconnexion
        # (sa propre réponse d'erreur est alors ignorée).
        recu = 0
        refusee = False

        async def recevoir() -> Message:
            nonlocal recu, refusee
            message = await receive()
            if message["type"] == "http.request":
                recu += len(message.get("body", b""))
                if recu > self.taille_max and not refusee:
                    refusee = True
                    await self._refuser(scope, receive, send)
                    return {"type": "http.disconnect"}
            return message

        async def envoyer(message: Message) -> None:
            if not refusee:
                await send(message)

        await self.app(scope, recevoir, envoyer)

    async def _refuser(self, scope: Scope, receive: Receive, send: Send) -> None:
        mega_octets = self.taille_max // 1_000_000
        detail = f"Requête trop volumineuse ({mega_octets} Mo maximum)"
        reponse = JSONResponse({"detail": detail}, 413)
        await reponse(scope, receive, send)
