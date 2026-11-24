"""Fixtures communes : catalogue réel et application sur une base temporaire."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from repas import securite
from repas.base import moteur
from repas.catalogue import Catalogue, catalogue, charger_catalogue
from repas.config import RACINE_DEPOT, parametres

DONNEES = RACINE_DEPOT / "donnees"


@pytest.fixture(scope="session")
def cat() -> Catalogue:
    """Le catalogue versionné du dépôt (sans recettes importées)."""
    return charger_catalogue(DONNEES)


@pytest.fixture(autouse=True)
def hachage_rapide(monkeypatch: pytest.MonkeyPatch) -> None:
    """Coût scrypt réduit en test (le coût réel, volontairement lent, ralentirait la suite)."""
    monkeypatch.setattr(securite, "_N", 2**8)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Client HTTP connecté, sur une base et un dossier d'import temporaires."""
    monkeypatch.setenv("REPAS_BASE_DE_DONNEES", str(tmp_path / "test.db"))
    monkeypatch.setenv("REPAS_MOT_DE_PASSE", "secret")
    monkeypatch.setattr(
        type(parametres()), "dossier_recettes_importees", property(lambda _: tmp_path / "imports")
    )
    for cache in (parametres, moteur, catalogue):
        cache.cache_clear()
    securite.limiteur.echecs.clear()

    from repas.api.catalogue import verificateur_lien
    from repas.application import creer_application

    application = creer_application()
    # Pas d'accès réseau en test : les liens « /introuvable » simulent une page 404.
    application.dependency_overrides[verificateur_lien] = lambda: (
        lambda url: "introuvable" if url.endswith("/introuvable") else "ok"
    )
    with TestClient(application) as c:
        assert c.post("/api/session", json={"mot_de_passe": "secret"}).status_code == 200
        yield c

    moteur().dispose()  # ferme les connexions SQLite avant de supprimer la base temporaire
    for cache in (parametres, moteur, catalogue):
        cache.cache_clear()
