"""Planning de la semaine : créneaux, génération, alternatives, bilan, courses, PDF."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import AwareDatetime, BaseModel, Field
from sqlmodel import Session, select

from repas import services
from repas.api.session import exiger_adulte
from repas.base import session
from repas.catalogue import catalogue
from repas.domaine.bilan import Bilan, InfosRepas, infos_repas, raisons
from repas.domaine.coches import ModificationCoche
from repas.domaine.courses import (
    AchatConstate,
    LigneCourses,
    ListeCourses,
    appliquer_achats_reels,
    format_quantite,
)
from repas.domaine.produits import code_barres_valide
from repas.modeles import AutreAchat, Creneau, Semaine
from repas.pdf import pdf_liste_courses, pdf_menu

router = APIRouter(prefix="/semaines", tags=["semaines"])
ADULTE = [Depends(exiger_adulte)]  # routes réservées aux comptes adultes


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
    infos: InfosRepas | None = None


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
    achete_g: float  # quantité brute prévue (estimation du prix d'un produit scanné)
    achat_reel: str | None = None  # quantité vraiment achetée (produits scannés)
    prix_reel_eur: float | None = None


class AutreAchatSortie(BaseModel):
    id: int
    libelle: str
    prix_eur: float


class CoursesSortie(BaseModel):
    rayons: list[tuple[str, list[LigneCoursesSortie]]]
    a_verifier: list[str]
    total_eur: float
    hors_liste: list[LigneCoursesSortie]  # ingrédients achetés sans être prévus
    autres_achats: list[AutreAchatSortie]  # budget seulement
    total_reel_eur: float  # prix payés quand ils sont connus, estimation sinon
    nb_achats_reels: int
    validees: bool
    coches: list[str]  # articles cochés, partagés entre appareils


class CocheEntree(BaseModel):
    ingredient_id: str = Field(max_length=80)
    cochee: bool
    modifiee_le: AwareDatetime  # heure de l'action sur l'appareil


MAX_COCHES_PAR_ENVOI = 500


class AchatEntree(BaseModel):
    ingredient_id: str = Field(max_length=80)
    quantite_g: float = Field(gt=0, le=100_000)  # quantité brute du produit acheté
    prix_eur: float = Field(ge=0, le=1_000)
    code: str | None = Field(default=None, max_length=14)  # code-barres, pour le prix suivant


class AutreAchatEntree(BaseModel):
    libelle: str = Field(min_length=1, max_length=120)
    prix_eur: float = Field(ge=0, le=1_000)
    code: str | None = Field(default=None, max_length=14)


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
    coefs = services.coefficients(s, semaine.lundi)
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
        infos = None
        if c.plat_id in cat.profils and c.dessert_id in cat.profils:
            infos = infos_repas(
                cat.profils[c.plat_id],
                cat.profils[c.dessert_id],
                services.somme_coefficients(c, coefs),
            )
        creneaux.append(
            CreneauSortie(
                **c.model_dump(exclude={"semaine_id"}), cle=c.cle, raisons=explications, infos=infos
            )
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


def _courses_sortie(
    liste: ListeCourses,
    validees: bool,
    coches: list[str],
    achats: dict[str, AchatConstate],
    autres: list[AutreAchat],
) -> CoursesSortie:
    def ligne(x: LigneCourses) -> LigneCoursesSortie:
        reel = achats.get(x.ingredient_id)
        achat = format_quantite(x.achete_g, x.unite) if x.hors_liste else " + ".join(
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
            achete_g=x.achete_g,
            achat_reel=format_quantite(reel.quantite_g, x.unite) if reel else None,
            prix_reel_eur=round(reel.prix_eur, 2) if reel else None,
        )

    reelle = appliquer_achats_reels(liste, achats, catalogue())
    return CoursesSortie(
        rayons=[(rayon, [ligne(x) for x in lignes]) for rayon, lignes in liste.par_rayon()],
        a_verifier=[x.nom for x in liste.a_verifier],
        total_eur=liste.total_eur,
        hors_liste=[ligne(x) for x in sorted(reelle.hors_liste, key=lambda x: x.nom)],
        autres_achats=[
            AutreAchatSortie(id=a.id or 0, libelle=a.libelle, prix_eur=a.prix_eur) for a in autres
        ],
        total_reel_eur=round(reelle.total_eur + sum(a.prix_eur for a in autres), 2),
        nb_achats_reels=len(achats) + len(autres),
        validees=validees,
        coches=coches,
    )


# --- Routes ----------------------------------------------------------------------------


@router.get("/{lundi}")
def lire(lundi: date, s: Session = Depends(session)) -> SemaineSortie:
    return _sortie(s, _semaine(s, lundi))


@router.put("/{lundi}/creneaux/{jour}/{moment}", dependencies=ADULTE)
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


@router.post("/{lundi}/generer", dependencies=ADULTE)
def generer(
    lundi: date,
    varier: bool = False,
    a_partir_du_jour: int = Query(0, ge=0, le=6),
    s: Session = Depends(session),
) -> SemaineSortie:
    """Génère les repas non verrouillés. ``varier=true`` propose une autre combinaison.

    ``a_partir_du_jour`` (0 = lundi) réajuste la fin de la semaine sans toucher aux jours passés.
    """
    try:
        semaine = services.generer(
            s, _semaine(s, lundi), catalogue(), varier=varier, a_partir_du_jour=a_partir_du_jour
        )
    except services.ErreurMetier as erreur:
        raise HTTPException(422, str(erreur)) from erreur
    return _sortie(s, semaine)


@router.get("/{lundi}/creneaux/{jour}/{moment}/alternatives", dependencies=ADULTE)
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


@router.get("/{lundi}/bilan", dependencies=ADULTE)
def bilan(lundi: date, s: Session = Depends(session)) -> Bilan:
    return services.bilan(s, _semaine(s, lundi), catalogue())


@router.get("/{lundi}/courses", dependencies=ADULTE)
def courses(lundi: date, s: Session = Depends(session)) -> CoursesSortie:
    semaine = _semaine(s, lundi)
    liste = services.courses(s, semaine, catalogue())
    return _courses_sortie(
        liste,
        semaine.courses_validees_le is not None,
        services.coches(s, semaine),
        services.achats_reels(s, semaine),
        services.autres_achats(s, semaine),
    )


@router.post("/{lundi}/courses/achats", status_code=204, dependencies=ADULTE)
def acheter(lundi: date, entree: AchatEntree, s: Session = Depends(session)) -> None:
    """Enregistre un produit acheté (scanné), prévu sur la liste ou non."""
    if entree.code is not None and not code_barres_valide(entree.code):
        raise HTTPException(422, "Code-barres invalide")
    ingredient = catalogue().ingredients.get(entree.ingredient_id)
    if ingredient is None or ingredient.basique:
        raise HTTPException(400, "Ingrédient inconnu ou non suivi au placard")
    semaine = _semaine(s, lundi)
    achat = AchatConstate(entree.quantite_g, entree.prix_eur)
    try:
        services.enregistrer_achat(s, semaine, entree.ingredient_id, achat, entree.code)
    except services.ErreurMetier as erreur:
        raise HTTPException(409, str(erreur)) from erreur


@router.delete("/{lundi}/courses/achats/{ingredient_id}", status_code=204, dependencies=ADULTE)
def annuler_achat(lundi: date, ingredient_id: str, s: Session = Depends(session)) -> None:
    """Oublie les achats réels d'un article : son prix estimé reprend sa place."""
    try:
        services.annuler_achat(s, _semaine(s, lundi), ingredient_id)
    except services.ErreurMetier as erreur:
        raise HTTPException(409, str(erreur)) from erreur


@router.post("/{lundi}/courses/autres-achats", status_code=204, dependencies=ADULTE)
def acheter_autre(lundi: date, entree: AutreAchatEntree, s: Session = Depends(session)) -> None:
    """Enregistre un achat sans ingrédient du référentiel : budget seulement."""
    if entree.code is not None and not code_barres_valide(entree.code):
        raise HTTPException(422, "Code-barres invalide")
    try:
        services.enregistrer_autre_achat(
            s, _semaine(s, lundi), entree.libelle.strip(), entree.prix_eur, entree.code
        )
    except services.ErreurMetier as erreur:
        raise HTTPException(409, str(erreur)) from erreur


@router.delete("/{lundi}/courses/autres-achats/{achat_id}", status_code=204, dependencies=ADULTE)
def annuler_autre_achat(lundi: date, achat_id: int, s: Session = Depends(session)) -> None:
    """Retire un achat « budget seulement »."""
    try:
        services.annuler_autre_achat(s, _semaine(s, lundi), achat_id)
    except services.ErreurMetier as erreur:
        raise HTTPException(409, str(erreur)) from erreur


@router.put("/{lundi}/courses/coches", dependencies=ADULTE)
def cocher(
    lundi: date,
    entrees: list[CocheEntree] = Body(max_length=MAX_COCHES_PAR_ENVOI),
    s: Session = Depends(session),
) -> list[str]:
    """Enregistre des coches (une ou une file d'attente hors ligne) ; renvoie les articles cochés.

    Pour chaque article, la modification la plus récente l'emporte, même arrivée en retard.
    """
    inconnus = sorted({e.ingredient_id for e in entrees} - catalogue().ingredients.keys())
    if inconnus:
        raise HTTPException(400, f"Ingrédients inconnus : {', '.join(inconnus)}")
    modifications = [ModificationCoche(e.ingredient_id, e.cochee, e.modifiee_le) for e in entrees]
    return services.enregistrer_coches(s, _semaine(s, lundi), modifications)


@router.post("/{lundi}/courses/valider", status_code=204, dependencies=ADULTE)
def valider_courses(lundi: date, s: Session = Depends(session)) -> None:
    try:
        services.valider_courses(s, _semaine(s, lundi), catalogue())
    except services.ErreurMetier as erreur:
        raise HTTPException(409, str(erreur)) from erreur


@router.get("/{lundi}/courses.pdf", dependencies=ADULTE)
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
