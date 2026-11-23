/**
 * Génération d'une semaine de repas (midi + soir, 7 jours), sans IA.
 *
 * Trois critères cumulés par plat, avec une petite part d'aléa pour varier
 * les semaines d'une fois sur l'autre :
 *
 *   1. SAISONNALITÉ — bonus si le plat est optimal pour le mois courant.
 *   2. VARIÉTÉ     — pénalité si la catégorie est déjà sur les deux derniers
 *                    repas ; un plat déjà pris dans le cycle est exclu.
 *   3. ADÉQUATION  — bonus si la portion couvre le besoin moyen par convive.
 *
 * Les notes a posteriori (moyenne par plat) servent de bonus "favoris".
 */
import type { Plat, Repas } from "./types.ts";

/** Options de génération. */
export interface OptionsGeneration {
  /** mois courant (1-12) */
  mois: number;
  /** besoin couvert par repas, par convive (kcal) */
  besoinMoyen: number;
  /** moyenne des notes par plat (note sur 5) ; optionnel */
  notes?: Record<number, number>;
  /** fonction aléatoire, injectable pour les tests (défaut : Math.random) */
  hasard?: () => number;
}

/**
 * Planifie les repas non encore définis d'une semaine.
 * Les repas avec convives = 0 (absence) ou déjà choisis sont conservés tels quels.
 * Retourne une NOUVELLE liste ; l'entrée n'est pas modifiée.
 */
export function genererSemaine(
  plats: Plat[],
  repasSemaine: Repas[],
  opts: OptionsGeneration
): Repas[] {
  const hasard = opts.hasard ?? Math.random;
  const pris = new Set<number>(); // plats déjà utilisés dans le cycle courant
  const categoriesRecentes: string[] = [];
  const score = (p: Plat): number => {
    const saison = p.saison.includes(opts.mois) ? 3 : 0;
    const varie = categoriesRecentes.slice(-2).includes(p.categorie) ? -4 : 1;
    const dejaPris = pris.has(p.id) ? -100 : 0;
    const adequat = -Math.abs(p.kcalParPortion - opts.besoinMoyen) / 100;
    const favori = (opts.notes?.[p.id] ?? 3) / 5; // note moyenne : léger bonus
    const chance = hasard() * 2;
    return saison + varie + dejaPris + adequat + favori + chance;
  };

  // On parcourt les 14 créneaux (7 jours x midi/soir) dans l'ordre,
  // ce qui donne à "variété" sa signification chronologique.
  const resultat = [...repasSemaine];
  for (let i = 0; i < resultat.length; i++) {
    const r = resultat[i];
    if (r.convives === 0 || r.platId !== null) continue; // absence ou choix conservé
    // Si tout le catalogue a été utilisé, on recommence un cycle :
    // on autorise à nouveau les plats (catégories toujours variées).
    if (pris.size >= plats.length) pris.clear();
    const meilleurs = [...plats]
      .map((p) => ({ id: p.id, s: score(p) }))
      .sort((a, b) => b.s - a.s)
      .filter((x) => x.s > -50); // exclut les doublons du cycle courant
    if (meilleurs.length === 0) continue;
    const choix = meilleurs[0].id;
    resultat[i] = { ...r, platId: choix };
    pris.add(choix);
    const platChoisi = plats.find((p) => p.id === choix);
    if (platChoisi) categoriesRecentes.push(platChoisi.categorie);
  }
  return resultat;
}
