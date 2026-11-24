"""Nutri-Score d'un repas (algorithme 2023 des aliments « généraux »).

Le Nutri-Score est conçu pour des produits emballés ; on l'applique ici, à titre
**indicatif**, à un repas complet (plat + dessert) ramené à 100 g. Source :
Santé publique France, *Update of the Nutri-Score algorithm* (comité scientifique,
2022-2023), en vigueur depuis 2024.

Points négatifs (N) pour 100 g : énergie (0-10), sucres (0-15), acides gras saturés
(0-10), sel (0-20). Points positifs (P) : protéines (0-7), fibres (0-5), fruits,
légumes et légumineuses (0-5).

Score = N - P, sauf si N ≥ 11 : les protéines ne sont alors pas comptées (sauf si
les fruits, légumes et légumineuses rapportent déjà le maximum de 5 points).

Classes : A ≤ 0, B 1-2, C 3-10, D 11-18, E ≥ 19.

Le poids du repas tient compte de l'eau absorbée à la cuisson par les féculents et
légumes secs (``rendement_cuisson`` des ingrédients) ; l'eau des soupes et bouillons
n'est pas comptée, ce qui rend le score des soupes légèrement sévère.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from repas.catalogue.schemas import Nutriments

type Lettre = Literal["A", "B", "C", "D", "E"]

# Seuils : un point par seuil strictement dépassé.
SEUILS_ENERGIE_KJ = [335, 670, 1005, 1340, 1675, 2010, 2345, 2680, 3015, 3350]
SEUILS_SUCRES_G = [3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51]
SEUILS_AGS_G = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
SEUILS_SEL_G = [round(0.2 * i, 1) for i in range(1, 21)]  # 0,2 à 4,0 g
SEUILS_PROTEINES_G = [2.4, 4.8, 7.2, 9.6, 12, 14, 17]
SEUILS_FIBRES_G = [3.0, 4.1, 5.2, 6.3, 7.4]
KJ_PAR_KCAL = 4.184


@dataclass(frozen=True)
class NutriScore:
    lettre: Lettre
    score: int
    points_negatifs: int
    points_positifs: int


def _points(valeur: float, seuils: Sequence[float]) -> int:
    """Nombre de seuils strictement dépassés par ``valeur``."""
    return bisect_left(seuils, valeur)


def _points_fruits_legumes(pourcentage: float) -> int:
    if pourcentage > 80:
        return 5
    if pourcentage > 60:
        return 2
    return 1 if pourcentage > 40 else 0


def lettre(score: int) -> Lettre:
    if score <= 0:
        return "A"
    if score <= 2:
        return "B"
    if score <= 10:
        return "C"
    return "D" if score <= 18 else "E"


def nutriscore(nutriments: Nutriments, poids_g: float, fruits_legumes_g: float) -> NutriScore:
    """Nutri-Score de ``poids_g`` grammes d'aliment ayant ces ``nutriments``."""
    if poids_g <= 0:
        raise ValueError("Le poids doit être positif")
    pour_100g = nutriments.fois(100 / poids_g)
    negatifs = (
        _points(pour_100g.energie_kcal * KJ_PAR_KCAL, SEUILS_ENERGIE_KJ)
        + _points(pour_100g.sucres_g, SEUILS_SUCRES_G)
        + _points(pour_100g.ags_g, SEUILS_AGS_G)
        + _points(pour_100g.sel_g, SEUILS_SEL_G)
    )
    fruits_legumes = _points_fruits_legumes(100 * fruits_legumes_g / poids_g)
    fibres = _points(pour_100g.fibres_g, SEUILS_FIBRES_G)
    proteines = _points(pour_100g.proteines_g, SEUILS_PROTEINES_G)
    if negatifs >= 11 and fruits_legumes < 5:
        proteines = 0
    positifs = fruits_legumes + fibres + proteines
    score = negatifs - positifs
    return NutriScore(lettre(score), score, negatifs, positifs)
