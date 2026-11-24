"""Repères nutritionnels appliqués aux repas planifiés (déjeuners et dîners).

Les valeurs sont exprimées pour une portion de référence (adulte à 2 000 kcal/jour)
et pour UN repas (plat + dessert). Le petit-déjeuner et le goûter, non planifiés,
apportent environ 40 % de l'énergie de la journée : chaque repas principal en
couvre donc environ 30 %.

Sources :

* ANSES (2016-2021), *Actualisation des repères du PNNS* et références
  nutritionnelles pour la population (protéines 10-20 % de l'énergie, lipides
  35-40 %, acides gras saturés ≤ 12 %, fibres ≥ 30 g/jour) ;
* OMS : sel < 5 g/jour ;
* Santé publique France, *Recommandations PNNS 4* (mangerbouger.fr) : au moins
  5 fruits et légumes par jour, poisson 2 fois par semaine dont un gras,
  légumes secs au moins 2 fois par semaine, viande hors volaille ≤ 500 g et
  charcuterie ≤ 150 g par semaine ; 2 produits laitiers par jour pour un adulte
  (davantage pour les enfants et adolescents).

Produits laitiers : le petit-déjeuner en apporte généralement un ; on demande donc
au moins **un produit laitier par jour** sur le déjeuner et le dîner (fromage dans
le plat, ou laitage en dessert).

La borne haute des protéines est portée à 25 % sur les repas principaux, car le
petit-déjeuner est en général pauvre en protéines.
"""

from __future__ import annotations

from dataclasses import dataclass

PART_ENERGIE_PAR_REPAS = 0.30
REPAS_PAR_SEMAINE = 14


@dataclass(frozen=True)
class Reperes:
    """Repères par repas (moyenne sur la semaine) pour une portion de référence."""

    energie_min_kcal: float = 480
    energie_max_kcal: float = 780
    proteines_min_part: float = 0.12  # part de l'énergie
    proteines_max_part: float = 0.25
    lipides_max_part: float = 0.40
    ags_max_part: float = 0.12
    fibres_min_g: float = 9.0  # 30 g/jour × 30 %
    sel_max_g: float = 1.75  # 5 g/jour × 35 %
    fruits_legumes_min_g: float = 200  # 2,5 portions de 80 g
    # Repères hebdomadaires PNNS (pour 14 repas pris à la maison).
    poissons_min: int = 2
    poissons_gras_min: int = 1
    legumineuses_min: int = 2
    viande_rouge_max_g: float = 500
    charcuterie_max_g: float = 150
    produits_laitiers_min_par_jour: int = 1

    def a_l_echelle(self, nb_repas: int) -> RepereHebdo:
        """Repères hebdomadaires ramenés au nombre de repas planifiés à la maison."""
        ratio = nb_repas / REPAS_PAR_SEMAINE
        return RepereHebdo(
            poissons_min=_arrondi_min(self.poissons_min * ratio, nb_repas),
            poissons_gras_min=_arrondi_min(self.poissons_gras_min * ratio, nb_repas),
            legumineuses_min=_arrondi_min(self.legumineuses_min * ratio, nb_repas),
            viande_rouge_max_g=self.viande_rouge_max_g * ratio,
            charcuterie_max_g=self.charcuterie_max_g * ratio,
        )


@dataclass(frozen=True)
class RepereHebdo:
    poissons_min: int
    poissons_gras_min: int
    legumineuses_min: int
    viande_rouge_max_g: float
    charcuterie_max_g: float


def _arrondi_min(valeur: float, nb_repas: int) -> int:
    """Arrondi au plus proche, sans dépasser la moitié des repas disponibles."""
    return min(round(valeur), nb_repas // 2)


REPERES = Reperes()
