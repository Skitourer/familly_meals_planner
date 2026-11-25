"""Courses faites : articles non cochés et réouverture (issue #46)."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from outils import ajouter_famille

LUNDI = "2026-11-30"
URL = f"/api/semaines/{LUNDI}/courses"


def preparer(client: TestClient) -> list[dict]:
    ajouter_famille(client)
    client.post(f"/api/semaines/{LUNDI}/generer")
    return [x for _, xs in client.get(URL).json()["rayons"] for x in xs]


def placard(client: TestClient) -> dict[str, float]:
    return {p["ingredient_id"]: p["quantite_g"] for p in client.get("/api/placard").json()}


def cocher(client: TestClient, ids: list[str]) -> None:
    maintenant = datetime.now(UTC).isoformat()
    coches = [{"ingredient_id": i, "cochee": True, "modifiee_le": maintenant} for i in ids]
    assert client.put(f"{URL}/coches", json=coches).status_code == 200


def test_articles_non_coches_non_achetes(client: TestClient):
    lignes = preparer(client)
    avec_reste = [x for x in lignes if x["surplus"] and x["surplus_au_placard"]]
    achete, oublie = avec_reste[0], avec_reste[1]
    cocher(client, [achete["ingredient_id"]])

    assert client.post(f"{URL}/valider", json={"tout_achete": False}).status_code == 204
    contenu = placard(client)
    assert achete["ingredient_id"] in contenu and oublie["ingredient_id"] not in contenu
    validee = client.get(URL).json()
    assert validee["validees"]
    # La liste affichée reste celle des courses, sans les surplus rangés depuis.
    assert [x["ingredient_id"] for _, xs in validee["rayons"] for x in xs] == [
        x["ingredient_id"] for x in lignes
    ]


def test_rouvrir_puis_revalider(client: TestClient):
    sur_la_liste = {x["ingredient_id"] for x in preparer(client)}
    client.put("/api/placard/riz", json={"quantite_g": 400})
    avant = placard(client)

    assert client.post(f"{URL}/valider").status_code == 204  # sans corps : tout acheté
    apres = placard(client)
    assert apres != avant
    # Ajout à la main d'un ingrédient que la validation n'a pas touché : il est conservé.
    ajout = next(i["id"] for i in client.get("/api/ingredients").json()
                 if not i["basique"] and i["conservation_jours"] > 30
                 and i["id"] not in sur_la_liste | apres.keys())  # fmt: skip
    client.put(f"/api/placard/{ajout}", json={"quantite_g": 250})

    assert client.post(f"{URL}/rouvrir").status_code == 204
    assert placard(client) == {**avant, ajout: 250}
    assert not client.get(URL).json()["validees"]
    assert client.post(f"{URL}/rouvrir").status_code == 409

    assert client.post(f"{URL}/valider", json={"tout_achete": True}).status_code == 204
    assert placard(client) == {**apres, ajout: 250}
