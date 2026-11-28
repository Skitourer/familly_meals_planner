"""Protections HTTP : en-têtes de sécurité, CSRF, taille des requêtes et erreurs."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from repas import protections
from repas.application import creer_application
from repas.config import CLE_DEVELOPPEMENT, parametres
from repas.protections import (
    EntetesSecurite,
    ProtectionCsrf,
    TailleMaximale,
    empreintes_interface,
    empreintes_scripts_en_ligne,
    politique_contenu,
)


def test_entetes_de_securite_sur_l_api(client: TestClient) -> None:
    reponse = client.get("/api/sante")
    assert reponse.headers["X-Content-Type-Options"] == "nosniff"
    assert reponse.headers["X-Frame-Options"] == "DENY"
    assert reponse.headers["Referrer-Policy"] == "same-origin"
    csp = reponse.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp
    assert "default-src 'self'" in csp
    # Sans HTTPS (REPAS_COOKIE_SECURISE absent), pas de HSTS.
    assert "Strict-Transport-Security" not in reponse.headers


def test_documentation_openapi_garde_ses_scripts(client: TestClient) -> None:
    reponse = client.get("/api/docs")
    assert reponse.headers["Content-Security-Policy"] == protections.CSP_DOCUMENTATION


def test_cookie_de_session_http_only_et_same_site(client: TestClient) -> None:
    reponse = client.post("/api/session", json={"mot_de_passe": "secret"})
    cookie = reponse.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_requete_modifiante_sans_entete_refusee(client: TestClient) -> None:
    del client.headers["X-Menu-Famille"]
    reponse = client.post("/api/session", json={"mot_de_passe": "secret"})
    assert reponse.status_code == 403
    assert reponse.headers["X-Content-Type-Options"] == "nosniff"
    # Les lectures restent possibles sans l'en-tête (liens directs vers les PDF).
    assert client.get("/api/sante").status_code == 200


def test_requete_trop_volumineuse_refusee(client: TestClient) -> None:
    corps = b"x" * (protections.TAILLE_MAX_OCTETS + 1)
    reponse = client.post("/api/session", content=corps)
    assert reponse.status_code == 413
    assert "3 Mo" in reponse.json()["detail"]


def _application_de_test(taille_max: int = 10) -> FastAPI:
    app = FastAPI()

    @app.post("/api/echo")
    async def echo(corps: dict[str, str]) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return corps

    @app.get("/api/panne")
    def panne() -> None:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("détail interne à ne pas divulguer")

    app.add_middleware(ProtectionCsrf)
    app.add_middleware(TailleMaximale, taille_max=taille_max)
    app.add_middleware(EntetesSecurite, csp=politique_contenu(), hsts=True)
    return app


def test_corps_par_morceaux_trop_long_refuse() -> None:
    client = TestClient(_application_de_test(), headers={"X-Menu-Famille": "1"})

    def morceaux():
        yield b'{"a": "'
        yield b"x" * 20
        yield b'"}'

    reponse = client.post(
        "/api/echo", content=morceaux(), headers={"Content-Type": "application/json"}
    )
    assert reponse.status_code == 413


def test_content_length_invalide_refuse() -> None:
    client = TestClient(_application_de_test(), headers={"X-Menu-Famille": "1"})
    reponse = client.post("/api/echo", json={"a": "b"}, headers={"Content-Length": "abc"})
    assert reponse.status_code == 413


def test_corps_dans_la_limite_accepte() -> None:
    client = TestClient(_application_de_test(taille_max=100), headers={"X-Menu-Famille": "1"})
    assert client.post("/api/echo", json={"a": "b"}).json() == {"a": "b"}


def test_hsts_derriere_https() -> None:
    reponse = TestClient(_application_de_test()).get("/api/inconnu")
    assert reponse.headers["Strict-Transport-Security"] == "max-age=31536000"


def test_erreur_interne_sans_detail() -> None:
    client = TestClient(_application_de_test(), raise_server_exceptions=False)
    reponse = client.get("/api/panne")
    assert reponse.status_code == 500
    assert "détail interne" not in reponse.text
    assert "Traceback" not in reponse.text


def test_empreintes_des_scripts_en_ligne() -> None:
    html = '<script src="/a.js"></script><SCRIPT>alert(1)</SCRIPT><p>x</p>'
    # Empreinte calculée par : printf 'alert(1)' | openssl dgst -sha256 -binary | base64
    assert empreintes_scripts_en_ligne(html) == [
        "sha256-bhHHL3z2vDgxUt0W3dWQOrprscmda2Y5pLsLg4GF+pI="
    ]


def test_politique_avec_empreintes() -> None:
    csp = politique_contenu(["sha256-abc"])
    assert "script-src 'self' 'wasm-unsafe-eval' 'sha256-abc';" in csp
    assert "'unsafe-eval'" not in csp
    assert "object-src 'none'" in csp


@pytest.mark.parametrize("avec_index", [True, False])
def test_empreintes_de_l_interface(tmp_path: Path, avec_index: bool) -> None:
    if avec_index:
        (tmp_path / "index.html").write_text("<script>alert(1)</script>", encoding="utf-8")
    assert len(empreintes_interface(tmp_path)) == int(avec_index)
    assert empreintes_interface(None) == []


@pytest.fixture
def interface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Interface compilée factice servie par l'application (mode production)."""
    dossier = tmp_path / "interface"
    (dossier / "_app").mkdir(parents=True)
    (dossier / "index.html").write_text("<script>alert(1)</script>", encoding="utf-8")
    monkeypatch.setenv("REPAS_DOSSIER_INTERFACE", str(dossier))
    parametres.cache_clear()
    yield dossier
    parametres.cache_clear()


def test_cle_de_developpement_refusee_en_production(
    interface: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REPAS_CLE_SECRETE", CLE_DEVELOPPEMENT)
    parametres.cache_clear()
    with pytest.raises(RuntimeError, match="REPAS_CLE_SECRETE"):
        creer_application()


def test_csp_de_production_autorise_le_script_de_l_interface(
    interface: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REPAS_CLE_SECRETE", "cle-de-test-suffisamment-longue")
    parametres.cache_clear()
    reponse = TestClient(creer_application()).get("/une-page")
    assert reponse.text == "<script>alert(1)</script>"
    assert (
        "'sha256-bhHHL3z2vDgxUt0W3dWQOrprscmda2Y5pLsLg4GF+pI='"
        in reponse.headers["Content-Security-Policy"]
    )
