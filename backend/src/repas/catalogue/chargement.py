"""Chargement du catalogue et calcul du profil de chaque recette.

Le catalogue réunit trois sources :

1. ``referentiel/ingredients.yaml`` : les ingrédients, édités à la main ;
2. ``referentiel/aliments.json`` : les données ouvertes importées
   (CIQUAL, Agribalyse, Impact CO2, Open Food Facts, Open Prices) ;
3. ``recettes/*.yaml`` : les recettes.

Pour chaque recette on pré-calcule un :class:`ProfilRecette` (nutrition,
carbone, prix, familles PNNS, saisonnalité) pour une portion de référence.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import yaml

from repas.catalogue.schemas import (
    DonneesAliment,
    Famille,
    FichierAliments,
    Ingredient,
    Nutriments,
    Recette,
)


class ErreurCatalogue(ValueError):
    """Le catalogue est incohérent (ingrédient inconnu, identifiant dupliqué...)."""


@dataclass(frozen=True)
class ProfilRecette:
    """Caractéristiques d'une recette pour UNE portion de référence."""

    recette: Recette
    nutriments: Nutriments
    co2_kg: float
    prix_eur: float
    grammes_par_famille: dict[Famille, float]
    mois_par_ingredient: dict[str, list[int]] = field(
        default_factory=dict,
        metadata={"doc": "Ingrédients saisonniers -> mois de saison."},
    )
    grammes_par_ingredient: dict[str, float] = field(default_factory=dict)
    poids_cuit_g: float = 0  # poids dans l'assiette (eau de cuisson des féculents comprise)

    @property
    def id(self) -> str:
        return self.recette.id

    @property
    def fruits_legumes_g(self) -> float:
        return self.grammes_par_famille.get(Famille.LEGUME, 0) + self.grammes_par_famille.get(
            Famille.FRUIT, 0
        )

    @property
    def fruits_legumes_legumineuses_g(self) -> float:
        """Fruits, légumes et légumineuses (au sens du Nutri-Score 2023)."""
        return self.fruits_legumes_g + self.grammes_par_famille.get(Famille.LEGUMINEUSE, 0)

    @property
    def est_laitier(self) -> bool:
        """Repère PNNS : une portion de produit laitier (30 g de fromage ou 100 g de laitage)."""
        return (
            self.grammes_par_famille.get(Famille.FROMAGE, 0) >= 25
            or self.grammes_par_famille.get(Famille.LAITIER, 0) >= 100
        )

    @property
    def est_vegetarien(self) -> bool:
        return not any(
            self.grammes_par_famille.get(f, 0) > 0
            for f in (Famille.VIANDE_ROUGE, Famille.VOLAILLE, Famille.CHARCUTERIE,
                      Famille.POISSON, Famille.POISSON_GRAS, Famille.FRUITS_DE_MER)
        )  # fmt: skip

    @property
    def est_poisson(self) -> bool:
        """Repère PNNS : une portion de poisson (au moins 60 g)."""
        poisson = self.grammes_par_famille.get(Famille.POISSON, 0) + self.grammes_par_famille.get(
            Famille.POISSON_GRAS, 0
        )
        return poisson >= 60

    @property
    def est_poisson_gras(self) -> bool:
        return self.grammes_par_famille.get(Famille.POISSON_GRAS, 0) >= 60

    @property
    def est_legumineuse(self) -> bool:
        """Repère PNNS : une portion de légumes secs (40 g secs ou 100 g en conserve)."""
        return self.grammes_par_famille.get(Famille.LEGUMINEUSE, 0) >= 40

    @property
    def viande_rouge_g(self) -> float:
        return self.grammes_par_famille.get(Famille.VIANDE_ROUGE, 0)

    @property
    def charcuterie_g(self) -> float:
        return self.grammes_par_famille.get(Famille.CHARCUTERIE, 0)

    @property
    def proteine_principale(self) -> str:
        """Source principale de protéines, pour varier les menus (ex. ``"poisson"``)."""
        groupes = {
            "legumineuse": [Famille.LEGUMINEUSE],
            "poisson": [Famille.POISSON, Famille.POISSON_GRAS, Famille.FRUITS_DE_MER],
            "volaille": [Famille.VOLAILLE],
            "viande": [Famille.VIANDE_ROUGE, Famille.CHARCUTERIE],
            "oeuf": [Famille.OEUF],
            "fromage": [Famille.FROMAGE, Famille.LAITIER],
        }
        grammes = {
            nom: sum(self.grammes_par_famille.get(f, 0) for f in familles)
            for nom, familles in groupes.items()
        }
        principal = max(grammes, key=lambda nom: grammes[nom])
        return principal if grammes[principal] > 0 else "vegetal"

    def hors_saison(self, mois: int) -> list[str]:
        """Ingrédients frais de la recette qui ne sont pas de saison ce mois-ci."""
        return [ing for ing, mois_ok in self.mois_par_ingredient.items() if mois not in mois_ok]

    def grammes_hors_saison(self, mois: int) -> float:
        return sum(self.grammes_par_ingredient[ing] for ing in self.hors_saison(mois))


@dataclass
class Catalogue:
    """Ensemble cohérent d'ingrédients, de données ouvertes et de recettes."""

    ingredients: dict[str, Ingredient]
    aliments: dict[str, DonneesAliment]
    recettes: dict[str, Recette]
    sources: dict[str, str]
    importees: set[str] = field(default_factory=set)  # recettes ajoutées par import JSON

    @cached_property
    def profils(self) -> dict[str, ProfilRecette]:
        return {rid: self.profiler(recette) for rid, recette in self.recettes.items()}

    def plats(self, *, plaisir: bool | None = None) -> list[ProfilRecette]:
        return self._filtrer("plat", plaisir)

    def desserts(self, *, plaisir: bool | None = None) -> list[ProfilRecette]:
        return self._filtrer("dessert", plaisir)

    def mois_saison(self, id_ingredient: str) -> list[int] | None:
        donnees = self.aliments.get(id_ingredient)
        return donnees.mois_saison if donnees else None

    def formats_vente(self, id_ingredient: str) -> list[float] | None:
        """Formats de vente : saisis à la main en priorité, sinon Open Food Facts."""
        ingredient = self.ingredients[id_ingredient]
        if ingredient.vente.mode != "paquet":
            return None
        if ingredient.vente.formats:
            return ingredient.vente.formats
        donnees = self.aliments.get(id_ingredient)
        return donnees.formats_off if donnees and donnees.formats_off else None

    def prix_kg(self, id_ingredient: str) -> float:
        """Prix au kg : médiane Open Prices si disponible, sinon valeur du référentiel."""
        donnees = self.aliments.get(id_ingredient)
        if donnees and donnees.prix_kg_open_prices:
            return donnees.prix_kg_open_prices
        return self.ingredients[id_ingredient].prix_kg

    def _filtrer(self, type_recette: str, plaisir: bool | None) -> list[ProfilRecette]:
        return [
            p
            for p in self.profils.values()
            if p.recette.type == type_recette and (plaisir is None or p.recette.plaisir == plaisir)
        ]

    def profiler(self, recette: Recette) -> ProfilRecette:
        """Calcule le profil d'une recette (portion de référence)."""
        nutriments = Nutriments()
        co2 = 0.0
        prix = 0.0
        familles: dict[Famille, float] = defaultdict(float)
        mois_par_ingredient: dict[str, list[int]] = {}
        poids_cuit = 0.0
        for id_ing, grammes in recette.ingredients.items():
            ingredient = self.ingredients[id_ing]
            donnees = self.aliments.get(id_ing)
            achete_kg = grammes / ingredient.part_comestible / 1000
            if donnees:
                nutriments = nutriments + donnees.nutriments_100g.fois(grammes / 100)
                co2 += achete_kg * (donnees.co2_kg_par_kg or 0)
                if donnees.mois_saison is not None:
                    mois_par_ingredient[id_ing] = donnees.mois_saison
            prix += achete_kg * self.prix_kg(id_ing)
            familles[ingredient.famille] += grammes
            poids_cuit += grammes * ingredient.rendement_cuisson
        return ProfilRecette(
            recette=recette,
            nutriments=nutriments,
            co2_kg=co2,
            prix_eur=prix,
            grammes_par_famille=dict(familles),
            mois_par_ingredient=mois_par_ingredient,
            grammes_par_ingredient=dict(recette.ingredients),
            poids_cuit_g=poids_cuit,
        )


# --- Lecture des fichiers ----------------------------------------------------------


def lire_ingredients(chemin: Path) -> dict[str, Ingredient]:
    brut = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    return {id_ing: Ingredient(id=id_ing, **valeurs) for id_ing, valeurs in brut.items()}


def lire_aliments(chemin: Path) -> FichierAliments:
    if not chemin.exists():
        return FichierAliments(genere_le="jamais", sources={}, aliments={})
    return FichierAliments.model_validate(json.loads(chemin.read_text(encoding="utf-8")))


def lire_recettes(dossier: Path) -> dict[str, Recette]:
    recettes: dict[str, Recette] = {}
    for fichier in sorted(dossier.glob("*.yaml")):
        for brut in yaml.safe_load(fichier.read_text(encoding="utf-8")) or []:
            recette = Recette.model_validate(brut)
            if recette.id in recettes:
                raise ErreurCatalogue(f"Recette en double : {recette.id} ({fichier.name})")
            recettes[recette.id] = recette
    return recettes


def charger_catalogue(dossier_donnees: Path, dossier_importees: Path | None = None) -> Catalogue:
    """Charge et valide le catalogue depuis ``dossier_donnees``.

    ``dossier_importees`` contient les recettes importées par la famille (JSON).
    """
    referentiel = dossier_donnees / "referentiel"
    ingredients = lire_ingredients(referentiel / "ingredients.yaml")
    fichier_aliments = lire_aliments(referentiel / "aliments.json")
    recettes = lire_recettes(dossier_donnees / "recettes")
    importees: dict[str, Recette] = {}
    if dossier_importees and dossier_importees.exists():
        importees = lire_recettes(dossier_importees)
        doublons = set(importees) & set(recettes)
        if doublons:
            raise ErreurCatalogue(f"Recettes importées en double : {sorted(doublons)}")
        recettes |= importees

    for recette in recettes.values():
        inconnus = set(recette.ingredients) - set(ingredients)
        if inconnus:
            raise ErreurCatalogue(
                f"Recette {recette.id} : ingrédients absents du référentiel : {sorted(inconnus)}"
            )

    return Catalogue(
        ingredients=ingredients,
        aliments=fichier_aliments.aliments,
        recettes=recettes,
        sources=fichier_aliments.sources,
        importees=set(importees),
    )
