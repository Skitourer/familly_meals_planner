"""Catalogue : recettes, ingrédients, import JSON et instructions pour une IA."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from repas.base import session
from repas.catalogue import Catalogue, ProfilRecette, catalogue, recharger_catalogue
from repas.catalogue.import_recettes import analyser_import, enregistrer, instructions_ia
from repas.catalogue.schemas import Nutriments, Recette
from repas.config import parametres
from repas.domaine.notes import NoteDonnee, Preferences
from repas.modeles import Creneau, Note

router = APIRouter(tags=["catalogue"])


class RecetteSortie(BaseModel):
    recette: Recette
    nutriments: Nutriments
    co2_kg: float
    prix_eur: float
    fruits_legumes_g: float
    proteine_principale: str
    de_saison: bool
    hors_saison: list[str]
    note_famille: float | None
    nombre_notes: int
    importee: bool
    ingredients_noms: dict[str, str]
    ingredients_unites: dict[str, str]


def _sortie(p: ProfilRecette, cat: Catalogue, prefs: Preferences, mois: int) -> RecetteSortie:
    hors = p.hors_saison(mois)
    return RecetteSortie(
        recette=p.recette,
        nutriments=p.nutriments,
        co2_kg=round(p.co2_kg, 2),
        prix_eur=round(p.prix_eur, 2),
        fruits_legumes_g=round(p.fruits_legumes_g),
        proteine_principale=p.proteine_principale,
        de_saison=not hors,
        hors_saison=[cat.ingredients[i].nom for i in hors],
        note_famille=prefs.note_famille(p.id),
        nombre_notes=prefs.nombre_notes(p.id),
        importee=p.id in cat.importees,
        ingredients_noms={i: cat.ingredients[i].nom for i in p.recette.ingredients},
        ingredients_unites={i: cat.ingredients[i].unite for i in p.recette.ingredients},
    )


@router.get("/recettes")
def lister(s: Session = Depends(session)) -> list[RecetteSortie]:
    cat = catalogue()
    prefs = Preferences(NoteDonnee(n.membre_id, n.recette_id, n.valeur)
                        for n in s.exec(select(Note)).all())  # fmt: skip
    mois = date.today().month
    profils = sorted(cat.profils.values(), key=lambda p: (p.recette.type, p.recette.nom))
    return [_sortie(p, cat, prefs, mois) for p in profils]


@router.get("/ingredients")
def ingredients() -> list[dict]:
    cat = catalogue()
    return [
        {
            "id": i.id,
            "nom": i.nom,
            "rayon": i.rayon,
            "unite": i.unite,
            "conservation_jours": i.conservation_jours,
            "basique": i.basique,
        }
        for i in sorted(cat.ingredients.values(), key=lambda i: i.nom)
    ]


@router.get("/sources")
def sources() -> dict[str, str]:
    """Attribution des bases de données ouvertes utilisées."""
    return catalogue().sources


# --- Import de recettes -------------------------------------------------------------


@router.get("/import/instructions-ia.md", response_class=PlainTextResponse)
def telecharger_instructions() -> PlainTextResponse:
    """Fichier d'instructions à donner à une IA (liste d'ingrédients toujours à jour)."""
    return PlainTextResponse(
        instructions_ia(catalogue()),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="instructions-ia.md"'},
    )


@router.post("/import/recettes")
async def importer(fichier: UploadFile, appliquer: bool = False) -> dict:
    """Valide un fichier JSON de recettes ; ``appliquer=true`` enregistre les recettes valides."""
    contenu = await fichier.read()
    if len(contenu) > 2_000_000:
        raise HTTPException(413, "Fichier trop volumineux (2 Mo maximum)")
    rapport, acceptees = analyser_import(contenu, catalogue())
    if appliquer and acceptees:
        enregistrer(acceptees, parametres().dossier_recettes_importees)
        recharger_catalogue()
    return {
        "erreur_fichier": rapport.erreur_fichier,
        "nb_acceptees": rapport.nb_acceptees,
        "applique": appliquer and bool(acceptees),
        "recettes": [r.__dict__ for r in rapport.recettes],
    }


@router.delete("/recettes/{recette_id}", status_code=204)
def supprimer_importee(recette_id: str, s: Session = Depends(session)) -> None:
    """Supprime une recette importée (les recettes du catalogue versionné ne le sont pas)."""
    if recette_id not in catalogue().importees:
        raise HTTPException(404, "Seules les recettes importées peuvent être supprimées")
    utilisee = s.exec(
        select(Creneau).where((Creneau.plat_id == recette_id) | (Creneau.dessert_id == recette_id))
    ).first()
    if utilisee:
        raise HTTPException(409, "Recette utilisée dans un planning : elle ne peut être supprimée")
    (parametres().dossier_recettes_importees / f"{recette_id}.yaml").unlink(missing_ok=True)
    recharger_catalogue()
