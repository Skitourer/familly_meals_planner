"""Produits scannés : code-barres, quantité et rapprochement avec les ingrédients.

Un produit du commerce est identifié par son code-barres (EAN-13, EAN-8, UPC-A) et
décrit par Open Food Facts. Ce module, sans accès réseau, valide le code, lit la
fiche Open Food Facts et propose les ingrédients du référentiel correspondants grâce
à leur catégorie Open Food Facts (``categorie_off``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from repas.catalogue.schemas import Ingredient

# Longueurs GTIN : EAN-8, UPC-A (12), EAN-13 et GTIN-14 (cartons).
LONGUEURS_CODE = (8, 12, 13, 14)

FACTEURS_GRAMMES = {"g": 1, "ml": 1, "kg": 1000, "l": 1000, "cl": 10}

# Catégories simples des autres produits du placard (hors repas), avec les catégories
# Open Food Facts qui y mènent ; la première qui correspond l'emporte.
CATEGORIES_PRODUITS: dict[str, tuple[str, ...]] = {
    "Petit-déjeuner": ("en:breakfast-cereals", "en:breakfasts", "en:spreads", "en:jams",
                       "en:honeys", "en:sweet-spreads"),
    "Biscuits et goûters": ("en:biscuits-and-cakes", "en:biscuits", "en:cakes",
                            "en:chocolates", "en:confectioneries", "en:sweet-snacks"),
    "Apéritif": ("en:salty-snacks", "en:appetizers", "en:crisps"),
    "Boissons": ("en:beverages",),
    "Surgelés": ("en:frozen-foods",),
    "Conserves": ("en:canned-foods",),
    "Produits frais": ("en:dairies", "en:meats", "en:fresh-foods"),
}  # fmt: skip
CATEGORIE_PAR_DEFAUT = "Épicerie"
CATEGORIES = (*CATEGORIES_PRODUITS, CATEGORIE_PAR_DEFAUT)

NUTRISCORES = ("a", "b", "c", "d", "e")


@dataclass(frozen=True)
class FicheProduit:
    """Ce qu'Open Food Facts dit d'un produit, réduit à l'utile."""

    code: str
    nom: str
    marque: str
    quantite_g: float | None  # contenu du paquet en g (ou ml), None si inconnu
    categories: tuple[str, ...]  # étiquettes Open Food Facts, de la plus générale à la plus précise
    contenu: str = ""  # tel qu'imprimé sur le paquet, ex. « 400 g »
    nutriscore: str | None = None  # a à e
    nova: int | None = None  # 1 à 4 (degré de transformation)
    green_score: str | None = None  # a à e (impact environnemental)


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
        contenu=_contenu(produit.get("quantity")),
        nutriscore=_note(produit.get("nutriscore_grade")),
        nova=_nova(produit.get("nova_group")),
        # Le Green-Score s'appelait Eco-Score : Open Food Facts garde les deux noms.
        green_score=_note(produit.get("environmental_score_grade"))
        or _note(produit.get("ecoscore_grade")),
    )


def _contenu(valeur: Any) -> str:
    """Contenu imprimé, sans le « ℮ » (quantité estimée) que les fiches recopient souvent."""
    return re.sub(r"\s+[℮e]$", "", str(valeur or "").strip())[:40]


def _note(valeur: Any) -> str | None:
    """Note de A à E, en minuscule ; None si absente ou inconnue (« unknown »)."""
    note = str(valeur or "").lower()
    return note if note in NUTRISCORES else None


def _nova(valeur: Any) -> int | None:
    try:
        groupe = int(valeur)
    except (TypeError, ValueError):
        return None
    return groupe if 1 <= groupe <= 4 else None


def categorie_produit(categories: tuple[str, ...]) -> str:
    """Catégorie simple d'un produit hors repas, d'après ses catégories Open Food Facts."""
    for categorie, etiquettes in CATEGORIES_PRODUITS.items():
        if any(e in categories for e in etiquettes):
            return categorie
    return CATEGORIE_PAR_DEFAUT


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


def meme_produit(code_a: str | None, nom_a: str, code_b: str | None, nom_b: str) -> bool:
    """Deux fiches désignent le même produit : même code-barres, sinon même nom (sans casse)."""
    if code_a or code_b:
        return code_a == code_b
    return nom_a.strip().casefold() == nom_b.strip().casefold()


def date_la_plus_proche(a: date | None, b: date | None) -> date | None:
    """Date limite d'un stock de plusieurs paquets : celle du paquet à finir en premier."""
    dates = [d for d in (a, b) if d is not None]
    return min(dates) if dates else None
