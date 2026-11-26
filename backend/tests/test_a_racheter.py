"""Produits à racheter : un autre produit fini au placard revient sur la liste de courses."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from outils import ajouter_famille

from repas.domaine.produits import a_ranger_a_la_validation, cle_coche_racheter, est_scanne
from repas.services import lundi_de

EAN8 = "12345670"


@dataclass
class Fiche:
    nom: str
    code: str | None = None
    id: int | None = None


# --- Règles (sans base) ----------------------------------------------------------------


def test_scanne_par_code_sinon_par_nom():
    assert est_scanne(Fiche("Pâte à tartiner", EAN8), [Fiche("Nom différent", EAN8)])
    assert est_scanne(Fiche("Céréales"), [Fiche(" céréales ")])
    assert not est_scanne(Fiche("Céréales"), [Fiche("Biscuits")])


def test_a_ranger_selon_coches_scans_et_confirmation():
    coche, non_coche, scanne = Fiche("Thé", id=1), Fiche("Café", id=2), Fiche("Jus", id=3)
    articles = [coche, non_coche, scanne]
    coches = {cle_coche_racheter(1), cle_coche_racheter(3)}
    achats = [Fiche("Jus")]
    # Scanné : rangé par son achat, jamais deux fois.
    assert a_ranger_a_la_validation(articles, coches, achats, tout_achete=False) == [coche]
    assert a_ranger_a_la_validation(articles, coches, achats, tout_achete=True) == [
        coche,
        non_coche,
    ]


# --- API -------------------------------------------------------------------------------


def url_courses(lundi: str) -> str:
    return f"/api/semaines/{lundi}/courses"


def test_produit_fini_remis_sur_la_liste_puis_range(client: TestClient):
    lundi = lundi_de(date.today()).isoformat()  # semaine retenue par le bilan
    url = url_courses(lundi)
    ajouter_famille(client)
    client.post(f"/api/semaines/{lundi}/generer")
    total_liste = client.get(url).json()["total_eur"]
    nutella = {"nom": "Pâte à tartiner", "categorie": "Petit-déjeuner", "code": EAN8}
    cereales = {"nom": "Céréales", "categorie": "Petit-déjeuner"}
    # Dernier prix payé connu pour le code-barres : il sert d'estimation.
    client.post(f"{url}/autres-achats", json={**nutella, "prix_eur": 3.2, "ranger": False})
    id_achat = client.get(url).json()["autres_achats"][0]["id"]
    client.delete(f"{url}/autres-achats/{id_achat}")

    for fiche in (nutella, cereales, nutella):  # le même produit n'est ajouté qu'une fois
        assert client.post(f"{url}/a-racheter", json=fiche).status_code == 204
    jouet = {**cereales, "categorie": "Jouets"}
    assert client.post(f"{url}/a-racheter", json=jouet).status_code == 422
    courses = client.get(url).json()
    rachats = courses["a_racheter"]
    assert [(r["nom"], r["prix_eur"], r["scanne"]) for r in rachats] == [
        ("Pâte à tartiner", 3.2, False),
        ("Céréales", None, False),
    ]
    assert courses["total_eur"] == round(total_liste + 3.2, 2)

    pdf = client.get(f"{url}.pdf")  # section « À racheter » imprimée
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # Coche partagée, avec la clé du produit ; une clé inconnue est refusée.
    maintenant = datetime.now(UTC).isoformat()
    coche = {"ingredient_id": rachats[0]["cle"], "cochee": True, "modifiee_le": maintenant}
    assert client.put(f"{url}/coches", json=[coche]).json() == [rachats[0]["cle"]]
    inconnue = {**coche, "ingredient_id": "racheter-9999"}
    assert client.put(f"{url}/coches", json=[inconnue]).status_code == 400

    # Les céréales ne sont pas achetées : seule la pâte à tartiner cochée rejoint le placard.
    assert client.post(f"{url}/valider", json={"tout_achete": False}).status_code == 204
    placard = client.get("/api/placard/produits").json()
    assert [(p["nom"], p["paquets"]) for p in placard] == [("Pâte à tartiner", 1)]
    semaine = next(x for x in client.get("/api/bilan").json()["semaines"] if x["lundi"] == lundi)
    assert semaine["budget_eur"] == 3.2  # ingrédients ni cochés ni scannés : non achetés
    assert client.post(f"{url}/a-racheter", json=cereales).status_code == 409
    assert client.delete(f"{url}/a-racheter/{rachats[1]['id']}").status_code == 409

    # Rouvrir retire le paquet rangé.
    assert client.post(f"{url}/rouvrir").status_code == 204
    assert client.get("/api/placard/produits").json() == []


def test_produit_scanne_range_une_seule_fois(client: TestClient):
    url = url_courses("2026-11-30")
    biscuits = {"nom": "Biscuits", "categorie": "Biscuits et goûters"}
    client.post(f"{url}/a-racheter", json=biscuits)
    client.post(f"{url}/autres-achats", json={**biscuits, "prix_eur": 2})
    courses = client.get(url).json()
    assert courses["a_racheter"][0]["scanne"]
    assert courses["total_reel_eur"] == 2

    assert client.post(f"{url}/valider").status_code == 204  # tout acheté
    placard = client.get("/api/placard/produits").json()
    assert [(p["nom"], p["paquets"]) for p in placard] == [("Biscuits", 1)]


def test_retirer_de_la_liste(client: TestClient):
    ajouter_famille(client)
    url = url_courses("2026-11-30")
    client.post(f"{url}/a-racheter", json={"nom": "Thé", "categorie": "Boissons"})
    produit = client.get(url).json()["a_racheter"][0]
    maintenant = datetime.now(UTC).isoformat()
    coche = {"ingredient_id": produit["cle"], "cochee": True, "modifiee_le": maintenant}
    client.put(f"{url}/coches", json=[coche])

    assert client.delete(f"{url}/a-racheter/{produit['id']}").status_code == 204
    assert client.delete(f"{url}/a-racheter/{produit['id']}").status_code == 204  # déjà retiré
    courses = client.get(url).json()
    assert courses["a_racheter"] == [] and courses["coches"] == []


# --- Ingrédients à racheter -------------------------------------------------------------


def lignes(client: TestClient, url: str) -> dict[str, dict]:
    return {x["ingredient_id"]: x for _, xs in client.get(url).json()["rayons"] for x in xs}


def test_ingredient_fini_remis_sur_la_liste_puis_range(client: TestClient):
    url = url_courses("2026-11-30")
    entree = {"ingredient_id": "beurre"}
    for _ in range(2):  # une seule fois sur la liste
        assert client.post(f"{url}/ingredients-a-racheter", json=entree).status_code == 204
    for invalide in ("licorne", "sel"):  # inconnu, basique
        reponse = client.post(f"{url}/ingredients-a-racheter", json={"ingredient_id": invalide})
        assert reponse.status_code == 400
    beurre = lignes(client, url)["beurre"]
    assert beurre["a_racheter"] and beurre["achat"] == "1 × paquet de 250 g"

    # Coché comme un ingrédient ordinaire, puis rangé au placard à la validation.
    maintenant = datetime.now(UTC).isoformat()
    coche = {"ingredient_id": "beurre", "cochee": True, "modifiee_le": maintenant}
    client.put(f"{url}/coches", json=[coche])
    assert client.post(f"{url}/valider", json={"tout_achete": False}).status_code == 204
    placard = {p["ingredient_id"]: p["quantite_g"] for p in client.get("/api/placard").json()}
    assert placard["beurre"] > 0
    assert client.post(f"{url}/ingredients-a-racheter", json=entree).status_code == 409
    assert client.delete(f"{url}/ingredients-a-racheter/beurre").status_code == 409

    assert client.post(f"{url}/rouvrir").status_code == 204
    assert "beurre" not in {p["ingredient_id"] for p in client.get("/api/placard").json()}
    assert client.delete(f"{url}/ingredients-a-racheter/beurre").status_code == 204
    assert "beurre" not in lignes(client, url)
