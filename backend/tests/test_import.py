import json

from repas.catalogue import Catalogue
from repas.catalogue.import_recettes import analyser_import, instructions_ia
from repas.config import RACINE_DEPOT

RECETTE_OK = {
    "id": "poelee-test",
    "nom": "Poêlée test",
    "type": "plat",
    "ingredients": {"poireau": 180, "pois-chiches": 120, "riz-complet": 70},
    "etapes": ["Cuire.", "Servir."],
}


def fichier(*recettes: dict) -> str:
    return json.dumps({"format": "menu-famille/recettes", "version": 1, "recettes": recettes})


def test_recette_valide(cat: Catalogue):
    rapport, acceptees = analyser_import(fichier(RECETTE_OK), cat)
    assert rapport.nb_acceptees == 1
    assert acceptees[0].source == "Import JSON"
    assert rapport.recettes[0].avertissements == []


def test_ingredient_inconnu_refuse(cat: Catalogue):
    recette = RECETTE_OK | {"ingredients": {"licorne": 100}}
    rapport, acceptees = analyser_import(fichier(recette), cat)
    assert not acceptees
    assert "licorne" in rapport.recettes[0].erreurs[0]


def test_identifiant_existant_ou_double(cat: Catalogue):
    rapport, _ = analyser_import(fichier(RECETTE_OK | {"id": "dahl-lentilles-corail"}), cat)
    assert not rapport.recettes[0].acceptee
    rapport, _ = analyser_import(fichier(RECETTE_OK, RECETTE_OK), cat)
    assert [r.acceptee for r in rapport.recettes] == [True, False]


def test_structure_invalide(cat: Catalogue):
    rapport, _ = analyser_import(fichier({"id": "Majuscules Interdites", "nom": "x"}), cat)
    assert rapport.recettes[0].erreurs
    rapport, _ = analyser_import("pas du json", cat)
    assert rapport.erreur_fichier


def test_avertissements_nutrition(cat: Catalogue):
    recette = RECETTE_OK | {"ingredients": {"pates": 300}, "etapes": []}
    rapport, acceptees = analyser_import(fichier(recette), cat)
    assert acceptees  # non bloquant
    avertissements = " ".join(rapport.recettes[0].avertissements)
    assert "Énergie" in avertissements and "légumes" in avertissements


def test_instructions_ia_a_jour(cat: Catalogue):
    """Le fichier docs/ia/instructions-ia.md doit être régénéré si le référentiel change.

    Commande : ``uv run python -m repas.catalogue.import_recettes``.
    """
    texte = instructions_ia(cat)
    assert "`pois-chiches`" in texte and "dahl-lentilles-corail" in texte
    publie = RACINE_DEPOT / "docs" / "ia" / "instructions-ia.md"
    assert publie.read_text(encoding="utf-8") == texte


def test_exemple_des_instructions_est_importable(cat: Catalogue):
    texte = instructions_ia(cat)
    exemple = texte.split("```json\n")[1].split("```")[0]
    rapport, _ = analyser_import(exemple, cat)
    assert rapport.nb_acceptees == 1, rapport
