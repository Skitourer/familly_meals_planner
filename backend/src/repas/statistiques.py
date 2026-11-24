"""Bilan sur plusieurs semaines : nutrition, carbone, budget, goûts, variété, saison,
anti-gaspillage. Alimente l'onglet « Bilan » de l'interface.

Toutes les valeurs sont calculées à partir des repas planifiés ; les semaines sans
repas générés sont ignorées.

Repas pris à l'extérieur (cantine, restaurant d'entreprise...) : ils ne sont pas
saisis et sont **supposés équilibrés**. Ils ne comptent donc ni dans les repères, ni
dans la couverture des besoins, calculée comme une moyenne par repas pris à la maison.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from pydantic import BaseModel
from sqlmodel import Session, col, select

from repas import services
from repas.catalogue import Catalogue
from repas.catalogue.schemas import Famille, Nutriments
from repas.domaine.bilan import bilan_semaine, infos_repas
from repas.domaine.courses import Portion, liste_de_courses
from repas.domaine.notes import NoteDonnee, Preferences
from repas.domaine.nutriscore import lettre
from repas.domaine.references import NUTRIMENTS_SUIVIS, reference_journaliere
from repas.domaine.reperes import PART_ENERGIE_PAR_REPAS, REPERES
from repas.modeles import BilanCourses, Membre, Note, Semaine, Stock

# ADEME (Impact CO2) : voiture thermique ≈ 0,22 kg CO2e par km et par personne.
CO2_KG_PAR_KM_VOITURE = 0.218


class StatutRepere(BaseModel):
    valeur: float
    statut: str


class BilanHebdo(BaseModel):
    """Bilan d'une semaine."""

    lundi: date
    nb_repas: int
    nutriscore_moyen: str
    nutriscore_repartition: dict[str, int]
    reperes: dict[str, StatutRepere]
    co2_kg: float
    co2_reference_kg: float
    budget_eur: float
    budget_estime: bool  # vrai si les courses n'ont pas été validées
    cout_par_repas_personne_eur: float
    part_saison: float  # % des fruits et légumes frais qui étaient de saison
    part_vegetarien: float  # % de repas sans viande ni poisson
    legumes_differents: int
    proteines: dict[str, int]  # source principale -> nombre de repas


class CouvertureNutriment(BaseModel):
    """Apport moyen d'un repas pris à la maison, comparé à 30 % de la référence du jour."""

    code: str
    libelle: str
    unite: str
    apport_par_repas: float
    reference_par_repas: float
    pourcentage: float


class BilanMembre(BaseModel):
    id: int
    prenom: str
    couleur: str
    repas_a_la_maison: int
    repas_dehors: int  # supposés équilibrés
    couverture: list[CouvertureNutriment]
    preferes: list[tuple[str, float]]  # (plat, moyenne des notes)
    moins_aimes: list[tuple[str, float]]


class Gaspillage(BaseModel):
    depuis_placard_kg: float
    surplus_placard_kg: float
    surplus_perdu_kg: float
    semaines_validees: int
    perimes: list[str]  # produits périmés encore au placard


class BilanPeriode(BaseModel):
    semaines: list[BilanHebdo]
    membres: list[BilanMembre]
    a_redecouvrir: list[str]  # plats appréciés pas servis depuis 4 semaines
    jamais_servis: list[str]
    nb_plats_differents: int
    gaspillage: Gaspillage
    co2_total_kg: float
    co2_economise_kg: float
    equivalent_km_voiture: float
    budget_total_eur: float


def bilan_periode(s: Session, catalogue: Catalogue, nb_semaines: int = 12) -> BilanPeriode:
    aujourd_hui = date.today()
    debut = services.lundi_de(aujourd_hui) - timedelta(weeks=nb_semaines - 1)
    semaines = s.exec(
        select(Semaine)
        .where(Semaine.lundi >= debut, Semaine.lundi <= aujourd_hui + timedelta(days=13))
        .order_by(col(Semaine.lundi))
    ).all()
    preferences = Preferences(
        NoteDonnee(n.membre_id, n.recette_id, n.valeur) for n in s.exec(select(Note)).all()
    )
    resumes_courses = {b.semaine_id: b for b in s.exec(select(BilanCourses)).all()}
    membres = list(s.exec(select(Membre).order_by(col(Membre.id))).all())

    resultats: list[BilanHebdo] = []
    servis: Counter[str] = Counter()
    dernier_service: dict[str, date] = {}
    presences: dict[int, list[Nutriments]] = defaultdict(list)  # apports de chaque repas
    creneaux_total = 0

    for semaine in semaines:
        repas = [
            (c, r)
            for c, r in services.repas_servis(s, semaine)
            if r.plat in catalogue.profils and r.dessert in catalogue.profils
        ]
        if not repas:
            continue
        coefs = services.coefficients(s, semaine.lundi)
        creneaux_total += len(services.creneaux_de(s, semaine))
        infos = [
            infos_repas(catalogue.profils[r.plat], catalogue.profils[r.dessert], r.coefficients)
            for _, r in repas
        ]
        bilan = bilan_semaine([r for _, r in repas], catalogue, REPERES)
        portions = [Portion(rid, r.coefficients) for _, r in repas for rid in (r.plat, r.dessert)]
        resume = resumes_courses.get(semaine.id or 0)
        budget = resume.budget_eur if resume else liste_de_courses(portions, catalogue).total_eur
        personnes_repas = sum(r.coefficients for _, r in repas) or 1

        saison_ok = saison_total = 0.0
        legumes: set[str] = set()
        proteines: Counter[str] = Counter()
        mois = (semaine.lundi + timedelta(days=3)).month
        for c, r in repas:
            for rid in (r.plat, r.dessert):
                profil = catalogue.profils[rid]
                for ing, mois_ok in profil.mois_par_ingredient.items():
                    grammes = profil.grammes_par_ingredient[ing] * r.coefficients
                    saison_total += grammes
                    saison_ok += grammes if mois in mois_ok else 0
                legumes.update(
                    i
                    for i in profil.recette.ingredients
                    if catalogue.ingredients[i].famille == Famille.LEGUME
                )
            plat = catalogue.profils[r.plat]
            proteines[plat.proteine_principale] += 1
            if not r.restes_de:
                servis[r.plat] += 1
            dernier_service[r.plat] = semaine.lundi + timedelta(days=r.jour)
            apports = plat.nutriments + catalogue.profils[r.dessert].nutriments
            for membre_id in c.convives:
                presences[membre_id].append(apports.fois(coefs.get(membre_id, 1.0)))

        scores = [i.nutriscore_points for i in infos]
        vegetariens = sum(catalogue.profils[r.plat].est_vegetarien for _, r in repas)
        resultats.append(
            BilanHebdo(
                lundi=semaine.lundi,
                nb_repas=len(repas),
                nutriscore_moyen=lettre(round(sum(scores) / len(scores))),
                nutriscore_repartition=dict(Counter(i.nutriscore for i in infos)),
                reperes={
                    i.code: StatutRepere(valeur=i.valeur, statut=i.statut)
                    for i in bilan.indicateurs
                },
                co2_kg=bilan.co2_kg,
                co2_reference_kg=bilan.co2_reference_kg,
                budget_eur=round(budget, 2),
                budget_estime=resume is None,
                cout_par_repas_personne_eur=round(budget / personnes_repas, 2),
                part_saison=round(100 * saison_ok / saison_total, 1) if saison_total else 100.0,
                part_vegetarien=round(100 * vegetariens / len(repas), 1),
                legumes_differents=len(legumes),
                proteines=dict(proteines),
            )
        )

    co2 = sum(x.co2_kg for x in resultats)
    co2_reference = sum(x.co2_reference_kg for x in resultats)
    limite_redecouverte = aujourd_hui - timedelta(weeks=4)
    plats_ordinaires = catalogue.plats(plaisir=False)
    return BilanPeriode(
        semaines=resultats,
        membres=[
            _membre(m, presences.get(m.id or 0, []), creneaux_total, preferences, catalogue)
            for m in membres
        ],
        a_redecouvrir=sorted(
            catalogue.recettes[p.id].nom
            for p in plats_ordinaires
            if (preferences.note_famille(p.id) or 0) >= 4
            and dernier_service.get(p.id, date.min) < limite_redecouverte
        ),
        jamais_servis=sorted(p.recette.nom for p in plats_ordinaires if p.id not in servis),
        nb_plats_differents=len(servis),
        gaspillage=_gaspillage(s, resumes_courses.values(), catalogue, aujourd_hui),
        co2_total_kg=round(co2, 1),
        co2_economise_kg=round(max(co2_reference - co2, 0), 1),
        equivalent_km_voiture=round(max(co2_reference - co2, 0) / CO2_KG_PAR_KM_VOITURE),
        budget_total_eur=round(sum(x.budget_eur for x in resultats), 2),
    )


def _membre(
    membre: Membre,
    repas: list[Nutriments],
    creneaux_total: int,
    preferences: Preferences,
    catalogue: Catalogue,
) -> BilanMembre:
    """Couverture des besoins par les repas pris à la maison, et goûts du membre."""
    age = membre.age()
    total = Nutriments()
    for apports in repas:
        total = total + apports
    moyenne = total.fois(1 / len(repas)) if repas else Nutriments()
    couverture = []
    for code, (unite, libelle) in NUTRIMENTS_SUIVIS.items():
        reference = reference_journaliere(code, age, membre.sexe) * PART_ENERGIE_PAR_REPAS
        apport = getattr(moyenne, code)
        couverture.append(
            CouvertureNutriment(
                code=code,
                libelle=libelle,
                unite=unite,
                apport_par_repas=round(apport, 2),
                reference_par_repas=round(reference, 2),
                pourcentage=round(100 * apport / reference) if repas else 0,
            )
        )
    notes: dict[str, float] = {}
    for rid in catalogue.recettes:
        note_moyenne = preferences.moyenne_brute(membre.id or 0, rid)
        if note_moyenne is not None:
            notes[rid] = note_moyenne
    tries = sorted(notes.items(), key=lambda x: x[1], reverse=True)
    return BilanMembre(
        id=membre.id or 0,
        prenom=membre.prenom,
        couleur=membre.couleur,
        repas_a_la_maison=len(repas),
        repas_dehors=max(creneaux_total - len(repas), 0),
        couverture=couverture,
        preferes=[(catalogue.recettes[r].nom, v) for r, v in tries[:3] if v >= 3.5],
        moins_aimes=[(catalogue.recettes[r].nom, v) for r, v in tries[::-1][:3] if v <= 2.5],
    )


def _gaspillage(s: Session, resumes, catalogue: Catalogue, aujourd_hui: date) -> Gaspillage:
    resumes = list(resumes)
    perimes = [
        catalogue.ingredients[st.ingredient_id].nom
        for st in s.exec(select(Stock)).all()
        if st.peremption < aujourd_hui and st.ingredient_id in catalogue.ingredients
    ]
    return Gaspillage(
        depuis_placard_kg=round(sum(r.depuis_placard_g for r in resumes) / 1000, 1),
        surplus_placard_kg=round(sum(r.surplus_placard_g for r in resumes) / 1000, 1),
        surplus_perdu_kg=round(sum(r.surplus_perdu_g for r in resumes) / 1000, 1),
        semaines_validees=len(resumes),
        perimes=sorted(perimes),
    )
