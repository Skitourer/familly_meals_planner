"""Articles cochés sur la liste de courses, partagés entre appareils.

Au magasin, un téléphone peut perdre le réseau : ses coches sont mises en file
d'attente puis envoyées au retour de la connexion, parfois après celles d'un autre
appareil. Pour chaque article, la modification la plus récente (heure de l'action
sur l'appareil) l'emporte, quel que soit l'ordre d'arrivée.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class ModificationCoche:
    """Un article coché ou décoché, à une heure donnée."""

    ingredient_id: str
    cochee: bool
    modifiee_le: datetime


def en_utc(moment: datetime) -> datetime:
    """Heure avec fuseau UTC (SQLite rend les dates sans fuseau, enregistrées en UTC)."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def fusionner_coches(
    actuelles: dict[str, ModificationCoche],
    modifications: list[ModificationCoche],
    maintenant: datetime,
) -> dict[str, ModificationCoche]:
    """État de chaque article après les ``modifications`` : la plus récente gagne.

    Une heure dans le futur (horloge d'un appareil en avance) est ramenée à
    ``maintenant`` : sinon, cette coche ne pourrait plus être annulée par un autre appareil.
    """
    resultat = dict(actuelles)
    limite = en_utc(maintenant)
    for modification in modifications:
        quand = min(en_utc(modification.modifiee_le), limite)
        actuelle = resultat.get(modification.ingredient_id)
        if actuelle is None or quand >= en_utc(actuelle.modifiee_le):
            resultat[modification.ingredient_id] = ModificationCoche(
                modification.ingredient_id, modification.cochee, quand
            )
    return resultat


def articles_coches(etat: dict[str, ModificationCoche]) -> list[str]:
    """Identifiants des articles cochés, triés."""
    return sorted(id_ing for id_ing, coche in etat.items() if coche.cochee)
