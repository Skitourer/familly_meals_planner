"""Un membre créé (ou de retour) rejoint les repas à venir des semaines déjà créées (#72)."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from repas.domaine.presences import convives_avec, creneau_a_venir
from repas.services import lundi_de

LUNDI = date(2026, 11, 30)
LEO = {"prenom": "Léo", "date_naissance": "2016-01-20", "sexe": "H", "poids_kg": 30,
       "mode_de_vie": "actif"}  # fmt: skip
SAM = {"prenom": "Sam", "date_naissance": "1987-07-15", "sexe": "F", "poids_kg": 60}

# Semaines relatives à aujourd'hui (la route utilise la date du jour) : l'une entièrement
# passée, l'autre entièrement à venir, quel que soit le jour où les tests tournent.
SEMAINE_PASSEE = lundi_de(date.today()) - timedelta(days=7)
SEMAINE_A_VENIR = lundi_de(date.today()) + timedelta(days=7)


def test_creneau_a_venir_a_partir_d_aujourd_hui():
    mercredi = LUNDI + timedelta(days=2)
    assert not creneau_a_venir(LUNDI, 1, mercredi)
    assert creneau_a_venir(LUNDI, 2, mercredi)
    assert creneau_a_venir(LUNDI, 6, mercredi)
    assert creneau_a_venir(LUNDI + timedelta(days=7), 0, mercredi)


def test_convives_avec_un_membre_dans_l_ordre():
    assert convives_avec([3, 1], 2) == [1, 2, 3]
    assert convives_avec([1, 2], 2) == [1, 2]
    assert convives_avec([], 5) == [5]


def convives(client: TestClient, lundi: date) -> dict[str, list[int]]:
    semaine = client.get(f"/api/semaines/{lundi}").json()
    return {c["cle"]: c["convives"] for c in semaine["creneaux"]}


def test_nouveau_membre_rejoint_les_repas_a_venir(client: TestClient):
    sam = client.post("/api/membres", json=SAM).json()["id"]
    convives(client, SEMAINE_PASSEE)  # semaines ouvertes avant l'arrivée de Léo
    convives(client, SEMAINE_A_VENIR)

    leo = client.post("/api/membres", json=LEO).json()["id"]

    assert set(map(tuple, convives(client, SEMAINE_A_VENIR).values())) == {(sam, leo)}
    assert set(map(tuple, convives(client, SEMAINE_PASSEE).values())) == {(sam,)}


def test_membre_inactif_n_est_pas_ajoute(client: TestClient):
    convives(client, SEMAINE_A_VENIR)
    client.post("/api/membres", json={**LEO, "actif": False})
    assert set(map(tuple, convives(client, SEMAINE_A_VENIR).values())) == {()}


def test_membre_de_retour_sauf_repas_pris_dehors(client: TestClient):
    sam = client.post("/api/membres", json=SAM).json()["id"]
    leo = client.post("/api/membres", json=LEO).json()["id"]
    url = f"/api/semaines/{SEMAINE_A_VENIR}/creneaux"
    convives(client, SEMAINE_A_VENIR)
    # Léo mange à la cantine lundi midi, et n'est pas là mardi soir (sans précision).
    for cle in ("0/midi", "1/soir"):
        client.put(f"{url}/{cle}", json={"convives": [sam]})
    reponse = client.put(f"{url}/0/midi/exterieurs/{leo}", json={"categorie": "poisson"})
    assert reponse.status_code == 200

    client.put(f"/api/membres/{leo}", json={**LEO, "actif": False})
    client.put(f"/api/membres/{leo}", json={**LEO, "actif": True})

    apres = convives(client, SEMAINE_A_VENIR)
    assert apres["0-midi"] == [sam]  # repas à l'extérieur respecté
    assert apres["1-soir"] == [sam, leo]
    assert all(leo in c for c in apres.values() if c != [sam])
