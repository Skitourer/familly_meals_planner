"""Repas pris à l'extérieur : catégorie indiquée pour un membre absent d'un créneau."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from outils import ajouter_famille

# Semaine en cours : le bilan ne regarde que les semaines récentes.
LUNDI = (date.today() - timedelta(days=date.today().weekday())).isoformat()


def _url(membre_id: int, jour: int = 0, moment: str = "midi") -> str:
    return f"/api/semaines/{LUNDI}/creneaux/{jour}/{moment}/exterieurs/{membre_id}"


def _creneau(semaine: dict, cle: str) -> dict:
    return next(c for c in semaine["creneaux"] if c["cle"] == cle)


def test_categorie_d_un_membre_absent(client: TestClient):
    alex, sam, leo = ajouter_famille(client)
    client.put(f"/api/semaines/{LUNDI}/creneaux/0/midi", json={"convives": [alex, sam]})

    semaine = client.put(_url(leo), json={"categorie": "poisson"}).json()
    assert _creneau(semaine, "0-midi")["exterieurs"] == [{"membre_id": leo, "categorie": "poisson"}]
    semaine = client.put(_url(leo), json={"categorie": "viande"}).json()
    assert _creneau(semaine, "0-midi")["exterieurs"][0]["categorie"] == "viande"

    # « Inconnu » efface la catégorie.
    semaine = client.put(_url(leo), json={"categorie": None}).json()
    assert _creneau(semaine, "0-midi")["exterieurs"] == []


def test_refus_pour_un_membre_present_ou_inconnu(client: TestClient):
    alex, _, _ = ajouter_famille(client)
    client.get(f"/api/semaines/{LUNDI}")
    assert client.put(_url(alex), json={"categorie": "poisson"}).status_code == 400
    assert client.put(_url(999), json={"categorie": "poisson"}).status_code == 404
    assert client.put(_url(alex), json={"categorie": "pizza"}).status_code == 422


def test_retour_a_la_maison_efface_la_categorie(client: TestClient):
    alex, sam, leo = ajouter_famille(client)
    client.put(f"/api/semaines/{LUNDI}/creneaux/0/midi", json={"convives": [alex, sam]})
    client.put(_url(leo), json={"categorie": "poisson"})
    client.put(f"/api/semaines/{LUNDI}/creneaux/0/midi", json={"convives": [alex, sam, leo]})
    semaine = client.put(f"/api/semaines/{LUNDI}/creneaux/0/midi", json={"convives": [alex]})
    assert _creneau(semaine.json(), "0-midi")["exterieurs"] == []


def test_generation_et_bilan_tiennent_compte_du_repas_exterieur(client: TestClient):
    alex, sam, leo = ajouter_famille(client)
    client.put(f"/api/semaines/{LUNDI}/creneaux/0/midi", json={"convives": [alex, sam]})
    client.put(_url(leo), json={"categorie": "poisson"})
    assert client.post(f"/api/semaines/{LUNDI}/generer").status_code == 200

    bilan = client.get("/api/bilan", params={"semaines": 1}).json()
    semaine = next(x for x in bilan["semaines"] if x["lundi"] == LUNDI)
    assert semaine["proteines_exterieur"] == {"poisson": 1}


def test_suppression_d_un_membre_avec_repas_exterieur(client: TestClient):
    alex, sam, leo = ajouter_famille(client)
    client.put(f"/api/semaines/{LUNDI}/creneaux/0/midi", json={"convives": [alex, sam]})
    client.put(_url(leo), json={"categorie": "vegetarien"})
    assert client.delete(f"/api/membres/{leo}").status_code == 204
    semaine = client.get(f"/api/semaines/{LUNDI}").json()
    assert _creneau(semaine, "0-midi")["exterieurs"] == []
