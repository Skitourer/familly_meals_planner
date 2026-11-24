"""Connexion familiale : un seul mot de passe partagé, session par cookie signé."""

import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from repas.config import parametres

router = APIRouter(prefix="/session", tags=["session"])


class Identifiants(BaseModel):
    mot_de_passe: str


class EtatSession(BaseModel):
    connecte: bool


def exiger_connexion(request: Request) -> None:
    """Dépendance : refuse la requête (401) si la famille n'est pas connectée."""
    if not request.session.get("connecte"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Connexion requise")


@router.get("")
def etat(request: Request) -> EtatSession:
    return EtatSession(connecte=bool(request.session.get("connecte")))


@router.post("")
def connecter(identifiants: Identifiants, request: Request) -> EtatSession:
    attendu = parametres().mot_de_passe.encode()
    if not hmac.compare_digest(identifiants.mot_de_passe.encode(), attendu):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mot de passe incorrect")
    request.session["connecte"] = True
    return EtatSession(connecte=True)


@router.delete("", dependencies=[Depends(exiger_connexion)])
def deconnecter(request: Request) -> EtatSession:
    request.session.clear()
    return EtatSession(connecte=False)
