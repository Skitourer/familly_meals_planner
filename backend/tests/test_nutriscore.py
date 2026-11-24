import pytest

from repas.catalogue import Catalogue
from repas.catalogue.schemas import Nutriments
from repas.domaine.bilan import infos_repas
from repas.domaine.nutriscore import lettre, nutriscore


@pytest.mark.parametrize(
    ("score", "attendu"), [(-5, "A"), (0, "A"), (1, "B"), (2, "B"), (3, "C"), (10, "C"),
                           (11, "D"), (18, "D"), (19, "E")],
)  # fmt: skip
def test_classes_2023(score, attendu):
    assert lettre(score) == attendu


def test_legumes_nature():
    # 100 g de légumes peu caloriques et riches en fibres : très bon score.
    legumes = Nutriments(energie_kcal=30, sucres_g=3, fibres_g=3.5, proteines_g=2, sel_g=0.05)
    resultat = nutriscore(legumes, 100, fruits_legumes_g=100)
    # 5 points (100 % de légumes) + 1 point de fibres (> 3,0 g)
    assert resultat.lettre == "A" and resultat.points_positifs == 6


def test_produit_gras_sucre_sale():
    biscuit = Nutriments(energie_kcal=500, sucres_g=35, ags_g=12, sel_g=1.0, proteines_g=6)
    resultat = nutriscore(biscuit, 100, fruits_legumes_g=0)
    assert resultat.lettre == "E"
    # N ≥ 11 et peu de fruits et légumes : les protéines ne comptent pas.
    assert resultat.points_positifs == 0


def test_seuils_stricts():
    # Exactement 3,4 g de sucres : pas de point (le seuil doit être dépassé).
    assert nutriscore(Nutriments(sucres_g=3.4), 100, 0).points_negatifs == 0
    assert nutriscore(Nutriments(sucres_g=3.5), 100, 0).points_negatifs == 1


def test_poids_invalide():
    with pytest.raises(ValueError):
        nutriscore(Nutriments(), 0, 0)


def test_repas_du_catalogue(cat: Catalogue):
    equilibre = infos_repas(cat.profils["ratatouille-oeufs"], cat.profils["fruit-peche"], 3.0)
    plaisir = infos_repas(cat.profils["croque-monsieur"], cat.profils["mousse-chocolat"], 3.0)
    assert equilibre.nutriscore == "A"
    assert plaisir.nutriscore_points > equilibre.nutriscore_points
    assert equilibre.co2_kg == pytest.approx(equilibre.co2_kg_portion * 3, abs=0.02)
    assert equilibre.vegetarien and not plaisir.vegetarien
