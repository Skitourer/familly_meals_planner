"""Cas d'usage de l'application : relie la base, le catalogue et le cœur métier.

Les routes HTTP (``api/``) restent ainsi très simples : elles valident les
entrées puis appellent les fonctions de ce module.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from repas.catalogue import Catalogue
from repas.domaine import planificateur as plan
from repas.domaine.articles_libres import a_reporter, cle_coche_libre
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
    retirer_non_achetes,
    stock_avant_validation,
)
from repas.domaine.notes import NoteDonnee, Preferences
from repas.domaine.placard import IdeePlat, a_vider, idees_pour_vider, jours_limites
from repas.domaine.presences import convives_avec, creneau_a_venir
from repas.domaine.produits import (
    a_ranger_a_la_validation,
    cle_coche_racheter,
    meme_produit,
    regrouper,
)
from repas.domaine.reperes import REPERES
from repas.modeles import (
    AchatProduit,
    AchatReel,
    ArticleLibre,
    BilanCourses,
    CategorieRepasExterieur,
    Coche,
    Creneau,
    EcartPlacard,
    EcartProduit,
    FicheProduitMixin,
    IngredientARacheter,
    Membre,
    Note,
    NotesStock,
    PrixProduit,
    ProduitARacheter,
    ProduitPlacard,
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
    semaine = _semaine_existante(s, lundi)
    if semaine:
        return semaine
    semaine = Semaine(lundi=lundi)
    s.add(semaine)
    try:
        s.flush()
    except IntegrityError:
        # Une requête simultanée a créé la semaine entre la lecture et l'insertion (issue #45).
        # Elle l'a enregistrée avec ses créneaux dans la même transaction : on la relit.
        s.rollback()
        existante = _semaine_existante(s, lundi)
        if existante is None:
            raise
        return existante
    tous = [m.id for m in membres_actifs(s) if m.id is not None]
    for jour in range(7):
        for moment in MOMENTS:
            s.add(Creneau(semaine_id=semaine.id or 0, jour=jour, moment=moment, convives=tous))
    s.commit()
    s.refresh(semaine)
    return semaine


def _semaine_existante(s: Session, lundi: date) -> Semaine | None:
    return s.exec(select(Semaine).where(Semaine.lundi == lundi)).first()


def creneaux_de(s: Session, semaine: Semaine) -> list[Creneau]:
    creneaux = s.exec(select(Creneau).where(Creneau.semaine_id == semaine.id)).all()
    return sorted(creneaux, key=lambda c: (c.jour, MOMENTS.index(c.moment)))


def membres_actifs(s: Session) -> list[Membre]:
    return list(s.exec(select(Membre).where(Membre.actif).order_by(col(Membre.id))).all())


def ajouter_aux_repas_a_venir(s: Session, membre_id: int, aujourd_hui: date) -> None:
    """Ajoute un membre (nouveau ou de retour) aux convives des repas à venir des semaines
    déjà créées, sauf là où il est noté « repas à l'extérieur » (issue #72).

    Une semaine reçoit ses convives à sa création : sans cela, un membre créé ensuite serait
    ignoré par la génération et les courses de ces semaines.
    """
    dehors = set(
        s.exec(
            select(CategorieRepasExterieur.creneau_id).where(
                CategorieRepasExterieur.membre_id == membre_id
            )
        ).all()
    )
    repas = s.exec(
        select(Creneau, Semaine)
        .join(Semaine, col(Creneau.semaine_id) == col(Semaine.id))
        .where(Semaine.lundi >= lundi_de(aujourd_hui))
    ).all()
    for creneau, semaine in repas:
        if creneau.id in dehors or not creneau_a_venir(semaine.lundi, creneau.jour, aujourd_hui):
            continue
        convives = convives_avec(creneau.convives, membre_id)
        if convives != creneau.convives:
            creneau.convives = convives
            s.add(creneau)


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
        repas_exterieurs=repas_exterieurs(s, semaine),
    )


def categories_exterieur(s: Session, semaine: Semaine) -> dict[int, dict[int, str]]:
    """Créneau -> membre -> catégorie du repas pris dehors (membres absents seulement)."""
    creneaux = {c.id: c for c in creneaux_de(s, semaine)}
    resultat: dict[int, dict[int, str]] = defaultdict(dict)
    lignes = s.exec(
        select(CategorieRepasExterieur).where(
            col(CategorieRepasExterieur.creneau_id).in_(list(creneaux))
        )
    ).all()
    for ligne in lignes:
        if ligne.membre_id not in creneaux[ligne.creneau_id].convives:
            resultat[ligne.creneau_id][ligne.membre_id] = ligne.categorie
    return resultat


def indiquer_repas_exterieur(
    s: Session, creneau: Creneau, membre_id: int, categorie: str | None
) -> None:
    """Enregistre (ou efface, si ``None``) la catégorie du repas pris dehors."""
    ligne = s.get(CategorieRepasExterieur, (creneau.id, membre_id))
    if categorie is None:
        if ligne:
            s.delete(ligne)
        return
    ligne = ligne or CategorieRepasExterieur(
        creneau_id=creneau.id or 0, membre_id=membre_id, categorie=categorie
    )
    ligne.categorie = categorie
    s.add(ligne)


def oublier_repas_exterieurs_des_presents(s: Session, creneau: Creneau) -> None:
    """Un membre revenu manger à la maison n'a plus de repas pris dehors à ce créneau."""
    lignes = s.exec(
        select(CategorieRepasExterieur).where(CategorieRepasExterieur.creneau_id == creneau.id)
    ).all()
    for ligne in lignes:
        if ligne.membre_id in creneau.convives:
            s.delete(ligne)


def repas_exterieurs(s: Session, semaine: Semaine) -> tuple[plan.RepasExterieur, ...]:
    """Repas pris dehors de la semaine dont la catégorie est connue, pour l'algorithme."""
    creneaux = {c.id: c for c in creneaux_de(s, semaine)}
    return tuple(
        plan.RepasExterieur(
            membre_id=membre_id,
            jour=creneaux[creneau_id].jour,
            moment=creneaux[creneau_id].moment,  # type: ignore[arg-type]
            categorie=categorie,  # type: ignore[arg-type]
        )
        for creneau_id, membres in categories_exterieur(s, semaine).items()
        for membre_id, categorie in membres.items()
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
    stock = stock_disponible(s, semaine.lundi)
    if semaine.courses_validees_le:
        # Liste telle qu'au moment des courses, sans les surplus qu'elles ont rangés.
        stock = stock_avant_validation(stock, _ecarts(s, semaine))
    return liste_de_courses(portions, catalogue, stock, ingredients_a_racheter(s, semaine))


def _ecarts(s: Session, semaine: Semaine) -> dict[str, tuple[float, float]]:
    lignes = s.exec(select(EcartPlacard).where(EcartPlacard.semaine_id == semaine.id)).all()
    return {e.ingredient_id: (e.avant_g, e.apres_g) for e in lignes}


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


def autres_achats(s: Session, semaine: Semaine) -> list[AchatProduit]:
    """Autres produits achetés (sans ingrédient du référentiel) : budget, et placard si rangés."""
    requete = select(AchatProduit).where(AchatProduit.semaine_id == semaine.id)
    return list(s.exec(requete.order_by(col(AchatProduit.id))).all())


def enregistrer_autre_achat(s: Session, semaine: Semaine, achat: AchatProduit) -> None:
    """Ajoute un autre produit acheté ; il rejoint le placard à la validation s'il est rangé."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    achat.semaine_id = semaine.id or 0
    s.add(achat)
    _retenir_prix(s, achat.code, achat.prix_eur)
    s.commit()


def annuler_autre_achat(s: Session, semaine: Semaine, achat_id: int) -> None:
    """Retire un autre produit acheté."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    achat = s.get(AchatProduit, achat_id)
    if achat and achat.semaine_id == semaine.id:
        s.delete(achat)
        s.commit()


# --- Produits à racheter ----------------------------------------------------------------


def produits_a_racheter(s: Session, semaine: Semaine) -> list[ProduitARacheter]:
    """Autres produits finis au placard, remis sur la liste de courses de la semaine."""
    requete = select(ProduitARacheter).where(ProduitARacheter.semaine_id == semaine.id)
    return list(s.exec(requete.order_by(col(ProduitARacheter.id))).all())


def ajouter_a_racheter(s: Session, semaine: Semaine, fiche: FicheProduitMixin) -> None:
    """Met un produit sur la liste de courses (une seule fois, même s'il est fini deux fois)."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    if any(meme_produit(p.code, p.nom, fiche.code, fiche.nom)
           for p in produits_a_racheter(s, semaine)):  # fmt: skip
        return
    champs = fiche.model_dump(include=set(FicheProduitMixin.model_fields))
    s.add(ProduitARacheter.model_validate({**champs, "semaine_id": semaine.id or 0}))
    s.commit()


def retirer_a_racheter(s: Session, semaine: Semaine, produit_id: int) -> None:
    """Retire un produit de la liste de courses, avec sa coche."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    produit = s.get(ProduitARacheter, produit_id)
    if produit is None or produit.semaine_id != semaine.id:
        return
    coche = s.get(Coche, (semaine.id, cle_coche_racheter(produit_id)))
    if coche:
        s.delete(coche)
    s.delete(produit)
    s.commit()


def ingredients_a_racheter(s: Session, semaine: Semaine) -> list[str]:
    """Ingrédients finis au placard, achetés en plus des repas sur la liste de la semaine."""
    requete = select(IngredientARacheter).where(IngredientARacheter.semaine_id == semaine.id)
    return [i.ingredient_id for i in s.exec(requete).all()]


def ajouter_ingredient_a_racheter(s: Session, semaine: Semaine, ingredient_id: str) -> None:
    """Met un ingrédient sur la liste de courses (une seule fois)."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    if s.get(IngredientARacheter, (semaine.id, ingredient_id)) is None:
        s.add(IngredientARacheter(semaine_id=semaine.id or 0, ingredient_id=ingredient_id))
        s.commit()


def retirer_ingredient_a_racheter(s: Session, semaine: Semaine, ingredient_id: str) -> None:
    """Retire l'achat en plus d'un ingrédient (le besoin des repas reste sur la liste)."""
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")
    ligne = s.get(IngredientARacheter, (semaine.id, ingredient_id))
    if ligne:
        s.delete(ligne)
        s.commit()


# --- Articles libres (hors repas, hors placard) -----------------------------------------


def articles_libres(s: Session, semaine: Semaine) -> list[ArticleLibre]:
    """Articles ajoutés à la main sur la liste de la semaine, dans l'ordre d'ajout."""
    requete = select(ArticleLibre).where(ArticleLibre.semaine_id == semaine.id)
    return list(s.exec(requete.order_by(col(ArticleLibre.id))).all())


def _exiger_courses_ouvertes(semaine: Semaine) -> None:
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine sont déjà validées")


def ajouter_article_libre(s: Session, semaine: Semaine, libelle: str, quantite: str) -> None:
    """Ajoute un article libre ; le même libellé n'est ajouté qu'une fois."""
    _exiger_courses_ouvertes(semaine)
    if any(meme_produit(None, a.libelle, None, libelle) for a in articles_libres(s, semaine)):
        return
    s.add(ArticleLibre(semaine_id=semaine.id or 0, libelle=libelle, quantite=quantite))
    s.commit()


def _article_libre(s: Session, semaine: Semaine, article_id: int) -> ArticleLibre | None:
    article = s.get(ArticleLibre, article_id)
    return article if article and article.semaine_id == semaine.id else None


def modifier_prix_article_libre(
    s: Session, semaine: Semaine, article_id: int, prix_eur: float | None
) -> None:
    """Enregistre le prix payé d'un article libre (``None`` l'efface)."""
    _exiger_courses_ouvertes(semaine)
    article = _article_libre(s, semaine, article_id)
    if article is None:
        raise ErreurMetier("Cet article n'est plus sur la liste")
    article.prix_eur = prix_eur
    s.add(article)
    s.commit()


def retirer_article_libre(s: Session, semaine: Semaine, article_id: int) -> None:
    """Retire un article libre de la liste, avec sa coche."""
    _exiger_courses_ouvertes(semaine)
    article = _article_libre(s, semaine, article_id)
    if article is None:
        return
    coche = s.get(Coche, (semaine.id, cle_coche_libre(article_id)))
    if coche:
        s.delete(coche)
    s.delete(article)
    s.commit()


def reporter_articles_libres(s: Session, semaine: Semaine) -> int:
    """Déplace les articles libres non cochés sur la semaine suivante ; renvoie leur nombre.

    Permis même après « Courses faites » : c'est justement là qu'on voit ce qui manque.
    """
    suivante = obtenir_semaine(s, semaine.lundi + timedelta(days=7))
    _exiger_courses_ouvertes(suivante)
    deja = articles_libres(s, suivante)
    reportes = a_reporter(articles_libres(s, semaine), coches(s, semaine))
    for article in reportes:
        coche = s.get(Coche, (semaine.id, cle_coche_libre(article.id or 0)))
        if coche:
            s.delete(coche)
        if any(meme_produit(None, a.libelle, None, article.libelle) for a in deja):
            s.delete(article)  # déjà prévu la semaine suivante : pas de doublon
            continue
        article.semaine_id, article.prix_eur = suivante.id or 0, None
        s.add(article)
    s.commit()
    return len(reportes)


def prix_estime(s: Session, produit: FicheProduitMixin) -> float | None:
    """Prix d'un produit à racheter : le dernier payé par la famille, s'il est connu."""
    return dernier_prix(s, produit.code) if produit.code else None


# --- Autres produits du placard (hors repas) ---------------------------------------------


def produits_placard(s: Session) -> list[ProduitPlacard]:
    """Autres produits du placard, par catégorie puis par nom."""
    produits = s.exec(select(ProduitPlacard)).all()
    return sorted(produits, key=lambda p: (p.categorie, p.nom.casefold()))


def ranger_produit(
    s: Session, fiche: FicheProduitMixin, paquets: int, peremption: date | None = None
) -> tuple[ProduitPlacard, bool]:
    """Ajoute des paquets au placard (même produit : on additionne) ; vrai si créé."""
    existant = next(
        (p for p in s.exec(select(ProduitPlacard)).all()
         if meme_produit(p.code, p.nom, fiche.code, fiche.nom)),
        None,
    )  # fmt: skip
    if existant is None:
        champs = fiche.model_dump(include=set(FicheProduitMixin.model_fields))
        existant = ProduitPlacard.model_validate({**champs, "paquets": 0, "peremption": peremption})
    existant.paquets, existant.peremption = regrouper(
        (existant.paquets, existant.peremption), (paquets, peremption)
    )
    existant.mis_a_jour_le = datetime.now(UTC)
    cree = existant.id is None
    s.add(existant)
    s.flush()
    return existant, cree


def modifier_produit(
    s: Session,
    produit_id: int,
    paquets: int | None = None,
    peremption: date | None = None,
    categorie: str | None = None,
) -> None:
    """Corrige un autre produit du placard ; 0 paquet le retire."""
    produit = s.get(ProduitPlacard, produit_id)
    if produit is None:
        raise ErreurMetier("Produit introuvable dans le placard")
    if paquets == 0:
        s.delete(produit)
    else:
        produit.paquets = paquets if paquets is not None else produit.paquets
        produit.peremption = peremption or produit.peremption
        produit.categorie = categorie or produit.categorie
        produit.mis_a_jour_le = datetime.now(UTC)
        s.add(produit)
    s.commit()


@dataclass(frozen=True)
class CibleIngredient:
    """Article modifié en ingrédient du placard (en grammes comestibles)."""

    ingredient_id: str
    quantite_g: float
    peremption: date | None


@dataclass(frozen=True)
class CibleProduit:
    """Article modifié en autre produit du placard (hors repas, en paquets)."""

    nom: str
    categorie: str
    paquets: int
    peremption: date | None


type Notes = tuple[str | None, int | None, str | None]  # Nutri-Score, NOVA, Green-Score


def modifier_article(
    s: Session, cat: Catalogue, source: str | int, cible: CibleIngredient | CibleProduit
) -> None:
    """Corrige un article du placard, en une seule transaction.

    ``source`` est l'identifiant d'un ingrédient (texte) ou d'un autre produit (entier).
    Rester le même article remplace ses valeurs ; changer d'ingrédient, ou passer
    d'ingrédient à autre produit et inversement, le range comme un ajout (regroupé avec le
    même article déjà au placard). Les notes Open Food Facts suivent l'article.
    """
    if isinstance(source, str):
        notes = _retirer_ingredient(s, source, cible)
    else:
        notes = _retirer_produit(s, source, cible)
    if notes is not None:  # article retiré : on le range sous sa nouvelle forme
        s.flush()
        if isinstance(cible, CibleIngredient):
            _ranger_ingredient(s, cat, cible, notes)
        else:
            fiche = FicheProduitMixin(nom=cible.nom, categorie=cible.categorie, nutriscore=notes[0],
                                      nova=notes[1], green_score=notes[2])  # fmt: skip
            ranger_produit(s, fiche, cible.paquets, cible.peremption)
    s.commit()


def _retirer_ingredient(
    s: Session, ingredient_id: str, cible: CibleIngredient | CibleProduit
) -> Notes | None:
    """Modifie l'ingrédient sur place s'il reste le même ; sinon le retire et rend ses notes."""
    stock = s.get(Stock, ingredient_id)
    if stock is None:
        raise ErreurMetier("Ingrédient absent du placard")
    if isinstance(cible, CibleIngredient) and cible.ingredient_id == ingredient_id:
        stock.quantite_g = cible.quantite_g
        stock.peremption = cible.peremption or stock.peremption
        stock.mis_a_jour_le = datetime.now(UTC)
        s.add(stock)
        return None
    notes_stock = s.get(NotesStock, ingredient_id)
    s.delete(stock)
    if notes_stock is None:
        return (None, None, None)
    s.delete(notes_stock)
    return (notes_stock.nutriscore, notes_stock.nova, notes_stock.green_score)


def _retirer_produit(
    s: Session, produit_id: int, cible: CibleIngredient | CibleProduit
) -> Notes | None:
    """Modifie l'autre produit sur place s'il le reste ; sinon le retire et rend ses notes."""
    produit = s.get(ProduitPlacard, produit_id)
    if produit is None:
        raise ErreurMetier("Produit introuvable dans le placard")
    if isinstance(cible, CibleProduit):
        produit.nom, produit.categorie = cible.nom, cible.categorie
        produit.paquets, produit.peremption = cible.paquets, cible.peremption
        produit.mis_a_jour_le = datetime.now(UTC)
        s.add(produit)
        return None
    s.delete(produit)
    return (produit.nutriscore, produit.nova, produit.green_score)


def _ranger_ingredient(s: Session, cat: Catalogue, cible: CibleIngredient, notes: Notes) -> None:
    """Range un ingrédient, regroupé avec celui déjà au placard ; ses notes remplacent les
    anciennes quand il en a."""
    peremption = cible.peremption or date.today() + timedelta(
        days=cat.ingredients[cible.ingredient_id].conservation_jours
    )
    stock = s.get(Stock, cible.ingredient_id)
    if stock is None:
        stock = Stock(ingredient_id=cible.ingredient_id, quantite_g=cible.quantite_g,
                      peremption=peremption)  # fmt: skip
    else:
        quantite, plus_proche = regrouper(
            (stock.quantite_g, stock.peremption), (cible.quantite_g, peremption)
        )
        stock.quantite_g, stock.peremption = quantite, plus_proche or peremption
    stock.mis_a_jour_le = datetime.now(UTC)
    s.add(stock)
    if any(note is not None for note in notes):
        s.merge(NotesStock(ingredient_id=cible.ingredient_id, nutriscore=notes[0],
                           nova=notes[1], green_score=notes[2]))  # fmt: skip


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


def articles_non_coches(s: Session, semaine: Semaine, catalogue: Catalogue) -> list[str]:
    """Articles de la liste ni cochés ni scannés : achetés ou non, la famille le dira."""
    faits = set(coches(s, semaine)) | achats_reels(s, semaine).keys()
    return [x.ingredient_id for x in courses(s, semaine, catalogue).a_acheter
            if x.ingredient_id not in faits]  # fmt: skip


def valider_courses(
    s: Session, semaine: Semaine, catalogue: Catalogue, *, tout_achete: bool
) -> None:
    """Courses faites : le placard est mis à jour (consommations et surplus).

    ``tout_achete`` faux : les articles ni cochés ni scannés n'ont pas été achetés.
    Les changements du placard sont gardés pour pouvoir rouvrir les courses.
    """
    if semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine ont déjà été validées")
    non_achetes = set() if tout_achete else set(articles_non_coches(s, semaine, catalogue))
    liste = retirer_non_achetes(
        appliquer_achats_reels(courses(s, semaine, catalogue), achats_reels(s, semaine), catalogue),
        non_achetes,
    )
    autres = autres_achats(s, semaine)
    rachats = a_ranger_a_la_validation(
        produits_a_racheter(s, semaine), set(coches(s, semaine)), autres, tout_achete=tout_achete
    )
    autres_eur = sum(a.prix_eur for a in autres) + sum(prix_estime(s, r) or 0 for r in rachats)
    nouveau = placard_apres_courses(liste, stock_disponible(s, semaine.lundi), catalogue)
    anciens = {st.ingredient_id: st for st in s.exec(select(Stock)).all()}
    for id_ing in anciens.keys() | nouveau.keys():
        ancien = anciens.get(id_ing)
        avant_g = ancien.quantite_g if ancien else 0.0
        if nouveau.get(id_ing, 0.0) != avant_g:
            s.add(EcartPlacard(
                semaine_id=semaine.id or 0, ingredient_id=id_ing, avant_g=avant_g,
                peremption_avant=ancien.peremption if ancien else None,
                apres_g=nouveau.get(id_ing, 0.0),
            ))  # fmt: skip
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
    _ranger_autres_achats(s, semaine, rachats)
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


def _ranger_autres_achats(s: Session, semaine: Semaine, rachats: list[ProduitARacheter]) -> None:
    """Range au placard les autres produits achetés et rachetés, en notant les paquets ajoutés."""
    ajouts: dict[int, EcartProduit] = {}
    fiches: list[FicheProduitMixin] = [a for a in autres_achats(s, semaine) if a.ranger]
    for fiche in fiches + list(rachats):
        produit, cree = ranger_produit(s, fiche, 1)
        ecart = ajouts.setdefault(
            produit.id or 0,
            EcartProduit(semaine_id=semaine.id or 0, produit_id=produit.id or 0, paquets=0,
                         cree=cree),
        )  # fmt: skip
        ecart.paquets += 1
    s.add_all(ajouts.values())


def _defaire_rangement(s: Session, semaine: Semaine) -> None:
    """Retire du placard les paquets rangés par la validation (corrections ultérieures gardées)."""
    requete = select(EcartProduit).where(EcartProduit.semaine_id == semaine.id)
    for ecart in s.exec(requete).all():
        produit = s.get(ProduitPlacard, ecart.produit_id)
        if produit is not None:
            produit.paquets -= ecart.paquets
            if produit.paquets <= 0:
                s.delete(produit)
            else:
                s.add(produit)
        s.delete(ecart)


def rouvrir_courses(s: Session, semaine: Semaine) -> None:
    """Défait la validation des courses : placard rendu, budget validé oublié.

    Les changements faits depuis à la main dans le placard sont conservés.
    """
    if not semaine.courses_validees_le:
        raise ErreurMetier("Les courses de cette semaine ne sont pas validées")
    lignes = s.exec(select(EcartPlacard).where(EcartPlacard.semaine_id == semaine.id)).all()
    bilan = s.get(BilanCourses, semaine.id)
    # Une validation qui a touché le placard sans en garder trace date d'avant la réouverture.
    if not lignes and bilan and bilan.depuis_placard_g + bilan.surplus_placard_g > 0:
        raise ErreurMetier(
            "Ces courses ont été validées avant la version qui permet de les rouvrir"
        )
    stock_actuel = {st.ingredient_id: st for st in s.exec(select(Stock)).all()}
    rendu = stock_avant_validation(
        {i: st.quantite_g for i, st in stock_actuel.items()},
        {e.ingredient_id: (e.avant_g, e.apres_g) for e in lignes},
    )
    for ecart in lignes:
        stock = stock_actuel.get(ecart.ingredient_id)
        quantite = rendu.get(ecart.ingredient_id)
        if quantite is None:
            if stock:
                s.delete(stock)
        else:
            stock = stock or Stock(ingredient_id=ecart.ingredient_id, quantite_g=0,
                                   peremption=ecart.peremption_avant or semaine.lundi)  # fmt: skip
            stock.quantite_g = quantite
            if ecart.peremption_avant:
                stock.peremption = ecart.peremption_avant
            stock.mis_a_jour_le = datetime.now(UTC)
            s.add(stock)
        s.delete(ecart)
    _defaire_rangement(s, semaine)
    if bilan:
        s.delete(bilan)
    semaine.courses_validees_le = None
    s.add(semaine)
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
