"""Consultation d'Open Food Facts à l'exécution : fiche d'un produit scanné (ADR 8).

Seul le code-barres est envoyé ; aucune donnée de la famille ne quitte l'application.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx

from repas.domaine.produits import FicheProduit, lire_fiche
from repas.import_donnees.sources_web import USER_AGENT

URL_PRODUIT = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
CHAMPS = (
    "product_name,product_name_fr,brands,product_quantity,product_quantity_unit,quantity,"
    "categories_tags,nutriscore_grade,nova_group,environmental_score_grade,ecoscore_grade"
)
DELAI_S = 6  # au magasin, mieux vaut une saisie manuelle qu'une longue attente


class OpenFoodFactsIndisponible(Exception):
    """Open Food Facts n'a pas répondu (réseau absent, délai dépassé, erreur serveur)."""


type ChercheurProduit = Callable[[str], FicheProduit | None]


def chercher_produit(
    code: str, *, transport: httpx.BaseTransport | None = None
) -> FicheProduit | None:
    """Fiche du produit ``code`` (code-barres déjà validé), None s'il est inconnu."""
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=DELAI_S, transport=transport
        ) as client:
            reponse = client.get(URL_PRODUIT.format(code=code), params={"fields": CHAMPS})
    except httpx.HTTPError as erreur:
        raise OpenFoodFactsIndisponible(str(erreur)) from erreur
    # Produit inconnu : Open Food Facts répond 404 avec un corps JSON « status: 0 ».
    if reponse.status_code == 404:
        return None
    if reponse.status_code != 200:
        raise OpenFoodFactsIndisponible(f"réponse HTTP {reponse.status_code}")
    try:
        contenu = reponse.json()
    except ValueError as erreur:
        raise OpenFoodFactsIndisponible("réponse illisible") from erreur
    return lire_fiche(code, contenu)
