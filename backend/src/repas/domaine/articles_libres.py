"""Articles libres de la liste de courses : hors repas, hors placard, comptés au budget."""

from collections.abc import Iterable, Sequence
from typing import Protocol

PREFIXE_COCHE_LIBRE = "libre-"


class ArticleIdentifie(Protocol):
    @property
    def id(self) -> int | None: ...


class ArticleAvecPrix(Protocol):
    @property
    def prix_eur(self) -> float | None: ...


def cle_coche_libre(article_id: int) -> str:
    """Clé de la coche d'un article libre : distincte des ingrédients et des produits à racheter."""
    return f"{PREFIXE_COCHE_LIBRE}{article_id}"


def a_reporter[A: ArticleIdentifie](articles: Sequence[A], coches: Iterable[str]) -> list[A]:
    """Articles non cochés : pas achetés, ils peuvent passer à la semaine suivante."""
    cochees = set(coches)
    return [a for a in articles if cle_coche_libre(a.id or 0) not in cochees]


def total_articles_libres(articles: Iterable[ArticleAvecPrix]) -> float:
    """Somme des prix saisis ; un article sans prix ne compte pas (pas d'estimation possible)."""
    return round(sum(a.prix_eur or 0 for a in articles), 2)
