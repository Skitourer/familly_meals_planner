import pytest

from repas.domaine.besoins import Sexe
from repas.domaine.references import NUTRIMENTS_SUIVIS, reference_journaliere


@pytest.mark.parametrize(
    ("nutriment", "age", "sexe", "attendu"),
    [("calcium_mg", 15, Sexe.HOMME, 1150), ("calcium_mg", 40, Sexe.FEMME, 950),
     ("fer_mg", 30, Sexe.FEMME, 16), ("fer_mg", 30, Sexe.HOMME, 11), ("fer_mg", 60, Sexe.FEMME, 11),
     ("fer_mg", 14, Sexe.FEMME, 13), ("vitamine_c_mg", 8, Sexe.HOMME, 45),
     ("fibres_g", 40, Sexe.HOMME, 30), ("fibres_g", 5, Sexe.FEMME, 14),
     ("folates_ug", 40, Sexe.FEMME, 330), ("epa_dha_g", 1, Sexe.HOMME, 0.1)],
)  # fmt: skip
def test_references(nutriment, age, sexe, attendu):
    assert reference_journaliere(nutriment, age, sexe) == attendu


def test_tous_les_ages_ont_une_reference():
    for nutriment in NUTRIMENTS_SUIVIS:
        for age in range(0, 100):
            for sexe in Sexe:
                assert reference_journaliere(nutriment, age, sexe) > 0
