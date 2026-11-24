"""Préférences de la famille, déduites des notes données après les repas.

Chaque membre note les plats de 1 à 5. Pour éviter qu'une seule note extrême ne
décide de tout, on utilise une **moyenne bayésienne** : la moyenne des notes
d'un membre pour un plat est « tirée » vers sa moyenne générale, d'autant plus
fortement que le plat a été peu noté.

    moyenne_bayésienne = (somme des notes + C × moyenne générale) / (nombre + C)

Le score d'un plat pour un repas est la moyenne de ce calcul sur les membres
présents, recentrée sur 0 (positif = apprécié, négatif = peu apprécié).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

POIDS_A_PRIORI = 2.0  # « C » : équivaut à 2 notes à la moyenne générale
NOTE_NEUTRE = 3.0


@dataclass(frozen=True)
class NoteDonnee:
    membre_id: int
    recette_id: str
    valeur: int  # 1 à 5


class Preferences:
    """Moyennes bayésiennes des notes, par membre et par recette."""

    def __init__(self, notes: Iterable[NoteDonnee]):
        self._notes: dict[tuple[int, str], list[int]] = defaultdict(list)
        toutes: dict[int, list[int]] = defaultdict(list)
        for note in notes:
            self._notes[(note.membre_id, note.recette_id)].append(note.valeur)
            toutes[note.membre_id].append(note.valeur)
        self._moyenne_membre = {m: sum(v) / len(v) for m, v in toutes.items()}

    def moyenne(self, membre_id: int, recette_id: str) -> float:
        """Moyenne bayésienne (1-5) d'un membre pour une recette."""
        a_priori = self._moyenne_membre.get(membre_id, NOTE_NEUTRE)
        valeurs = self._notes.get((membre_id, recette_id), [])
        return (sum(valeurs) + POIDS_A_PRIORI * a_priori) / (len(valeurs) + POIDS_A_PRIORI)

    def nombre_notes(self, recette_id: str) -> int:
        return sum(len(v) for (_, r), v in self._notes.items() if r == recette_id)

    def score(self, membres: Iterable[int], recette_id: str) -> float:
        """Score de -2 à +2 d'une recette pour les membres présents (0 = neutre)."""
        presents = list(membres)
        if not presents:
            return 0.0
        moyenne = sum(self.moyenne(m, recette_id) for m in presents) / len(presents)
        return moyenne - NOTE_NEUTRE

    def note_famille(self, recette_id: str) -> float | None:
        """Moyenne brute de toutes les notes d'une recette (pour l'affichage)."""
        valeurs = [v for (_, r), vs in self._notes.items() if r == recette_id for v in vs]
        return round(sum(valeurs) / len(valeurs), 1) if valeurs else None
