"""Membres de la famille et réglages de l'algorithme."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from repas import services
from repas.api.session import exiger_adulte
from repas.base import session
from repas.domaine.besoins import (
    ModeDeVie,
    ProfilPhysique,
    Sexe,
    besoin_energetique_kcal,
    coefficient_portion,
)
from repas.modeles import CategorieRepasExterieur, Compte, Creneau, Membre, Note, Reglages

router = APIRouter(tags=["famille"])
ADULTE = [Depends(exiger_adulte)]  # routes réservées aux comptes adultes


class MembreEntree(BaseModel):
    prenom: str = Field(min_length=1, max_length=40)
    couleur: str = Field(default="#4f8a5b", pattern=r"^#[0-9a-fA-F]{6}$")
    date_naissance: date
    sexe: Sexe
    poids_kg: float = Field(gt=0, lt=300)
    mode_de_vie: ModeDeVie = ModeDeVie.SEDENTAIRE
    heures_sport_semaine: float = Field(default=0, ge=0, le=40)
    actif: bool = True


class MembreSortie(MembreEntree):
    id: int
    age: int
    besoin_kcal: int
    coefficient_portion: float


class ReglagesEntree(BaseModel):
    priorite_budget: int = Field(ge=0, le=3)
    priorite_carbone: int = Field(ge=0, le=3)
    cuisine_en_lot: int = Field(ge=0, le=3)
    restes_max: int = Field(ge=0, le=8)


def _sortie(m: Membre) -> MembreSortie:
    profil = ProfilPhysique(m.age(), m.poids_kg, m.sexe, m.mode_de_vie, m.heures_sport_semaine)
    return MembreSortie(
        **m.model_dump(exclude={"id"}),
        id=m.id or 0,
        age=m.age(),
        besoin_kcal=round(besoin_energetique_kcal(profil)),
        coefficient_portion=coefficient_portion(profil),
    )


@router.get("/membres")
def lister(s: Session = Depends(session)) -> list[MembreSortie]:
    return [_sortie(m) for m in s.exec(select(Membre).order_by(col(Membre.id))).all()]


@router.post("/membres", status_code=201, dependencies=ADULTE)
def creer(entree: MembreEntree, s: Session = Depends(session)) -> MembreSortie:
    membre = Membre(**entree.model_dump())
    s.add(membre)
    s.commit()
    s.refresh(membre)
    return _sortie(membre)


@router.put("/membres/{membre_id}", dependencies=ADULTE)
def modifier(membre_id: int, entree: MembreEntree, s: Session = Depends(session)) -> MembreSortie:
    membre = s.get(Membre, membre_id)
    if membre is None:
        raise HTTPException(404, "Membre introuvable")
    membre.sqlmodel_update(entree.model_dump())
    s.add(membre)
    s.commit()
    s.refresh(membre)
    return _sortie(membre)


@router.delete("/membres/{membre_id}", status_code=204, dependencies=ADULTE)
def supprimer(membre_id: int, s: Session = Depends(session)) -> None:
    """Supprime définitivement un membre, ses notes et sa présence aux repas planifiés.

    Pour garder son historique (un enfant parti étudier...), il suffit plutôt de le
    marquer comme « ne mange plus à la maison » (``actif = false``).
    """
    membre = s.get(Membre, membre_id)
    if membre is None:
        raise HTTPException(404, "Membre introuvable")
    for note in s.exec(select(Note).where(Note.membre_id == membre_id)).all():
        s.delete(note)
    exterieurs = select(CategorieRepasExterieur).where(
        CategorieRepasExterieur.membre_id == membre_id
    )
    for repas in s.exec(exterieurs).all():
        s.delete(repas)
    for creneau in s.exec(select(Creneau)).all():
        if membre_id in creneau.convives:
            creneau.convives = [m for m in creneau.convives if m != membre_id]
            s.add(creneau)
    for compte in s.exec(select(Compte).where(Compte.membre_id == membre_id)).all():
        if compte.role == "enfant":
            s.delete(compte)  # un compte enfant n'existe pas sans son membre
        else:
            compte.membre_id = None
            s.add(compte)
    s.delete(membre)
    s.commit()


@router.get("/reglages", dependencies=ADULTE)
def lire_reglages(s: Session = Depends(session)) -> Reglages:
    return services.obtenir_reglages(s)


@router.put("/reglages", dependencies=ADULTE)
def modifier_reglages(entree: ReglagesEntree, s: Session = Depends(session)) -> Reglages:
    reglages = services.obtenir_reglages(s)
    reglages.sqlmodel_update(entree.model_dump())
    s.add(reglages)
    s.commit()
    s.refresh(reglages)
    return reglages
