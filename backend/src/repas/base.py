"""Connexion à la base SQLite et session par requête."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine

from repas import modeles  # noqa: F401  (enregistre les tables)
from repas.config import parametres


@lru_cache
def moteur() -> Engine:
    """Moteur SQLAlchemy ; crée le fichier et les tables au premier appel."""
    chemin = parametres().chemin_base
    chemin.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{chemin}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragmas(connexion, _):  # pyright: ignore[reportUnusedFunction]
        curseur = connexion.cursor()
        curseur.execute("PRAGMA foreign_keys=ON")
        curseur.execute("PRAGMA journal_mode=WAL")
        curseur.close()

    SQLModel.metadata.create_all(engine)
    return engine


def session() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    with Session(moteur()) as s:
        yield s
