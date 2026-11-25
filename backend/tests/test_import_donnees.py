"""Conversion des valeurs des bases ouvertes (sans accès réseau)."""

import pytest

from repas.domaine.produits import quantite_en_grammes
from repas.import_donnees.ciqual import valeur_numerique


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [(12, 12.0), ("3,5", 3.5), ("traces", 0.0), ("tr", 0.0), ("-", 0.0), ("< 0,5", 0.25),
     (None, 0.0), ("n/a", 0.0)],
)  # fmt: skip
def test_valeur_ciqual(brut, attendu):
    assert valeur_numerique(brut) == attendu


@pytest.mark.parametrize(
    ("quantite", "unite", "attendu"),
    [(500, "g", 500), ("1", "kg", 1000), (75, "cl", 750), (1, "L", 1000), (0, "g", None),
     ("abc", "g", None), (3, "pièces", None)],
)  # fmt: skip
def test_quantite_open_food_facts(quantite, unite, attendu):
    assert quantite_en_grammes(quantite, unite) == attendu
