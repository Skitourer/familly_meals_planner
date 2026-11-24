"""Suivi après les repas : notes de la famille et placard."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from repas.base import session
from repas.catalogue import catalogue
from repas.modeles import Creneau, Note, Semaine, Stock, maintenant

router = APIRouter(tags=["suivi"])


# --- Notes ------------------------------------------------------------------------------


class RepasANoter(BaseModel):
    creneau_id: int
    date: date
    moment: str
    recette_id: str
    nom: str
    convives: list[int]
    notes: dict[int, int]  # membre -> note déjà donnée


class NoteEntree(BaseModel):
    membre_id: int
    creneau_id: int
    recette_id: str
    valeur: int = Field(ge=1, le=5)
    commentaire: str = Field(default="", max_length=500)


@router.get("/notes/a-noter")
def a_noter(jours: int = 14, s: Session = Depends(session)) -> list[RepasANoter]:
    """Repas passés des ``jours`` derniers jours, avec les notes déjà données."""
    cat = catalogue()
    aujourd_hui = date.today()
    debut = aujourd_hui - timedelta(days=jours)
    semaines = s.exec(select(Semaine).where(Semaine.lundi >= debut - timedelta(days=6))).all()
    resultat: list[RepasANoter] = []
    for semaine in semaines:
        creneaux = s.exec(select(Creneau).where(Creneau.semaine_id == semaine.id)).all()
        for c in creneaux:
            jour = semaine.lundi + timedelta(days=c.jour)
            if not (debut <= jour <= aujourd_hui) or not c.plat_id or not c.convives:
                continue
            if c.plat_id not in cat.recettes or c.restes_de:  # les restes ne se notent pas
                continue
            notes = s.exec(
                select(Note).where(Note.creneau_id == c.id, Note.recette_id == c.plat_id)
            ).all()
            resultat.append(
                RepasANoter(
                    creneau_id=c.id or 0,
                    date=jour,
                    moment=c.moment,
                    recette_id=c.plat_id,
                    nom=cat.recettes[c.plat_id].nom,
                    convives=c.convives,
                    notes={n.membre_id: n.valeur for n in notes},
                )
            )
    return sorted(resultat, key=lambda r: (r.date, r.moment), reverse=True)


@router.put("/notes")
def noter(entree: NoteEntree, s: Session = Depends(session)) -> Note:
    """Crée ou met à jour la note d'un membre pour un plat servi."""
    if s.get(Creneau, entree.creneau_id) is None:
        raise HTTPException(404, "Repas introuvable")
    note = s.exec(
        select(Note).where(
            Note.membre_id == entree.membre_id,
            Note.creneau_id == entree.creneau_id,
            Note.recette_id == entree.recette_id,
        )
    ).first() or Note(**entree.model_dump())
    note.valeur, note.commentaire = entree.valeur, entree.commentaire
    s.add(note)
    s.commit()
    s.refresh(note)
    return note


# --- Placard --------------------------------------------------------------------------


class StockSortie(BaseModel):
    ingredient_id: str
    nom: str
    quantite_g: float
    unite: str
    peremption: date
    bientot_perime: bool


class StockEntree(BaseModel):
    quantite_g: float = Field(ge=0)
    peremption: date | None = None


@router.get("/placard")
def placard(s: Session = Depends(session)) -> list[StockSortie]:
    cat = catalogue()
    limite = date.today() + timedelta(days=7)
    return [
        StockSortie(
            ingredient_id=st.ingredient_id,
            nom=cat.ingredients[st.ingredient_id].nom,
            quantite_g=st.quantite_g,
            unite=cat.ingredients[st.ingredient_id].unite,
            peremption=st.peremption,
            bientot_perime=st.peremption <= limite,
        )
        for st in s.exec(select(Stock).order_by(col(Stock.peremption))).all()
        if st.ingredient_id in cat.ingredients
    ]


@router.put("/placard/{ingredient_id}")
def ajuster(ingredient_id: str, entree: StockEntree, s: Session = Depends(session)) -> None:
    """Corrige la quantité d'un ingrédient (0 = retirer du placard)."""
    cat = catalogue()
    if ingredient_id not in cat.ingredients:
        raise HTTPException(404, "Ingrédient inconnu")
    stock = s.get(Stock, ingredient_id)
    if entree.quantite_g == 0:
        if stock:
            s.delete(stock)
            s.commit()
        return
    peremption = entree.peremption or date.today() + timedelta(
        days=cat.ingredients[ingredient_id].conservation_jours
    )
    stock = stock or Stock(ingredient_id=ingredient_id, quantite_g=0, peremption=peremption)
    stock.quantite_g, stock.peremption, stock.mis_a_jour_le = (
        entree.quantite_g, peremption, maintenant(),
    )  # fmt: skip
    s.add(stock)
    s.commit()
