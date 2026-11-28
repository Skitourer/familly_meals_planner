"""Modification d'un article du placard : valeurs, ingrédient, ingrédient ⇄ autre produit."""

from datetime import date

from fastapi.testclient import TestClient

from repas.domaine.produits import regrouper

URL = "/api/placard/modification"
NOTES = {"nutriscore": "b", "nova": 3, "green_score": "c"}


def ingredients(client: TestClient) -> dict[str, dict]:
    return {st["ingredient_id"]: st for st in client.get("/api/placard").json()}


def produits(client: TestClient) -> list[dict]:
    return client.get("/api/placard/produits").json()


def vers_ingredient(ingredient_id: str, quantite_g: float, peremption: str | None = None) -> dict:
    return {"type": "ingredient", "ingredient_id": ingredient_id, "quantite_g": quantite_g,
            "peremption": peremption}  # fmt: skip


def vers_produit(nom: str, categorie: str = "Épicerie", paquets: int = 1) -> dict:
    return {"type": "produit", "nom": nom, "categorie": categorie, "paquets": paquets}


def test_regrouper_additionne_et_garde_la_date_la_plus_proche():
    assert regrouper((300.0, date(2027, 2, 1)), (200.0, date(2027, 1, 1))) == (
        500.0,
        date(2027, 1, 1),
    )
    assert regrouper((2, None), (1, date(2027, 1, 1))) == (3, date(2027, 1, 1))
    assert regrouper((2, None), (1, None)) == (3, None)


def test_meme_ingredient_remplace_ses_valeurs(client: TestClient):
    client.put("/api/placard/riz", json={"quantite_g": 400, "peremption": "2027-01-10", **NOTES})
    cible = vers_ingredient("riz", 250, "2027-02-01")
    assert client.post(URL, json={"ingredient_id": "riz", "cible": cible}).status_code == 204
    riz = ingredients(client)["riz"]
    assert (riz["quantite_g"], riz["peremption"], riz["nova"]) == (250, "2027-02-01", 3)


def test_changer_d_ingredient_regroupe_avec_le_stock_existant(client: TestClient):
    client.put("/api/placard/riz", json={"quantite_g": 400, "peremption": "2027-03-01", **NOTES})
    client.put("/api/placard/pates", json={"quantite_g": 500, "peremption": "2027-05-01"})
    cible = vers_ingredient("pates", 400, "2027-03-01")
    assert client.post(URL, json={"ingredient_id": "riz", "cible": cible}).status_code == 204
    stock = ingredients(client)
    assert "riz" not in stock
    pates = stock["pates"]
    assert (pates["quantite_g"], pates["peremption"]) == (900, "2027-03-01")
    assert {cle: pates[cle] for cle in NOTES} == NOTES  # les notes suivent le produit


def test_ingredient_devient_autre_produit_avec_ses_notes(client: TestClient):
    client.put("/api/placard/riz", json={"quantite_g": 400, **NOTES})
    cible = {**vers_produit("Céréales", "Petit-déjeuner", 2), "peremption": "2027-04-01"}
    assert client.post(URL, json={"ingredient_id": "riz", "cible": cible}).status_code == 204
    assert ingredients(client) == {}
    [cereales] = produits(client)
    assert (cereales["nom"], cereales["categorie"], cereales["paquets"]) == (
        "Céréales",
        "Petit-déjeuner",
        2,
    )
    assert (cereales["peremption"], cereales["nova"]) == ("2027-04-01", 3)


def test_autre_produit_modifie_sur_place(client: TestClient):
    client.post("/api/placard/produits", json={"nom": "Nutela", "categorie": "Épicerie"})
    [produit] = produits(client)
    cible = {**vers_produit("Nutella", "Petit-déjeuner", 3), "peremption": None}
    reponse = client.post(URL, json={"produit_id": produit["id"], "cible": cible})
    assert reponse.status_code == 204
    [corrige] = produits(client)
    assert corrige["id"] == produit["id"]
    assert (corrige["nom"], corrige["categorie"], corrige["paquets"]) == (
        "Nutella",
        "Petit-déjeuner",
        3,
    )


def test_autre_produit_devient_ingredient(client: TestClient):
    fiche = {"nom": "Riz basmati", "categorie": "Épicerie", **NOTES}
    client.post("/api/placard/produits", json=fiche)
    [produit] = produits(client)
    cible = vers_ingredient("riz", 1000)  # sans date : conservation de l'ingrédient
    assert client.post(URL, json={"produit_id": produit["id"], "cible": cible}).status_code == 204
    assert produits(client) == []
    riz = ingredients(client)["riz"]
    assert (riz["quantite_g"], riz["nova"]) == (1000, 3)
    assert riz["peremption"] > date.today().isoformat()


def test_modification_refusee_sans_rien_changer(client: TestClient):
    client.put("/api/placard/riz", json={"quantite_g": 400})
    erreurs = [
        ({"ingredient_id": "riz", "cible": vers_ingredient("licorne", 100)}, 422),
        ({"ingredient_id": "riz", "cible": vers_produit("Jouet", "Jouets")}, 422),
        ({"ingredient_id": "riz", "cible": vers_ingredient("riz", 0)}, 422),
        ({"cible": vers_ingredient("riz", 100)}, 422),
        ({"ingredient_id": "riz", "produit_id": 1, "cible": vers_ingredient("riz", 100)}, 422),
        ({"ingredient_id": "pates", "cible": vers_ingredient("riz", 100)}, 404),
        ({"produit_id": 99, "cible": vers_produit("Fantôme")}, 404),
    ]
    for corps, statut in erreurs:
        assert client.post(URL, json=corps).status_code == statut, corps
    assert ingredients(client)["riz"]["quantite_g"] == 400
    assert produits(client) == []
