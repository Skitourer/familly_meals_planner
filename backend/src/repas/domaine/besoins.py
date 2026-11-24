"""Besoins énergétiques individuels et coefficient de portion.

Méthode (détaillée dans ``docs/algorithme.md``) :

1. **Métabolisme de base (MB)** : équations de Henry (2005, *Public Health
   Nutrition* 8(7A)), version « poids seul ». Elles couvrent tous les âges, y
   compris les enfants, et sont utilisées par l'EFSA et le SACN britannique.
2. **Niveau d'activité physique (NAP)** : un niveau de base selon le mode de vie,
   augmenté de la dépense des séances de sport hebdomadaires :
   ``ΔNAP = (MET - 1) × heures / 168`` (168 heures dans une semaine).
3. **Besoin énergétique** = MB × NAP.
4. **Coefficient de portion** = besoin / 2 000 kcal (adulte de référence,
   règlement UE 1169/2011). Les recettes sont écrites pour une portion de
   référence ; la portion de chacun est multipliée par son coefficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

ENERGIE_REFERENCE_KCAL = 2000
KCAL_PAR_MJ = 239.0
MET_SPORT = 7.0  # intensité moyenne d'une séance modérée à soutenue
NAP_MAX = 2.2


class Sexe(StrEnum):
    FEMME = "F"
    HOMME = "H"


class ModeDeVie(StrEnum):
    """Activité hors sport (travail, trajets, tâches quotidiennes)."""

    SEDENTAIRE = "sedentaire"  # travail assis, peu de marche
    MODERE = "modere"  # debout une partie de la journée, trajets à pied ou à vélo
    ACTIF = "actif"  # métier physique, enfant très actif


NAP_BASE: dict[ModeDeVie, float] = {
    ModeDeVie.SEDENTAIRE: 1.4,
    ModeDeVie.MODERE: 1.6,
    ModeDeVie.ACTIF: 1.8,
}

# Henry (2005), poids seul : MB (MJ/jour) = a × poids + b, par tranche d'âge.
# (âge minimal inclus, a, b)
_HENRY: dict[Sexe, list[tuple[int, float, float]]] = {
    Sexe.HOMME: [
        (0, 0.255, -0.141),
        (3, 0.0937, 2.15),
        (10, 0.0769, 2.43),
        (18, 0.0669, 2.28),
        (30, 0.0592, 2.48),
        (60, 0.0563, 2.15),
    ],
    Sexe.FEMME: [
        (0, 0.246, -0.0965),
        (3, 0.0842, 2.12),
        (10, 0.0465, 3.18),
        (18, 0.0546, 2.33),
        (30, 0.0407, 2.90),
        (60, 0.0424, 2.38),
    ],
}


@dataclass(frozen=True)
class ProfilPhysique:
    age: int
    poids_kg: float
    sexe: Sexe
    mode_de_vie: ModeDeVie = ModeDeVie.SEDENTAIRE
    heures_sport_semaine: float = 0.0


def metabolisme_de_base_kcal(age: int, poids_kg: float, sexe: Sexe) -> float:
    """Métabolisme de base (kcal/jour) selon Henry (2005)."""
    if age < 0 or poids_kg <= 0:
        raise ValueError("Âge et poids doivent être positifs")
    _, a, b = next(t for t in reversed(_HENRY[sexe]) if age >= t[0])
    return (a * poids_kg + b) * KCAL_PAR_MJ


def niveau_activite(mode_de_vie: ModeDeVie, heures_sport_semaine: float) -> float:
    """NAP = niveau de base + dépense liée au sport, plafonné à 2,2."""
    bonus_sport = (MET_SPORT - 1) * max(heures_sport_semaine, 0) / 168
    return min(NAP_BASE[mode_de_vie] + bonus_sport, NAP_MAX)


def besoin_energetique_kcal(profil: ProfilPhysique) -> float:
    """Dépense énergétique totale estimée (kcal/jour)."""
    mb = metabolisme_de_base_kcal(profil.age, profil.poids_kg, profil.sexe)
    return mb * niveau_activite(profil.mode_de_vie, profil.heures_sport_semaine)


def coefficient_portion(profil: ProfilPhysique) -> float:
    """Taille de portion relative à l'adulte de référence (1,0 = 2 000 kcal/jour)."""
    coefficient = besoin_energetique_kcal(profil) / ENERGIE_REFERENCE_KCAL
    return round(min(max(coefficient, 0.3), 1.8), 2)
