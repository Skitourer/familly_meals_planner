"""Schémas du catalogue : ingrédients, données ouvertes importées et recettes.

Ces modèles valident les fichiers YAML/JSON de ``donnees/``. Une erreur de
saisie (ingrédient inconnu, quantité négative...) est donc détectée au
chargement, et en intégration continue par les tests.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, model_validator


class Famille(StrEnum):
    """Famille d'aliments, utilisée pour les repères du PNNS."""

    FECULENT = "feculent"
    FECULENT_COMPLET = "feculent-complet"
    LEGUMINEUSE = "legumineuse"
    LEGUME = "legume"
    FRUIT = "fruit"
    VIANDE_ROUGE = "viande-rouge"
    VOLAILLE = "volaille"
    CHARCUTERIE = "charcuterie"
    POISSON = "poisson"
    POISSON_GRAS = "poisson-gras"
    FRUITS_DE_MER = "fruits-de-mer"
    OEUF = "oeuf"
    LAITIER = "laitier"
    FROMAGE = "fromage"
    MATIERE_GRASSE = "matiere-grasse"
    SUCRE = "sucre"
    CONDIMENT = "condiment"


class Rayon(StrEnum):
    """Rayons du magasin, dans l'ordre d'un parcours type."""

    FRUITS_LEGUMES = "fruits-legumes"
    BOULANGERIE = "boulangerie"
    BOUCHERIE = "boucherie"
    POISSONNERIE = "poissonnerie"
    CREMERIE = "cremerie"
    EPICERIE_SALEE = "epicerie-salee"
    CONSERVES = "conserves"
    EPICERIE_SUCREE = "epicerie-sucree"
    SURGELES = "surgeles"


LIBELLES_RAYONS: dict[Rayon, str] = {
    Rayon.FRUITS_LEGUMES: "Fruits et légumes",
    Rayon.BOULANGERIE: "Boulangerie",
    Rayon.BOUCHERIE: "Boucherie, volaille",
    Rayon.POISSONNERIE: "Poissonnerie",
    Rayon.CREMERIE: "Crèmerie, œufs, fromages",
    Rayon.EPICERIE_SALEE: "Épicerie salée",
    Rayon.CONSERVES: "Conserves",
    Rayon.EPICERIE_SUCREE: "Épicerie sucrée",
    Rayon.SURGELES: "Surgelés",
}


# --- Ingrédients (référentiel édité à la main) -----------------------------------


class VentePaquet(BaseModel):
    """Vendu en paquets de poids fixe (pâtes 500 g, crème 20 cl...)."""

    mode: Literal["paquet"]
    formats: list[PositiveFloat] | None = Field(
        default=None, description="Formats en g. Absent : déduits d'Open Food Facts."
    )


class VentePiece(BaseModel):
    """Vendu à l'unité, éventuellement par lots (œufs par 6 ou 12)."""

    mode: Literal["piece"]
    poids: PositiveFloat = Field(description="Poids moyen d'une pièce, en g.")
    lots: list[PositiveInt] | None = None


class VenteVrac(BaseModel):
    """Vendu au poids (fruits, légumes, poisson à la coupe)."""

    mode: Literal["vrac"]
    pas: PositiveFloat = Field(default=50, description="Arrondi supérieur, en g.")


type Vente = VentePaquet | VentePiece | VenteVrac


class Ingredient(BaseModel):
    """Un ingrédient du référentiel ``donnees/referentiel/ingredients.yaml``."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nom: str
    ciqual: int
    ciqual_agribalyse: int | None = Field(
        default=None, description="Code CIQUAL proche pour le CO2 si Agribalyse ignore `ciqual`."
    )
    famille: Famille
    rayon: Rayon
    saison: str | None = None
    conservation_jours: PositiveInt
    vente: Vente = Field(discriminator="mode")
    unite: Literal["g", "ml"] = "g"
    part_comestible: float = Field(default=1.0, gt=0, le=1)
    rendement_cuisson: float = Field(
        default=1.0, ge=1, le=4, description="Poids cuit / poids cru (pâtes, riz...)."
    )
    basique: bool = False
    categorie_off: str | None = None
    prix_kg: PositiveFloat


# --- Données ouvertes importées (aliments.json, généré) ---------------------------


class Nutriments(BaseModel):
    """Apports nutritionnels d'une quantité d'aliment (ou d'une portion)."""

    model_config = ConfigDict(frozen=True)

    energie_kcal: float = 0
    proteines_g: float = 0
    glucides_g: float = 0
    lipides_g: float = 0
    ags_g: float = 0
    sucres_g: float = 0
    fibres_g: float = 0
    sel_g: float = 0
    calcium_mg: float = 0
    fer_mg: float = 0
    vitamine_c_mg: float = 0
    folates_ug: float = 0
    epa_dha_g: float = 0

    def __add__(self, autre: Nutriments) -> Nutriments:
        return Nutriments(
            **{nom: getattr(self, nom) + getattr(autre, nom) for nom in Nutriments.model_fields}
        )

    def fois(self, facteur: float) -> Nutriments:
        """Nutriments multipliés par ``facteur`` (ex. 1,5 portion)."""
        return Nutriments(**{nom: getattr(self, nom) * facteur for nom in Nutriments.model_fields})


class DonneesAliment(BaseModel):
    """Données ouvertes rattachées à un ingrédient (produites par ``repas-import``)."""

    nom_ciqual: str
    nutriments_100g: Nutriments
    co2_kg_par_kg: float | None = Field(description="Agribalyse : kg CO2e par kg.")
    nom_agribalyse: str | None = None
    mois_saison: list[int] | None = Field(
        default=None, description="Impact CO2 : mois de saison (1-12). None = toute l'année."
    )
    formats_off: list[float] | None = Field(
        default=None, description="Open Food Facts : formats de vente les plus courants (g)."
    )
    prix_kg_open_prices: float | None = None
    releves_prix: int = 0


class FichierAliments(BaseModel):
    """Contenu de ``donnees/referentiel/aliments.json``."""

    genere_le: str
    sources: dict[str, str]
    aliments: dict[str, DonneesAliment]


# --- Recettes --------------------------------------------------------------------


class Temps(BaseModel):
    preparation: int = Field(default=0, ge=0, description="Minutes.")
    cuisson: int = Field(default=0, ge=0, description="Minutes.")

    @property
    def total(self) -> int:
        return self.preparation + self.cuisson


class CuisineEnLot(BaseModel):
    """Plat qu'on cuisine une fois et qu'on sert sur plusieurs repas (soupe, mijoté)."""

    repas_max: int = Field(ge=2, le=4, description="Nombre de repas couverts par une cuisson.")
    conservation_jours: int = Field(ge=1, le=5, description="Écart maximal entre les repas.")


class Recette(BaseModel):
    """Une recette du catalogue (``donnees/recettes/*.yaml``)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    nom: str
    type: Literal["plat", "dessert"]
    plaisir: bool = Field(default=False, description="Réservé aux créneaux joker.")
    temps: Temps = Temps()
    lot: CuisineEnLot | None = None
    etiquettes: list[str] = []
    ingredients: dict[str, PositiveFloat] = Field(
        description="Identifiant d'ingrédient -> grammes par portion de référence."
    )
    etapes: list[str] = []
    source: str = "Catalogue Menu Famille"
    lien: str | None = Field(
        default=None,
        pattern=r"^https?://\S+$",
        description="Adresse d'une recette détaillée en ligne (obligatoire pour un plat).",
    )

    @model_validator(mode="after")
    def _plat_avec_recette(self) -> Recette:
        """Chaque plat doit renvoyer vers une recette détaillée en ligne."""
        if self.type == "plat" and not self.lien:
            raise ValueError("un plat doit avoir un « lien » vers sa recette (https://…)")
        return self
