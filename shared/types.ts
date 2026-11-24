/**
 * Types du domaine : membres, plats, repas, semaines.
 * Ce module est partagé entre le serveur et le client web.
 */

/** Niveau d'activité physique (coefficient multiplicateur du métabolisme de base). */
export type Activite = "sedentaire" | "leger" | "modere" | "intense";

export const ACTIVITES: Record<Activite, { label: string; coef: number }> = {
  sedentaire: { label: "Sédentaire", coef: 1.2 },
  leger: { label: "Léger (1-2 séances/semaine)", coef: 1.375 },
  modere: { label: "Modéré (3-5 séances/semaine)", coef: 1.55 },
  intense: { label: "Intense (6-7 séances/semaine)", coef: 1.725 },
};

/** Sexe biologique, utilisé uniquement dans la formule du métabolisme de base. */
export type Sexe = "F" | "H";

/** Membre de la famille : son profil définit son besoin énergétique. */
export interface Membre {
  id: number;
  nom: string;
  age: number;
  /** en cm, optionnel : améliore la précision de la formule */
  tailleCm?: number;
  /** en kg, optionnel */
  poidsKg?: number;
  sexe: Sexe;
  activite: Activite;
}

/** Catégorie de plat : la rotation entre catégories garantit la variété. */
export type Categorie = "viande" | "poisson" | "volaille" | "pates" | "vegetarien" | "autre";

export interface Ingredient {
  /** nom normalisé, ex. "Pommes de terre" */
  nom: string;
  /** quantité pour UNE portion de référence */
  quantite: number;
  /** "g", "ml", "p" (pièce)... */
  unite: string;
}

/** Un plat du catalogue familial. */
export interface Plat {
  id: number;
  nom: string;
  categorie: Categorie;
  /** besoin couvert par une portion de référence (kcal) */
  kcalParPortion: number;
  /** mois (1-12) où le plat est optimal */
  saison: number[];
  ingredients: Ingredient[];
  /** lien vers la recette détaillée (Marmiton, 750g, blog…), optionnel */
  lienRecette?: string;
}

export type Service = "midi" | "soir";

/** Un repas planifié dans une semaine. `convives === 0` = repas hors maison. */
export interface Repas {
  /** 0 = lundi ... 6 = dimanche */
  jour: number;
  service: Service;
  platId: number | null;
  convives: number;
}

/** Note donnée à un plat après un repas (1 à 5 étoiles). */
export interface NotePlat {
  platId: number;
  /** identifiant de semaine : date du lundi au format ISO "2026-11-23" */
  semaine: string;
  note: number;
  commentaire?: string;
}
