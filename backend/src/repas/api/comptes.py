"""Gestion des comptes de connexion (réservée aux adultes)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, col, select

from repas import securite
from repas.api.session import compte_connecte
from repas.base import session
from repas.modeles import Compte, Membre

router = APIRouter(prefix="/comptes", tags=["comptes"])


class CompteSortie(BaseModel):
    id: int
    identifiant: str
    role: str
    membre_id: int | None
    actif: bool


class CompteEntree(BaseModel):
    identifiant: str = Field(min_length=2, max_length=40, pattern=r"^[a-zA-Z0-9._-]+$")
    role: Literal["adulte", "enfant"]
    membre_id: int | None = None
    actif: bool = True
    mot_de_passe: str | None = Field(
        default=None, min_length=securite.LONGUEUR_MIN, max_length=200,
        description="Obligatoire à la création ; à la modification, None = inchangé.",
    )  # fmt: skip

    @field_validator("identifiant")
    @classmethod
    def _minuscules(cls, valeur: str) -> str:
        return valeur.strip().lower()


def _sortie(c: Compte) -> CompteSortie:
    return CompteSortie(
        id=c.id or 0, identifiant=c.identifiant, role=c.role, membre_id=c.membre_id,
        actif=c.actif,
    )  # fmt: skip


def _verifier(entree: CompteEntree, s: Session, compte_id: int | None = None) -> None:
    if entree.role == "enfant" and entree.membre_id is None:
        raise HTTPException(400, "Un compte enfant doit être relié à un membre de la famille")
    if entree.membre_id is not None and s.get(Membre, entree.membre_id) is None:
        raise HTTPException(400, "Membre inconnu")
    homonyme = s.exec(select(Compte).where(Compte.identifiant == entree.identifiant)).first()
    if homonyme and homonyme.id != compte_id:
        raise HTTPException(409, f"L'identifiant « {entree.identifiant} » est déjà pris")


def _reste_un_adulte(s: Session, sauf: int) -> bool:
    adultes = s.exec(select(Compte).where(Compte.role == "adulte", Compte.actif)).all()
    return any(c.id != sauf for c in adultes)


@router.get("")
def lister(s: Session = Depends(session)) -> list[CompteSortie]:
    return [_sortie(c) for c in s.exec(select(Compte).order_by(col(Compte.id))).all()]


@router.post("", status_code=201)
def creer(entree: CompteEntree, s: Session = Depends(session)) -> CompteSortie:
    _verifier(entree, s)
    if not entree.mot_de_passe:
        raise HTTPException(400, "Mot de passe obligatoire")
    compte = Compte(
        identifiant=entree.identifiant,
        mot_de_passe_hache=securite.hacher(entree.mot_de_passe),
        role=entree.role,
        membre_id=entree.membre_id,
        actif=entree.actif,
    )
    s.add(compte)
    s.commit()
    s.refresh(compte)
    return _sortie(compte)


@router.put("/{compte_id}")
def modifier(
    compte_id: int,
    entree: CompteEntree,
    s: Session = Depends(session),
    moi: Compte = Depends(compte_connecte),
) -> CompteSortie:
    compte = s.get(Compte, compte_id)
    if compte is None:
        raise HTTPException(404, "Compte introuvable")
    _verifier(entree, s, compte_id)
    perd_ses_droits = compte.role == "adulte" and (entree.role != "adulte" or not entree.actif)
    if perd_ses_droits and not _reste_un_adulte(s, compte_id):
        raise HTTPException(400, "Il doit rester au moins un compte adulte actif")
    if perd_ses_droits and compte.id == moi.id:
        raise HTTPException(400, "Vous ne pouvez pas retirer vos propres droits d'adulte")
    compte.identifiant, compte.role = entree.identifiant, entree.role
    compte.membre_id, compte.actif = entree.membre_id, entree.actif
    if entree.mot_de_passe:
        compte.mot_de_passe_hache = securite.hacher(entree.mot_de_passe)
    s.add(compte)
    s.commit()
    s.refresh(compte)
    return _sortie(compte)


@router.delete("/{compte_id}", status_code=204)
def supprimer(
    compte_id: int, s: Session = Depends(session), moi: Compte = Depends(compte_connecte)
) -> None:
    compte = s.get(Compte, compte_id)
    if compte is None:
        raise HTTPException(404, "Compte introuvable")
    if compte.id == moi.id:
        raise HTTPException(400, "Vous ne pouvez pas supprimer votre propre compte")
    if compte.role == "adulte" and not _reste_un_adulte(s, compte_id):
        raise HTTPException(400, "Il doit rester au moins un compte adulte actif")
    s.delete(compte)
    s.commit()
