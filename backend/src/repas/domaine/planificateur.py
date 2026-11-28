"""Choix des repas de la semaine par optimisation sous contraintes.

Le problème est résolu par le solveur CP-SAT d'OR-Tools (Google, open source).

Variables
    ``plat[c, r]`` vaut 1 si le plat ``r`` est servi au créneau ``c`` ;
    ``dessert[c, d]`` vaut 1 si le dessert ``d`` est servi au créneau ``c``.

Contraintes strictes
    * un plat et un dessert par créneau où quelqu'un mange à la maison ;
    * les plats « plaisir » seulement sur les créneaux joker ;
    * pas de répétition : un plat au plus une fois par semaine, sauf les plats
      cuisinés en lot (soupes, mijotés), servis au plus ``repas_max`` fois dans
      leur durée de conservation, et jamais deux fois le même jour ;
    * un dessert au plus deux fois par semaine ;
    * variété : une même source de protéines (légumineuses, poisson, volaille,
      viande, œuf, fromage) sur au plus 35 % des repas ;
    * les choix verrouillés par la famille sont respectés.

Contraintes souples (pénalisées très fortement : la nutrition prime)
    Repères ANSES/PNNS de ``reperes.py`` sur les créneaux non joker : énergie
    par repas, part des protéines, lipides et graisses saturées, fibres, sel,
    fruits et légumes, poisson, légumineuses, produits laitiers, viande rouge,
    charcuterie.

Préférences (objectif, à poids réglables)
    repas pris à l'extérieur le même jour (pas de second poisson ou de seconde
    viande pour un membre qui en a déjà mangé), notes de la famille, saisonnalité,
    empreinte carbone, prix, répétition des semaines précédentes, restes de plats
    cuisinés en lot, utilisation du placard (bonus fort pour le frigo à vider avant
    sa date limite), plaisirs sur les jokers, temps de préparation en semaine, et
    une petite part de hasard pour varier les propositions.

L'algorithme est détaillé dans ``docs/algorithme.md``.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from ortools.sat.python import cp_model

from repas.catalogue import Catalogue, ProfilRecette
from repas.domaine.notes import Preferences
from repas.domaine.reperes import REPERES, Reperes

type Moment = Literal["midi", "soir"]
type CategorieExterieur = Literal["poisson", "viande", "vegetarien"]

DESSERT_MAX_PAR_SEMAINE = 2
PART_MAX_MEME_PROTEINE = 0.35  # variété des sources de protéines
TEMPS_SEMAINE_MAX_MIN = 45
JOURS_OUVRES = range(5)  # lundi à vendredi


class ErreurPlanification(RuntimeError):
    """Aucun planning ne respecte les contraintes strictes (verrous contradictoires...)."""


@dataclass(frozen=True)
class CreneauAPlanifier:
    """Un repas de la semaine, tel que défini par la famille le vendredi."""

    cle: str  # identifiant stable, ex. "0-midi"
    jour: int  # 0 = lundi ... 6 = dimanche
    moment: Moment
    convives: tuple[int, ...] = ()  # identifiants des membres présents
    invites: int = 0
    joker: bool = False
    plat_impose: str | None = None
    dessert_impose: str | None = None
    coefficients: float | None = None  # somme des coefficients de portion des convives

    @property
    def a_la_maison(self) -> bool:
        return bool(self.convives) or self.invites > 0

    @property
    def portions(self) -> float:
        """Nombre de portions de référence servies (une par personne à défaut)."""
        if self.coefficients is not None:
            return self.coefficients
        return len(self.convives) + self.invites

    @property
    def ordre(self) -> int:
        return self.jour * 2 + (0 if self.moment == "midi" else 1)


@dataclass(frozen=True)
class RepasExterieur:
    """Repas pris dehors par un membre (cantine...), dont la famille connaît la catégorie."""

    membre_id: int
    jour: int
    moment: Moment
    categorie: CategorieExterieur


@dataclass(frozen=True)
class Poids:
    """Importance relative de chaque critère dans l'objectif."""

    nutrition: float = 1000  # pénalité pour un écart de 100 % sur un repère
    notes: float = 40  # par point de note au-dessus/au-dessous de 3/5
    saison: float = 0.6  # par gramme d'ingrédient hors saison
    carbone: float = 25  # par kg CO2e (portion de référence)
    prix: float = 0  # par euro (portion de référence)
    repetition: tuple[float, ...] = (40, 20, 10)  # servi il y a 1, 2, 3 semaines
    cuisine_en_lot: float = 6  # par repas de restes (une cuisson pour plusieurs repas)
    placard: float = 20  # par ingrédient du placard entièrement consommé (au prorata)
    frigo_a_vider: float = 200  # idem pour un produit consommé avant sa date limite
    plaisir_joker: float = 80  # pour un plat ou dessert plaisir sur un joker
    # Par membre présent ayant déjà mangé la même catégorie dehors le même jour : un peu
    # plus qu'une étoile d'écart de note, pour l'emporter sur une légère préférence.
    exterieur_meme_jour: float = 60
    temps_semaine: float = 0.5  # par minute au-delà de 45 min en semaine
    hasard: float = 6  # amplitude du bruit aléatoire


@dataclass
class ContextePlanification:
    mois: int
    preferences: Preferences = field(default_factory=lambda: Preferences([]))
    semaines_depuis: dict[str, int] = field(default_factory=dict)
    stock: dict[str, float] = field(default_factory=dict)
    # Produits à vider -> dernier jour (0 = lundi) où les consommer.
    a_consommer_avant: dict[str, int] = field(default_factory=dict)
    premier_jour: int = 0  # jours déjà passés : leurs repas ne puisent plus dans le placard
    poids: Poids = field(default_factory=Poids)
    reperes: Reperes = REPERES
    graine: int = 0
    restes_max: int = 4  # repas de restes au plus par semaine
    repas_exterieurs: tuple[RepasExterieur, ...] = ()
    duree_max_s: float = 10.0


@dataclass(frozen=True)
class RepasPlanifie:
    cle: str
    plat: str
    dessert: str
    restes_de: str | None = None  # clé du créneau où le plat a été cuisiné


@dataclass
class ResultatPlanification:
    repas: dict[str, RepasPlanifie]
    optimal: bool
    score: float
    ecarts: dict[str, float]  # repère non atteint -> écart (unité du repère)


def planifier(
    creneaux: list[CreneauAPlanifier],
    catalogue: Catalogue,
    contexte: ContextePlanification,
    *,
    interdits: dict[str, set[str]] | None = None,
) -> ResultatPlanification:
    """Calcule le meilleur planning pour les créneaux donnés.

    ``interdits`` permet d'exclure des plats sur certains créneaux (utilisé pour
    proposer des alternatives à un repas).
    """
    return _Modele(creneaux, catalogue, contexte, interdits or {}).resoudre()


def alternatives(
    creneaux: list[CreneauAPlanifier],
    catalogue: Catalogue,
    contexte: ContextePlanification,
    plan: dict[str, RepasPlanifie],
    cle: str,
    nombre: int = 5,
) -> list[tuple[str, float]]:
    """Meilleurs plats de remplacement pour un créneau, le reste de la semaine étant figé.

    Renvoie une liste ``(id du plat, perte de score)`` triée du meilleur au moins bon.
    """
    figes = [
        _figer(c, plan[c.cle], figer_plat=c.cle != cle) if c.cle in plan else c for c in creneaux
    ]
    reference = planifier(figes, catalogue, contexte).score
    exclus = {plan[cle].plat} if cle in plan else set()
    resultats: list[tuple[str, float]] = []
    for _ in range(nombre):
        try:
            essai = planifier(figes, catalogue, contexte, interdits={cle: exclus})
        except ErreurPlanification:
            break
        plat = essai.repas[cle].plat
        resultats.append((plat, round(reference - essai.score, 1)))
        exclus.add(plat)
    return sorted(resultats, key=lambda r: r[1])


def attribuer_restes(
    services: list[tuple[str, int, str]], catalogue: Catalogue
) -> dict[str, str | None]:
    """Indique, pour chaque repas, le repas où son plat a été cuisiné (None = cuisiné ce jour).

    ``services`` : (clé du créneau, jour, plat) dans l'ordre chronologique. Un plat
    cuisiné en lot fournit des restes tant que l'on reste dans sa durée de conservation
    (comptée depuis le jour de cuisson) et dans son nombre de repas maximal ; au-delà,
    il faut le cuisiner à nouveau. Un plat ordinaire est toujours cuisiné le jour même.
    """
    lots: dict[str, tuple[str, int, int]] = {}  # plat -> (clé de cuisson, jour, repas servis)
    resultat: dict[str, str | None] = {}
    for cle, jour, plat in services:
        lot = catalogue.recettes[plat].lot if plat in catalogue.recettes else None
        en_cours = lots.get(plat)
        if (
            lot
            and en_cours
            and jour - en_cours[1] <= lot.conservation_jours
            and en_cours[2] < lot.repas_max
        ):
            resultat[cle] = en_cours[0]
            lots[plat] = (en_cours[0], en_cours[1], en_cours[2] + 1)
        else:
            resultat[cle] = None
            lots[plat] = (cle, jour, 1)
    return resultat


def _figer(creneau: CreneauAPlanifier, repas: RepasPlanifie, *, figer_plat: bool):
    return CreneauAPlanifier(
        cle=creneau.cle,
        jour=creneau.jour,
        moment=creneau.moment,
        convives=creneau.convives,
        invites=creneau.invites,
        joker=creneau.joker,
        plat_impose=repas.plat if figer_plat else None,
        dessert_impose=repas.dessert,
        coefficients=creneau.coefficients,
    )


class _Modele:
    """Construction et résolution du modèle CP-SAT (usage interne)."""

    def __init__(
        self,
        creneaux: list[CreneauAPlanifier],
        catalogue: Catalogue,
        contexte: ContextePlanification,
        interdits: dict[str, set[str]],
    ):
        self.creneaux = sorted((c for c in creneaux if c.a_la_maison), key=lambda c: c.ordre)
        self.catalogue = catalogue
        self.ctx = contexte
        self.interdits = interdits
        self.modele = cp_model.CpModel()
        self.objectif: list = []  # termes à maximiser
        self.ecarts: dict[str, tuple[cp_model.IntVar, float]] = {}
        self.plat: dict[tuple[str, str], cp_model.IntVar] = {}
        self.dessert: dict[tuple[str, str], cp_model.IntVar] = {}

    # --- Résolution ---------------------------------------------------------------

    def resoudre(self) -> ResultatPlanification:
        if not self.creneaux:
            return ResultatPlanification(repas={}, optimal=True, score=0, ecarts={})
        self._variables()
        self._contraintes_repetition()
        self._contraintes_nutrition()
        self._preferences()
        self._repas_exterieurs()
        self._placard()
        self.modele.maximize(sum(self.objectif))

        solveur = cp_model.CpSolver()
        solveur.parameters.max_time_in_seconds = self.ctx.duree_max_s
        solveur.parameters.num_workers = 8
        solveur.parameters.random_seed = self.ctx.graine % 1000
        statut = solveur.solve(self.modele)
        if statut not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise ErreurPlanification(
                "Aucun planning possible : vérifiez les plats verrouillés (un même plat "
                "ne peut être servi qu'une fois, sauf plats cuisinés en lot)."
            )
        return self._lire_solution(solveur, optimal=statut == cp_model.OPTIMAL)

    def _lire_solution(self, solveur: cp_model.CpSolver, *, optimal: bool):
        choix: dict[str, tuple[str, str]] = {}
        for c in self.creneaux:
            plat = next(r for (k, r), v in self.plat.items() if k == c.cle and solveur.value(v))
            dessert = next(
                d for (k, d), v in self.dessert.items() if k == c.cle and solveur.value(v)
            )
            choix[c.cle] = (plat, dessert)

        restes = attribuer_restes(
            [(c.cle, c.jour, choix[c.cle][0]) for c in self.creneaux], self.catalogue
        )
        repas = {
            c.cle: RepasPlanifie(c.cle, *choix[c.cle], restes_de=restes[c.cle])
            for c in self.creneaux
        }

        ecarts = {
            nom: round(solveur.value(var) / echelle, 2)
            for nom, (var, echelle) in self.ecarts.items()
            if solveur.value(var) > 0
        }
        return ResultatPlanification(repas, optimal, solveur.objective_value, ecarts)

    # --- Variables -------------------------------------------------------------------

    def _variables(self) -> None:
        for c in self.creneaux:
            interdits = self.interdits.get(c.cle, set())
            plats = [
                p
                for p in self.catalogue.plats()
                if (c.joker or not p.recette.plaisir or p.id == c.plat_impose)
                and p.id not in interdits
            ]
            desserts = [
                d
                for d in self.catalogue.desserts()
                if c.joker or not d.recette.plaisir or d.id == c.dessert_impose
            ]
            for p in plats:
                self.plat[c.cle, p.id] = self.modele.new_bool_var(f"plat[{c.cle},{p.id}]")
            for d in desserts:
                self.dessert[c.cle, d.id] = self.modele.new_bool_var(f"dessert[{c.cle},{d.id}]")

            self.modele.add_exactly_one(v for (k, _), v in self.plat.items() if k == c.cle)
            self.modele.add_exactly_one(v for (k, _), v in self.dessert.items() if k == c.cle)
            if c.plat_impose:
                if (c.cle, c.plat_impose) not in self.plat:
                    raise ErreurPlanification(f"Plat inconnu ou interdit : {c.plat_impose}")
                self.modele.add(self.plat[c.cle, c.plat_impose] == 1)
            if c.dessert_impose and (c.cle, c.dessert_impose) in self.dessert:
                self.modele.add(self.dessert[c.cle, c.dessert_impose] == 1)

    def _par_recette(self, variables: dict[tuple[str, str], cp_model.IntVar]):
        groupes: dict[str, list[tuple[CreneauAPlanifier, cp_model.IntVar]]] = defaultdict(list)
        creneau = {c.cle: c for c in self.creneaux}
        for (cle, rid), var in variables.items():
            groupes[rid].append((creneau[cle], var))
        return groupes

    # --- Contraintes strictes : répétition et cuisine en lot ----------------------------

    def _contraintes_repetition(self) -> None:
        tous_les_restes = []
        for rid, services in self._par_recette(self.plat).items():
            lot = self.catalogue.recettes[rid].lot
            vars_plat = [v for _, v in services]
            if lot is None:
                self.modele.add(sum(vars_plat) <= 1)
                continue
            self.modele.add(sum(vars_plat) <= lot.repas_max)
            for i, (c1, v1) in enumerate(services):
                for c2, v2 in services[i + 1 :]:
                    trop_loin = abs(c1.jour - c2.jour) > lot.conservation_jours
                    if trop_loin or c1.jour == c2.jour:
                        self.modele.add(v1 + v2 <= 1)
            # Bonus « restes » : chaque service au-delà du premier évite une cuisson.
            utilise = self.modele.new_bool_var(f"cuisine[{rid}]")
            for v in vars_plat:
                self.modele.add_implication(v, utilise)
            self.modele.add(sum(vars_plat) >= utilise)
            restes = sum(vars_plat) - utilise
            self.objectif.append(self.ctx.poids.cuisine_en_lot * restes)
            tous_les_restes.append(restes)
        if tous_les_restes:
            self.modele.add(sum(tous_les_restes) <= self.ctx.restes_max)

        for _, services in self._par_recette(self.dessert).items():
            self.modele.add(sum(v for _, v in services) <= DESSERT_MAX_PAR_SEMAINE)

        # Variété : une même source de protéines sur au plus ~35 % des repas.
        par_proteine: dict[str, list[cp_model.IntVar]] = defaultdict(list)
        for (_, rid), var in self.plat.items():
            par_proteine[self.catalogue.profils[rid].proteine_principale].append(var)
        maximum = max(2, math.ceil(PART_MAX_MEME_PROTEINE * len(self.creneaux)))
        for variables in par_proteine.values():
            self.modele.add(sum(variables) <= maximum)

    # --- Contraintes souples : repères nutritionnels ------------------------------------

    def _contraintes_nutrition(self) -> None:
        r = self.ctx.reperes
        suivis = [c for c in self.creneaux if not c.joker]
        if not suivis:
            return
        n = len(suivis)

        def somme(attribut) -> cp_model.LinearExpr:
            """Somme d'un attribut (entier) des plats et desserts servis sur les créneaux suivis."""
            termes = []
            for c in suivis:
                for (k, rid), v in self.plat.items():
                    if k == c.cle:
                        termes.append(attribut(self.catalogue.profils[rid]) * v)
                for (k, rid), v in self.dessert.items():
                    if k == c.cle:
                        termes.append(attribut(self.catalogue.profils[rid]) * v)
            return sum(termes)  # type: ignore[return-value]

        def kcal(p: ProfilRecette) -> int:
            return round(p.nutriments.energie_kcal)

        energie = somme(kcal)
        energie_cible = n * (r.energie_min_kcal + r.energie_max_kcal) / 2

        # Énergie de chaque repas (portion de référence).
        for c in suivis:
            e = sum(
                kcal(self.catalogue.profils[rid]) * v
                for (k, rid), v in (*self.plat.items(), *self.dessert.items())
                if k == c.cle
            )
            self._au_moins(f"energie_min_{c.cle}", e, r.energie_min_kcal, 2 * r.energie_min_kcal)
            self._au_plus(f"energie_max_{c.cle}", e, r.energie_max_kcal, 2 * r.energie_max_kcal)

        # Parts de l'énergie (en centièmes) : 100 × kcal_nutriment ≥ part × 100 × kcal_total.
        proteines = somme(lambda p: round(4 * p.nutriments.proteines_g))
        lipides = somme(lambda p: round(9 * p.nutriments.lipides_g))
        ags = somme(lambda p: round(9 * p.nutriments.ags_g))
        reference = 100 * energie_cible
        self._au_moins(
            "proteines_min", 100 * proteines - round(100 * r.proteines_min_part) * energie,
            0, reference * r.proteines_min_part,
        )  # fmt: skip
        self._au_plus(
            "proteines_max", 100 * proteines - round(100 * r.proteines_max_part) * energie,
            0, reference * r.proteines_max_part,
        )  # fmt: skip
        self._au_plus(
            "lipides_max", 100 * lipides - round(100 * r.lipides_max_part) * energie,
            0, reference * r.lipides_max_part,
        )  # fmt: skip
        self._au_plus(
            "ags_max", 100 * ags - round(100 * r.ags_max_part) * energie,
            0, reference * r.ags_max_part,
        )  # fmt: skip

        # Fibres (dixièmes de g), sel (centièmes de g), fruits et légumes (g).
        fibres = somme(lambda p: round(10 * p.nutriments.fibres_g))
        self._au_moins("fibres_min", fibres, 10 * r.fibres_min_g * n, 10 * r.fibres_min_g * n)
        sel = somme(lambda p: round(100 * p.nutriments.sel_g))
        self._au_plus("sel_max", sel, 100 * r.sel_max_g * n, 100 * r.sel_max_g * n)
        fl = somme(lambda p: round(p.fruits_legumes_g))
        self._au_moins(
            "fruits_legumes_min", fl, r.fruits_legumes_min_g * n, r.fruits_legumes_min_g * n
        )

        # Repères hebdomadaires du PNNS (plats uniquement).
        hebdo = r.a_l_echelle(n)
        cles_suivies = {c.cle for c in suivis}

        def compte(critere) -> cp_model.LinearExpr:
            return sum(  # type: ignore[return-value]
                v
                for (k, rid), v in self.plat.items()
                if k in cles_suivies and critere(self.catalogue.profils[rid])
            )

        def grammes(attribut) -> cp_model.LinearExpr:
            return sum(  # type: ignore[return-value]
                round(attribut(self.catalogue.profils[rid])) * v
                for (k, rid), v in self.plat.items()
                if k in cles_suivies
            )

        poissons_min = max(0, hebdo.poissons_min - self._poissons_manges_dehors(suivis))
        if poissons_min:
            poissons = compte(lambda p: p.est_poisson)
            self._au_moins("poisson_min", poissons, poissons_min, poissons_min)
        if hebdo.poissons_gras_min:
            gras = compte(lambda p: p.est_poisson_gras)
            self._au_moins("poisson_gras_min", gras, hebdo.poissons_gras_min, 2)
        if hebdo.legumineuses_min:
            legumineuses = compte(lambda p: p.est_legumineuse)
            self._au_moins(
                "legumineuses_min", legumineuses, hebdo.legumineuses_min, hebdo.legumineuses_min
            )
        # Produits laitiers : au moins un par jour (plat au fromage ou laitage en dessert).
        jours = len({c.jour for c in suivis})
        laitiers = sum(
            v
            for (k, rid), v in (*self.plat.items(), *self.dessert.items())
            if k in cles_suivies and self.catalogue.profils[rid].est_laitier
        )
        minimum_laitiers = r.produits_laitiers_min_par_jour * jours
        self._au_moins("laitiers_min", laitiers, minimum_laitiers, minimum_laitiers)

        rouge = grammes(lambda p: p.viande_rouge_g)
        self._au_plus("viande_rouge_max", rouge, hebdo.viande_rouge_max_g, r.viande_rouge_max_g)
        charcuterie = grammes(lambda p: p.charcuterie_g)
        self._au_plus("charcuterie_max", charcuterie, hebdo.charcuterie_max_g, r.charcuterie_max_g)

    def _poissons_manges_dehors(self, suivis: list[CreneauAPlanifier]) -> int:
        """Poissons mangés dehors, ramenés à des repas de toute la famille.

        Les repères sont fixés pour chaque personne : quand deux enfants sur quatre
        mangent du poisson à la cantine, c'est un demi-repas de poisson pour la famille.
        """
        membres = {m for c in suivis for m in c.convives}
        poissons = sum(
            1
            for r in self.ctx.repas_exterieurs
            if r.categorie == "poisson" and r.membre_id in membres
        )
        return poissons // len(membres) if membres else 0

    def _au_moins(self, nom: str, expression, borne: float, echelle: float) -> None:
        """expression ≥ borne, avec un écart pénalisé proportionnellement à ``echelle``."""
        ecart = self.modele.new_int_var(0, 10**9, f"ecart_{nom}")
        self.modele.add(expression + ecart >= round(borne))
        self._penaliser(nom, ecart, echelle)

    def _au_plus(self, nom: str, expression, borne: float, echelle: float) -> None:
        """expression ≤ borne, avec un écart pénalisé proportionnellement à ``echelle``."""
        ecart = self.modele.new_int_var(0, 10**9, f"ecart_{nom}")
        self.modele.add(expression - ecart <= round(borne))
        self._penaliser(nom, ecart, echelle)

    def _penaliser(self, nom: str, ecart: cp_model.IntVar, echelle: float) -> None:
        echelle = max(echelle, 1)
        self.ecarts[nom] = (ecart, echelle)
        self.objectif.append(-self.ctx.poids.nutrition / echelle * ecart)

    # --- Préférences ------------------------------------------------------------------

    def _preferences(self) -> None:
        creneau = {c.cle: c for c in self.creneaux}
        for (cle, rid), var in self.plat.items():
            self.objectif.append(self._interet(creneau[cle], self.catalogue.profils[rid]) * var)
        for (cle, rid), var in self.dessert.items():
            self.objectif.append(self._interet(creneau[cle], self.catalogue.profils[rid]) * var)

    def _interet(self, c: CreneauAPlanifier, profil: ProfilRecette) -> float:
        """Intérêt (positif = souhaitable) de servir ``profil`` au créneau ``c``."""
        poids = self.ctx.poids
        recette = profil.recette
        interet = poids.notes * self.ctx.preferences.score(c.convives, recette.id)
        interet -= poids.saison * profil.grammes_hors_saison(self.ctx.mois)
        interet -= poids.carbone * profil.co2_kg
        interet -= poids.prix * profil.prix_eur

        semaines = self.ctx.semaines_depuis.get(recette.id)
        if semaines and semaines <= len(poids.repetition):
            interet -= poids.repetition[semaines - 1]

        if c.joker and recette.plaisir:
            interet += poids.plaisir_joker
        if c.jour in JOURS_OUVRES and recette.type == "plat" and recette.lot is None:
            interet -= poids.temps_semaine * max(0, recette.temps.total - TEMPS_SEMAINE_MAX_MIN)

        return interet + poids.hasard * self._bruit(c.cle, recette.id)

    def _repas_exterieurs(self) -> None:
        """Évite au membre un second poisson (ou une seconde viande) dans la même journée."""
        dehors: dict[tuple[int, int], set[str]] = defaultdict(set)  # (jour, membre) -> catégories
        for r in self.ctx.repas_exterieurs:
            dehors[r.jour, r.membre_id].add(r.categorie)
        criteres = {
            "poisson": lambda p: p.est_poisson,
            "viande": lambda p: p.proteine_principale in ("viande", "volaille"),
        }
        for c in self.creneaux:
            for categorie, critere in criteres.items():
                membres = sum(categorie in dehors.get((c.jour, m), ()) for m in c.convives)
                if not membres:
                    continue
                penalite = self.ctx.poids.exterieur_meme_jour * membres
                self.objectif.extend(
                    -penalite * v
                    for (k, rid), v in self.plat.items()
                    if k == c.cle and critere(self.catalogue.profils[rid])
                )

    def _placard(self) -> None:
        """Bonus pour la part du placard consommée par les repas de la semaine.

        Pour chaque produit, la consommation (en g) est bornée par le stock ; le bonus est
        proportionnel à la part consommée. Un produit à vider ne compte que sur les repas
        servis au plus tard à sa date limite, avec un poids bien plus fort. Les restes d'un
        plat cuisiné en lot sont comptés au jour où ils sont servis (estimation prudente).
        """
        creneau = {c.cle: c for c in self.creneaux}
        for id_ing, quantite in self.ctx.stock.items():
            ingredient = self.catalogue.ingredients.get(id_ing)
            if quantite < 1 or ingredient is None or ingredient.basique:
                continue
            dernier_jour = self.ctx.a_consommer_avant.get(id_ing, 6)
            usage = [
                round(recette.ingredients[id_ing] * creneau[cle].portions) * var
                for (cle, rid), var in (*self.plat.items(), *self.dessert.items())
                if self.ctx.premier_jour <= creneau[cle].jour <= dernier_jour
                and id_ing in (recette := self.catalogue.recettes[rid]).ingredients
            ]
            if not usage:
                continue
            consomme = self.modele.new_int_var(0, round(quantite), f"placard[{id_ing}]")
            self.modele.add(consomme <= sum(usage))
            poids = (
                self.ctx.poids.frigo_a_vider
                if id_ing in self.ctx.a_consommer_avant
                else self.ctx.poids.placard
            )
            self.objectif.append(poids / round(quantite) * consomme)

    def _bruit(self, cle: str, recette_id: str) -> float:
        """Nombre pseudo-aléatoire dans [0, 1[, stable pour une graine, un créneau et un plat."""
        empreinte = hashlib.sha256(f"{self.ctx.graine}:{cle}:{recette_id}".encode()).digest()
        return int.from_bytes(empreinte[:4]) / 2**32
