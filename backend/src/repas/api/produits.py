"""Produits du commerce lus par leur code-barres (placard et courses), réservé aux adultes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from repas import services
from repas.base import session
from repas.catalogue import catalogue
from repas.domaine.produits import (
    code_barres_valide,
    ingredients_correspondants,
    quantite_comestible,
)
from repas.open_food_facts import ChercheurProduit, OpenFoodFactsIndisponible, chercher_produit

router = APIRouter(prefix="/produits", tags=["produits"])


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
    propositions: list[PropositionSortie]  # ingrédients correspondants, le plus probable d'abord
    dernier_prix_eur: float | None  # dernier prix payé par la famille pour ce produit


def chercheur_produit() -> ChercheurProduit:
    """Dépendance : recherche Open Food Facts (remplaçable dans les tests)."""
    return chercher_produit


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
