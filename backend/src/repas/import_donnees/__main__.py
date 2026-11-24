"""Import des données ouvertes : produit ``donnees/referentiel/aliments.json``.

Usage ::

    uv run repas-import                       # import complet (réseau)
    uv run repas-import --hors-ligne          # rejoue le cache local
    uv run repas-import --ciqual chemin.xlsx  # autre version de CIQUAL

Seuls les aliments utilisés par ``ingredients.yaml`` sont conservés, ce qui
garde le fichier généré petit et lisible dans les revues de code.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from repas.catalogue.chargement import lire_aliments, lire_ingredients
from repas.catalogue.schemas import DonneesAliment, FichierAliments, Ingredient, Nutriments, Rayon
from repas.config import parametres
from repas.import_donnees.ciqual import lire_ciqual
from repas.import_donnees.sources_web import (
    ClientCache,
    calendrier_saisons,
    empreintes_agribalyse,
    formats_courants,
    prix_median_kg,
)

SOURCES = {
    "ciqual": "ANSES, Table de composition nutritionnelle des aliments CIQUAL 2025, "
    "licence ouverte Etalab 2.0 — https://ciqual.anses.fr/",
    "agribalyse": "ADEME, AGRIBALYSE 4 (synthèse, changement climatique), "
    "licence ouverte Etalab 2.0 — https://agribalyse.ademe.fr/",
    "saisons": "ADEME, Impact CO2 — calendrier des fruits et légumes de saison — "
    "https://impactco2.fr/outils/fruitsetlegumes",
    "open_food_facts": "Open Food Facts, formats de vente des produits, licence ODbL — "
    "https://world.openfoodfacts.org/",
    "open_prices": "Open Prices (Open Food Facts), relevés de prix, licence ODbL — "
    "https://prices.openfoodfacts.org/",
}


def trouver_ciqual(dossier_sources: Path) -> Path | None:
    """Fichier CIQUAL le plus récent dans ``donnees/sources/ciqual/`` (ou None)."""
    candidats = sorted((dossier_sources / "ciqual").glob("*.xlsx")) + sorted(
        (dossier_sources / "ciqual").glob("*.json")
    )
    return candidats[0] if candidats else None


def ciqual_depuis_import_precedent(
    precedent: FichierAliments, ingredients: dict[str, Ingredient]
) -> dict[int, tuple[str, Nutriments]]:
    """Sans fichier CIQUAL, on reprend les valeurs nutritionnelles du dernier import.

    La table CIQUAL ne change qu'environ une fois par an : l'import mensuel
    automatique (CO2, saisons, formats, prix) n'a pas besoin de la retélécharger.
    """
    return {
        ingredients[id_ing].ciqual: (donnees.nom_ciqual, donnees.nutriments_100g)
        for id_ing, donnees in precedent.aliments.items()
        if id_ing in ingredients
    }


def main(arguments: list[str] | None = None) -> None:
    analyseur = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    analyseur.add_argument("--ciqual", type=Path, help="Fichier CIQUAL (.xlsx ou .json)")
    analyseur.add_argument("--hors-ligne", action="store_true", help="N'utiliser que le cache")
    analyseur.add_argument("--sans-prix", action="store_true", help="Ne pas interroger Open Prices")
    options = analyseur.parse_args(arguments)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # accents sous Windows

    reglages = parametres()
    dossier_sources = reglages.dossier_donnees / "sources"
    ingredients = lire_ingredients(reglages.dossier_referentiel / "ingredients.yaml")
    client = ClientCache(dossier_sources, hors_ligne=options.hors_ligne)

    chemin_sortie = reglages.dossier_referentiel / "aliments.json"
    precedent = lire_aliments(chemin_sortie)
    chemin_ciqual = options.ciqual or trouver_ciqual(dossier_sources)
    if chemin_ciqual:
        print(f"CIQUAL      : {chemin_ciqual.name}")
        ciqual = lire_ciqual(chemin_ciqual)
        fichier_ciqual = chemin_ciqual.name
    else:
        print("CIQUAL      : pas de fichier, valeurs du précédent import conservées")
        ciqual = ciqual_depuis_import_precedent(precedent, ingredients)
        fichier_ciqual = precedent.sources.get("ciqual_fichier", "inconnu")
    print("Agribalyse  : téléchargement des empreintes carbone…")
    agribalyse = empreintes_agribalyse(client)
    print("Impact CO2  : calendrier des saisons…")
    saisons = calendrier_saisons(client)

    aliments: dict[str, DonneesAliment] = {}
    erreurs: list[str] = []
    for id_ing, ingredient in ingredients.items():
        if ingredient.ciqual not in ciqual:
            erreurs.append(
                f"{id_ing} : code CIQUAL {ingredient.ciqual} inconnu (nouvel ingrédient ? "
                "placer la table CIQUAL dans donnees/sources/ciqual/)"
            )
            continue
        if ingredient.saison and ingredient.saison not in saisons:
            erreurs.append(f"{id_ing} : saison « {ingredient.saison} » inconnue d'Impact CO2")
        nom_ciqual, nutriments = ciqual[ingredient.ciqual]
        code_agb = ingredient.ciqual_agribalyse or ingredient.ciqual
        nom_agb, co2 = agribalyse.get(code_agb, (None, None))
        if co2 is None:
            print(f"  ! {id_ing} : pas d'empreinte Agribalyse pour le code {code_agb}")

        formats = prix = None
        releves = 0
        categorie = ingredient.categorie_off
        try:
            if categorie and ingredient.vente.mode == "paquet" and not ingredient.vente.formats:
                formats = formats_courants(client, categorie)
            if categorie and not options.sans_prix:
                # Fruits et légumes : relevés « au kg » sans code-barres.
                vrac = ingredient.rayon == Rayon.FRUITS_LEGUMES
                prix, releves = prix_median_kg(client, categorie, vrac=vrac)
                prix = _prix_plausible(prix, ingredient.prix_kg)
        except (httpx.HTTPError, FileNotFoundError) as erreur:
            # Une API indisponible ne bloque pas l'import : on garde les valeurs de repli.
            print(f"  ! {id_ing} : Open Food Facts / Open Prices indisponible ({erreur})")
        aliments[id_ing] = DonneesAliment(
            nom_ciqual=nom_ciqual,
            nutriments_100g=nutriments,
            co2_kg_par_kg=co2,
            nom_agribalyse=nom_agb,
            mois_saison=saisons.get(ingredient.saison) if ingredient.saison else None,
            formats_off=formats,
            prix_kg_open_prices=prix,
            releves_prix=releves,
        )
        print(
            f"  {id_ing:<26} CO2 {co2 or 0:5.2f} kg/kg  "
            f"formats {formats or '-'}  prix {prix or '-'} €/kg ({releves} relevés)"
        )

    if erreurs:
        sys.exit("Erreurs dans ingredients.yaml :\n  " + "\n  ".join(erreurs))

    sortie = FichierAliments(
        genere_le=datetime.now(UTC).isoformat(timespec="seconds"),
        sources=SOURCES | {"ciqual_fichier": fichier_ciqual},
        aliments=aliments,
    )
    chemin_sortie.write_text(
        json.dumps(sortie.model_dump(mode="json"), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",  # LF, comme dans le dépôt
    )
    print(f"\n{len(aliments)} aliments écrits dans {chemin_sortie}")


def _prix_plausible(prix: float | None, prix_reference: float) -> float | None:
    """Écarte une médiane aberrante (catégorie mal renseignée, prix au détail...)."""
    if prix is None or not prix_reference / 3 <= prix <= prix_reference * 3:
        return None
    return prix


if __name__ == "__main__":
    main()
