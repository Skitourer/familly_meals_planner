"""Tables de la base SQLite (SQLModel = SQLAlchemy + Pydantic).

Le catalogue (recettes, ingrédients) n'est PAS en base : il vit dans des
fichiers versionnés (``donnees/``). La base ne contient que les données de la
famille : membres, semaines planifiées, notes, placard et réglages.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from repas.domaine.besoins import ModeDeVie, Sexe


def maintenant() -> datetime:
    return datetime.now(UTC)


class Membre(SQLModel, table=True):
    """Un membre de la famille et ses caractéristiques physiques."""

    id: int | None = Field(default=None, primary_key=True)
    prenom: str = Field(min_length=1, max_length=40)
    couleur: str = Field(default="#4f8a5b", max_length=9)
    date_naissance: date
    sexe: Sexe
    poids_kg: float = Field(gt=0, lt=300)
    mode_de_vie: ModeDeVie = ModeDeVie.SEDENTAIRE
    heures_sport_semaine: float = Field(default=0, ge=0, le=40)
    actif: bool = True  # un membre parti (étudiant...) reste dans l'historique

    def age(self, le: date | None = None) -> int:
        jour = le or date.today()
        avant_anniversaire = (jour.month, jour.day) < (self.date_naissance.month,
                                                        self.date_naissance.day)  # fmt: skip
        return jour.year - self.date_naissance.year - int(avant_anniversaire)


class Semaine(SQLModel, table=True):
    """Une semaine de repas, identifiée par la date de son lundi."""

    id: int | None = Field(default=None, primary_key=True)
    lundi: date = Field(unique=True, index=True)
    graine: int = 0  # change à chaque « Régénérer » pour varier les propositions
    generee_le: datetime | None = None
    courses_validees_le: datetime | None = None
    ecarts: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Creneau(SQLModel, table=True):
    """Un repas (midi ou soir) d'une semaine."""

    __table_args__ = (UniqueConstraint("semaine_id", "jour", "moment"),)

    id: int | None = Field(default=None, primary_key=True)
    semaine_id: int = Field(foreign_key="semaine.id", index=True)
    jour: int = Field(ge=0, le=6)  # 0 = lundi
    moment: str = Field(regex="^(midi|soir)$")
    convives: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    invites: int = Field(default=0, ge=0, le=20)
    joker: bool = False
    plat_id: str | None = None
    dessert_id: str | None = None
    verrouille: bool = False  # choix fait à la main, conservé lors d'une régénération
    restes_de: str | None = None  # clé "jour-moment" du créneau où le plat est cuisiné

    @property
    def cle(self) -> str:
        return f"{self.jour}-{self.moment}"


class Note(SQLModel, table=True):
    """Note (1 à 5) donnée par un membre à un plat servi lors d'un repas."""

    __table_args__ = (UniqueConstraint("membre_id", "creneau_id", "recette_id"),)

    id: int | None = Field(default=None, primary_key=True)
    membre_id: int = Field(foreign_key="membre.id", index=True)
    creneau_id: int = Field(foreign_key="creneau.id", index=True)
    recette_id: str = Field(index=True)
    valeur: int = Field(ge=1, le=5)
    commentaire: str = Field(default="", max_length=500)
    creee_le: datetime = Field(default_factory=maintenant)


class Stock(SQLModel, table=True):
    """Contenu du placard : reste de paquets entamés, en grammes comestibles."""

    ingredient_id: str = Field(primary_key=True)
    quantite_g: float = Field(ge=0)
    peremption: date
    mis_a_jour_le: datetime = Field(default_factory=maintenant)


class Reglages(SQLModel, table=True):
    """Préférences de la famille pour l'algorithme (une seule ligne, id = 1)."""

    id: int = Field(default=1, primary_key=True)
    priorite_budget: int = Field(default=1, ge=0, le=3)
    priorite_carbone: int = Field(default=2, ge=0, le=3)
    cuisine_en_lot: int = Field(default=2, ge=0, le=3)
    restes_max: int = Field(default=4, ge=0, le=8)
