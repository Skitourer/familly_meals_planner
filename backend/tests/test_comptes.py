"""Comptes adulte / enfant : connexion, droits, gestion des comptes."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from outils import ajouter_famille

from repas import securite

LUNDI = date.today() - timedelta(days=date.today().weekday())


def connecter(client: TestClient, identifiant: str, mot_de_passe: str) -> int:
    client.delete("/api/session")
    corps = {"identifiant": identifiant, "mot_de_passe": mot_de_passe}
    return client.post("/api/session", json=corps).status_code


@pytest.fixture
def famille(client: TestClient) -> dict[str, int]:
    """Famille, semaine en cours générée, et un compte enfant pour Léo."""
    alex, sam, leo = ajouter_famille(client)
    client.get(f"/api/semaines/{LUNDI}")
    client.post(f"/api/semaines/{LUNDI}/generer")
    reponse = client.post(
        "/api/comptes",
        json={"identifiant": "Leo", "role": "enfant", "membre_id": leo, "mot_de_passe": "leo-123"},
    )
    assert reponse.status_code == 201
    return {"alex": alex, "sam": sam, "leo": leo, "compte_leo": reponse.json()["id"]}


# --- Sécurité -----------------------------------------------------------------------


def test_hachage():
    empreinte = securite.hacher("secret")
    assert empreinte.startswith("scrypt$") and "secret" not in empreinte
    assert securite.verifier("secret", empreinte)
    assert not securite.verifier("Secret", empreinte)
    assert securite.hacher("secret") != empreinte  # sel aléatoire
    assert not securite.verifier("secret", "format-inconnu")


def test_limiteur():
    limiteur = securite.LimiteurEssais()
    for i in range(securite.ESSAIS_MAX):
        assert not limiteur.bloque("x", maintenant=float(i))
        limiteur.echec("x", maintenant=float(i))
    assert limiteur.bloque("x", maintenant=10.0)
    assert not limiteur.bloque("x", maintenant=10.0 + securite.BLOCAGE_S)


# --- Connexion ------------------------------------------------------------------------


def test_compte_initial(client: TestClient):
    etat = client.get("/api/session").json()
    assert etat == {"connecte": True, "identifiant": "famille", "role": "adulte",
                    "membre_id": None, "prenom": None}  # fmt: skip
    assert [c["identifiant"] for c in client.get("/api/comptes").json()] == ["famille"]


def test_blocage_apres_echecs(client: TestClient):
    for _ in range(securite.ESSAIS_MAX):
        assert connecter(client, "famille", "faux") == 401
    assert connecter(client, "famille", "secret") == 429


def test_changer_son_mot_de_passe(client: TestClient):
    corps = {"actuel": "faux", "nouveau": "nouveau-secret"}
    assert client.put("/api/session/mot-de-passe", json=corps).status_code == 400
    corps["actuel"] = "secret"
    assert client.put("/api/session/mot-de-passe", json=corps).status_code == 204
    assert connecter(client, "famille", "secret") == 401
    assert connecter(client, "famille", "nouveau-secret") == 200


# --- Gestion des comptes --------------------------------------------------------------


def test_regles_de_gestion(client: TestClient, famille):
    assert client.post("/api/comptes", json={"identifiant": "sans", "role": "enfant",
                       "mot_de_passe": "abcdef"}).status_code == 400  # fmt: skip
    assert client.post("/api/comptes", json={"identifiant": "leo", "role": "adulte",
                       "mot_de_passe": "abcdef"}).status_code == 409  # fmt: skip
    moi = client.get("/api/comptes").json()[0]
    assert client.delete(f"/api/comptes/{moi['id']}").status_code == 400  # pas soi-même
    retrogradation = {"identifiant": "famille", "role": "enfant", "membre_id": famille["alex"]}
    assert client.put(f"/api/comptes/{moi['id']}", json=retrogradation).status_code == 400


def test_suppression_du_membre_supprime_son_compte_enfant(client: TestClient, famille):
    client.delete(f"/api/membres/{famille['leo']}")
    assert [c["identifiant"] for c in client.get("/api/comptes").json()] == ["famille"]


# --- Droits d'un compte enfant --------------------------------------------------------


def test_un_enfant_consulte_le_menu(client: TestClient, famille):
    assert connecter(client, "leo", "leo-123") == 200
    assert client.get("/api/session").json()["prenom"] == "Léo"
    assert client.get(f"/api/semaines/{LUNDI}").status_code == 200
    assert client.get("/api/recettes").status_code == 200
    assert client.get("/api/membres").status_code == 200
    assert client.get(f"/api/semaines/{LUNDI}/menu.pdf").status_code == 200


@pytest.mark.parametrize(
    ("methode", "chemin"),
    [("post", "/api/semaines/{lundi}/generer"), ("get", "/api/semaines/{lundi}/courses"),
     ("put", "/api/semaines/{lundi}/creneaux/0/soir"), ("get", "/api/placard"),
     ("get", "/api/bilan"), ("get", "/api/comptes"), ("post", "/api/membres"),
     ("get", "/api/reglages"), ("post", "/api/import/recettes")],
)  # fmt: skip
def test_un_enfant_ne_modifie_rien(client: TestClient, famille, methode: str, chemin: str):
    assert connecter(client, "leo", "leo-123") == 200
    reponse = getattr(client, methode)(chemin.format(lundi=LUNDI), **({"json": {}} if methode
                                       in ("post", "put") else {}))  # fmt: skip
    assert reponse.status_code == 403


def test_un_enfant_note_ses_repas_passes_et_a_venir(client: TestClient, famille):
    assert connecter(client, "leo", "leo-123") == 200
    repas = client.get("/api/notes/a-noter").json()
    assert repas and all(famille["leo"] in r["convives"] for r in repas)
    a_venir = [r for r in repas if r["a_venir"]]
    if date.today().weekday() < 6:  # il reste des repas cette semaine
        assert a_venir
    cible = (a_venir or repas)[0]

    def noter(membre: int) -> int:
        corps = {"membre_id": membre, "creneau_id": cible["creneau_id"],
                 "recette_id": cible["recette_id"], "valeur": 4}  # fmt: skip
        return client.put("/api/notes", json=corps).status_code

    assert noter(famille["leo"]) == 200
    assert noter(famille["alex"]) == 403  # pas pour quelqu'un d'autre


def test_note_refusee_pour_un_absent(client: TestClient, famille):
    client.put(f"/api/semaines/{LUNDI}/creneaux/0/soir", json={"convives": [famille["alex"]]})
    repas = next(r for r in client.get("/api/notes/a-noter").json()
                 if r["convives"] == [famille["alex"]])  # fmt: skip
    corps = {"membre_id": famille["leo"], "creneau_id": repas["creneau_id"],
             "recette_id": repas["recette_id"], "valeur": 3}  # fmt: skip
    assert client.put("/api/notes", json=corps).status_code == 400  # Léo était absent
    corps |= {"membre_id": famille["alex"], "recette_id": "autre-plat"}
    assert client.put("/api/notes", json=corps).status_code == 404
