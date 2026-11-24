"""Import de recettes au format JSON (par exemple générées par une IA).

L'application n'est connectée à aucune IA. La famille peut en revanche donner
le fichier d'instructions (``instructions_ia()``) à l'assistant de son choix,
qui produit un fichier JSON ; ce fichier est ensuite importé ici.

Chaque recette est **validée** avant d'être acceptée :

* structure conforme au schéma (mêmes champs que les fichiers YAML du catalogue) ;
* identifiant unique, absent du catalogue ;
* tous les ingrédients existent dans le référentiel (donc ont des données
  nutritionnelles, carbone et de saison issues des bases ouvertes) ;
* profil nutritionnel plausible (avertissements, non bloquants).

Les recettes acceptées sont enregistrées dans
``donnees/local/recettes-importees/<id>.yaml`` et rejoignent le catalogue.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from repas.catalogue.chargement import Catalogue, ProfilRecette
from repas.catalogue.schemas import Famille, Recette

FORMAT = "menu-famille/recettes"
VERSION = 1


class FichierImport(BaseModel):
    """Enveloppe du fichier JSON importé."""

    format: Literal["menu-famille/recettes"] = FORMAT
    version: Literal[1] = VERSION
    recettes: list[dict]


@dataclass
class ResultatRecette:
    id: str
    nom: str
    acceptee: bool
    erreurs: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)


@dataclass
class RapportImport:
    recettes: list[ResultatRecette]
    erreur_fichier: str | None = None

    @property
    def nb_acceptees(self) -> int:
        return sum(r.acceptee for r in self.recettes)


def analyser_import(
    contenu: str | bytes, catalogue: Catalogue
) -> tuple[RapportImport, list[Recette]]:
    """Valide un fichier JSON ; renvoie le rapport et les recettes acceptées."""
    try:
        fichier = FichierImport.model_validate(json.loads(contenu))
    except (json.JSONDecodeError, ValidationError) as erreur:
        return RapportImport([], erreur_fichier=f"Fichier invalide : {erreur}"), []

    rapport = RapportImport([])
    acceptees: list[Recette] = []
    vus: set[str] = set()
    for brut in fichier.recettes:
        resultat = ResultatRecette(id=str(brut.get("id", "?")), nom=str(brut.get("nom", "?")),
                                   acceptee=False)  # fmt: skip
        rapport.recettes.append(resultat)
        try:
            recette = Recette.model_validate(brut)
        except ValidationError as erreur:
            resultat.erreurs = [
                f"{'.'.join(str(x) for x in e['loc'])} : {e['msg']}" for e in erreur.errors()
            ]
            continue
        if recette.id in catalogue.recettes or recette.id in vus:
            resultat.erreurs.append(f"L'identifiant « {recette.id} » existe déjà")
        inconnus = sorted(set(recette.ingredients) - set(catalogue.ingredients))
        if inconnus:
            resultat.erreurs.append("Ingrédients absents du référentiel : " + ", ".join(inconnus))
        if resultat.erreurs:
            continue
        profil = catalogue.profiler(recette)
        resultat.avertissements = avertissements_nutrition(profil)
        resultat.acceptee = True
        vus.add(recette.id)
        if "source" not in brut:
            recette = recette.model_copy(update={"source": "Import JSON"})
        acceptees.append(recette)
    return rapport, acceptees


def avertissements_nutrition(profil: ProfilRecette) -> list[str]:
    """Signale un profil nutritionnel inhabituel pour une portion de référence."""
    alertes: list[str] = []
    kcal = profil.nutriments.energie_kcal
    if profil.recette.type == "plat":
        if not 300 <= kcal <= 900:
            alertes.append(f"Énergie inhabituelle pour un plat : {kcal:.0f} kcal (300–900)")
        if profil.fruits_legumes_g < 100 and not profil.recette.plaisir:
            alertes.append(f"Peu de légumes : {profil.fruits_legumes_g:.0f} g (≥ 100 g conseillés)")
        if profil.nutriments.proteines_g < 12:
            alertes.append(f"Peu de protéines : {profil.nutriments.proteines_g:.0f} g")
    elif not 30 <= kcal <= 400:
        alertes.append(f"Énergie inhabituelle pour un dessert : {kcal:.0f} kcal (30–400)")
    if profil.nutriments.sel_g > 2.5:
        alertes.append(f"Très salé : {profil.nutriments.sel_g:.1f} g de sel")
    if not profil.recette.etapes:
        alertes.append("Aucune étape de préparation")
    return alertes


def enregistrer(recettes: list[Recette], dossier: Path) -> None:
    """Écrit chaque recette acceptée dans un fichier YAML lisible."""
    dossier.mkdir(parents=True, exist_ok=True)
    for recette in recettes:
        contenu = recette.model_dump(mode="json", exclude_defaults=True)
        (dossier / f"{recette.id}.yaml").write_text(
            yaml.safe_dump([contenu], allow_unicode=True, sort_keys=False),
            encoding="utf-8",
            newline="\n",
        )


# --- Instructions pour une IA ---------------------------------------------------------

_LIBELLES_FAMILLES = {
    Famille.FECULENT: "Féculents",
    Famille.FECULENT_COMPLET: "Féculents complets",
    Famille.LEGUMINEUSE: "Légumineuses",
    Famille.LEGUME: "Légumes",
    Famille.FRUIT: "Fruits",
    Famille.VIANDE_ROUGE: "Viandes (hors volaille)",
    Famille.VOLAILLE: "Volailles",
    Famille.CHARCUTERIE: "Charcuterie",
    Famille.POISSON: "Poissons",
    Famille.POISSON_GRAS: "Poissons gras",
    Famille.FRUITS_DE_MER: "Fruits de mer",
    Famille.OEUF: "Œufs",
    Famille.LAITIER: "Produits laitiers",
    Famille.FROMAGE: "Fromages",
    Famille.MATIERE_GRASSE: "Matières grasses",
    Famille.SUCRE: "Produits sucrés",
    Famille.CONDIMENT: "Condiments et épices",
}

_MOIS = ["janv.", "févr.", "mars", "avril", "mai", "juin", "juil.", "août", "sept.", "oct.",
         "nov.", "déc."]  # fmt: skip

_EXEMPLE = {
    "format": FORMAT,
    "version": VERSION,
    "recettes": [
        {
            "id": "poelee-poireaux-pois-chiches",
            "nom": "Poêlée de poireaux et pois chiches, riz complet",
            "type": "plat",
            "temps": {"preparation": 15, "cuisson": 25},
            "etiquettes": ["vegetarien", "legumineuses"],
            "ingredients": {
                "poireau": 180,
                "pois-chiches": 120,
                "riz-complet": 70,
                "huile-olive": 8,
                "cumin": 1,
            },
            "etapes": [
                "Cuire le riz complet 25 min.",
                "Faire fondre les poireaux émincés dans l'huile avec le cumin.",
                "Ajouter les pois chiches égouttés, réchauffer 5 min et servir avec le riz.",
            ],
            "source": "Proposition IA",
        }
    ],
}


def instructions_ia(catalogue: Catalogue) -> str:
    """Fichier Markdown d'instructions à donner à une IA pour générer des recettes.

    Il est produit à partir du référentiel : la liste des ingrédients autorisés
    est donc toujours à jour.
    """
    par_famille: dict[Famille, list[str]] = {}
    for ing in sorted(catalogue.ingredients.values(), key=lambda i: i.id):
        mois = catalogue.mois_saison(ing.id)
        saison = f" — saison : {', '.join(_MOIS[m - 1] for m in mois)}" if mois else ""
        par_famille.setdefault(ing.famille, []).append(f"- `{ing.id}` : {ing.nom}{saison}")
    liste = "\n\n".join(
        f"### {_LIBELLES_FAMILLES[f]}\n\n" + "\n".join(lignes)
        for f, lignes in sorted(par_famille.items(), key=lambda x: list(Famille).index(x[0]))
    )
    exemple = json.dumps(_EXEMPLE, ensure_ascii=False, indent=2)
    deja = ", ".join(sorted(catalogue.recettes))
    return _GABARIT.format(liste=liste, exemple=exemple, deja=deja)


_GABARIT = """\
# Instructions pour générer des recettes « Menu Famille »

Tu es un assistant culinaire. Tu vas proposer des recettes familiales
**équilibrées**, de **saison** et à **faible empreinte carbone**, au format JSON
décrit ci-dessous, pour qu'elles soient importées dans l'application
« Menu Famille ».

## Ce que je te demande

(Remplace cette section par ta demande, par exemple : « Propose 10 plats
d'hiver rapides (moins de 30 min), dont 4 végétariens et 2 à base de poisson ».)

## Règles impératives

1. Réponds **uniquement** par un objet JSON valide, sans texte autour.
2. Utilise **seulement** les identifiants d'ingrédients de la liste plus bas
   (colonne de gauche, entre accents graves). N'invente aucun ingrédient : si
   une recette en exige un autre, choisis une autre recette.
3. Les quantités sont en **grammes (ou ml) par portion pour UN adulte de
   référence** (2 000 kcal/jour), **poids net** (épluché, égoutté, sans os).
   L'application ajuste ensuite les portions pour chaque membre de la famille.
4. Un **plat** est un plat principal complet (féculent + légumes + protéines),
   d'environ 450 à 650 kcal par portion, avec au moins 150 g de légumes. Le
   dessert est choisi séparément : ne l'inclus pas dans le plat.
5. Un **dessert** fait environ 60 à 150 kcal (fruit, laitage) ; les desserts
   riches (gâteaux...) portent `"plaisir": true`.
6. `"plaisir": true` est réservé aux repas « joker » (pizza, burger,
   raclette...). Les autres recettes doivent respecter les repères du PNNS :
   peu de sel (≤ 1,5 g par portion), peu de charcuterie, des légumineuses et
   du poisson régulièrement, des céréales complètes.
7. Pour les soupes et les plats mijotés qui se réchauffent bien, ajoute
   `"lot": {{"repas_max": 3, "conservation_jours": 3}}` (repas_max de 2 à 4,
   conservation de 1 à 5 jours).
8. `id` : en minuscules, mots séparés par des tirets, sans accent, unique, et
   **différent** des recettes déjà présentes (liste en fin de document).
9. Pas de sel ni de poivre dans la liste d'ingrédients sauf s'ils sont
   caractéristiques ; 3 à 6 étapes courtes et précises.
10. Privilégie les légumes et fruits **de saison** (mois indiqués dans la liste).

## Format attendu

```json
{exemple}
```

Champs d'une recette :

| Champ | Obligatoire | Description |
|---|---|---|
| `id` | oui | identifiant unique (`a-z`, `0-9`, tirets) |
| `nom` | oui | nom affiché |
| `type` | oui | `"plat"` ou `"dessert"` |
| `ingredients` | oui | objet `{{ "identifiant": grammes }}` |
| `etapes` | conseillé | liste de phrases |
| `temps` | conseillé | `{{"preparation": minutes, "cuisson": minutes}}` |
| `etiquettes` | non | ex. `vegetarien`, `rapide`, `enfants`, `four`, `soupe` |
| `lot` | non | plat cuisiné une fois pour plusieurs repas |
| `plaisir` | non | `true` pour les repas joker uniquement |
| `source` | non | ex. `"Proposition IA"` |
| `lien` | non | adresse (https://…) d'une recette détaillée en ligne, si elle existe vraiment |

## Ingrédients autorisés

{liste}

## Recettes déjà présentes (ne pas reprendre ces identifiants)

{deja}
"""


if __name__ == "__main__":
    # Régénère docs/ia/instructions-ia.md : uv run python -m repas.catalogue.import_recettes
    from repas.catalogue import charger_catalogue
    from repas.config import RACINE_DEPOT

    cible = RACINE_DEPOT / "docs" / "ia" / "instructions-ia.md"
    cible.parent.mkdir(parents=True, exist_ok=True)
    texte = instructions_ia(charger_catalogue(RACINE_DEPOT / "donnees"))
    cible.write_text(texte, encoding="utf-8", newline="\n")  # LF, comme dans le dépôt
    print(f"Écrit : {cible}")
