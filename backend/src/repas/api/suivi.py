"""Suivi après les repas : notes de la famille et placard."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from repas import services
from repas.api.session import compte_connecte, exiger_adulte
from repas.base import session
from repas.catalogue import catalogue
from repas.domaine.placard import a_vider
from repas.domaine.produits import (
    code_barres_valide,
    ingredients_correspondants,
    quantite_comestible,
)
from repas.modeles import Compte, Creneau, Note, Semaine, Stock, maintenant
from repas.open_food_facts import ChercheurProduit, OpenFoodFactsIndisponible, chercher_produit

router = APIRouter(tags=["suivi"])
ADULTE = [Depends(exiger_adulte)]  # routes réservées aux comptes adultes


# --- Notes ------------------------------------------------------------------------------


class RepasANoter(BaseModel):
    creneau_id: int
    date: date
    moment: str
    recette_id: str
    nom: str
    convives: list[int]
    notes: dict[int, int]  # membre -> note déjà donnée
    a_venir: bool = False  # repas futur : avis donné à l'avance


class NoteEntree(BaseModel):
    membre_id: int
    creneau_id: int
    recette_id: str
    valeur: int = Field(ge=1, le=5)
    commentaire: str = Field(default="", max_length=500)


@router.get("/notes/a-noter")
def a_noter(
    jours: int = 14,
    jours_a_venir: int = 7,
    s: Session = Depends(session),
    compte: Compte = Depends(compte_connecte),
) -> list[RepasANoter]:
    """Repas des ``jours`` derniers jours (à noter) et des ``jours_a_venir`` prochains
    (avis à l'avance), avec les notes déjà données.

    Un compte enfant ne voit que les repas auxquels il participe.
    """
    cat = catalogue()
    aujourd_hui = date.today()
    debut = aujourd_hui - timedelta(days=jours)
    fin = aujourd_hui + timedelta(days=jours_a_venir)
    semaines = s.exec(
        select(Semaine).where(Semaine.lundi >= debut - timedelta(days=6), Semaine.lundi <= fin)
    ).all()
    resultat: list[RepasANoter] = []
    for semaine in semaines:
        creneaux = s.exec(select(Creneau).where(Creneau.semaine_id == semaine.id)).all()
        for c in creneaux:
            jour = semaine.lundi + timedelta(days=c.jour)
            if not (debut <= jour <= fin) or not c.plat_id or not c.convives:
                continue
            if compte.role == "enfant" and compte.membre_id not in c.convives:
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
                    a_venir=jour > aujourd_hui,
                )
            )
    return sorted(resultat, key=lambda r: (r.date, r.moment), reverse=True)


@router.put("/notes")
def noter(
    entree: NoteEntree,
    s: Session = Depends(session),
    compte: Compte = Depends(compte_connecte),
) -> Note:
    """Crée ou met à jour la note d'un membre pour un plat servi (ou prévu).

    Un adulte peut noter pour n'importe quel membre (utile pour les petits) ; un
    compte enfant uniquement pour lui-même.
    """
    creneau = s.get(Creneau, entree.creneau_id)
    if creneau is None or creneau.plat_id != entree.recette_id:
        raise HTTPException(404, "Repas introuvable")
    if compte.role == "enfant" and entree.membre_id != compte.membre_id:
        raise HTTPException(403, "Un compte enfant ne peut noter que pour lui-même")
    if entree.membre_id not in creneau.convives:
        raise HTTPException(400, "Ce membre ne participe pas à ce repas")
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
    bientot_perime: bool  # à vider : à consommer dans les 7 jours


class StockEntree(BaseModel):
    quantite_g: float = Field(ge=0)
    peremption: date | None = None


@router.get("/placard", dependencies=ADULTE)
def placard(s: Session = Depends(session)) -> list[StockSortie]:
    cat = catalogue()
    aujourd_hui = date.today()
    return [
        StockSortie(
            ingredient_id=st.ingredient_id,
            nom=cat.ingredients[st.ingredient_id].nom,
            quantite_g=st.quantite_g,
            unite=cat.ingredients[st.ingredient_id].unite,
            peremption=st.peremption,
            bientot_perime=a_vider(st.peremption, aujourd_hui),
        )
        for st in s.exec(select(Stock).order_by(col(Stock.peremption))).all()
        if st.ingredient_id in cat.ingredients
    ]


class IdeeSortie(BaseModel):
    plat: str
    nom: str
    ingredients: list[str]  # noms des produits à vider utilisés
    part_videe: float


@router.get("/placard/idees", dependencies=ADULTE)
def idees(s: Session = Depends(session)) -> list[IdeeSortie]:
    """Plats qui consomment le mieux les produits à vider (frigo à vider)."""
    cat = catalogue()
    return [
        IdeeSortie(
            plat=idee.plat,
            nom=cat.recettes[idee.plat].nom,
            ingredients=[cat.ingredients[i].nom for i in idee.ingredients],
            part_videe=idee.part_videe,
        )
        for idee in services.idees_frigo_a_vider(s, cat, date.today())
    ]


@router.put("/placard/{ingredient_id}", dependencies=ADULTE)
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


class PropositionSortie(BaseModel):
    ingredient_id: str
    nom: str
    quantite_g: float | None  # part comestible du paquet, None si contenu inconnu


class ProduitSortie(BaseModel):
    code: str
    nom: str
    marque: str
    quantite_g: float | None  # contenu du paquet
    propositions: list[PropositionSortie]  # ingrédients correspondants, le plus probable d'abord


def chercheur_produit() -> ChercheurProduit:
    """Dépendance : recherche Open Food Facts (remplaçable dans les tests)."""
    return chercher_produit


@router.get("/placard/produit/{code}", dependencies=ADULTE)
def produit_scanne(
    code: str, chercher: ChercheurProduit = Depends(chercheur_produit)
) -> ProduitSortie:
    """Produit lu par son code-barres et ingrédients du placard qui lui correspondent."""
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
            )
            for i in ingredients_correspondants(fiche.categories, cat.ingredients)
            if not cat.ingredients[i].basique  # produits de fond de placard : non suivis
        ],
    )
