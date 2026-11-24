"""Liste de courses : agrégation, déduction du placard et arrondi aux conditionnements.

Étapes, pour chaque ingrédient :

1. **Besoin** : somme, sur tous les repas, de la quantité de la recette multipliée
   par la somme des coefficients de portion des convives (voir ``besoins.py``) ;
2. **Placard** : on retire ce qui est déjà en stock ;
3. **Achat brut** : on divise par la part comestible (épluchures, noyaux...) ;
4. **Arrondi** au conditionnement réellement vendu : combinaison de paquets la
   moins gaspilleuse (ex. 850 g de pâtes -> 2 × 500 g), nombre de pièces ou de
   lots (œufs par 6 ou 12), ou arrondi au pas pour le vrac ;
5. **Surplus** : ce qui reste après la semaine part au placard si l'ingrédient
   se conserve au moins 7 jours, sinon il est signalé (risque de gaspillage).

Les produits « basiques » (sel, épices, huile...) ne sont pas achetés
systématiquement : ils sont listés à part, « à vérifier dans le placard ».
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations_with_replacement

from repas.catalogue import Catalogue
from repas.catalogue.schemas import LIBELLES_RAYONS, Rayon

CONSERVATION_MIN_PLACARD_JOURS = 7


@dataclass(frozen=True)
class Portion:
    """Une recette servie à un repas, pour une somme de coefficients de portion."""

    recette_id: str
    coefficients: float  # ex. 1,0 + 0,8 + 0,55 pour trois convives


@dataclass(frozen=True)
class Achat:
    """Ce qu'il faut acheter : ``nombre`` × ``format_g`` (ou un poids en vrac)."""

    nombre: int
    format_g: float
    libelle: str

    @property
    def total_g(self) -> float:
        return self.nombre * self.format_g


@dataclass
class LigneCourses:
    ingredient_id: str
    nom: str
    rayon: Rayon
    unite: str
    besoin_g: float  # quantité consommée (part comestible)
    depuis_placard_g: float
    achats: list[Achat]
    achete_g: float  # quantité brute achetée
    surplus_g: float  # restera après la semaine (brut)
    surplus_au_placard: bool
    prix_eur: float
    basique: bool = False


@dataclass
class ListeCourses:
    lignes: list[LigneCourses] = field(default_factory=list)

    @property
    def a_acheter(self) -> list[LigneCourses]:
        return [ligne for ligne in self.lignes if ligne.achats and not ligne.basique]

    @property
    def a_verifier(self) -> list[LigneCourses]:
        return [ligne for ligne in self.lignes if ligne.basique]

    @property
    def total_eur(self) -> float:
        return round(sum(ligne.prix_eur for ligne in self.a_acheter), 2)

    def par_rayon(self) -> list[tuple[str, list[LigneCourses]]]:
        """Lignes à acheter regroupées dans l'ordre du parcours en magasin."""
        groupes: dict[Rayon, list[LigneCourses]] = defaultdict(list)
        for ligne in self.a_acheter:
            groupes[ligne.rayon].append(ligne)
        return [
            (LIBELLES_RAYONS[rayon], sorted(groupes[rayon], key=lambda ligne: ligne.nom))
            for rayon in Rayon
            if rayon in groupes
        ]


def besoins_par_ingredient(portions: list[Portion], catalogue: Catalogue) -> dict[str, float]:
    """Grammes consommés de chaque ingrédient sur la semaine."""
    besoins: dict[str, float] = defaultdict(float)
    for portion in portions:
        recette = catalogue.recettes[portion.recette_id]
        for id_ing, grammes in recette.ingredients.items():
            besoins[id_ing] += grammes * portion.coefficients
    return dict(besoins)


def liste_de_courses(
    portions: list[Portion], catalogue: Catalogue, stock: dict[str, float] | None = None
) -> ListeCourses:
    """Construit la liste de courses de la semaine."""
    stock = stock or {}
    liste = ListeCourses()
    for id_ing, besoin in sorted(besoins_par_ingredient(portions, catalogue).items()):
        ingredient = catalogue.ingredients[id_ing]
        depuis_placard = min(stock.get(id_ing, 0.0), besoin)
        brut = (besoin - depuis_placard) / ingredient.part_comestible
        achats = [] if brut <= 0 or ingredient.basique else _arrondir(id_ing, brut, catalogue)
        achete = sum(a.total_g for a in achats)
        liste.lignes.append(
            LigneCourses(
                ingredient_id=id_ing,
                nom=ingredient.nom,
                rayon=ingredient.rayon,
                unite=ingredient.unite,
                besoin_g=round(besoin),
                depuis_placard_g=round(depuis_placard),
                achats=achats,
                achete_g=round(achete),
                surplus_g=round(max(achete - brut, 0)),
                surplus_au_placard=ingredient.conservation_jours >= CONSERVATION_MIN_PLACARD_JOURS,
                prix_eur=round(achete / 1000 * catalogue.prix_kg(id_ing), 2),
                basique=ingredient.basique,
            )
        )
    return liste


def _arrondir(id_ing: str, brut_g: float, catalogue: Catalogue) -> list[Achat]:
    vente = catalogue.ingredients[id_ing].vente
    unite = catalogue.ingredients[id_ing].unite
    if vente.mode == "piece":
        pieces = math.ceil(brut_g / vente.poids - 0.05)  # tolérance de 5 % d'une pièce
        pieces = max(pieces, 1)
        if vente.lots:
            lots = meilleure_combinaison(pieces, vente.lots)
            return [
                Achat(n, taille * vente.poids, f"boîte de {taille:g}")
                for taille, n in sorted(lots.items())
            ]
        return [Achat(pieces, vente.poids, "pièce")]
    if vente.mode == "vrac":
        quantite = math.ceil(brut_g / vente.pas) * vente.pas
        return [Achat(1, quantite, "au poids")]
    formats = catalogue.formats_vente(id_ing) or [100.0]
    paquets = meilleure_combinaison(brut_g, formats)
    return [
        Achat(n, taille, f"paquet de {format_quantite(taille, unite)}")
        for taille, n in sorted(paquets.items())
    ]


def meilleure_combinaison(
    besoin: float, tailles: list[float] | list[int], max_unites: int = 12
) -> dict[float, int]:
    """Combinaison de conditionnements couvrant ``besoin`` avec le moins de surplus.

    À surplus égal, on préfère le moins d'unités (un paquet de 1 kg plutôt que
    deux de 500 g). Ex. : besoin 850 g, tailles [500, 1000] -> {1000: 1}.
    """
    tailles = sorted(set(float(t) for t in tailles))
    plus_grande = tailles[-1]
    # Au-delà de quelques unités, on complète d'abord avec le plus grand format.
    base = max(0, math.floor(besoin / plus_grande) - 2)
    reste = besoin - base * plus_grande
    meilleure: tuple[float, int, tuple[float, ...]] | None = None
    for nombre in range(1, max_unites + 1):
        for combo in combinations_with_replacement(tailles, nombre):
            total = sum(combo)
            if total + 1e-9 < reste:
                continue
            critere = (total - reste, nombre, combo)
            if meilleure is None or critere[:2] < meilleure[:2]:
                meilleure = critere
        if meilleure is not None and meilleure[0] == 0:
            break
    combinaison: dict[float, int] = defaultdict(int)
    if base:
        combinaison[plus_grande] += base
    for taille in meilleure[2] if meilleure else (plus_grande,):
        combinaison[taille] += 1
    return dict(combinaison)


def format_quantite(grammes: float, unite: str = "g") -> str:
    """Affichage lisible : 1500 g -> « 1,5 kg », 200 ml -> « 20 cl »."""
    if unite == "ml":
        if grammes >= 1000:
            return f"{grammes / 1000:g} L".replace(".", ",")
        return f"{grammes / 10:g} cl".replace(".", ",")
    if grammes >= 1000:
        return f"{grammes / 1000:g} kg".replace(".", ",")
    return f"{grammes:g} g"


def placard_apres_courses(
    liste: ListeCourses, stock: dict[str, float], catalogue: Catalogue
) -> dict[str, float]:
    """Contenu du placard une fois les courses faites et les repas de la semaine cuisinés."""
    nouveau = dict(stock)
    for ligne in liste.lignes:
        restant = nouveau.get(ligne.ingredient_id, 0.0) - ligne.depuis_placard_g
        if ligne.surplus_au_placard and ligne.surplus_g > 0:
            # Le stock est exprimé en part comestible, comme les recettes.
            restant += ligne.surplus_g * catalogue.ingredients[ligne.ingredient_id].part_comestible
        if restant > 1:
            nouveau[ligne.ingredient_id] = round(restant)
        else:
            nouveau.pop(ligne.ingredient_id, None)
    return nouveau
