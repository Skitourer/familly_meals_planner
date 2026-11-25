"""Accès aux API ouvertes, avec un cache local sur disque.

Chaque réponse est enregistrée dans ``donnees/sources/<source>/`` : un nouvel
import peut ainsi être rejoué hors ligne (``repas-import --hors-ligne``) et le
résultat reste reproductible.

Sources :

* Agribalyse 4 (ADEME) — empreinte carbone, licence ouverte Etalab 2.0 ;
* Impact CO2 (ADEME) — calendrier des fruits et légumes de saison ;
* Open Food Facts — formats de vente des produits, licence ODbL ;
* Open Prices (Open Food Facts) — relevés de prix, licence ODbL.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

from repas.domaine.produits import quantite_en_grammes

# Les API Open Food Facts demandent un User-Agent identifiant l'application.
USER_AGENT = "MenuFamille/1.0 (planificateur de repas open source)"

URL_AGRIBALYSE = "https://data.ademe.fr/data-fair/api/v1/datasets/shxqzuee9i461wn9lmdsbnvr/lines"
URL_SAISONS = "https://impactco2.fr/api/v1/fruitsetlegumes"
URL_OFF_RECHERCHE = "https://world.openfoodfacts.org/api/v2/search"
URL_OPEN_PRICES = "https://prices.openfoodfacts.org/api/v1/prices"

ESSAIS = 3  # tentatives par requête avant d'abandonner


class ClientCache:
    """Client HTTP qui mémorise chaque réponse JSON dans un fichier."""

    def __init__(self, dossier: Path, *, hors_ligne: bool = False, pause_s: float = 0.5):
        self.dossier = dossier
        self.hors_ligne = hors_ligne
        self.pause_s = pause_s
        self._http = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60)

    def obtenir(self, source: str, url: str, params: dict[str, Any]) -> Any:
        cle = hashlib.sha1(f"{url}?{sorted(params.items())}".encode()).hexdigest()[:16]
        fichier = self.dossier / source / f"{cle}.json"
        if fichier.exists():
            return json.loads(fichier.read_text(encoding="utf-8"))
        if self.hors_ligne:
            raise FileNotFoundError(f"Pas de cache pour {source} ({url}) en mode hors ligne")
        reponse = self._telecharger(url, params)
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(reponse.text, encoding="utf-8")
        time.sleep(self.pause_s)  # politesse envers les API publiques
        return reponse.json()

    def _telecharger(self, url: str, params: dict[str, Any]) -> httpx.Response:
        """GET avec quelques nouvelles tentatives (les API publiques saturent parfois)."""
        for tentative in range(1, ESSAIS):
            try:
                reponse = self._http.get(url, params=params)
                reponse.raise_for_status()
                return reponse
            except httpx.HTTPError:
                time.sleep(2 * tentative)
        reponse = self._http.get(url, params=params)
        reponse.raise_for_status()
        return reponse


# --- Agribalyse ----------------------------------------------------------------------


def empreintes_agribalyse(client: ClientCache) -> dict[int, tuple[str, float]]:
    """Code CIQUAL -> (nom Agribalyse, kg CO2e par kg de produit)."""
    resultat: dict[int, tuple[str, float]] = {}
    apres: str | None = None
    while True:
        params: dict[str, Any] = {
            "size": 1000,
            "select": "Code_CIQUAL,Nom_du_Produit_en_Français,Changement_climatique",
        }
        if apres:
            params["after"] = apres
        page = client.obtenir("agribalyse", URL_AGRIBALYSE, params)
        for ligne in page["results"]:
            code = str(ligne.get("Code_CIQUAL", "")).strip()
            if code.isdigit() and ligne.get("Changement_climatique") is not None:
                resultat[int(code)] = (
                    ligne["Nom_du_Produit_en_Français"],
                    float(ligne["Changement_climatique"]),
                )
        suivant = page.get("next")
        if not suivant or not page["results"]:
            return resultat
        apres = httpx.URL(suivant).params.get("after")


# --- Impact CO2 : saisons --------------------------------------------------------------


def calendrier_saisons(client: ClientCache) -> dict[str, list[int]]:
    """Identifiant Impact CO2 (ex. ``"poireau"``) -> mois de saison."""
    calendrier: dict[str, list[int]] = {}
    for mois in range(1, 13):
        for produit in client.obtenir("saisons", URL_SAISONS, {"month": mois})["data"]:
            calendrier[produit["slug"]] = sorted(produit["months"])
    return calendrier


# --- Open Food Facts : formats de vente ----------------------------------------------------


def formats_courants(
    client: ClientCache, categorie: str, *, part_min: float = 0.1, minimum: int = 10
) -> list[float] | None:
    """Formats de vente représentant au moins ``part_min`` des produits français."""
    page = client.obtenir(
        "off-formats",
        URL_OFF_RECHERCHE,
        {
            "categories_tags": categorie,
            "countries_tags": "en:france",
            "fields": "product_quantity,product_quantity_unit",
            "page_size": 200,
            "sort_by": "unique_scans_n",
        },
    )
    quantites = [
        q
        for p in page.get("products", [])
        if (q := quantite_en_grammes(p.get("product_quantity"), p.get("product_quantity_unit")))
    ]
    if len(quantites) < minimum:
        return None
    compte = Counter(round(q) for q in quantites)
    retenus = [q for q, n in compte.most_common(3) if n / len(quantites) >= part_min]
    return sorted(float(q) for q in retenus) or None


# --- Open Prices : prix au kg ------------------------------------------------------------


def prix_median_kg(
    client: ClientCache, categorie: str, *, vrac: bool, minimum: int = 5
) -> tuple[float | None, int]:
    """Prix médian en €/kg des relevés Open Prices récents, et nombre de relevés."""
    if vrac:
        # Produits sans code-barres (fruits, légumes) : prix déjà exprimés au kg.
        params = {"category_tag": categorie, "currency": "EUR", "size": 100, "order_by": "-date"}
    else:
        params = {
            "product__categories_tags__contains": categorie,
            "currency": "EUR",
            "size": 100,
            "order_by": "-date",
        }
    prix_kg: list[float] = []
    for releve in client.obtenir("open-prices", URL_OPEN_PRICES, params).get("items", []):
        prix = releve.get("price")
        if not prix:
            continue
        if vrac:
            if releve.get("price_per") == "KILOGRAM":
                prix_kg.append(float(prix))
            continue
        produit = releve.get("product") or {}
        grammes = quantite_en_grammes(
            produit.get("product_quantity"), produit.get("product_quantity_unit")
        )
        if grammes:
            prix_kg.append(float(prix) / grammes * 1000)
    if len(prix_kg) < minimum:
        return None, len(prix_kg)
    return round(statistics.median(prix_kg), 2), len(prix_kg)
