"""Frigo à vider : produits à consommer vite, idées de plats et bonus du planificateur."""

from datetime import date

from repas.catalogue import Catalogue
from repas.domaine.placard import a_vider, idees_pour_vider, jours_limites
from repas.domaine.planificateur import ContextePlanification, CreneauAPlanifier, planifier

LUNDI = date(2026, 11, 30)
FAMILLE = (1, 2, 3, 4)


def semaine() -> list[CreneauAPlanifier]:
    return [
        CreneauAPlanifier(cle=f"{j}-{m}", jour=j, moment=m, convives=FAMILLE)
        for j in range(7)
        for m in ("midi", "soir")
    ]


def jours_avec(cat: Catalogue, repas: dict, ingredient: str) -> list[int]:
    return sorted(
        int(cle.split("-")[0])
        for cle, r in repas.items()
        if ingredient in cat.recettes[r.plat].ingredients
        or ingredient in cat.recettes[r.dessert].ingredients
    )


def test_a_vider_dans_la_semaine():
    assert a_vider(date(2026, 12, 6), LUNDI)
    assert not a_vider(date(2026, 12, 7), LUNDI)


def test_jours_limites_seulement_pour_les_produits_a_vider():
    peremptions = {"courgette": date(2026, 12, 2), "riz": date(2027, 6, 1)}
    assert jours_limites(peremptions, LUNDI) == {"courgette": 2}


def test_idees_utilisent_les_produits_a_vider(cat: Catalogue):
    idees = idees_pour_vider({"courgette": 400}, cat, portions=4)
    assert idees and all("courgette" in idee.ingredients for idee in idees)
    assert idees == sorted(idees, key=lambda idee: -idee.part_videe)
    assert all(0 < idee.part_videe <= 1 for idee in idees)


def test_idees_ignorent_les_basiques(cat: Catalogue):
    basique = next(i for i, ing in cat.ingredients.items() if ing.basique)
    assert idees_pour_vider({basique: 500}, cat, portions=4) == []


def test_le_frigo_a_vider_est_consomme_avant_sa_date_limite(cat: Catalogue):
    # En novembre, la courgette est hors saison : sans le frigo à vider, elle est évitée.
    sans = planifier(semaine(), cat, ContextePlanification(mois=11))
    assert jours_avec(cat, sans.repas, "courgette") == []

    contexte = ContextePlanification(
        mois=11, stock={"courgette": 600}, a_consommer_avant={"courgette": 2}
    )
    avec = planifier(semaine(), cat, contexte)
    jours = jours_avec(cat, avec.repas, "courgette")
    assert jours and min(jours) <= 2
    assert avec.ecarts == sans.ecarts == {}


def test_les_jours_passes_ne_videnent_pas_le_frigo(cat: Catalogue):
    # Tout est à consommer lundi, mais lundi est passé : aucun bonus possible.
    contexte = ContextePlanification(
        mois=11, stock={"courgette": 600}, a_consommer_avant={"courgette": 0}, premier_jour=1
    )
    resultat = planifier(semaine(), cat, contexte)
    assert jours_avec(cat, resultat.repas, "courgette") == []
