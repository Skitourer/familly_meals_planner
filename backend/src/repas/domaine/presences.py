"""Présences aux repas : un membre nouveau (ou de retour) rejoint les repas à venir."""

from datetime import date, timedelta


def creneau_a_venir(lundi: date, jour: int, aujourd_hui: date) -> bool:
    """Repas d'aujourd'hui ou plus tard : les jours passés gardent leurs convives (bilans)."""
    return lundi + timedelta(days=jour) >= aujourd_hui


def convives_avec(convives: list[int], membre_id: int) -> list[int]:
    """Convives d'un repas avec ce membre, dans l'ordre des identifiants (comme à la création
    d'une semaine)."""
    return convives if membre_id in convives else sorted([*convives, membre_id])
