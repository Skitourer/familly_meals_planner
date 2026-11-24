"""Cas d'usage de l'application : relie la base, le catalogue et le cœur métier.

Les routes HTTP (``api/``) restent ainsi très simples : elles valident les
entrées puis appellent les fonctions de ce module.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, col, select

from repas.catalogue import Catalogue
from repas.domaine import planificateur as plan
from repas.domaine.besoins import ProfilPhysique, coefficient_portion
from repas.domaine.bilan import Bilan, RepasServi, bilan_semaine
from repas.domaine.courses import ListeCourses, Portion, liste_de_courses, placard_apres_courses
from repas.domaine.notes import NoteDonnee, Preferences
from repas.domaine.reperes import REPERES
from repas.modeles import BilanCourses, Creneau, Membre, Note, Reglages, Semaine, Stock

MOMENTS = ("midi", "soir")
COEFFICIENT_INVITE = 1.0
SEMAINES_HISTORIQUE = 3


class ErreurMetier(ValueError):
    """Erreur à présenter telle quelle à l'utilisateur."""


# --- Semaines et créneaux -----------------------------------------------------------


def lundi_de(jour: date) -> date:
    return jour - timedelta(days=jour.weekday())


def obtenir_semaine(s: Session, lundi: date) -> Semaine:
    """Semaine du lundi donné, créée avec 14 créneaux (toute la famille) si besoin."""
    if lundi.weekday() != 0:
        raise ErreurMetier("La date doit être un lundi")
    semaine = s.exec(select(Semaine).where(Semaine.lundi == lundi)).first()
    if semaine:
        return semaine
    semaine = Semaine(lundi=lundi)
    s.add(semaine)
    s.flush()
    tous = [m.id for m in membres_actifs(s) if m.id is not None]
    for jour in range(7):
        for moment in MOMENTS:
            s.add(Creneau(semaine_id=semaine.id or 0, jour=jour, moment=moment, convives=tous))
    s.commit()
    s.refresh(semaine)
    return semaine


def creneaux_de(s: Session, semaine: Semaine) -> list[Creneau]:
    creneaux = s.exec(select(Creneau).where(Creneau.semaine_id == semaine.id)).all()
    return sorted(creneaux, key=lambda c: (c.jour, MOMENTS.index(c.moment)))


def membres_actifs(s: Session) -> list[Membre]:
    return list(s.exec(select(Membre).where(Membre.actif).order_by(col(Membre.id))).all())


def coefficients(s: Session, le: date) -> dict[int, float]:
    """Coefficient de portion de chaque membre (actif ou non) à une date donnée."""
    return {
        m.id: coefficient_portion(
            ProfilPhysique(
                age=m.age(le),
                poids_kg=m.poids_kg,
                sexe=m.sexe,
                mode_de_vie=m.mode_de_vie,
                heures_sport_semaine=m.heures_sport_semaine,
            )
        )
        for m in s.exec(select(Membre)).all()
        if m.id is not None
    }


def somme_coefficients(creneau: Creneau, coefs: dict[int, float]) -> float:
    return sum(coefs.get(m, 1.0) for m in creneau.convives) + creneau.invites * COEFFICIENT_INVITE


# --- Génération -------------------------------------------------------------------


def contexte(s: Session, semaine: Semaine, catalogue: Catalogue) -> plan.ContextePlanification:
    """Rassemble tout ce que l'algorithme doit savoir sur la famille."""
    reglages = obtenir_reglages(s)
    notes = [NoteDonnee(n.membre_id, n.recette_id, n.valeur) for n in s.exec(select(Note)).all()]
    poids = plan.Poids(
        prix=[0, 3, 8, 15][reglages.priorite_budget],
        carbone=[0, 10, 25, 50][reglages.priorite_carbone],
        cuisine_en_lot=[0, 3, 6, 12][reglages.cuisine_en_lot],
    )
    return plan.ContextePlanification(
        mois=(semaine.lundi + timedelta(days=3)).month,
        preferences=Preferences(notes),
        semaines_depuis=historique(s, semaine.lundi),
        stock=stock_disponible(s, semaine.lundi),
        poids=poids,
        graine=semaine.graine,
        restes_max=reglages.restes_max,
    )


def historique(s: Session, lundi: date) -> dict[str, int]:
    """Plats servis les semaines précédentes -> nombre de semaines écoulées (1 = la dernière)."""
    resultat: dict[str, int] = {}
    for ecart in range(SEMAINES_HISTORIQUE, 0, -1):
        precedente = s.exec(
            select(Semaine).where(Semaine.lundi == lundi - timedelta(weeks=ecart))
        ).first()
        if precedente:
            for c in creneaux_de(s, precedente):
                if c.plat_id:
                    resultat[c.plat_id] = ecart
    return resultat


def en_creneaux_a_planifier(creneaux: list[Creneau], *, garder_verrous: bool = True):
    return [
        plan.CreneauAPlanifier(
            cle=c.cle,
            jour=c.jour,
            moment=c.moment,  # type: ignore[arg-type]
            convives=tuple(c.convives),
            invites=c.invites,
            joker=c.joker,
            plat_impose=c.plat_id if garder_verrous and c.verrouille else None,
            dessert_impose=c.dessert_id if garder_verrous and c.verrouille else None,
        )
        for c in creneaux
    ]


def generer(s: Session, semaine: Semaine, catalogue: Catalogue, *, varier: bool) -> Semaine:
    """(Re)génère les repas non verrouillés de la semaine."""
    if varier:
        semaine.graine += 1
    creneaux = creneaux_de(s, semaine)
    try:
        resultat = plan.planifier(
            en_creneaux_a_planifier(creneaux), catalogue, contexte(s, semaine, catalogue)
        )
    except plan.ErreurPlanification as erreur:
        raise ErreurMetier(str(erreur)) from erreur
    for c in creneaux:
        repas = resultat.repas.get(c.cle)
        c.plat_id = repas.plat if repas else None
        c.dessert_id = repas.dessert if repas else None
        c.restes_de = repas.restes_de if repas else None
        if not repas:
            c.verrouille = False
        s.add(c)
    semaine.generee_le = datetime.now(UTC)
    semaine.ecarts = resultat.ecarts
    s.add(semaine)
    s.commit()
    s.refresh(semaine)
    return semaine


def recalculer_restes(s: Session, semaine: Semaine, catalogue: Catalogue) -> None:
    """Après une modification manuelle, recalcule les liens « restes de ».

    Même règle que le solveur : des restes seulement dans la durée de conservation et
    le nombre de repas du plat cuisiné en lot ; sinon le plat est cuisiné à nouveau.
    """
    creneaux = creneaux_de(s, semaine)
    servis = [c for c in creneaux if c.plat_id and (c.convives or c.invites)]
    restes = plan.attribuer_restes([(c.cle, c.jour, c.plat_id or "") for c in servis], catalogue)
    for c in creneaux:
        c.restes_de = restes.get(c.cle)
        s.add(c)
    s.commit()


def alternatives(
    s: Session, semaine: Semaine, creneau: Creneau, catalogue: Catalogue
) -> list[tuple[str, float]]:
    creneaux = creneaux_de(s, semaine)
    plan_actuel = {
        c.cle: plan.RepasPlanifie(c.cle, c.plat_id, c.dessert_id)
        for c in creneaux
        if c.plat_id and c.dessert_id and (c.convives or c.invites)
    }
    if creneau.cle not in plan_actuel:
        raise ErreurMetier("Ce repas n'a pas encore été généré")
    return plan.alternatives(
        en_creneaux_a_planifier(creneaux, garder_verrous=False),
        catalogue,
        contexte(s, semaine, catalogue),
        plan_actuel,
        creneau.cle,
    )


# --- Bilan et courses -----------------------------------------------------------------


def repas_servis(s: Session, semaine: Semaine) -> list[tuple[Creneau, RepasServi]]:
    coefs = coefficients(s, semaine.lundi)
    return [
        (
            c,
            RepasServi(
                cle=c.cle,
                jour=c.jour,
                moment=c.moment,
                plat=c.plat_id,
                dessert=c.dessert_id,
                coefficients=somme_coefficients(c, coefs),
                joker=c.joker,
                restes_de=c.restes_de,
            ),
        )
        for c in creneaux_de(s, semaine)
        if c.plat_id and c.dessert_id and (c.convives or c.invites)
    ]


def bilan(s: Session, semaine: Semaine, catalogue: Catalogue) -> Bilan:
    return bilan_semaine([r for _, r in repas_servis(s, semaine)], catalogue, REPERES)


def courses(s: Session, semaine: Semaine, catalogue: Catalogue) -> ListeCourses:
    portions = [
        Portion(recette, r.coefficients)
        for _, r in repas_servis(s, semaine)
        for recette in (r.plat, r.dessert)
    ]
    return liste_de_courses(portions, catalogue, stock_disponible(s, semaine.lundi))


def valider_courses(s: Session, semaine: Semaine, catalogue: Catalogue) -> None:
    """Courses faites : le placard est mis à jour (consommations et surplus)."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine ont déjà été validées")
    liste = courses(s, semaine, catalogue)
    nouveau = placard_apres_courses(liste, stock_disponible(s, semaine.lundi), catalogue)
    anciens = {st.ingredient_id: st for st in s.exec(select(Stock)).all()}
    for id_ing, stock in anciens.items():
        if id_ing not in nouveau:
            s.delete(stock)
    for id_ing, quantite in nouveau.items():
        peremption = semaine.lundi + timedelta(
            days=catalogue.ingredients[id_ing].conservation_jours
        )
        stock = anciens.get(id_ing)
        if stock is None:
            stock = Stock(ingredient_id=id_ing, quantite_g=quantite, peremption=peremption)
        elif quantite > stock.quantite_g:  # du neuf a été ajouté : nouvelle date
            stock.quantite_g, stock.peremption = quantite, max(stock.peremption, peremption)
        else:
            stock.quantite_g = quantite
        stock.mis_a_jour_le = datetime.now(UTC)
        s.add(stock)
    semaine.courses_validees_le = datetime.now(UTC)
    s.add(semaine)
    s.add(
        BilanCourses(
            semaine_id=semaine.id or 0,
            budget_eur=liste.total_eur,
            depuis_placard_g=sum(ligne.depuis_placard_g for ligne in liste.lignes),
            surplus_placard_g=sum(
                ligne.surplus_g for ligne in liste.a_acheter if ligne.surplus_au_placard
            ),
            surplus_perdu_g=sum(
                ligne.surplus_g for ligne in liste.a_acheter if not ligne.surplus_au_placard
            ),
        )
    )
    s.commit()


def stock_disponible(s: Session, le: date) -> dict[str, float]:
    """Placard utilisable à une date (les produits périmés sont ignorés)."""
    return {st.ingredient_id: st.quantite_g for st in s.exec(select(Stock)).all()
            if st.peremption >= le}  # fmt: skip


# --- Réglages ----------------------------------------------------------------------


def obtenir_reglages(s: Session) -> Reglages:
    reglages = s.get(Reglages, 1)
    if reglages is None:
        reglages = Reglages()
        s.add(reglages)
        s.commit()
        s.refresh(reglages)
    return reglages
