"""Articles libres : ajoutés à la main sur la liste de courses, hors repas et hors placard."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from outils import ajouter_famille

from repas.domaine.articles_libres import a_reporter, cle_coche_libre, total_articles_libres
from repas.services import lundi_de


@dataclass
class Article:
    id: int | None
    prix_eur: float | None = None


# --- Règles (sans base) ----------------------------------------------------------------


def test_reporter_les_articles_non_coches():
    chaussures, savon = Article(1), Article(2)
    assert a_reporter([chaussures, savon], {cle_coche_libre(1), "carotte"}) == [savon]


def test_total_des_prix_saisis():
    assert total_articles_libres([Article(1, 24.99), Article(2), Article(3, 3.5)]) == 28.49


# --- API -------------------------------------------------------------------------------


def url_courses(lundi: str) -> str:
    return f"/api/semaines/{lundi}/courses"


def coche(cle: str, cochee: bool = True) -> dict[str, object]:
    return {"ingredient_id": cle, "cochee": cochee, "modifiee_le": datetime.now(UTC).isoformat()}


def test_ajouter_cocher_et_retirer(client: TestClient):
    url = url_courses("2026-11-30")
    for libelle in ("Chaussures enfant", " chaussures ENFANT ", "Liquide vaisselle"):
        assert client.post(f"{url}/articles", json={"libelle": libelle}).status_code == 204
    assert client.post(f"{url}/articles", json={"libelle": "  "}).status_code == 422
    client.post(f"{url}/articles", json={"libelle": "Piles", "quantite": " 4 × AA "})
    articles = client.get(url).json()["articles_libres"]
    assert [(a["libelle"], a["quantite"]) for a in articles] == [
        ("Chaussures enfant", ""),  # même libellé : ajouté une seule fois
        ("Liquide vaisselle", ""),
        ("Piles", "4 × AA"),
    ]

    chaussures = articles[0]
    assert client.put(f"{url}/coches", json=[coche(chaussures["cle"])]).json() == [
        chaussures["cle"]
    ]
    prix = f"{url}/articles/{chaussures['id']}"
    assert client.put(prix, json={"prix_eur": 24.99}).status_code == 204
    assert client.put(prix, json={"prix_eur": -1}).status_code == 422
    courses = client.get(url).json()
    assert courses["articles_libres"][0]["prix_eur"] == 24.99
    assert courses["total_articles_libres_eur"] == 24.99

    assert client.delete(prix).status_code == 204
    assert client.delete(prix).status_code == 204  # déjà retiré
    assert client.put(prix, json={"prix_eur": 1}).status_code == 409
    # Coche venue d'un appareil qui ne savait pas l'article retiré : ignorée.
    assert client.put(f"{url}/coches", json=[coche(chaussures["cle"])]).json() == []
    courses = client.get(url).json()
    assert len(courses["articles_libres"]) == 2 and courses["coches"] == []

    pdf = client.get(f"{url}.pdf")  # section « Autres articles » imprimée
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_ni_placard_ni_cout_des_repas(client: TestClient):
    lundi = lundi_de(date.today()).isoformat()  # semaine retenue par le bilan
    url = url_courses(lundi)
    ajouter_famille(client)
    client.post(f"/api/semaines/{lundi}/generer")
    budget_repas = client.get(url).json()["total_eur"]
    client.post(f"{url}/articles", json={"libelle": "Nettoyant"})
    article = client.get(url).json()["articles_libres"][0]
    client.put(f"{url}/articles/{article['id']}", json={"prix_eur": 4.5})

    assert client.post(f"{url}/valider").status_code == 204
    assert client.get("/api/placard/produits").json() == []
    semaine = next(x for x in client.get("/api/bilan").json()["semaines"] if x["lundi"] == lundi)
    assert semaine["budget_eur"] == budget_repas
    assert client.post(f"{url}/articles", json={"libelle": "Éponges"}).status_code == 409
    assert client.delete(f"{url}/articles/{article['id']}").status_code == 409


def test_reporter_a_la_semaine_suivante(client: TestClient):
    url, suivante = url_courses("2026-11-30"), url_courses("2026-12-07")
    for libelle in ("Chaussures", "Piles", "Éponges"):
        client.post(f"{url}/articles", json={"libelle": libelle})
    client.post(f"{suivante}/articles", json={"libelle": "piles"})  # déjà prévu la suivante
    chaussures, piles, _ = client.get(url).json()["articles_libres"]
    client.put(f"{url}/articles/{piles['id']}", json={"prix_eur": 3})
    client.put(f"{url}/coches", json=[coche(chaussures["cle"]), coche(piles["cle"], False)])
    client.post(f"{url}/valider")  # le report reste possible après « Courses faites »

    reponse = client.post(f"{url}/articles/reporter")
    assert reponse.status_code == 200 and reponse.json() == {"reportes": 2}
    courses = client.get(url).json()
    assert [a["libelle"] for a in courses["articles_libres"]] == ["Chaussures"]
    assert courses["coches"] == [chaussures["cle"]]
    reportes = client.get(suivante).json()["articles_libres"]
    assert [(a["libelle"], a["prix_eur"]) for a in reportes] == [("Éponges", None), ("piles", None)]

    client.post(f"{suivante}/valider")
    assert client.post(f"{url}/articles/reporter").status_code == 409
