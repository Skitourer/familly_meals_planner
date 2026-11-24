"""Catalogue : ingrédients, données ouvertes et recettes."""

from functools import lru_cache

from repas.catalogue.chargement import Catalogue, ProfilRecette, charger_catalogue
from repas.config import parametres

__all__ = [
    "Catalogue",
    "ProfilRecette",
    "catalogue",
    "charger_catalogue",
    "recharger_catalogue",
]


@lru_cache
def catalogue() -> Catalogue:
    """Catalogue de l'application (chargé une seule fois au démarrage)."""
    reglages = parametres()
    return charger_catalogue(reglages.dossier_donnees, reglages.dossier_recettes_importees)


def recharger_catalogue() -> Catalogue:
    """Vide le cache (après un import de recettes) et recharge le catalogue."""
    catalogue.cache_clear()
    return catalogue()
