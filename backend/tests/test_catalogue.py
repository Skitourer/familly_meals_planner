"""Cohérence des données : ces tests protègent le catalogue lors des contributions."""

import pytest

from repas.catalogue import Catalogue
from repas.catalogue.schemas import Famille


def test_catalogue_complet(cat: Catalogue):
    assert len(cat.plats(plaisir=False)) >= 40
    assert len(cat.plats(plaisir=True)) >= 5
    assert len(cat.desserts()) >= 15


def test_chaque_ingredient_a_des_donnees_ouvertes(cat: Catalogue):
    manquants = set(cat.ingredients) - set(cat.aliments)
    assert not manquants, f"Relancer `uv run repas-import` : {manquants}"


def test_chaque_ingredient_a_une_empreinte_carbone(cat: Catalogue):
    sans = [i for i, a in cat.aliments.items() if a.co2_kg_par_kg is None]
    assert not sans, f"Ajouter `ciqual_agribalyse` pour : {sans}"


def test_ingredients_saisonniers_ont_un_calendrier(cat: Catalogue):
    for ing in cat.ingredients.values():
        if ing.saison:
            assert cat.mois_saison(ing.id), ing.id


def test_chaque_paquet_a_des_formats(cat: Catalogue):
    for ing in cat.ingredients.values():
        if ing.vente.mode == "paquet":
            assert cat.formats_vente(ing.id), f"{ing.id} : formats de vente inconnus"


@pytest.mark.parametrize("type_recette", ["plat", "dessert"])
def test_energie_plausible(cat: Catalogue, type_recette: str):
    bornes = {"plat": (350, 800), "dessert": (40, 350)}[type_recette]
    for p in cat.profils.values():
        if p.recette.type == type_recette:
            assert bornes[0] <= p.nutriments.energie_kcal <= bornes[1], p.id


def test_plats_quotidiens_assez_proteines_et_legumes(cat: Catalogue):
    for p in cat.plats(plaisir=False):
        assert p.nutriments.proteines_g >= 15, p.id
        assert p.fruits_legumes_g >= 75, p.id


def test_familles_pnns(cat: Catalogue):
    saumon = cat.profils["saumon-brocoli-riz"]
    assert saumon.est_poisson and saumon.est_poisson_gras
    assert cat.profils["dahl-lentilles-corail"].est_legumineuse
    assert cat.profils["spaghetti-bolognaise"].grammes_par_famille[Famille.VIANDE_ROUGE] == 70


def test_saisonnalite(cat: Catalogue):
    ratatouille = cat.profils["ratatouille-oeufs"]
    assert ratatouille.hors_saison(7) == []
    assert "tomate" in ratatouille.hors_saison(1)


def test_chaque_mois_a_assez_de_plats_de_saison(cat: Catalogue):
    for mois in range(1, 13):
        de_saison = [p for p in cat.plats(plaisir=False) if not p.hors_saison(mois)]
        assert len(de_saison) >= 14, f"mois {mois} : {len(de_saison)} plats de saison"
