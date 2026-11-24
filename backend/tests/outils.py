"""Aides partagées par les tests (importées par les modules de test)."""

from fastapi.testclient import TestClient


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
