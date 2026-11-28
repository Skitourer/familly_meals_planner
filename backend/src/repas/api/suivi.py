"""Suivi après les repas : notes de la famille et placard."""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from repas import services
from repas.api.produits import FicheEntree
from repas.api.produits import Note as LettreNote
from repas.api.session import compte_connecte, exiger_adulte
from repas.base import session
from repas.catalogue import catalogue
from repas.catalogue.schemas import LIBELLES_RAYONS, Rayon
from repas.domaine.nutriscore import nutriscore_ingredient
from repas.domaine.placard import a_vider
from repas.domaine.produits import CATEGORIES
from repas.modeles import Compte, Creneau, Note, NotesStock, Semaine, Stock, maintenant

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
    rayon: str  # libellé, pour regrouper le placard comme la liste de courses
    rang_rayon: int  # ordre du rayon dans le parcours du magasin
    # Notes du dernier produit scanné ; sans scan, Nutri-Score calculé depuis CIQUAL.
    nutriscore: LettreNote | None
    nutriscore_calcule: bool
    nova: int | None
    green_score: LettreNote | None


class StockEntree(BaseModel):
    quantite_g: float = Field(ge=0)
    peremption: date | None = None
    # Notes Open Food Facts du produit scanné (absentes en saisie manuelle : on garde
    # celles déjà connues).
    nutriscore: LettreNote | None = None
    nova: int | None = Field(default=None, ge=1, le=4)
    green_score: LettreNote | None = None


def _sortie_stock(st: Stock, notes: NotesStock | None, aujourd_hui: date) -> StockSortie:
    cat = catalogue()
    ingredient = cat.ingredients[st.ingredient_id]
    nutriscore = notes.nutriscore if notes else None
    calcule = nutriscore is None and st.ingredient_id in cat.aliments
    if calcule:
        nutriments = cat.aliments[st.ingredient_id].nutriments_100g
        nutriscore = nutriscore_ingredient(nutriments, ingredient.famille).lower()
    return StockSortie(
        ingredient_id=st.ingredient_id,
        nom=ingredient.nom,
        quantite_g=st.quantite_g,
        unite=ingredient.unite,
        peremption=st.peremption,
        bientot_perime=a_vider(st.peremption, aujourd_hui),
        rayon=LIBELLES_RAYONS[ingredient.rayon],
        rang_rayon=list(Rayon).index(ingredient.rayon),
        nutriscore=nutriscore,  # pyright: ignore[reportArgumentType]
        nutriscore_calcule=calcule,
        nova=notes.nova if notes else None,
        green_score=notes.green_score if notes else None,  # pyright: ignore[reportArgumentType]
    )


@router.get("/placard", dependencies=ADULTE)
def placard(s: Session = Depends(session)) -> list[StockSortie]:
    cat = catalogue()
    notes = {n.ingredient_id: n for n in s.exec(select(NotesStock)).all()}
    return [
        _sortie_stock(st, notes.get(st.ingredient_id), date.today())
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
    notes = s.get(NotesStock, ingredient_id)
    if entree.quantite_g == 0:
        for ligne in (stock, notes):
            if ligne:
                s.delete(ligne)
        s.commit()
        return
    if entree.nutriscore or entree.nova or entree.green_score:
        notes = notes or NotesStock(ingredient_id=ingredient_id)
        notes.nutriscore, notes.nova, notes.green_score = (
            entree.nutriscore, entree.nova, entree.green_score,
        )  # fmt: skip
        s.add(notes)
    peremption = entree.peremption or date.today() + timedelta(
        days=cat.ingredients[ingredient_id].conservation_jours
    )
    stock = stock or Stock(ingredient_id=ingredient_id, quantite_g=0, peremption=peremption)
    stock.quantite_g, stock.peremption, stock.mis_a_jour_le = (
        entree.quantite_g, peremption, maintenant(),
    )  # fmt: skip
    s.add(stock)
    s.commit()


# --- Autres produits du placard (hors repas, comptés en paquets) -------------------------


class ProduitPlacardSortie(BaseModel):
    id: int
    code: str | None
    nom: str
    marque: str
    contenu: str
    categorie: str
    nutriscore: str | None
    nova: int | None
    green_score: str | None
    paquets: int
    peremption: date | None
    bientot_perime: bool


class ProduitPlacardEntree(FicheEntree):
    paquets: int = Field(default=1, ge=1, le=99)
    peremption: date | None = None


class ProduitPlacardModification(BaseModel):
    paquets: int | None = Field(default=None, ge=0, le=99)
    peremption: date | None = None
    categorie: str | None = None


@router.get("/placard/produits", dependencies=ADULTE)
def autres_produits(s: Session = Depends(session)) -> list[ProduitPlacardSortie]:
    """Autres produits du placard, par catégorie puis par nom."""
    aujourd_hui = date.today()
    return [
        ProduitPlacardSortie(
            **p.model_dump(exclude={"id", "mis_a_jour_le"}),
            id=p.id or 0,
            bientot_perime=p.peremption is not None and a_vider(p.peremption, aujourd_hui),
        )
        for p in services.produits_placard(s)
    ]


@router.post("/placard/produits", status_code=204, dependencies=ADULTE)
def ranger_produit(entree: ProduitPlacardEntree, s: Session = Depends(session)) -> None:
    """Range des paquets d'un autre produit (même produit : les paquets s'additionnent)."""
    services.ranger_produit(s, entree.fiche(), entree.paquets, entree.peremption)
    s.commit()


@router.put("/placard/produits/{produit_id}", status_code=204, dependencies=ADULTE)
def modifier_produit(
    produit_id: int, entree: ProduitPlacardModification, s: Session = Depends(session)
) -> None:
    """Corrige le nombre de paquets (0 = retirer), la date limite ou la catégorie."""
    if entree.categorie is not None and entree.categorie not in CATEGORIES:
        raise HTTPException(422, "Catégorie inconnue")
    try:
        services.modifier_produit(
            s, produit_id, entree.paquets, entree.peremption, entree.categorie
        )
    except services.ErreurMetier as erreur:
        raise HTTPException(404, str(erreur)) from erreur


class CibleIngredientEntree(BaseModel):
    type: Literal["ingredient"]
    ingredient_id: str
    quantite_g: float = Field(gt=0, le=100_000)
    peremption: date | None = None


class CibleProduitEntree(BaseModel):
    type: Literal["produit"]
    nom: str = Field(min_length=1, max_length=120)
    categorie: str
    paquets: int = Field(ge=1, le=99)
    peremption: date | None = None


class ArticleModification(BaseModel):
    """Article à corriger (un ingrédient ou un autre produit) et ce qu'il devient."""

    ingredient_id: str | None = None
    produit_id: int | None = None
    cible: Annotated[CibleIngredientEntree | CibleProduitEntree, Field(discriminator="type")]


@router.post("/placard/modification", status_code=204, dependencies=ADULTE)
def modifier_article(entree: ArticleModification, s: Session = Depends(session)) -> None:
    """Corrige un article du placard : valeurs, ingrédient, passage ingrédient ⇄ autre produit."""
    source: str | int
    match entree.ingredient_id, entree.produit_id:
        case str() as ingredient_id, None:
            source = ingredient_id
        case None, int() as produit_id:
            source = produit_id
        case _:
            raise HTTPException(422, "Indiquer ingredient_id ou produit_id, pas les deux")
    cat = catalogue()
    cible = entree.cible
    if isinstance(cible, CibleIngredientEntree):
        if cible.ingredient_id not in cat.ingredients:
            raise HTTPException(422, "Ingrédient inconnu")
        nouvelle: services.CibleIngredient | services.CibleProduit = services.CibleIngredient(
            cible.ingredient_id, cible.quantite_g, cible.peremption
        )
    else:
        if cible.categorie not in CATEGORIES:
            raise HTTPException(422, "Catégorie inconnue")
        nouvelle = services.CibleProduit(
            cible.nom.strip(), cible.categorie, cible.paquets, cible.peremption
        )
    try:
        services.modifier_article(s, cat, source, nouvelle)
    except services.ErreurMetier as erreur:
        raise HTTPException(404, str(erreur)) from erreur
