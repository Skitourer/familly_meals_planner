import pytest

from repas.domaine.besoins import (
    ModeDeVie,
    ProfilPhysique,
    Sexe,
    besoin_energetique_kcal,
    coefficient_portion,
    metabolisme_de_base_kcal,
    niveau_activite,
)


def test_metabolisme_adulte_henry():
    # Homme de 40 ans, 75 kg : (0,0592 × 75 + 2,48) MJ × 239 ≈ 1 654 kcal
    assert metabolisme_de_base_kcal(40, 75, Sexe.HOMME) == pytest.approx(1654, abs=2)


def test_metabolisme_enfant():
    # Fille de 8 ans, 25 kg : (0,0842 × 25 + 2,12) MJ ≈ 1 010 kcal
    assert metabolisme_de_base_kcal(8, 25, Sexe.FEMME) == pytest.approx(1010, abs=2)


def test_sport_augmente_le_niveau_activite():
    sans = niveau_activite(ModeDeVie.SEDENTAIRE, 0)
    avec = niveau_activite(ModeDeVie.SEDENTAIRE, 4)
    assert sans == 1.4
    assert avec == pytest.approx(1.4 + 6 * 4 / 168)


def test_niveau_activite_plafonne():
    assert niveau_activite(ModeDeVie.ACTIF, 40) == 2.2


def test_adulte_moyen_proche_de_la_reference():
    femme = ProfilPhysique(age=40, poids_kg=62, sexe=Sexe.FEMME, mode_de_vie=ModeDeVie.MODERE)
    assert 1800 < besoin_energetique_kcal(femme) < 2200
    assert 0.9 <= coefficient_portion(femme) <= 1.1


def test_enfant_a_une_plus_petite_portion():
    enfant = ProfilPhysique(age=6, poids_kg=20, sexe=Sexe.HOMME, mode_de_vie=ModeDeVie.ACTIF)
    adolescent = ProfilPhysique(age=16, poids_kg=65, sexe=Sexe.HOMME, heures_sport_semaine=6)
    assert coefficient_portion(enfant) < 0.9 < coefficient_portion(adolescent)


def test_valeurs_invalides():
    with pytest.raises(ValueError):
        metabolisme_de_base_kcal(30, 0, Sexe.FEMME)
