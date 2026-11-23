/**
 * Calcul des besoins énergétiques d'un membre de la famille.
 *
 * Formule Mifflin-St Jeor (référence actuelle) pour le métabolisme de base,
 * multiplié par le coefficient d'activité. Si taille/poids manquent,
 * on retombe sur une estimation par tranches d'âge (inspirée des ANC).
 */
import type { Membre } from "./types.ts";
import { ACTIVITES } from "./types.ts";

/** Métabolisme de base (kcal/jour) par la formule Mifflin-St Jeor. */
export function metabolismeDeBase(m: Membre): number {
  if (m.tailleCm && m.poidsKg) {
    // Femmes : 10 x poids + 6,25 x taille - 5 x âge - 161
    // Hommes : 10 x poids + 6,25 x taille - 5 x âge + 5
    const s = m.sexe === "F" ? -161 : 5;
    return 10 * m.poidsKg + 6.25 * m.tailleCm - 5 * m.age + s;
  }
  // Estimation par tranches d'âge (kcal/jour, adulte moyen)
  return m.age < 10 ? 1300 : m.age < 15 ? 1700 : m.age < 65 ? 1900 : 1600;
}

/** Besoin énergétique total (kcal/jour), arrondi à la dizaine. */
export function besoinKcal(m: Membre): number {
  const coef = ACTIVITES[m.activite].coef;
  return Math.round((metabolismeDeBase(m) * coef) / 10) * 10;
}

/** Besoin total de la famille (kcal/jour). */
export function besoinFamille(membres: Membre[]): number {
  return membres.reduce((total, m) => total + besoinKcal(m), 0);
}

/**
 * Besoin couvert par un seul repas (midi ou soir).
 * Convention : le déjeuner + le dîner couvrent 45 % de la journée,
 * le petit-déjeuner et les collations étant hors périmètre.
 */
export function besoinParRepas(membres: Membre[]): number {
  return Math.round(besoinFamille(membres) * 0.45);
}
