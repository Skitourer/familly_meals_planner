"""Scénario complet par l'API : du vendredi soir au placard."""

import json
from datetime import date, timedelta

from fastapi.testclient import TestClient

LUNDI = "2026-11-30"


def ajouter_famille(client: TestClient) -> list[int]:
    membres = [
        {"prenom": "Alex", "date_naissance": "1985-03-02", "sexe": "H", "poids_kg": 78,
         "heures_sport_semaine": 3},
        {"prenom": "Sam", "date_naissance": "1987-07-15", "sexe": "F", "poids_kg": 60,
         "mode_de_vie": "modere"},
        {"prenom": "Léo", "date_naissance": "2016-01-20", "sexe": "H", "poids_kg": 30,
         "mode_de_vie": "actif"},
    ]  # fmt: skip
    return [client.post("/api/membres", json=m).json()["id"] for m in membres]


def test_connexion_obligatoire(client: TestClient):
    client.delete("/api/session")
    assert client.get("/api/membres").status_code == 401
    assert client.post("/api/session", json={"mot_de_passe": "faux"}).status_code == 401
    assert client.get("/api/sante").status_code == 200


def test_membres_et_besoins(client: TestClient):
    ajouter_famille(client)
    membres = client.get("/api/membres").json()
    assert [m["prenom"] for m in membres] == ["Alex", "Sam", "Léo"]
    leo = membres[2]
    assert leo["coefficient_portion"] < membres[0]["coefficient_portion"]


def test_scenario_du_vendredi(client: TestClient):
    alex, sam, _leo = ajouter_famille(client)

    # 1. Planification : Léo mange à la cantine en semaine, samedi soir joker.
    semaine = client.get(f"/api/semaines/{LUNDI}").json()
    assert len(semaine["creneaux"]) == 14
    for jour in range(5):
        client.put(f"/api/semaines/{LUNDI}/creneaux/{jour}/midi", json={"convives": [alex, sam]})
    client.put(f"/api/semaines/{LUNDI}/creneaux/3/soir", json={"convives": [], "invites": 0})
    client.put(f"/api/semaines/{LUNDI}/creneaux/5/soir", json={"joker": True, "invites": 2})

    # 2. Génération
    semaine = client.post(f"/api/semaines/{LUNDI}/generer").json()
    servis = [c for c in semaine["creneaux"] if c["plat_id"]]
    assert len(servis) == 13
    assert all(c["raisons"] for c in servis if not c["restes_de"])

    # 3. Modification d'un repas : alternatives puis choix manuel (verrouillé)
    alternatives = client.get(f"/api/semaines/{LUNDI}/creneaux/2/soir/alternatives").json()
    assert alternatives
    choix = alternatives[0]["plat_id"]
    semaine = client.put(f"/api/semaines/{LUNDI}/creneaux/2/soir", json={"plat_id": choix}).json()
    mercredi_soir = next(c for c in semaine["creneaux"] if c["cle"] == "2-soir")
    assert mercredi_soir["plat_id"] == choix and mercredi_soir["verrouille"]
    semaine = client.post(f"/api/semaines/{LUNDI}/generer", params={"varier": True}).json()
    assert next(c for c in semaine["creneaux"] if c["cle"] == "2-soir")["plat_id"] == choix

    # 4. Bilan
    bilan = client.get(f"/api/semaines/{LUNDI}/bilan").json()
    assert bilan["nb_repas"] == 13 and bilan["nb_jokers"] == 1
    assert bilan["co2_kg"] < bilan["co2_reference_kg"]

    # 5. Courses et PDF
    courses = client.get(f"/api/semaines/{LUNDI}/courses").json()
    assert courses["rayons"] and courses["total_eur"] > 0
    for chemin in ("courses.pdf", "menu.pdf"):
        pdf = client.get(f"/api/semaines/{LUNDI}/{chemin}")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # 6. Courses faites : le placard récupère les surplus
    assert client.post(f"/api/semaines/{LUNDI}/courses/valider").status_code == 204
    assert client.post(f"/api/semaines/{LUNDI}/courses/valider").status_code == 409
    placard = client.get("/api/placard").json()
    assert placard


def test_notes(client: TestClient):
    alex, sam, _ = ajouter_famille(client)
    lundi = date.today() - timedelta(days=date.today().weekday() + 7)
    client.get(f"/api/semaines/{lundi}")
    client.post(f"/api/semaines/{lundi}/generer")
    a_noter = client.get("/api/notes/a-noter").json()
    assert a_noter
    repas = a_noter[0]

    def noter(membre: int, valeur: int) -> int:
        corps = {
            "membre_id": membre,
            "valeur": valeur,
            "creneau_id": repas["creneau_id"],
            "recette_id": repas["recette_id"],
        }
        return client.put("/api/notes", json=corps).status_code

    assert noter(alex, 5) == 200
    assert noter(sam, 4) == 200
    assert noter(alex, 3) == 200  # modifier une note ne la duplique pas
    mis_a_jour = next(
        r for r in client.get("/api/notes/a-noter").json() if r["creneau_id"] == repas["creneau_id"]
    )
    assert mis_a_jour["notes"] == {str(alex): 3, str(sam): 4}
    recette = next(
        r for r in client.get("/api/recettes").json() if r["recette"]["id"] == repas["recette_id"]
    )
    assert recette["note_famille"] == 3.5


def test_placard_manuel(client: TestClient):
    assert client.put("/api/placard/riz", json={"quantite_g": 400}).status_code == 200
    assert client.get("/api/placard").json()[0]["ingredient_id"] == "riz"
    client.put("/api/placard/riz", json={"quantite_g": 0})
    assert client.get("/api/placard").json() == []
    assert client.put("/api/placard/licorne", json={"quantite_g": 1}).status_code == 404


def test_import_de_recettes(client: TestClient):
    instructions = client.get("/api/import/instructions-ia.md")
    assert instructions.status_code == 200 and "Ingrédients autorisés" in instructions.text

    contenu = json.dumps({"format": "menu-famille/recettes", "version": 1, "recettes": [
        {"id": "soupe-test", "nom": "Soupe test", "type": "plat", "etapes": ["Mixer."],
         "lien": "https://exemple.fr/soupe",
         "ingredients": {"poireau": 200, "pomme-de-terre": 150, "lentilles-corail": 50,
                         "pain-complet": 60}},
    ]})  # fmt: skip
    envoi = {"fichier": ("recettes.json", contenu, "application/json")}
    apercu = client.post("/api/import/recettes", files=envoi).json()
    assert apercu["nb_acceptees"] == 1 and not apercu["applique"]

    resultat = client.post("/api/import/recettes", params={"appliquer": True}, files=envoi).json()
    assert resultat["applique"]
    recettes = {r["recette"]["id"]: r for r in client.get("/api/recettes").json()}
    assert recettes["soupe-test"]["importee"]

    assert client.delete("/api/recettes/dahl-lentilles-corail").status_code == 404
    assert client.delete("/api/recettes/soupe-test").status_code == 204
    assert "soupe-test" not in {r["recette"]["id"] for r in client.get("/api/recettes").json()}


def test_reglages(client: TestClient):
    reglages = client.get("/api/reglages").json()
    reglages["priorite_budget"] = 3
    assert client.put("/api/reglages", json=reglages).json()["priorite_budget"] == 3
    assert client.get(f"/api/semaines/{LUNDI}").status_code == 200
    assert client.get("/api/semaines/2026-12-01").status_code == 400  # pas un lundi


def test_suppression_definitive_d_un_membre(client: TestClient):
    alex, sam, leo = ajouter_famille(client)
    lundi = date.today() - timedelta(days=date.today().weekday() + 7)
    client.get(f"/api/semaines/{lundi}")
    client.post(f"/api/semaines/{lundi}/generer")
    repas = client.get("/api/notes/a-noter").json()[0]
    client.put("/api/notes", json={"membre_id": leo, "valeur": 5, "creneau_id": repas["creneau_id"],
                                  "recette_id": repas["recette_id"]})  # fmt: skip

    assert client.delete(f"/api/membres/{leo}").status_code == 204
    assert [m["id"] for m in client.get("/api/membres").json()] == [alex, sam]
    semaine = client.get(f"/api/semaines/{lundi}").json()
    assert all(leo not in c["convives"] for c in semaine["creneaux"])
    notes = next(r for r in client.get("/api/notes/a-noter").json()
                 if r["creneau_id"] == repas["creneau_id"])["notes"]  # fmt: skip
    assert str(leo) not in notes
    assert client.delete(f"/api/membres/{leo}").status_code == 404


def test_lien_de_recette(client: TestClient):
    contenu = json.dumps({"format": "menu-famille/recettes", "version": 1, "recettes": [
        {"id": "avec-lien", "nom": "Avec lien", "type": "dessert", "ingredients": {"pomme": 150},
         "lien": "https://exemple.fr/recette"},
        {"id": "lien-invalide", "nom": "Lien invalide", "type": "dessert",
         "ingredients": {"pomme": 150}, "lien": "javascript:alert(1)"},
        {"id": "lien-introuvable", "nom": "Lien introuvable", "type": "dessert",
         "ingredients": {"pomme": 150}, "lien": "https://exemple.fr/introuvable"},
    ]})  # fmt: skip
    envoi = {"fichier": ("r.json", contenu, "application/json")}
    rapport = client.post("/api/import/recettes", params={"appliquer": True}, files=envoi).json()
    assert [r["acceptee"] for r in rapport["recettes"]] == [True, False, False]
    recettes = {r["recette"]["id"]: r for r in client.get("/api/recettes").json()}
    assert recettes["avec-lien"]["recette"]["lien"] == "https://exemple.fr/recette"
    assert recettes["dahl-lentilles-corail"]["recette"]["lien"].startswith("https://")
    assert recettes["dahl-lentilles-corail"]["ingredients_unites"]["lait-coco"] == "ml"


def test_infos_du_repas_et_bilan(client: TestClient):
    ajouter_famille(client)
    lundi = date.today() - timedelta(days=date.today().weekday() + 7)
    client.get(f"/api/semaines/{lundi}")
    semaine = client.post(f"/api/semaines/{lundi}/generer").json()
    infos = next(c["infos"] for c in semaine["creneaux"] if c["plat_id"])
    assert infos["nutriscore"] in "ABCDE"
    assert infos["co2_kg"] > 0 and infos["prix_eur"] > 0 and infos["energie_kcal"] > 300

    bilan = client.get("/api/bilan", params={"semaines": 4}).json()
    assert len(bilan["semaines"]) == 1
    hebdo = bilan["semaines"][0]
    assert hebdo["budget_estime"] and hebdo["nutriscore_moyen"] in "ABCDE"
    assert "laitiers" in hebdo["reperes"] and 0 <= hebdo["part_saison"] <= 100
    assert sum(hebdo["proteines"].values()) == hebdo["nb_repas"]
    assert bilan["nb_plats_differents"] > 5 and bilan["jamais_servis"]
    assert {m["prenom"] for m in bilan["membres"]} == {"Alex", "Sam", "Léo"}
    assert all(50 < m["couverture_energie"] < 200 for m in bilan["membres"])

    client.post(f"/api/semaines/{lundi}/courses/valider")
    apres = client.get("/api/bilan", params={"semaines": 4}).json()
    assert not apres["semaines"][0]["budget_estime"]
    assert apres["gaspillage"]["semaines_validees"] == 1
