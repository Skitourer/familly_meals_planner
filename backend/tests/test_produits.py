"""Produits scannés : code-barres, fiche Open Food Facts et ajout au placard (sans réseau)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from repas.api.suivi import chercheur_produit
from repas.catalogue import Catalogue
from repas.domaine.produits import (
    FicheProduit,
    code_barres_valide,
    ingredients_correspondants,
    lire_fiche,
    quantite_comestible,
)
from repas.open_food_facts import OpenFoodFactsIndisponible, chercher_produit

# Codes fictifs avec une clé de contrôle correcte.
EAN13 = "3000000000007"
EAN8 = "12345670"

PATES_COMPLETES = {
    "status": 1,
    "product": {
        "product_name": "Whole wheat penne",
        "product_name_fr": "Penne complètes",
        "brands": "Marque Exemple, Autre",
        "product_quantity": "1",
        "product_quantity_unit": "kg",
        "categories_tags": ["en:plant-based-foods", "en:dry-pastas", "en:wholemeal-pasta"],
    },
}


# --- Code-barres ------------------------------------------------------------------------


@pytest.mark.parametrize("code", [EAN13, EAN8, "036000291452", "4006381333931"])
def test_code_barres_valide(code: str):
    assert code_barres_valide(code)


@pytest.mark.parametrize(
    "code",
    ["3000000000008", "1234567", "abcdefghijklm", "", "300000000000٧", "30000 0000007", "../x"],
)
def test_code_barres_invalide(code: str):
    assert not code_barres_valide(code)


# --- Fiche Open Food Facts --------------------------------------------------------------


def test_lire_fiche():
    fiche = lire_fiche(EAN13, PATES_COMPLETES)
    assert fiche == FicheProduit(
        code=EAN13,
        nom="Penne complètes",
        marque="Marque Exemple",
        quantite_g=1000,
        categories=("en:plant-based-foods", "en:dry-pastas", "en:wholemeal-pasta"),
    )


def test_lire_fiche_incomplete():
    fiche = lire_fiche(EAN13, {"status": 1, "product": {"product_name": "Sans détail"}})
    assert fiche is not None
    assert (fiche.nom, fiche.marque, fiche.quantite_g, fiche.categories) == (
        "Sans détail", "", None, ()
    )  # fmt: skip


@pytest.mark.parametrize("reponse", [{"status": 0}, {"status": 1, "product": "?"}, {}])
def test_lire_fiche_absente(reponse: dict):
    assert lire_fiche(EAN13, reponse) is None


def test_ingredients_correspondants_plus_precis_d_abord(cat: Catalogue):
    categories = ("en:plant-based-foods", "en:dry-pastas", "en:wholemeal-pasta")
    assert ingredients_correspondants(categories, cat.ingredients) == ["pates-completes", "pates"]
    assert ingredients_correspondants(("en:sodas",), cat.ingredients) == []


def test_quantite_comestible(cat: Catalogue):
    assert quantite_comestible(1000, cat.ingredients["carotte"]) == 900
    assert quantite_comestible(500, cat.ingredients["pates"]) == 500


# --- Client Open Food Facts (transport simulé) -----------------------------------------


def transport(statut: int, corps: object = None) -> httpx.MockTransport:
    def repondre(requete: httpx.Request) -> httpx.Response:
        assert requete.url.path == f"/api/v2/product/{EAN13}.json"
        assert "MenuFamille" in requete.headers["User-Agent"]
        return httpx.Response(statut, json=corps) if corps is not None else httpx.Response(statut)

    return httpx.MockTransport(repondre)


def test_chercher_produit():
    fiche = chercher_produit(EAN13, transport=transport(200, PATES_COMPLETES))
    assert fiche is not None and fiche.nom == "Penne complètes"


def test_chercher_produit_inconnu():
    assert chercher_produit(EAN13, transport=transport(404, {"status": 0})) is None


@pytest.mark.parametrize("statut", [500, 503])
def test_chercher_produit_erreur_serveur(statut: int):
    with pytest.raises(OpenFoodFactsIndisponible):
        chercher_produit(EAN13, transport=transport(statut, {}))


def test_chercher_produit_reponse_illisible():
    with pytest.raises(OpenFoodFactsIndisponible):
        chercher_produit(EAN13, transport=transport(200))


def test_chercher_produit_reseau_absent():
    def couper(requete: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("pas de réseau", request=requete)

    with pytest.raises(OpenFoodFactsIndisponible):
        chercher_produit(EAN13, transport=httpx.MockTransport(couper))


# --- API -------------------------------------------------------------------------------


def simuler(client: TestClient, chercher) -> None:
    client.app.dependency_overrides[chercheur_produit] = lambda: chercher  # type: ignore[attr-defined]


def test_api_produit_scanne(client: TestClient):
    simuler(client, lambda code: lire_fiche(code, PATES_COMPLETES))
    reponse = client.get(f"/api/placard/produit/{EAN13}")
    assert reponse.status_code == 200
    produit = reponse.json()
    assert (produit["nom"], produit["marque"], produit["quantite_g"]) == (
        "Penne complètes", "Marque Exemple", 1000
    )  # fmt: skip
    assert [p["ingredient_id"] for p in produit["propositions"]] == ["pates-completes", "pates"]
    assert produit["propositions"][0]["quantite_g"] == 1000


def test_api_produit_basique_non_propose(client: TestClient):
    huile = {"status": 1, "product": {"categories_tags": ["en:extra-virgin-olive-oils"]}}
    simuler(client, lambda code: lire_fiche(code, huile))
    produit = client.get(f"/api/placard/produit/{EAN13}").json()
    assert produit["propositions"] == []
    assert produit["quantite_g"] is None


def test_api_produit_erreurs(client: TestClient):
    def indisponible(code: str) -> None:
        raise OpenFoodFactsIndisponible("délai dépassé")

    simuler(client, lambda code: None)
    assert client.get("/api/placard/produit/3000000000008").status_code == 422
    assert client.get(f"/api/placard/produit/{EAN13}").status_code == 404
    simuler(client, indisponible)
    reponse = client.get(f"/api/placard/produit/{EAN13}")
    assert reponse.status_code == 503
    assert "délai" not in reponse.text  # pas de détail interne renvoyé au client


def test_dependance_par_defaut_interroge_open_food_facts():
    assert chercheur_produit() is chercher_produit
