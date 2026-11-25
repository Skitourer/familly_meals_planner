"""Produits du commerce lus par leur code-barres (placard et courses), réservé aux adultes."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session

from repas import services
from repas.base import session
from repas.catalogue import catalogue
from repas.domaine.produits import (
    CATEGORIES,
    categorie_produit,
    code_barres_valide,
    ingredients_correspondants,
    quantite_comestible,
)
from repas.modeles import FicheProduitMixin
from repas.open_food_facts import ChercheurProduit, OpenFoodFactsIndisponible, chercher_produit

router = APIRouter(prefix="/produits", tags=["produits"])

type Note = Literal["a", "b", "c", "d", "e"]


class FicheEntree(BaseModel):
    """Autre produit (hors repas) décrit par Open Food Facts ou saisi à la main."""

    code: str | None = Field(default=None, max_length=14)
    nom: str = Field(min_length=1, max_length=120)
    marque: str = Field(default="", max_length=80)
    contenu: str = Field(default="", max_length=40)
    categorie: str = Field(max_length=40)
    nutriscore: Note | None = None
    nova: int | None = Field(default=None, ge=1, le=4)
    green_score: Note | None = None

    @field_validator("code")
    @classmethod
    def code_valide(cls, code: str | None) -> str | None:
        if code is not None and not code_barres_valide(code):
            raise ValueError("code-barres invalide")
        return code

    @field_validator("categorie")
    @classmethod
    def categorie_connue(cls, categorie: str) -> str:
        if categorie not in CATEGORIES:
            raise ValueError(f"catégorie inconnue (attendu : {', '.join(CATEGORIES)})")
        return categorie

    def fiche(self) -> FicheProduitMixin:
        """Fiche à enregistrer (achat ou placard)."""
        return FicheProduitMixin(**self.model_dump())


class PropositionSortie(BaseModel):
    ingredient_id: str
    nom: str
    quantite_g: float | None  # part comestible du paquet, None si contenu inconnu
    prix_estime_eur: float | None  # prix médian au kg × contenu du paquet


class ProduitSortie(BaseModel):
    code: str
    nom: str
    marque: str
    quantite_g: float | None  # contenu du paquet
    contenu: str  # tel qu'imprimé, ex. « 400 g »
    categorie: str  # catégorie proposée s'il est rangé parmi les autres produits
    nutriscore: Note | None
    nova: int | None
    green_score: Note | None
    propositions: list[PropositionSortie]  # ingrédients correspondants, le plus probable d'abord
    dernier_prix_eur: float | None  # dernier prix payé par la famille pour ce produit


def chercheur_produit() -> ChercheurProduit:
    """Dépendance : recherche Open Food Facts (remplaçable dans les tests)."""
    return chercher_produit


@router.get("/categories")
def categories() -> list[str]:
    """Catégories des autres produits du placard."""
    return list(CATEGORIES)


@router.get("/{code}")
def produit_scanne(
    code: str,
    chercher: ChercheurProduit = Depends(chercheur_produit),
    s: Session = Depends(session),
) -> ProduitSortie:
    """Produit lu par son code-barres et ingrédients du référentiel qui lui correspondent."""
    if not code_barres_valide(code):
        raise HTTPException(422, "Code-barres invalide : vérifiez les chiffres saisis")
    try:
        fiche = chercher(code)
    except OpenFoodFactsIndisponible as erreur:
        raise HTTPException(
            503, "Open Food Facts est injoignable : réessayez ou ajoutez le produit à la main"
        ) from erreur
    if fiche is None:
        raise HTTPException(404, "Produit absent d'Open Food Facts : ajoutez-le à la main")
    cat = catalogue()
    return ProduitSortie(
        code=fiche.code,
        nom=fiche.nom,
        marque=fiche.marque,
        quantite_g=fiche.quantite_g,
        contenu=fiche.contenu,
        categorie=categorie_produit(fiche.categories),
        nutriscore=fiche.nutriscore,  # pyright: ignore[reportArgumentType]
        nova=fiche.nova,
        green_score=fiche.green_score,  # pyright: ignore[reportArgumentType]
        propositions=[
            PropositionSortie(
                ingredient_id=i,
                nom=cat.ingredients[i].nom,
                quantite_g=quantite_comestible(fiche.quantite_g, cat.ingredients[i])
                if fiche.quantite_g
                else None,
                prix_estime_eur=round(cat.prix_kg(i) * fiche.quantite_g / 1000, 2)
                if fiche.quantite_g
                else None,
            )
            for i in ingredients_correspondants(fiche.categories, cat.ingredients)
            if not cat.ingredients[i].basique  # produits de fond de placard : non suivis
        ],
        dernier_prix_eur=services.dernier_prix(s, code),
    )
