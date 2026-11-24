"""Mots de passe et protection contre les essais répétés.

* Les mots de passe sont hachés avec **scrypt** (bibliothèque standard Python),
  avec un sel aléatoire par compte : la base ne contient jamais de mot de passe
  en clair.
* Après ``ESSAIS_MAX`` échecs pour un même identifiant, la connexion est bloquée
  pendant ``BLOCAGE`` (protection simple contre la devinette de mot de passe).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field

# Paramètres scrypt (coût mémoire ≈ 16 Mo) : recommandations OWASP 2023.
_N, _R, _P = 2**14, 8, 1
LONGUEUR_MIN = 6

ESSAIS_MAX = 5
BLOCAGE_S = 60.0


def hacher(mot_de_passe: str) -> str:
    """Empreinte stockable : ``scrypt$<sel>$<empreinte>`` (base64)."""
    sel = secrets.token_bytes(16)
    empreinte = hashlib.scrypt(mot_de_passe.encode(), salt=sel, n=_N, r=_R, p=_P)
    return "scrypt$" + "$".join(base64.b64encode(x).decode() for x in (sel, empreinte))


def verifier(mot_de_passe: str, stocke: str) -> bool:
    """Compare un mot de passe à son empreinte, en temps constant."""
    try:
        algorithme, sel, empreinte = stocke.split("$")
    except ValueError:
        return False
    if algorithme != "scrypt":
        return False
    calcule = hashlib.scrypt(mot_de_passe.encode(), salt=base64.b64decode(sel), n=_N, r=_R, p=_P)
    return hmac.compare_digest(calcule, base64.b64decode(empreinte))


@dataclass
class LimiteurEssais:
    """Compte les échecs de connexion par identifiant (en mémoire, par processus)."""

    echecs: dict[str, list[float]] = field(default_factory=dict)

    def bloque(self, identifiant: str, maintenant: float | None = None) -> bool:
        instant = maintenant if maintenant is not None else time.monotonic()
        recents = [t for t in self.echecs.get(identifiant, []) if instant - t < BLOCAGE_S]
        self.echecs[identifiant] = recents
        return len(recents) >= ESSAIS_MAX

    def echec(self, identifiant: str, maintenant: float | None = None) -> None:
        instant = maintenant if maintenant is not None else time.monotonic()
        self.echecs.setdefault(identifiant, []).append(instant)

    def succes(self, identifiant: str) -> None:
        self.echecs.pop(identifiant, None)


limiteur = LimiteurEssais()
