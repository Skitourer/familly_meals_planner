/**
 * Liste de courses : agrégation des ingrédients puis arrondi au conditionnement
 * vendu en magasin (paquets, boîtes, barquettes).
 *
 * Exemple : besoin de 800 g de spaghetti -> 2 paquets de 500 g = 1 kg.
 * Les articles en vrac (fruits, légumes au détail) ne sont pas arrondis.
 */
import type { Plat, Repas } from "./types.ts";

/** Ligne de liste de courses, après agrégation et arrondi. */
export interface LigneCourse {
  nom: string;
  unite: string;
  /** besoin total calculé à partir des recettes */
  besoin: number;
  /** quantité à acheter en magasin (>= besoin) */
  achat: number;
  /** vrai si l'arrondi magasin a modifié la quantité */
  arrondi: boolean;
}

/** Conditionnement par article : liste de mots-clés et pas d'achat. */
export interface Emballage {
  motifs: string[];
  /** pas d'achat dans l'unité de l'article ; 1 = pas d'arrondi */
  pas: number;
}

/**
 * Conditionnements usuels. En production cette table est en base et éditable ;
 * ces valeurs servent d'initialisation par défaut pour une famille française.
 */
export const EMBALLAGES_DEFAUT: Emballage[] = [
  { motifs: ["spaghetti", "penne", "macaroni", "farfalle", "pâtes", "riz", "lentille", "haricot sec", "semoule"], pas: 500 },
  { motifs: ["viande hachée", "blanc de poulet", "lardons", "jambon"], pas: 250 },
  { motifs: ["tomates concassées", "tomate pelée", "maïs", "haricots rouges", "pois chiches"], pas: 400 },
  { motifs: ["lait de coco"], pas: 200 },
  { motifs: ["crème"], pas: 20 },
  { motifs: ["farine", "sucre"], pas: 500 },
];

/** Retourne le pas d'achat d'un article ; 1 si vendu en vrac. */
export function pasDAchat(nom: string, unite: string, emballages: Emballage[]): number {
  if (unite === "p") return 1; // pièces : jamais arrondies
  const n = nom.toLowerCase();
  for (const e of emballages) {
    if (e.motifs.some((m) => n.includes(m))) return e.pas;
  }
  return 1;
}

/**
 * Construit la liste de courses d'une semaine.
 * Les repas annulés (convives = 0) ou sans plat sont ignorés.
 */
export function construireListe(
  repasSemaine: Repas[],
  platsParId: Map<number, Plat>,
  emballages: Emballage[] = EMBALLAGES_DEFAUT
): LigneCourse[] {
  // 1. Agrégation : somme des quantités par article (nom + unité)
  const agg = new Map<string, { nom: string; unite: string; total: number }>();
  for (const r of repasSemaine) {
    if (r.convives === 0 || r.platId === null) continue;
    const plat = platsParId.get(r.platId);
    if (!plat) continue;
    for (const ing of plat.ingredients) {
      const cle = `${ing.nom}|${ing.unite}`;
      const ligne = agg.get(cle) ?? { nom: ing.nom, unite: ing.unite, total: 0 };
      ligne.total += ing.quantite * r.convives;
      agg.set(cle, ligne);
    }
  }
  // 2. Arrondi magasin : plus petit multiple du pas d'achat >= besoin
  return [...agg.values()]
    .map((e) => {
      const pas = pasDAchat(e.nom, e.unite, emballages);
      const achat = pas > 1 ? Math.ceil(e.total / pas) * pas : e.total;
      return { nom: e.nom, unite: e.unite, besoin: e.total, achat, arrondi: achat !== e.total };
    })
    .sort((a, b) => a.nom.localeCompare(b.nom, "fr"));
}
