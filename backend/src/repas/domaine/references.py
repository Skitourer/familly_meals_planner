"""Références nutritionnelles journalières par âge et par sexe.

Nutriments retenus : ceux dont les apports sont le plus souvent insuffisants en
France (ANSES, étude INCA 3) et que les repas de midi et du soir influencent
directement — calcium, fer, folates, fibres, oméga-3 à longue chaîne (EPA + DHA) —
ainsi que la vitamine C.

Valeurs : références nutritionnelles pour la population (RNP) ou apports
satisfaisants (AS) de l'EFSA (*Dietary Reference Values*, 2013-2017), reprises par
l'ANSES (*Actualisation des références nutritionnelles*, 2016 et 2021 pour les
enfants). Fibres de l'adulte : 30 g/jour (ANSES). Fer de la femme de 18 à 49 ans :
16 mg/jour (EFSA, couvre les pertes menstruelles élevées ; l'ANSES retient 11 mg pour
des pertes faibles ou normales).

Ces références couvrent les besoins de presque toute la population : un apport
inférieur n'est pas une carence, mais un point d'attention.
"""

from __future__ import annotations

from repas.domaine.besoins import Sexe

# Nutriment -> (unité, libellé).
NUTRIMENTS_SUIVIS: dict[str, tuple[str, str]] = {
    "calcium_mg": ("mg", "Calcium"),
    "fer_mg": ("mg", "Fer"),
    "vitamine_c_mg": ("mg", "Vitamine C"),
    "fibres_g": ("g", "Fibres"),
    "folates_ug": ("µg", "Folates (B9)"),
    "epa_dha_g": ("g", "Oméga-3 EPA + DHA"),
}

# (âge minimal, valeur homme, valeur femme), par ordre d'âge croissant.
_TABLE: dict[str, list[tuple[int, float, float]]] = {
    "calcium_mg": [(1, 450, 450), (4, 800, 800), (11, 1150, 1150), (18, 1000, 1000),
                   (25, 950, 950)],
    "fer_mg": [(1, 7, 7), (7, 11, 11), (12, 11, 13), (18, 11, 16), (50, 11, 11)],
    "vitamine_c_mg": [(1, 20, 20), (4, 30, 30), (7, 45, 45), (11, 70, 70), (15, 100, 90),
                      (18, 110, 95)],
    "fibres_g": [(1, 10, 10), (4, 14, 14), (7, 16, 16), (11, 19, 19), (15, 21, 21),
                 (18, 30, 30)],
    "folates_ug": [(1, 120, 120), (4, 140, 140), (7, 200, 200), (11, 270, 270),
                   (15, 330, 330)],
    "epa_dha_g": [(1, 0.1, 0.1), (2, 0.25, 0.25)],
}  # fmt: skip


def reference_journaliere(nutriment: str, age: int, sexe: Sexe) -> float:
    """Apport de référence journalier d'un nutriment pour un âge et un sexe."""
    tranches = _TABLE[nutriment]
    _, homme, femme = next((t for t in reversed(tranches) if age >= t[0]), tranches[0])
    return homme if sexe == Sexe.HOMME else femme
