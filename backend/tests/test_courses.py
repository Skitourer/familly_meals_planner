from repas.catalogue import Catalogue
from repas.domaine.courses import (
    AchatConstate,
    Portion,
    appliquer_achats_reels,
    format_quantite,
    liste_de_courses,
    meilleure_combinaison,
    placard_apres_courses,
    retirer_non_achetes,
    stock_avant_validation,
)


def test_combinaison_minimise_le_surplus():
    assert meilleure_combinaison(350, [500]) == {500: 1}
    assert meilleure_combinaison(850, [500, 1000]) == {1000: 1}
    assert meilleure_combinaison(450, [250, 500]) == {500: 1}
    assert meilleure_combinaison(9, [6, 12]) == {12: 1}
    assert meilleure_combinaison(12, [6, 12]) == {12: 1}  # moins d'unités à surplus égal


def test_grandes_quantites():
    combinaison = meilleure_combinaison(4300, [500, 1000])
    assert sum(t * n for t, n in combinaison.items()) == 4500


def test_format_quantite():
    assert format_quantite(1500) == "1,5 kg"
    assert format_quantite(250) == "250 g"
    assert format_quantite(200, "ml") == "20 cl"
    assert format_quantite(1000, "ml") == "1 L"


def test_paquet_de_pates_et_surplus_au_placard(cat: Catalogue):
    # 350 g de pâtes nécessaires : on achète un paquet de 500 g, 150 g iront au placard.
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 350 / 90)], cat)
    pates = next(ligne for ligne in liste.lignes if ligne.ingredient_id == "pates")
    assert pates.besoin_g == 350
    assert pates.achete_g == 500 and pates.surplus_g == 150
    assert pates.surplus_au_placard
    nouveau = placard_apres_courses(liste, {}, cat)
    assert nouveau["pates"] == 150


def test_le_placard_est_utilise_en_priorite(cat: Catalogue):
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 2)], cat, {"pates": 300})
    pates = next(ligne for ligne in liste.lignes if ligne.ingredient_id == "pates")
    assert pates.depuis_placard_g == 180 and not pates.achats
    assert placard_apres_courses(liste, {"pates": 300}, cat)["pates"] == 120


def test_basiques_a_verifier(cat: Catalogue):
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 4)], cat)
    assert "Huile d'olive" in [ligne.nom for ligne in liste.a_verifier]
    assert all(not ligne.basique for ligne in liste.a_acheter)


def test_oeufs_par_boites_et_part_comestible(cat: Catalogue):
    liste = liste_de_courses([Portion("omelette-champignons", 4)], cat)
    oeufs = next(ligne for ligne in liste.lignes if ligne.ingredient_id == "oeuf")
    # 480 g d'œufs sans coquille ≈ 545 g bruts ≈ 9,1 œufs -> une boîte de 12
    assert [(a.nombre, a.libelle) for a in oeufs.achats] == [(1, "boîte de 12")]


def test_rayons_ordonnes_et_budget(cat: Catalogue):
    liste = liste_de_courses([Portion("saumon-brocoli-riz", 4), Portion("fruit-pomme", 4)], cat)
    rayons = [rayon for rayon, _ in liste.par_rayon()]
    assert rayons[0] == "Fruits et légumes"
    assert liste.total_eur > 0


def test_achat_reel_change_le_surplus_et_le_prix(cat: Catalogue):
    # 350 g de pâtes prévus en paquet de 500 g ; le magasin n'avait que des paquets de 1 kg.
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 350 / 90)], cat)
    estime = liste.total_eur
    reelle = appliquer_achats_reels(liste, {"pates": AchatConstate(1000, 2.345)}, cat)
    pates = next(ligne for ligne in reelle.lignes if ligne.ingredient_id == "pates")
    assert (pates.achete_g, pates.surplus_g, pates.prix_eur) == (1000, 650, 2.35)
    assert placard_apres_courses(reelle, {}, cat)["pates"] == 650
    avant = next(ligne for ligne in liste.lignes if ligne.ingredient_id == "pates")
    assert reelle.total_eur == round(estime - avant.prix_eur + 2.35, 2)


def test_achat_reel_insuffisant_sans_surplus(cat: Catalogue):
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 350 / 90)], cat)
    reelle = appliquer_achats_reels(liste, {"pates": AchatConstate(250, 1)}, cat)
    pates = next(ligne for ligne in reelle.lignes if ligne.ingredient_id == "pates")
    assert pates.surplus_g == 0 and "pates" not in placard_apres_courses(reelle, {}, cat)


def test_achat_hors_liste_va_au_placard(cat: Catalogue):
    # Des poireaux achetés sans être prévus : tout va au placard (part comestible).
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 350 / 90)], cat)
    reelle = appliquer_achats_reels(liste, {"poireau": AchatConstate(1000, 1.5)}, cat)
    (poireaux,) = reelle.hors_liste
    assert (poireaux.nom, poireaux.surplus_g, poireaux.prix_eur) == ("Poireaux", 1000, 1.5)
    assert poireaux not in reelle.a_acheter
    assert reelle.total_eur == round(liste.total_eur + 1.5, 2)
    assert placard_apres_courses(reelle, {}, cat)["poireau"] == 650


def test_achat_d_un_besoin_couvert_par_le_placard(cat: Catalogue):
    # Pâtes prévues mais déjà au placard : le paquet acheté s'ajoute au reste.
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 2)], cat, {"pates": 300})
    reelle = appliquer_achats_reels(liste, {"pates": AchatConstate(500, 0.9)}, cat)
    (pates,) = reelle.hors_liste
    assert pates.depuis_placard_g == 180
    assert placard_apres_courses(reelle, {"pates": 300}, cat)["pates"] == 620


def test_article_non_achete_sans_surplus_ni_prix(cat: Catalogue):
    liste = liste_de_courses([Portion("spaghetti-bolognaise", 350 / 90)], cat, {"carotte": 50})
    reelle = retirer_non_achetes(liste, {"pates", "carotte"})
    pates = next(ligne for ligne in reelle.lignes if ligne.ingredient_id == "pates")
    carotte = next(ligne for ligne in reelle.lignes if ligne.ingredient_id == "carotte")
    assert (pates.achats, pates.surplus_g, pates.prix_eur) == ([], 0, 0)
    assert pates not in reelle.a_acheter
    assert carotte.depuis_placard_g == 50  # ce que les repas prennent au placard reste déduit
    assert "pates" not in placard_apres_courses(reelle, {}, cat)


def test_stock_avant_validation():
    ecarts = {"pates": (0, 150), "riz": (300, 120), "lait": (200, 0)}
    # Depuis la validation, la famille a fini le riz à la main et ajouté des œufs.
    actuel = {"pates": 150, "riz": 0, "oeufs": 6}
    assert stock_avant_validation(actuel, ecarts) == {"riz": 180, "lait": 200, "oeufs": 6}
