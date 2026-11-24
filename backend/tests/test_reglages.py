"""Réglages par défaut : création sûre quand plusieurs requêtes arrivent en même temps."""

from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from repas import services
from repas.modeles import Reglages


def test_reglages_crees_par_defaut(tmp_path: Path):
    moteur = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(moteur)
    with Session(moteur) as s:
        assert services.obtenir_reglages(s).restes_max == Reglages().restes_max


def test_reglages_crees_en_meme_temps_par_une_autre_requete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Issue #38 : la ligne est créée par une autre requête entre la lecture et l'insertion."""
    moteur = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(moteur)
    with Session(moteur) as s, Session(moteur) as concurrente:
        lecture = s.get

        def lecture_avant_la_requete_concurrente(*args: object, **kwargs: object):
            # Première lecture : la table est encore vide ; la requête concurrente crée alors
            # la ligne avec un réglage modifié, avant que celle-ci n'insère la sienne.
            monkeypatch.setattr(s, "get", lecture)
            concurrente.add(Reglages(restes_max=2))
            concurrente.commit()
            return None

        monkeypatch.setattr(s, "get", lecture_avant_la_requete_concurrente)
        reglages = services.obtenir_reglages(s)

    assert reglages.restes_max == 2  # la ligne de l'autre requête est gardée, pas écrasée
