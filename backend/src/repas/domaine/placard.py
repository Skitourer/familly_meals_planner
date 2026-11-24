"""Frigo à vider : produits du placard à consommer vite et plats qui les utilisent.

Un produit est « à vider » quand sa date limite tombe dans les 7 prochains jours.
Le planificateur le favorise fortement (voir ``Poids.frigo_a_vider``) ; ce module
fournit en plus une liste d'idées de plats, sans lancer le solveur.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from repas.catalogue import Catalogue

JOURS_AVANT_PEREMPTION = 7  # horizon « à vider » : une semaine de repas
NOMBRE_IDEES = 8


@dataclass(frozen=True)
class IdeePlat:
    """Plat qui consomme une partie des produits à vider."""

    plat: str
    ingredients: tuple[str, ...]  # produits à vider utilisés
    part_videe: float  # somme, sur les produits à vider, de la part consommée (0 à 1 chacun)


def a_vider(peremption: date, le: date) -> bool:
    """Vrai si le produit doit être consommé dans la semaine qui commence ``le``."""
    return (peremption - le).days < JOURS_AVANT_PEREMPTION


def jours_limites(peremptions: dict[str, date], lundi: date) -> dict[str, int]:
    """Dernier jour de la semaine (0 = lundi) où consommer chaque produit à vider."""
    return {
        id_ing: (peremption - lundi).days
        for id_ing, peremption in peremptions.items()
        if a_vider(peremption, lundi)
    }


def idees_pour_vider(
    stock: dict[str, float], catalogue: Catalogue, portions: float
) -> list[IdeePlat]:
    """Plats qui consomment la plus grande part des produits à vider.

    ``stock`` : produits à vider et quantités (g) ; ``portions`` : somme des coefficients
    de portion des convives habituels. Les ingrédients basiques (sel, huile...) sont ignorés.
    """
    idees: list[IdeePlat] = []
    for profil in catalogue.plats():
        utilises = [
            id_ing
            for id_ing in profil.recette.ingredients
            if stock.get(id_ing, 0) > 0 and not catalogue.ingredients[id_ing].basique
        ]
        if not utilises:
            continue
        part = sum(
            min(profil.recette.ingredients[i] * portions, stock[i]) / stock[i] for i in utilises
        )
        idees.append(IdeePlat(profil.recette.id, tuple(utilises), round(part, 2)))
    idees.sort(key=lambda idee: (-idee.part_videe, idee.plat))
    return idees[:NOMBRE_IDEES]
