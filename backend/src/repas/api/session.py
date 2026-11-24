"""Connexion par compte (adulte ou enfant) et session par cookie signé.

Au premier démarrage, s'il n'existe aucun compte, un compte adulte ``famille`` est
créé avec le mot de passe ``REPAS_MOT_DE_PASSE`` : l'installation reste utilisable
tout de suite, puis les adultes créent les autres comptes (onglet Famille).

Droits :

* **adulte** : tout ;
* **enfant** : consulter le menu, les plats et les recettes, et noter ses propres
  repas passés et à venir (contrôlé côté serveur par ``exiger_adulte`` et dans
  les routes de notes).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from repas import securite
from repas.base import session
from repas.config import parametres
from repas.modeles import Compte, Membre

router = APIRouter(prefix="/session", tags=["session"])

IDENTIFIANT_INITIAL = "famille"


class Identifiants(BaseModel):
    identifiant: str = IDENTIFIANT_INITIAL
    mot_de_passe: str


class EtatSession(BaseModel):
    connecte: bool
    identifiant: str | None = None
    role: str | None = None
    membre_id: int | None = None
    prenom: str | None = None


class ChangementMotDePasse(BaseModel):
    actuel: str
    nouveau: str = Field(min_length=securite.LONGUEUR_MIN, max_length=200)


def creer_compte_initial(s: Session) -> None:
    """Crée le compte adulte « famille » si la base ne contient encore aucun compte."""
    if s.exec(select(Compte)).first() is None:
        s.add(
            Compte(
                identifiant=IDENTIFIANT_INITIAL,
                mot_de_passe_hache=securite.hacher(parametres().mot_de_passe),
                role="adulte",
            )
        )
        s.commit()


def compte_connecte(request: Request, s: Session = Depends(session)) -> Compte:
    """Dépendance : le compte de la session (401 si personne n'est connecté)."""
    compte_id = request.session.get("compte_id")
    compte = s.get(Compte, compte_id) if compte_id else None
    if compte is None or not compte.actif:
        request.session.clear()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Connexion requise")
    return compte


def exiger_connexion(compte: Compte = Depends(compte_connecte)) -> None:
    """Dépendance : n'importe quel compte connecté."""


def exiger_adulte(compte: Compte = Depends(compte_connecte)) -> None:
    """Dépendance : réservé aux comptes adultes (403 pour un compte enfant)."""
    if compte.role != "adulte":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux adultes")


def _etat(compte: Compte, s: Session) -> EtatSession:
    membre = s.get(Membre, compte.membre_id) if compte.membre_id else None
    return EtatSession(
        connecte=True,
        identifiant=compte.identifiant,
        role=compte.role,
        membre_id=compte.membre_id,
        prenom=membre.prenom if membre else None,
    )


@router.get("")
def etat(request: Request, s: Session = Depends(session)) -> EtatSession:
    compte_id = request.session.get("compte_id")
    compte = s.get(Compte, compte_id) if compte_id else None
    return _etat(compte, s) if compte and compte.actif else EtatSession(connecte=False)


@router.post("")
def connecter(
    identifiants: Identifiants, request: Request, s: Session = Depends(session)
) -> EtatSession:
    nom = identifiants.identifiant.strip().lower()
    if securite.limiteur.bloque(nom):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Trop d'essais : réessayez dans une minute"
        )
    compte = s.exec(select(Compte).where(Compte.identifiant == nom)).first()
    if (
        compte is None
        or not compte.actif
        or not securite.verifier(identifiants.mot_de_passe, compte.mot_de_passe_hache)
    ):
        securite.limiteur.echec(nom)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect")
    securite.limiteur.succes(nom)
    request.session.clear()
    request.session["compte_id"] = compte.id
    return _etat(compte, s)


@router.delete("", dependencies=[Depends(exiger_connexion)])
def deconnecter(request: Request) -> EtatSession:
    request.session.clear()
    return EtatSession(connecte=False)


@router.put("/mot-de-passe", status_code=204)
def changer_mot_de_passe(
    changement: ChangementMotDePasse,
    compte: Compte = Depends(compte_connecte),
    s: Session = Depends(session),
) -> None:
    """Chacun peut changer son propre mot de passe."""
    if not securite.verifier(changement.actuel, compte.mot_de_passe_hache):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    compte.mot_de_passe_hache = securite.hacher(changement.nouveau)
    s.add(compte)
    s.commit()
