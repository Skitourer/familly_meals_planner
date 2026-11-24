from collections import Counter

import pytest

from repas.catalogue import Catalogue
from repas.domaine.notes import NoteDonnee, Preferences
from repas.domaine.planificateur import (
    ContextePlanification,
    CreneauAPlanifier,
    ErreurPlanification,
    alternatives,
    attribuer_restes,
    planifier,
)

FAMILLE = (1, 2, 3, 4)


def semaine(
    joker: frozenset[str] = frozenset(), absents: frozenset[str] = frozenset(), **imposes: str
):
    return [
        CreneauAPlanifier(
            cle=f"{j}-{m}",
            jour=j,
            moment=m,
            convives=() if f"{j}-{m}" in absents else FAMILLE,
            joker=f"{j}-{m}" in joker,
            plat_impose=imposes.get(f"p{j}{m}"),
        )
        for j in range(7)
        for m in ("midi", "soir")
    ]


@pytest.mark.parametrize("mois", [1, 4, 7, 10])
def test_semaine_equilibree_toute_l_annee(cat: Catalogue, mois: int):
    resultat = planifier(semaine(), cat, ContextePlanification(mois=mois))
    assert len(resultat.repas) == 14
    assert resultat.ecarts == {}, f"repères non atteints en mois {mois} : {resultat.ecarts}"


def test_pas_de_repetition_hors_cuisine_en_lot(cat: Catalogue):
    resultat = planifier(semaine(), cat, ContextePlanification(mois=11))
    services = Counter(r.plat for r in resultat.repas.values())
    for plat, nombre in services.items():
        lot = cat.recettes[plat].lot
        assert nombre <= (lot.repas_max if lot else 1), plat


def test_restes_coherents(cat: Catalogue):
    resultat = planifier(semaine(), cat, ContextePlanification(mois=11, restes_max=4))
    restes = [r for r in resultat.repas.values() if r.restes_de]
    assert len(restes) <= 4
    for r in restes:
        assert r.restes_de is not None
        origine = resultat.repas[r.restes_de]
        assert origine.plat == r.plat and cat.recettes[r.plat].lot is not None


def test_plaisir_uniquement_sur_joker(cat: Catalogue):
    resultat = planifier(semaine(joker=frozenset({"5-soir"})), cat, ContextePlanification(mois=3))
    for cle, repas in resultat.repas.items():
        if cle != "5-soir":
            assert not cat.recettes[repas.plat].plaisir
            assert not cat.recettes[repas.dessert].plaisir
    assert cat.recettes[resultat.repas["5-soir"].plat].plaisir


def test_absents_et_verrous(cat: Catalogue):
    creneaux = semaine(absents=frozenset({"0-midi", "1-midi"}), p2soir="spaghetti-bolognaise")
    resultat = planifier(creneaux, cat, ContextePlanification(mois=5))
    assert "0-midi" not in resultat.repas and len(resultat.repas) == 12
    assert resultat.repas["2-soir"].plat == "spaghetti-bolognaise"


def test_verrous_contradictoires(cat: Catalogue):
    creneaux = semaine(p0midi="omelette-champignons", p3soir="omelette-champignons")
    with pytest.raises(ErreurPlanification):
        planifier(creneaux, cat, ContextePlanification(mois=5))


def test_les_notes_comptent(cat: Catalogue):
    notes = [NoteDonnee(m, "pates-pesto-haricots", 1) for m in FAMILLE for _ in range(3)]
    notes += [NoteDonnee(m, "tofu-saute-legumes", 5) for m in FAMILLE for _ in range(3)]
    ctx = ContextePlanification(mois=6, preferences=Preferences(notes))
    plats = {r.plat for r in planifier(semaine(), cat, ctx).repas.values()}
    assert "pates-pesto-haricots" not in plats
    assert "tofu-saute-legumes" in plats


def test_historique_evite_les_repetitions(cat: Catalogue):
    premiere = planifier(semaine(), cat, ContextePlanification(mois=2))
    deja = {r.plat: 1 for r in premiere.repas.values()}
    seconde = planifier(semaine(), cat, ContextePlanification(mois=2, semaines_depuis=deja))
    communs = {r.plat for r in seconde.repas.values()} & set(deja)
    assert len(communs) <= 4


def test_alternatives(cat: Catalogue):
    ctx = ContextePlanification(mois=9)
    creneaux = semaine()
    plan = planifier(creneaux, cat, ctx).repas
    propositions = alternatives(creneaux, cat, ctx, plan, "3-soir", nombre=3)
    assert len(propositions) == 3
    assert plan["3-soir"].plat not in [p for p, _ in propositions]
    pertes = [perte for _, perte in propositions]
    assert pertes == sorted(pertes)


def test_semaine_vide(cat: Catalogue):
    tous_absents = {f"{j}-{m}" for j in range(7) for m in ("midi", "soir")}
    assert (
        planifier(
            semaine(absents=frozenset(tous_absents)), cat, ContextePlanification(mois=1)
        ).repas
        == {}
    )


def test_restes_dans_la_duree_de_conservation(cat: Catalogue):
    for mois in (1, 6, 11):
        resultat = planifier(semaine(), cat, ContextePlanification(mois=mois, restes_max=6))
        jours = {cle: int(cle.split("-")[0]) for cle in resultat.repas}
        for r in resultat.repas.values():
            if r.restes_de:
                lot = cat.recettes[r.plat].lot
                assert lot is not None
                assert 0 < jours[r.cle] - jours[r.restes_de] <= lot.conservation_jours


def test_attribuer_restes_limite_de_repas_et_de_conservation(cat: Catalogue):
    dahl = "dahl-lentilles-corail"  # 3 repas au plus, 4 jours de conservation
    restes = attribuer_restes(
        [("0-soir", 0, dahl), ("1-midi", 1, dahl), ("2-soir", 2, dahl), ("3-midi", 3, dahl),
         ("4-soir", 4, "omelette-champignons"), ("6-soir", 6, dahl)],
        cat,
    )  # fmt: skip
    assert restes["0-soir"] is None  # cuisson
    assert restes["1-midi"] == restes["2-soir"] == "0-soir"
    assert restes["3-midi"] is None  # 3 repas déjà servis : on recuisine
    assert restes["6-soir"] == "3-midi"  # 3 jours après la seconde cuisson
    assert restes["4-soir"] is None  # plat ordinaire


def test_attribuer_restes_au_dela_de_la_conservation(cat: Catalogue):
    dahl = "dahl-lentilles-corail"
    restes = attribuer_restes([("0-soir", 0, dahl), ("5-soir", 5, dahl)], cat)
    assert restes["5-soir"] is None  # 5 jours > 4 jours de conservation : on recuisine
