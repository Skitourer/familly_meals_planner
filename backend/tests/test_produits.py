"""Produits scannés : code-barres, fiche Open Food Facts et ajout au placard (sans réseau)."""

from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from outils import ajouter_famille

from repas.api.produits import chercheur_produit
from repas.catalogue import Catalogue
from repas.domaine.produits import (
    FicheProduit,
    categorie_produit,
    code_barres_valide,
    date_la_plus_proche,
    ingredients_correspondants,
    lire_fiche,
    meme_produit,
    quantite_comestible,
)
from repas.open_food_facts import OpenFoodFactsIndisponible, chercher_produit
from repas.services import lundi_de

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
    reponse = client.get(f"/api/produits/{EAN13}")
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
    produit = client.get(f"/api/produits/{EAN13}").json()
    assert produit["propositions"] == []
    assert produit["quantite_g"] is None


def test_api_produit_erreurs(client: TestClient):
    def indisponible(code: str) -> None:
        raise OpenFoodFactsIndisponible("délai dépassé")

    simuler(client, lambda code: None)
    assert client.get("/api/produits/3000000000008").status_code == 422
    assert client.get(f"/api/produits/{EAN13}").status_code == 404
    simuler(client, indisponible)
    reponse = client.get(f"/api/produits/{EAN13}")
    assert reponse.status_code == 503
    assert "délai" not in reponse.text  # pas de détail interne renvoyé au client


def test_dependance_par_defaut_interroge_open_food_facts():
    assert chercheur_produit() is chercher_produit


# --- Achats réels aux courses -----------------------------------------------------------


def test_api_achats_reels(client: TestClient):
    lundi = "2026-11-30"
    ajouter_famille(client)
    client.post(f"/api/semaines/{lundi}/generer")
    courses = client.get(f"/api/semaines/{lundi}/courses").json()
    ligne = courses["rayons"][0][1][0]
    url = f"/api/semaines/{lundi}/courses/achats"
    achat = {"ingredient_id": ligne["ingredient_id"], "quantite_g": 500, "prix_eur": 1.2}

    assert client.post(url, json={**achat, "code": EAN13}).status_code == 204
    assert client.post(url, json=achat).status_code == 204  # deuxième paquet : s'additionne
    apres = client.get(f"/api/semaines/{lundi}/courses").json()
    lignes = [x for _, xs in apres["rayons"] for x in xs]
    reelle = next(x for x in lignes if x["ingredient_id"] == achat["ingredient_id"])
    assert (reelle["achat_reel"], reelle["prix_reel_eur"]) == ("1 kg", 2.4)
    assert apres["nb_achats_reels"] == 1
    assert apres["total_reel_eur"] == round(apres["total_eur"] - ligne["prix_eur"] + 2.4, 2)

    # Le prix payé est proposé au prochain scan du même produit.
    simuler(client, lambda code: lire_fiche(code, PATES_COMPLETES))
    assert client.get(f"/api/produits/{EAN13}").json()["dernier_prix_eur"] == 1.2

    # Refus : hors liste, code invalide, quantité nulle.
    assert client.post(url, json={**achat, "ingredient_id": "huile-olive"}).status_code == 400
    assert client.post(url, json={**achat, "code": "3000000000008"}).status_code == 422
    assert client.post(url, json={**achat, "quantite_g": 0}).status_code == 422

    # Annulation, puis validation : achats figés.
    assert client.delete(f"{url}/{achat['ingredient_id']}").status_code == 204
    assert client.get(f"/api/semaines/{lundi}/courses").json()["nb_achats_reels"] == 0
    client.post(url, json=achat)
    assert client.post(f"/api/semaines/{lundi}/courses/valider").status_code == 204
    assert client.post(url, json=achat).status_code == 409
    assert client.delete(f"{url}/{achat['ingredient_id']}").status_code == 409


def test_api_achats_hors_liste_et_budget_seulement(client: TestClient):
    lundi = lundi_de(date.today()).isoformat()  # semaine retenue par le bilan
    ajouter_famille(client)
    client.post(f"/api/semaines/{lundi}/generer")
    avant = client.get(f"/api/semaines/{lundi}/courses").json()
    prevus = {x["ingredient_id"] for _, xs in avant["rayons"] for x in xs}
    hors = next(i["id"] for i in client.get("/api/ingredients").json()
                if i["id"] not in prevus and not i["basique"])  # fmt: skip
    url = f"/api/semaines/{lundi}/courses"
    achat = {"ingredient_id": hors, "quantite_g": 400, "prix_eur": 3}
    assert client.post(f"{url}/achats", json=achat).status_code == 204
    autre = {"nom": "Biscuits", "categorie": "Biscuits et goûters", "prix_eur": 2.5, "code": EAN8}
    assert client.post(f"{url}/autres-achats", json=autre).status_code == 204
    sandwich = {"nom": "Sandwich", "categorie": "Épicerie", "prix_eur": 4, "ranger": False}
    assert client.post(f"{url}/autres-achats", json=sandwich).status_code == 204
    for invalide in ({**autre, "nom": ""}, {**autre, "categorie": "Jouets"},
                     {**autre, "code": "3000000000008"}):  # fmt: skip
        assert client.post(f"{url}/autres-achats", json=invalide).status_code == 422

    courses = client.get(url).json()
    assert [x["ingredient_id"] for x in courses["hors_liste"]] == [hors]
    assert courses["hors_liste"][0]["achat_reel"] is not None
    assert [(a["nom"], a["ranger"]) for a in courses["autres_achats"]] == [
        ("Biscuits", True), ("Sandwich", False)
    ]  # fmt: skip
    assert courses["total_reel_eur"] == round(avant["total_eur"] + 3 + 2.5 + 4, 2)
    assert courses["nb_achats_reels"] == 3

    # Retrait puis remise de l'autre produit.
    id_autre = courses["autres_achats"][0]["id"]
    assert client.delete(f"{url}/autres-achats/{id_autre}").status_code == 204
    assert [a["nom"] for a in client.get(url).json()["autres_achats"]] == ["Sandwich"]
    client.post(f"{url}/autres-achats", json=autre)
    courses = client.get(url).json()

    # Validation : l'achat hors liste rejoint le placard, le budget compte tout.
    assert client.post(f"{url}/valider").status_code == 204
    placard = {p["ingredient_id"] for p in client.get("/api/placard").json()}
    assert hors in placard
    # Les biscuits sont rangés, pas le sandwich.
    rayon = client.get("/api/placard/produits").json()
    assert [(p["nom"], p["paquets"]) for p in rayon] == [("Biscuits", 1)]
    semaine = next(x for x in client.get("/api/bilan").json()["semaines"] if x["lundi"] == lundi)
    assert (semaine["budget_eur"], semaine["budget_estime"]) == (courses["total_reel_eur"], False)
    assert client.post(f"{url}/autres-achats", json=autre).status_code == 409
    assert client.delete(f"{url}/autres-achats/{id_autre}").status_code == 409

    # Rouvrir les courses retire les paquets rangés.
    assert client.post(f"{url}/rouvrir").status_code == 204
    assert client.get("/api/placard/produits").json() == []


# --- Autres produits du placard -----------------------------------------------------------


NUTELLA = {
    "status": 1,
    "product": {
        "product_name": "Nutella",
        "brands": "Ferrero",
        "quantity": "400 g ℮",
        "product_quantity": 400,
        "product_quantity_unit": "g",
        "categories_tags": ["en:breakfasts", "en:spreads", "en:sweet-spreads"],
        "nutriscore_grade": "e",
        "nova_group": "4",
        "environmental_score_grade": "unknown",
        "ecoscore_grade": "d",
    },
}


def test_fiche_autre_produit():
    fiche = lire_fiche(EAN13, NUTELLA)
    assert fiche is not None
    notes = (fiche.contenu, fiche.nutriscore, fiche.nova, fiche.green_score)
    assert notes == ("400 g", "e", 4, "d")
    assert categorie_produit(fiche.categories) == "Petit-déjeuner"
    assert categorie_produit(("en:beverages", "en:sodas")) == "Boissons"
    assert categorie_produit(()) == "Épicerie"
    inconnues = {"status": 1, "product": {"nova_group": "7", "nutriscore_grade": "unknown"}}
    sans_notes = lire_fiche(EAN13, inconnues)
    assert sans_notes is not None and (sans_notes.nova, sans_notes.nutriscore) == (None, None)


def test_meme_produit_et_date():
    assert meme_produit(EAN13, "Nutella", EAN13, "Pâte à tartiner")
    assert not meme_produit(EAN13, "Nutella", EAN8, "Nutella")
    assert meme_produit(None, "Gâteau maison ", None, "gâteau MAISON")
    assert not meme_produit(None, "Nutella", EAN13, "Nutella")
    assert date_la_plus_proche(date(2027, 1, 5), date(2026, 12, 1)) == date(2026, 12, 1)
    assert date_la_plus_proche(None, date(2026, 12, 1)) == date(2026, 12, 1)
    assert date_la_plus_proche(None, None) is None


def test_api_autres_produits_du_placard(client: TestClient):
    simuler(client, lambda code: lire_fiche(code, NUTELLA))
    produit = client.get(f"/api/produits/{EAN13}").json()
    resume = (produit["categorie"], produit["contenu"], produit["nova"])
    assert resume == ("Petit-déjeuner", "400 g", 4)
    assert produit["propositions"] == []
    assert "Boissons" in client.get("/api/produits/categories").json()

    fiche = {k: produit[k] for k in ("code", "nom", "marque", "contenu", "categorie",
                                     "nutriscore", "nova", "green_score")}  # fmt: skip
    url_placard = "/api/placard/produits"
    premier = {**fiche, "peremption": "2027-03-01"}
    assert client.post(url_placard, json=premier).status_code == 204
    deux_de_plus = {**fiche, "paquets": 2, "peremption": "2027-01-15"}
    assert client.post(url_placard, json=deux_de_plus).status_code == 204
    client.post(url_placard, json={"nom": "Gâteau maison", "categorie": "Biscuits et goûters"})
    produits = client.get("/api/placard/produits").json()
    assert [(p["nom"], p["paquets"]) for p in produits] == [("Gâteau maison", 1), ("Nutella", 3)]
    nutella = produits[1]
    assert (nutella["peremption"], nutella["green_score"]) == ("2027-01-15", "d")

    url = f"/api/placard/produits/{nutella['id']}"
    assert client.put(url, json={"paquets": 1, "categorie": "Épicerie"}).status_code == 204
    assert client.get("/api/placard/produits").json()[1]["categorie"] == "Épicerie"
    assert client.put(url, json={"categorie": "Jouets"}).status_code == 422
    assert client.put(url, json={"paquets": 0}).status_code == 204
    assert [p["nom"] for p in client.get("/api/placard/produits").json()] == ["Gâteau maison"]
    assert client.put(url, json={"paquets": 2}).status_code == 404
