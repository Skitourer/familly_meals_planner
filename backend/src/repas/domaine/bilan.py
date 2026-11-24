"""Bilan d'une semaine planifiée : nutrition, repères PNNS, carbone, budget.

Le bilan est recalculé à partir des repas choisis (y compris ceux modifiés à la
main) : il montre à la famille si la semaine reste équilibrée.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from repas.catalogue import Catalogue, ProfilRecette
from repas.catalogue.schemas import Nutriments
from repas.domaine.notes import Preferences
from repas.domaine.nutriscore import nutriscore
from repas.domaine.reperes import Reperes

type Statut = Literal["ok", "attention", "hors_cible"]

NOMS_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


@dataclass(frozen=True)
class RepasServi:
    cle: str
    jour: int
    moment: str
    plat: str
    dessert: str
    coefficients: float  # somme des coefficients de portion des convives
    joker: bool = False
    restes_de: str | None = None


@dataclass(frozen=True)
class Indicateur:
    code: str
    libelle: str
    valeur: float
    cible: str
    unite: str
    statut: Statut


@dataclass
class Bilan:
    indicateurs: list[Indicateur]
    co2_kg: float  # pour toute la famille, sur la semaine
    co2_reference_kg: float  # même nombre de repas « moyens » français
    nb_repas: int
    nb_jokers: int


# Empreinte d'un repas moyen en France : ~2,0 kg CO2e (ADEME, Impact CO2,
# « repas classique » ≈ 2,1 ; « repas végétarien » ≈ 0,5).
CO2_REPAS_MOYEN_KG = 2.0


def bilan_semaine(repas: list[RepasServi], catalogue: Catalogue, reperes: Reperes) -> Bilan:
    suivis = [r for r in repas if not r.joker]
    n = len(suivis)
    co2 = sum(
        (catalogue.profils[r.plat].co2_kg + catalogue.profils[r.dessert].co2_kg) * r.coefficients
        for r in repas
    )
    personnes_repas = sum(r.coefficients for r in repas)
    bilan = Bilan(
        indicateurs=[],
        co2_kg=round(co2, 1),
        co2_reference_kg=round(personnes_repas * CO2_REPAS_MOYEN_KG, 1),
        nb_repas=len(repas),
        nb_jokers=len(repas) - n,
    )
    if not n:
        return bilan

    total = Nutriments()
    for r in suivis:
        total = (
            total + catalogue.profils[r.plat].nutriments + catalogue.profils[r.dessert].nutriments
        )
    moyenne = total.fois(1 / n)
    kcal = max(moyenne.energie_kcal, 1)
    fl = (
        sum(
            catalogue.profils[r.plat].fruits_legumes_g
            + catalogue.profils[r.dessert].fruits_legumes_g
            for r in suivis
        )
        / n
    )
    plats = [catalogue.profils[r.plat] for r in suivis]
    hebdo = reperes.a_l_echelle(n)

    def entre(code, libelle, valeur, mini, maxi, unite) -> Indicateur:
        cible = f"{mini:g}–{maxi:g}" if maxi is not None else f"≥ {mini:g}"
        return Indicateur(code, libelle, round(valeur, 1), cible, unite,
                          _statut(valeur, mini, maxi))  # fmt: skip

    def au_plus(code, libelle, valeur, maxi, unite) -> Indicateur:
        return Indicateur(code, libelle, round(valeur, 1), f"≤ {maxi:g}", unite,
                          _statut(valeur, None, maxi))  # fmt: skip

    bilan.indicateurs = [
        entre("energie", "Énergie par repas", kcal, reperes.energie_min_kcal,
              reperes.energie_max_kcal, "kcal"),
        entre("proteines", "Protéines", 400 * moyenne.proteines_g / kcal,
              100 * reperes.proteines_min_part, 100 * reperes.proteines_max_part, "% énergie"),
        au_plus("lipides", "Lipides", 900 * moyenne.lipides_g / kcal,
                100 * reperes.lipides_max_part, "% énergie"),
        au_plus("ags", "Acides gras saturés", 900 * moyenne.ags_g / kcal,
                100 * reperes.ags_max_part, "% énergie"),
        entre("fibres", "Fibres par repas", moyenne.fibres_g, reperes.fibres_min_g, None, "g"),
        au_plus("sel", "Sel par repas", moyenne.sel_g, reperes.sel_max_g, "g"),
        entre("fruits_legumes", "Fruits et légumes par repas", fl,
              reperes.fruits_legumes_min_g, None, "g"),
        entre("poisson", "Repas avec poisson", sum(p.est_poisson for p in plats),
              hebdo.poissons_min, None, "repas"),
        entre("legumineuses", "Repas avec légumineuses", sum(p.est_legumineuse for p in plats),
              hebdo.legumineuses_min, None, "repas"),
        entre("laitiers", "Produits laitiers (midi et soir)",
              sum(catalogue.profils[r.plat].est_laitier + catalogue.profils[r.dessert].est_laitier
                  for r in suivis),
              reperes.produits_laitiers_min_par_jour * len({r.jour for r in suivis}), None,
              "portions"),
        au_plus("viande_rouge", "Viande hors volaille", sum(p.viande_rouge_g for p in plats),
                round(hebdo.viande_rouge_max_g), "g/pers."),
        au_plus("charcuterie", "Charcuterie", sum(p.charcuterie_g for p in plats),
                round(hebdo.charcuterie_max_g), "g/pers."),
    ]  # fmt: skip
    return bilan


def _statut(valeur: float, mini: float | None, maxi: float | None) -> Statut:
    """« ok » dans la cible, « attention » à moins de 10 % d'écart, sinon « hors_cible »."""
    if (mini is None or valeur >= mini) and (maxi is None or valeur <= maxi):
        return "ok"
    reference = mini if mini is not None and valeur < mini else maxi
    if reference and abs(valeur - reference) / reference <= 0.10:
        return "attention"
    return "hors_cible"


def raisons(
    profil: ProfilRecette,
    *,
    mois: int,
    catalogue: Catalogue,
    preferences: Preferences,
    stock: dict[str, float],
    restes_de: str | None = None,
    joker: bool = False,
) -> list[str]:
    """Explications lisibles du choix d'un plat (« Pourquoi ce plat ? »)."""
    explications: list[str] = []
    if restes_de:
        jour, moment = restes_de.split("-")
        explications.append(f"Restes du {NOMS_JOURS[int(jour)]} {moment} : pas de cuisine")
    if joker and profil.recette.plaisir:
        explications.append("Repas plaisir du joker")
    saisonniers = [catalogue.ingredients[i].nom for i in profil.mois_par_ingredient]
    hors = profil.hors_saison(mois)
    if saisonniers and not hors:
        explications.append("De saison : " + ", ".join(saisonniers[:3]).lower())
    elif hors:
        noms = ", ".join(catalogue.ingredients[i].nom for i in hors).lower()
        explications.append(f"Attention, hors saison : {noms}")
    note = preferences.note_famille(profil.id)
    if note is not None:
        explications.append(f"Note de la famille : {note:g}/5".replace(".", ","))
    if profil.est_poisson_gras:
        explications.append("Poisson gras (oméga-3)")
    elif profil.est_poisson:
        explications.append("Poisson")
    if profil.est_legumineuse:
        explications.append("Légumineuses")
    if profil.co2_kg < 0.8:
        explications.append(f"Bas carbone ({profil.co2_kg:.1f} kg CO2e)".replace(".", ","))
    du_placard = [
        catalogue.ingredients[i].nom.lower()
        for i in profil.recette.ingredients
        if stock.get(i, 0) > 0 and not catalogue.ingredients[i].basique
    ]
    if du_placard:
        explications.append("Utilise le placard : " + ", ".join(du_placard))
    return explications


@dataclass(frozen=True)
class InfosRepas:
    """Chiffres clés d'un repas (plat + dessert), affichés dans le planning."""

    nutriscore: str  # lettre A à E
    nutriscore_points: int
    energie_kcal: float  # portion adulte de référence
    proteines_g: float
    fibres_g: float
    fruits_legumes_g: float
    vegetarien: bool
    co2_kg: float  # pour tous les convives
    co2_kg_portion: float  # portion adulte de référence
    prix_eur: float  # pour tous les convives (estimation, ingrédients consommés)


def infos_repas(plat: ProfilRecette, dessert: ProfilRecette, coefficients: float) -> InfosRepas:
    """Nutri-Score, valeurs nutritionnelles, carbone et coût d'un repas."""
    nutriments = plat.nutriments + dessert.nutriments
    score = nutriscore(
        nutriments,
        plat.poids_cuit_g + dessert.poids_cuit_g,
        plat.fruits_legumes_legumineuses_g + dessert.fruits_legumes_legumineuses_g,
    )
    co2 = plat.co2_kg + dessert.co2_kg
    return InfosRepas(
        nutriscore=score.lettre,
        nutriscore_points=score.score,
        energie_kcal=round(nutriments.energie_kcal),
        proteines_g=round(nutriments.proteines_g, 1),
        fibres_g=round(nutriments.fibres_g, 1),
        fruits_legumes_g=round(plat.fruits_legumes_g + dessert.fruits_legumes_g),
        vegetarien=plat.est_vegetarien,
        co2_kg=round(co2 * coefficients, 2),
        co2_kg_portion=round(co2, 2),
        prix_eur=round((plat.prix_eur + dessert.prix_eur) * coefficients, 2),
    )
