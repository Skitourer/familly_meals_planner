/**
 * Utilitaires de dates pour les semaines ISO (lundi -> dimanche).
 */
import { MOIS } from "./mois.ts";

export const MOIS_FR = MOIS;

/** Retourne la date du lundi de la semaine contenant `date`. */
export function lundiDe(date: Date): Date {
  const d = new Date(date);
  const jour = (d.getDay() + 6) % 7; // 0 = lundi
  d.setDate(d.getDate() - jour);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Identifiant de semaine : date du lundi au format "2026-11-23". */
export function idSemaine(date: Date): string {
  return lundiDe(date).toISOString().slice(0, 10);
}

/** Liste des jours (Date) d'une semaine à partir de son identifiant. */
export function joursDeSemaine(id: string): Date[] {
  const lundi = new Date(`${id}T00:00:00`);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(lundi);
    d.setDate(d.getDate() + i);
    return d;
  });
}

/** Numéro du mois (1-12) applicable à une semaine (mois du mercredi). */
export function moisDeSemaine(id: string): number {
  const jours = joursDeSemaine(id);
  return jours[2].getMonth() + 1;
}

/** Libellé français du jour, ex. "lundi 23 novembre". */
export function libelleJour(date: Date): string {
  const jours = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  return `${jours[date.getDay()]} ${date.getDate()} ${MOIS[date.getMonth()].toLowerCase()}`;
}
