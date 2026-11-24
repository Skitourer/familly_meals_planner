"""Coches de la liste de courses : la modification la plus récente l'emporte."""

from datetime import UTC, datetime, timedelta, timezone

from repas.domaine.coches import ModificationCoche, articles_coches, en_utc, fusionner_coches

MAINTENANT = datetime(2026, 12, 5, 10, 0, tzinfo=UTC)


def coche(id_ing: str, cochee: bool, minutes: int) -> ModificationCoche:
    return ModificationCoche(id_ing, cochee, MAINTENANT + timedelta(minutes=minutes))


def test_la_plus_recente_gagne_quel_que_soit_l_ordre_d_arrivee():
    # Le téléphone hors ligne décoche à 9 h 50, l'autre appareil coche à 9 h 55 :
    # l'envoi tardif du téléphone ne doit pas annuler la coche plus récente.
    actuelles = {"riz": coche("riz", True, -5)}
    resultat = fusionner_coches(actuelles, [coche("riz", False, -10)], MAINTENANT)
    assert resultat["riz"].cochee

    resultat = fusionner_coches(actuelles, [coche("riz", False, -1)], MAINTENANT)
    assert not resultat["riz"].cochee


def test_une_file_d_attente_s_applique_dans_l_ordre_des_heures():
    file = [coche("pates", True, -3), coche("pates", False, -2), coche("lait", True, -1)]
    assert articles_coches(fusionner_coches({}, file, MAINTENANT)) == ["lait"]


def test_horloge_en_avance_ramenee_a_maintenant():
    resultat = fusionner_coches({}, [coche("riz", True, 60)], MAINTENANT)
    assert resultat["riz"].modifiee_le == MAINTENANT
    # Un autre appareil peut donc décocher juste après.
    plus_tard = MAINTENANT + timedelta(minutes=1)
    resultat = fusionner_coches(resultat, [coche("riz", False, 1)], plus_tard)
    assert not resultat["riz"].cochee


def test_heures_sans_fuseau_considerees_en_utc():
    assert en_utc(datetime(2026, 12, 5, 10, 0)) == MAINTENANT
    heure_de_paris = datetime(2026, 12, 5, 11, 0, tzinfo=timezone(timedelta(hours=1)))
    assert en_utc(heure_de_paris) == MAINTENANT
