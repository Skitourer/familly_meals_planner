"""Planning de la semaine : créneaux, génération, alternatives, bilan, courses, PDF."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from repas import services
from repas.base import session
from repas.catalogue import catalogue
from repas.domaine.bilan import Bilan, raisons
from repas.domaine.courses import ListeCourses, format_quantite
from repas.modeles import Creneau, Semaine
from repas.pdf import pdf_liste_courses, pdf_menu

router = APIRouter(prefix="/semaines", tags=["semaines"])


# --- Schémas -------------------------------------------------------------------------


class CreneauSortie(BaseModel):
    id: int
    cle: str
    jour: int
    moment: str
    convives: list[int]
    invites: int
    joker: bool
    verrouille: bool
    plat_id: str | None
    dessert_id: str | None
    restes_de: str | None
    raisons: list[str]


class SemaineSortie(BaseModel):
    lundi: date
    generee_le: str | None
    courses_validees_le: str | None
    ecarts: dict[str, float]
    creneaux: list[CreneauSortie]


class CreneauModification(BaseModel):
    convives: list[int] | None = None
    invites: int | None = Field(default=None, ge=0, le=20)
    joker: bool | None = None
    verrouille: bool | None = None
    plat_id: str | None = None
    dessert_id: str | None = None


class Alternative(BaseModel):
    plat_id: str
    perte_score: float


class LigneCoursesSortie(BaseModel):
    ingredient_id: str
    nom: str
    achat: str
    besoin: str
    depuis_placard: str | None
    surplus: str | None
    surplus_au_placard: bool
    prix_eur: float


class CoursesSortie(BaseModel):
    rayons: list[tuple[str, list[LigneCoursesSortie]]]
    a_verifier: list[str]
    total_eur: float
    validees: bool


# --- Utilitaires ---------------------------------------------------------------------


def _semaine(s: Session, lundi: date) -> Semaine:
    try:
        return services.obtenir_semaine(s, lundi)
    except services.ErreurMetier as erreur:
        raise HTTPException(400, str(erreur)) from erreur


def _creneau(s: Session, semaine: Semaine, jour: int, moment: str) -> Creneau:
    creneau = s.exec(
        select(Creneau).where(
            Creneau.semaine_id == semaine.id, Creneau.jour == jour, Creneau.moment == moment
        )
    ).first()
    if creneau is None:
        raise HTTPException(404, "Créneau introuvable")
    return creneau


def _sortie(s: Session, semaine: Semaine) -> SemaineSortie:
    cat = catalogue()
    ctx = services.contexte(s, semaine, cat)
    creneaux = []
    for c in services.creneaux_de(s, semaine):
        explications = []
        if c.plat_id in cat.profils:
            explications = raisons(
                cat.profils[c.plat_id],
                mois=ctx.mois,
                catalogue=cat,
                preferences=ctx.preferences,
                stock=ctx.stock,
                restes_de=c.restes_de,
                joker=c.joker,
            )
        creneaux.append(
            CreneauSortie(**c.model_dump(exclude={"semaine_id"}), cle=c.cle, raisons=explications)
        )
    return SemaineSortie(
        lundi=semaine.lundi,
        generee_le=semaine.generee_le.isoformat() if semaine.generee_le else None,
        courses_validees_le=(
            semaine.courses_validees_le.isoformat() if semaine.courses_validees_le else None
        ),
        ecarts=semaine.ecarts or {},
        creneaux=creneaux,
    )


def _courses_sortie(liste: ListeCourses, validees: bool) -> CoursesSortie:
    def ligne(x) -> LigneCoursesSortie:
        achat = " + ".join(
            format_quantite(a.total_g, x.unite) if a.libelle == "au poids"
            else f"{a.nombre} × {a.libelle}"
            for a in x.achats
        )  # fmt: skip
        return LigneCoursesSortie(
            ingredient_id=x.ingredient_id,
            nom=x.nom,
            achat=achat,
            besoin=format_quantite(x.besoin_g, x.unite),
            depuis_placard=format_quantite(x.depuis_placard_g, x.unite)
            if x.depuis_placard_g
            else None,
            surplus=format_quantite(x.surplus_g, x.unite) if x.surplus_g else None,
            surplus_au_placard=x.surplus_au_placard,
            prix_eur=x.prix_eur,
        )

    return CoursesSortie(
        rayons=[(rayon, [ligne(x) for x in lignes]) for rayon, lignes in liste.par_rayon()],
        a_verifier=[x.nom for x in liste.a_verifier],
        total_eur=liste.total_eur,
        validees=validees,
    )


# --- Routes ----------------------------------------------------------------------------


@router.get("/{lundi}")
def lire(lundi: date, s: Session = Depends(session)) -> SemaineSortie:
    return _sortie(s, _semaine(s, lundi))


@router.put("/{lundi}/creneaux/{jour}/{moment}")
def modifier_creneau(
    lundi: date,
    jour: int,
    moment: Literal["midi", "soir"],
    modif: CreneauModification,
    s: Session = Depends(session),
) -> SemaineSortie:
    """Présences, joker, verrou, ou choix manuel d'un plat/dessert (qui le verrouille)."""
    semaine = _semaine(s, lundi)
    creneau = _creneau(s, semaine, jour, moment)
    cat = catalogue()
    valeurs = modif.model_dump(exclude_unset=True)
    for champ in ("plat_id", "dessert_id"):
        if valeurs.get(champ) and valeurs[champ] not in cat.recettes:
            raise HTTPException(400, f"Recette inconnue : {valeurs[champ]}")
    if "plat_id" in valeurs or "dessert_id" in valeurs:
        valeurs.setdefault("verrouille", True)
    creneau.sqlmodel_update(valeurs)
    s.add(creneau)
    s.commit()
    services.recalculer_restes(s, semaine, cat)
    return _sortie(s, semaine)


@router.post("/{lundi}/generer")
def generer(lundi: date, varier: bool = False, s: Session = Depends(session)) -> SemaineSortie:
    """Génère les repas non verrouillés. ``varier=true`` propose une autre combinaison."""
    try:
        semaine = services.generer(s, _semaine(s, lundi), catalogue(), varier=varier)
    except services.ErreurMetier as erreur:
        raise HTTPException(422, str(erreur)) from erreur
    return _sortie(s, semaine)


@router.get("/{lundi}/creneaux/{jour}/{moment}/alternatives")
def alternatives(
    lundi: date, jour: int, moment: Literal["midi", "soir"], s: Session = Depends(session)
) -> list[Alternative]:
    semaine = _semaine(s, lundi)
    try:
        resultats = services.alternatives(s, semaine, _creneau(s, semaine, jour, moment),
                                          catalogue())  # fmt: skip
    except services.ErreurMetier as erreur:
        raise HTTPException(422, str(erreur)) from erreur
    return [Alternative(plat_id=p, perte_score=perte) for p, perte in resultats]


@router.get("/{lundi}/bilan")
def bilan(lundi: date, s: Session = Depends(session)) -> Bilan:
    return services.bilan(s, _semaine(s, lundi), catalogue())


@router.get("/{lundi}/courses")
def courses(lundi: date, s: Session = Depends(session)) -> CoursesSortie:
    semaine = _semaine(s, lundi)
    liste = services.courses(s, semaine, catalogue())
    return _courses_sortie(liste, semaine.courses_validees_le is not None)


@router.post("/{lundi}/courses/valider", status_code=204)
def valider_courses(lundi: date, s: Session = Depends(session)) -> None:
    try:
        services.valider_courses(s, _semaine(s, lundi), catalogue())
    except services.ErreurMetier as erreur:
        raise HTTPException(409, str(erreur)) from erreur


@router.get("/{lundi}/courses.pdf")
def courses_pdf(lundi: date, s: Session = Depends(session)) -> Response:
    liste = services.courses(s, _semaine(s, lundi), catalogue())
    return Response(
        pdf_liste_courses(liste, lundi),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="courses-{lundi}.pdf"'},
    )


@router.get("/{lundi}/menu.pdf")
def menu_pdf(lundi: date, s: Session = Depends(session)) -> Response:
    semaine = _semaine(s, lundi)
    cat = catalogue()
    contenu = pdf_menu(services.creneaux_de(s, semaine), cat, services.bilan(s, semaine, cat),
                       lundi)  # fmt: skip
    return Response(
        contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="menu-{lundi}.pdf"'},
    )
