"""Produits scannés : code-barres, quantité et rapprochement avec les ingrédients.

Un produit du commerce est identifié par son code-barres (EAN-13, EAN-8, UPC-A) et
décrit par Open Food Facts. Ce module, sans accès réseau, valide le code, lit la
fiche Open Food Facts et propose les ingrédients du référentiel correspondants grâce
à leur catégorie Open Food Facts (``categorie_off``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from repas.catalogue.schemas import Ingredient

# Longueurs GTIN : EAN-8, UPC-A (12), EAN-13 et GTIN-14 (cartons).
LONGUEURS_CODE = (8, 12, 13, 14)

FACTEURS_GRAMMES = {"g": 1, "ml": 1, "kg": 1000, "l": 1000, "cl": 10}


@dataclass(frozen=True)
class FicheProduit:
    """Ce qu'Open Food Facts dit d'un produit, réduit à l'utile."""

    code: str
    nom: str
    marque: str
    quantite_g: float | None  # contenu du paquet en g (ou ml), None si inconnu
    categories: tuple[str, ...]  # étiquettes Open Food Facts, de la plus générale à la plus précise


def code_barres_valide(code: str) -> bool:
    """Vrai si ``code`` est un GTIN bien formé (chiffres, longueur et clé de contrôle).

    Clé GS1 : en partant du chiffre qui précède la clé, poids alternés 3 et 1 ; la clé
    complète la somme au multiple de 10 supérieur.
    """
    if not code.isascii() or not code.isdigit() or len(code) not in LONGUEURS_CODE:
        return False
    chiffres = [int(c) for c in code]
    somme = sum(
        chiffre * (3 if position % 2 == 0 else 1)
        for position, chiffre in enumerate(reversed(chiffres[:-1]))
    )
    return (10 - somme % 10) % 10 == chiffres[-1]


def quantite_en_grammes(quantite: Any, unite: Any) -> float | None:
    """Convertit une quantité Open Food Facts en g (ou ml, densité ~1)."""
    try:
        valeur = float(quantite)
    except (TypeError, ValueError):
        return None
    facteur = FACTEURS_GRAMMES.get(str(unite).lower())
    return valeur * facteur if facteur and valeur > 0 else None


def lire_fiche(code: str, reponse: Mapping[str, Any]) -> FicheProduit | None:
    """Fiche d'un produit à partir de la réponse de l'API Open Food Facts (None si absent)."""
    produit = reponse.get("product")
    if reponse.get("status") != 1 or not isinstance(produit, Mapping):
        return None
    nom = produit.get("product_name_fr") or produit.get("product_name") or ""
    marque = str(produit.get("brands") or "").split(",")[0].strip()
    categories = produit.get("categories_tags") or []
    return FicheProduit(
        code=code,
        nom=str(nom).strip(),
        marque=marque,
        quantite_g=quantite_en_grammes(
            produit.get("product_quantity"), produit.get("product_quantity_unit") or "g"
        ),
        categories=tuple(str(c) for c in categories),
    )


def ingredients_correspondants(
    categories: tuple[str, ...], ingredients: Mapping[str, Ingredient]
) -> list[str]:
    """Ingrédients dont la catégorie figure dans celles du produit, les plus précis d'abord.

    Open Food Facts range les catégories de la plus générale à la plus précise : des
    pâtes complètes portent ``en:dry-pastas`` puis ``en:wholemeal-pasta`` ; l'ingrédient
    « pâtes complètes » passe donc avant « pâtes ».
    """
    rang = {categorie: position for position, categorie in enumerate(categories)}
    trouves = [i for i in ingredients.values() if i.categorie_off in rang]
    trouves.sort(key=lambda i: (-rang[i.categorie_off or ""], i.nom))
    return [i.id for i in trouves]


def quantite_comestible(quantite_g: float, ingredient: Ingredient) -> float:
    """Part comestible d'un paquet (le placard compte en grammes comestibles)."""
    return round(quantite_g * ingredient.part_comestible)
