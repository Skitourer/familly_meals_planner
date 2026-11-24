"""Configuration de l'application, lue depuis les variables d'environnement.

Toutes les variables sont préfixées par ``REPAS_`` (voir ``.env.example``).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du dépôt : backend/src/repas/config.py -> remonte de 4 niveaux.
RACINE_DEPOT = Path(__file__).resolve().parents[3]


class Parametres(BaseSettings):
    """Paramètres d'exécution. Les valeurs par défaut conviennent au développement local."""

    model_config = SettingsConfigDict(env_prefix="REPAS_", env_file=".env", extra="ignore")

    mot_de_passe: str = Field(
        default="famille",
        description="Mot de passe unique partagé par la famille.",
    )
    cle_secrete: str = Field(
        default="a-changer-en-production",
        description="Clé de signature des cookies de session.",
    )
    dossier_donnees: Path = Field(
        default=RACINE_DEPOT / "donnees",
        description="Dossier contenant referentiel/, recettes/ et la base locale.",
    )
    base_de_donnees: Path | None = Field(
        default=None,
        description="Chemin du fichier SQLite (défaut : <dossier_donnees>/local/repas.db).",
    )
    dossier_interface: Path | None = Field(
        default=None,
        description="Dossier de l'interface compilée à servir (production).",
    )
    cookie_securise: bool = Field(
        default=False,
        description="Cookie HTTPS uniquement (à activer derrière un reverse proxy TLS).",
    )

    @property
    def chemin_base(self) -> Path:
        return self.base_de_donnees or self.dossier_donnees / "local" / "repas.db"

    @property
    def dossier_referentiel(self) -> Path:
        return self.dossier_donnees / "referentiel"

    @property
    def dossier_recettes(self) -> Path:
        return self.dossier_donnees / "recettes"

    @property
    def dossier_recettes_importees(self) -> Path:
        """Recettes importées par la famille (JSON), propres à cette installation."""
        return self.dossier_donnees / "local" / "recettes-importees"


@lru_cache
def parametres() -> Parametres:
    """Paramètres de l'application (lus une seule fois)."""
    return Parametres()
