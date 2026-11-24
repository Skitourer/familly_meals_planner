"""Lecture de la table CIQUAL (ANSES) — composition nutritionnelle des aliments.

Source : https://ciqual.anses.fr/ — licence ouverte Etalab 2.0.

Deux formats sont acceptés :

* le fichier Excel officiel (``Table Ciqual 2025_FR_*.xlsx``), téléchargeable
  sur le site de l'ANSES ou sur data.gouv.fr ;
* une conversion JSON compacte (``ciqual-*.json``) : ``{"nutriments": [...],
  "aliments": [[code, nom, ..., [valeurs]]]}``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from repas.catalogue.schemas import Nutriments

# Champ de Nutriments -> clé du format JSON compact.
CLES_JSON: dict[str, list[str]] = {
    "energie_kcal": ["kcal"],
    "proteines_g": ["prot"],
    "glucides_g": ["gluc"],
    "lipides_g": ["lip"],
    "ags_g": ["ags"],
    "sucres_g": ["sucres"],
    "fibres_g": ["fibres"],
    "sel_g": ["sel"],
    "calcium_mg": ["calcium"],
    "fer_mg": ["fer"],
    "vitamine_c_mg": ["vitc"],
    "folates_ug": ["b9"],
    "epa_dha_g": ["epa", "dha"],
}

# Champ de Nutriments -> début des en-têtes de colonnes du fichier Excel officiel.
COLONNES_EXCEL: dict[str, list[str]] = {
    "energie_kcal": ["Energie, Règlement UE N° 1169/2011 (kcal/100 g)"],
    "proteines_g": ["Protéines, N x facteur de Jones"],
    "glucides_g": ["Glucides (g/100 g)"],
    "lipides_g": ["Lipides (g/100 g)"],
    "ags_g": ["AG saturés"],
    "sucres_g": ["Sucres (g/100 g)"],
    "fibres_g": ["Fibres alimentaires"],
    "sel_g": ["Sel chlorure de sodium"],
    "calcium_mg": ["Calcium"],
    "fer_mg": ["Fer (mg"],
    "vitamine_c_mg": ["Vitamine C"],
    "folates_ug": ["Vitamine B9"],
    "epa_dha_g": ["AG 20:5", "AG 22:6"],
}


def valeur_numerique(brut: object) -> float:
    """Convertit une cellule CIQUAL en nombre.

    CIQUAL utilise des notations particulières : ``"traces"``/``"tr"`` (≈ 0),
    ``"< 0,5"`` (inférieur au seuil : on retient la moitié du seuil), ``"-"``
    (non mesuré : 0 par prudence).
    """
    if brut is None:
        return 0.0
    if isinstance(brut, int | float):
        return float(brut)
    texte = str(brut).strip().replace(",", ".").lower()
    if texte in {"", "-", "tr", "traces"}:
        return 0.0
    seuil = re.fullmatch(r"<\s*([\d.]+)", texte)
    if seuil:
        return float(seuil.group(1)) / 2
    try:
        return float(texte)
    except ValueError:
        return 0.0


def lire_ciqual(chemin: Path) -> dict[int, tuple[str, Nutriments]]:
    """Lit la table CIQUAL : code aliment -> (nom, nutriments pour 100 g)."""
    if chemin.suffix == ".json":
        return _lire_json(chemin)
    if chemin.suffix == ".xlsx":
        return _lire_excel(chemin)
    raise ValueError(f"Format CIQUAL non reconnu : {chemin.name}")


def _lire_json(chemin: Path) -> dict[int, tuple[str, Nutriments]]:
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    index = {nom: i for i, nom in enumerate(brut["nutriments"])}
    table: dict[int, tuple[str, Nutriments]] = {}
    for code, nom, *_, valeurs in brut["aliments"]:
        champs = {
            champ: sum(valeur_numerique(valeurs[index[cle]]) for cle in cles)
            for champ, cles in CLES_JSON.items()
        }
        table[int(code)] = (nom, Nutriments(**champs))
    return table


def _lire_excel(chemin: Path) -> dict[int, tuple[str, Nutriments]]:
    from openpyxl import load_workbook  # import local : dépendance lourde

    feuille = load_workbook(chemin, read_only=True).active
    if feuille is None:
        raise ValueError("Fichier CIQUAL vide")
    lignes = feuille.iter_rows(values_only=True)
    entetes = [str(e or "") for e in next(lignes)]

    def colonnes(prefixes: list[str]) -> list[int]:
        trouvees = [i for p in prefixes for i, e in enumerate(entetes) if e.startswith(p)]
        if not trouvees:
            raise ValueError(f"Colonne CIQUAL introuvable : {prefixes}")
        return trouvees

    i_code, i_nom = entetes.index("alim_code"), entetes.index("alim_nom_fr")
    index = {champ: colonnes(prefixes) for champ, prefixes in COLONNES_EXCEL.items()}
    table: dict[int, tuple[str, Nutriments]] = {}
    for ligne in lignes:
        if ligne[i_code] is None:
            continue
        champs = {
            champ: sum(valeur_numerique(ligne[i]) for i in idx) for champ, idx in index.items()
        }
        table[int(str(ligne[i_code]))] = (str(ligne[i_nom]), Nutriments(**champs))
    return table
