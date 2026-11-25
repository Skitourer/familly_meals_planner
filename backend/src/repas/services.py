"""Cas d'usage de l'application : relie la base, le catalogue et le cœur métier.

Les routes HTTP (``api/``) restent ainsi très simples : elles valident les
entrées puis appellent les fonctions de ce module.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, col, select

from repas.catalogue import Catalogue
from repas.domaine import planificateur as plan
from repas.domaine.besoins import ProfilPhysique, coefficient_portion
from repas.domaine.bilan import Bilan, RepasServi, bilan_semaine
from repas.domaine.coches import (
    ModificationCoche,
    articles_coches,
    en_utc,
    fusionner_coches,
)
from repas.domaine.courses import (
    AchatConstate,
    ListeCourses,
    Portion,
    appliquer_achats_reels,
    liste_de_courses,
    placard_apres_courses,
)
from repas.domaine.notes import NoteDonnee, Preferences
from repas.domaine.placard import IdeePlat, a_vider, idees_pour_vider, jours_limites
from repas.domaine.reperes import REPERES
from repas.modeles import (
    AchatReel,
    AutreAchat,
    BilanCourses,
    Coche,
    Creneau,
    Membre,
    Note,
    PrixProduit,
    Reglages,
    Semaine,
    Stock,
)

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


def contexte(
    s: Session, semaine: Semaine, catalogue: Catalogue, *, premier_jour: int = 0
) -> plan.ContextePlanification:
    """Rassemble tout ce que l'algorithme doit savoir sur la famille.

    ``premier_jour`` : en cours de semaine, le placard est celui de ce jour-là.
    """
    reglages = obtenir_reglages(s)
    notes = [NoteDonnee(n.membre_id, n.recette_id, n.valeur) for n in s.exec(select(Note)).all()]
    debut = semaine.lundi + timedelta(days=premier_jour)
    peremptions = {st.ingredient_id: st.peremption for st in s.exec(select(Stock)).all()}
    poids = plan.Poids(
        prix=[0, 3, 8, 15][reglages.priorite_budget],
        carbone=[0, 10, 25, 50][reglages.priorite_carbone],
        cuisine_en_lot=[0, 3, 6, 12][reglages.cuisine_en_lot],
    )
    return plan.ContextePlanification(
        mois=(semaine.lundi + timedelta(days=3)).month,
        preferences=Preferences(notes),
        semaines_depuis=historique(s, semaine.lundi),
        stock=stock_disponible(s, debut),
        a_consommer_avant=jours_limites(peremptions, semaine.lundi),
        premier_jour=premier_jour,
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


def en_creneaux_a_planifier(
    creneaux: list[Creneau],
    coefs: dict[int, float],
    *,
    garder_verrous: bool = True,
    figes_avant: int = 0,
):
    """Créneaux pour le solveur ; les repas des jours avant ``figes_avant`` sont conservés."""

    def impose(c: Creneau) -> bool:
        return (garder_verrous and c.verrouille) or c.jour < figes_avant

    return [
        plan.CreneauAPlanifier(
            cle=c.cle,
            jour=c.jour,
            moment=c.moment,  # type: ignore[arg-type]
            convives=tuple(c.convives),
            invites=c.invites,
            joker=c.joker,
            plat_impose=c.plat_id if impose(c) else None,
            dessert_impose=c.dessert_id if impose(c) else None,
            coefficients=somme_coefficients(c, coefs),
        )
        for c in creneaux
        if c.jour >= figes_avant or c.plat_id
    ]


def generer(
    s: Session, semaine: Semaine, catalogue: Catalogue, *, varier: bool, a_partir_du_jour: int = 0
) -> Semaine:
    """(Re)génère les repas non verrouillés de la semaine.

    ``a_partir_du_jour`` (0 = lundi) : réajuste seulement la fin de la semaine en cours ;
    les repas des jours précédents sont gardés tels quels.
    """
    if varier:
        semaine.graine += 1
    creneaux = creneaux_de(s, semaine)
    a_planifier = en_creneaux_a_planifier(
        creneaux, coefficients(s, semaine.lundi), figes_avant=a_partir_du_jour
    )
    try:
        resultat = plan.planifier(
            a_planifier,
            catalogue,
            contexte(s, semaine, catalogue, premier_jour=a_partir_du_jour),
        )
    except plan.ErreurPlanification as erreur:
        raise ErreurMetier(str(erreur)) from erreur
    for c in creneaux:
        if c.jour < a_partir_du_jour:
            continue
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
        en_creneaux_a_planifier(creneaux, coefficients(s, semaine.lundi), garder_verrous=False),
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


def coches(s: Session, semaine: Semaine) -> list[str]:
    """Articles cochés sur la liste de courses de la semaine."""
    return articles_coches(_etat(_lignes_coches(s, semaine)))


def enregistrer_coches(
    s: Session, semaine: Semaine, modifications: list[ModificationCoche]
) -> list[str]:
    """Applique des coches venues d'un appareil (éventuellement en retard) ; renvoie l'état."""
    lignes = _lignes_coches(s, semaine)
    avant = _etat(lignes)
    apres = fusionner_coches(avant, modifications, datetime.now(UTC))
    for id_ing, coche in apres.items():
        if avant.get(id_ing) == coche:
            continue
        ligne = lignes.get(id_ing) or Coche(
            semaine_id=semaine.id or 0, ingredient_id=id_ing, cochee=coche.cochee,
            modifiee_le=coche.modifiee_le,
        )  # fmt: skip
        ligne.cochee, ligne.modifiee_le = coche.cochee, coche.modifiee_le
        s.add(ligne)
    s.commit()
    return articles_coches(apres)


def _lignes_coches(s: Session, semaine: Semaine) -> dict[str, Coche]:
    lignes = s.exec(select(Coche).where(Coche.semaine_id == semaine.id)).all()
    return {c.ingredient_id: c for c in lignes}


def _etat(lignes: dict[str, Coche]) -> dict[str, ModificationCoche]:
    return {
        id_ing: ModificationCoche(id_ing, c.cochee, en_utc(c.modifiee_le))
        for id_ing, c in lignes.items()
    }


def achats_reels(s: Session, semaine: Semaine) -> dict[str, AchatConstate]:
    """Achats réels enregistrés pour la liste de la semaine, par ingrédient."""
    lignes = s.exec(select(AchatReel).where(AchatReel.semaine_id == semaine.id)).all()
    return {a.ingredient_id: AchatConstate(a.quantite_g, a.prix_eur) for a in lignes}


def enregistrer_achat(
    s: Session,
    semaine: Semaine,
    ingredient_id: str,
    achat: AchatConstate,
    code: str | None = None,
) -> None:
    """Ajoute un produit acheté à l'article (deux paquets scannés s'additionnent)."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    ligne = s.get(AchatReel, (semaine.id, ingredient_id))
    if ligne is None:
        ligne = AchatReel(semaine_id=semaine.id or 0, ingredient_id=ingredient_id,
                          quantite_g=0, prix_eur=0)  # fmt: skip
    ligne.quantite_g += achat.quantite_g
    ligne.prix_eur = round(ligne.prix_eur + achat.prix_eur, 2)
    ligne.modifie_le = datetime.now(UTC)
    s.add(ligne)
    _retenir_prix(s, code, achat.prix_eur)
    s.commit()


def _retenir_prix(s: Session, code: str | None, prix_eur: float) -> None:
    if code:
        prix = s.get(PrixProduit, code) or PrixProduit(code=code, prix_eur=prix_eur)
        prix.prix_eur, prix.releve_le = prix_eur, datetime.now(UTC)
        s.add(prix)


def autres_achats(s: Session, semaine: Semaine) -> list[AutreAchat]:
    """Achats sans ingrédient du référentiel, comptés dans le budget seulement."""
    requete = select(AutreAchat).where(AutreAchat.semaine_id == semaine.id)
    return list(s.exec(requete.order_by(col(AutreAchat.id))).all())


def enregistrer_autre_achat(
    s: Session, semaine: Semaine, libelle: str, prix_eur: float, code: str | None = None
) -> None:
    """Ajoute un achat compté dans le budget mais pas dans le placard."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    s.add(AutreAchat(semaine_id=semaine.id or 0, libelle=libelle, prix_eur=prix_eur))
    _retenir_prix(s, code, prix_eur)
    s.commit()


def annuler_autre_achat(s: Session, semaine: Semaine, achat_id: int) -> None:
    """Retire un achat « budget seulement »."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    achat = s.get(AutreAchat, achat_id)
    if achat and achat.semaine_id == semaine.id:
        s.delete(achat)
        s.commit()


def annuler_achat(s: Session, semaine: Semaine, ingredient_id: str) -> None:
    """Oublie les achats réels d'un article (l'estimation reprend sa place)."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    ligne = s.get(AchatReel, (semaine.id, ingredient_id))
    if ligne:
        s.delete(ligne)
        s.commit()


def dernier_prix(s: Session, code: str) -> float | None:
    """Dernier prix payé par la famille pour ce code-barres."""
    prix = s.get(PrixProduit, code)
    return prix.prix_eur if prix else None


def valider_courses(s: Session, semaine: Semaine, catalogue: Catalogue) -> None:
    """Courses faites : le placard est mis à jour (consommations et surplus)."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine ont déjà été validées")
    liste = appliquer_achats_reels(
        courses(s, semaine, catalogue), achats_reels(s, semaine), catalogue
    )
    autres_eur = sum(a.prix_eur for a in autres_achats(s, semaine))
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
            budget_eur=round(liste.total_eur + autres_eur, 2),
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


def idees_frigo_a_vider(s: Session, catalogue: Catalogue, le: date) -> list[IdeePlat]:
    """Plats qui consomment le mieux les produits du placard à vider, pour toute la famille."""
    a_consommer = {
        st.ingredient_id: st.quantite_g
        for st in s.exec(select(Stock)).all()
        if st.ingredient_id in catalogue.ingredients
        and le <= st.peremption
        and a_vider(st.peremption, le)
    }
    coefs = coefficients(s, le)
    portions = sum(coefs[m.id] for m in membres_actifs(s) if m.id is not None)
    return idees_pour_vider(a_consommer, catalogue, portions or 1.0)


def stock_disponible(s: Session, le: date) -> dict[str, float]:
    """Placard utilisable à une date (les produits périmés sont ignorés)."""
    return {st.ingredient_id: st.quantite_g for st in s.exec(select(Stock)).all()
            if st.peremption >= le}  # fmt: skip


# --- Réglages ----------------------------------------------------------------------


def obtenir_reglages(s: Session) -> Reglages:
    """Réglages de la famille, créés avec les valeurs par défaut à la première lecture."""
    reglages = s.get(Reglages, 1)
    if reglages is not None:
        return reglages
    # Deux requêtes simultanées peuvent trouver la table vide (issue #38) : l'insertion
    # ignore le conflit, puis on relit la ligne, créée par l'une ou l'autre.
    s.exec(sqlite_insert(Reglages).values(Reglages().model_dump()).on_conflict_do_nothing())
    s.commit()
    reglages = s.get(Reglages, 1)
    if reglages is None:
        raise RuntimeError("Réglages introuvables après leur création")
    return reglages
