"""Bilan sur plusieurs semaines (onglet « Bilan »)."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from repas.base import session
from repas.catalogue import catalogue
from repas.statistiques import BilanPeriode, bilan_periode

router = APIRouter(tags=["bilan"])


@router.get("/bilan")
def lire(
    semaines: int = Query(default=12, ge=1, le=104), s: Session = Depends(session)
) -> BilanPeriode:
    """Bilan des ``semaines`` dernières semaines (et de la semaine suivante si planifiée)."""
    return bilan_periode(s, catalogue(), semaines)
