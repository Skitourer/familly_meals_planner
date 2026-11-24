/**
 * Source fiable des valeurs nutritionnelles : table CIQUAL 2025 de l'Anses
 * (licence ouverte Etalab 2.0), fichier donnees/ciqual/ciqual-2025.json.
 *
 * - `alimentPour(ingredient)` retrouve l'aliment CIQUAL le plus proche d'un
 *   nom d'ingrédient (matching par tokens, pénalités pour les plats composés).
 * - `kcalPlat(ingredients)` calcule les kcal d'une portion d'un plat à partir
 *   de ses ingrédients : plus aucune valeur nutritionnelle inventée.
 */
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { Ingredient } from "../../shared/types.ts";

interface AlimentCiqual {
  code: string;
  nom: string;
  groupe: string;
  kcal: number; // pour 100 g
  prot: number;
  gluc: number;
  lip: number;
}

/* ---------- Chargement ---------- */

const CHEMIN = join(dirname(fileURLToPath(import.meta.url)), "../../donnees/ciqual/ciqual-2025.json");

let cache: AlimentCiqual[] | null = null;

function table(): AlimentCiqual[] {
  if (cache) return cache;
  const brut = JSON.parse(readFileSync(CHEMIN, "utf-8")) as {
    nutriments: string[];
    aliments: Array<[string, string, string, string, string, unknown, number[]]>;
  };
  const iKcal = brut.nutriments.indexOf("kcal");
  const iProt = brut.nutriments.indexOf("prot");
  const iGluc = brut.nutriments.indexOf("gluc");
  const iLip = brut.nutriments.indexOf("lip");
  cache = brut.aliments.map((a) => ({
    code: a[0],
    nom: a[1],
    groupe: a[2],
    kcal: Number(a[6][iKcal]) || 0,
    prot: Number(a[6][iProt]) || 0,
    gluc: Number(a[6][iGluc]) || 0,
    lip: Number(a[6][iLip]) || 0,
  }));
  return cache;
}

/* ---------- Normalisation et matching ---------- */

const STOP = new Set(["de", "du", "des", "au", "aux", "la", "le", "les", "un", "une", "et", "ou", "d", "l", "sur", "en"]);

function normaliser(s: string): string[] {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(" ")
    .filter((t) => t.length > 1 && !STOP.has(t));
}

// Mots qui indiquent un plat composé / industriel : à éviter comme source de kcal
const PENALITE_COMPOSE = ["preemball", "sandwich", "soupe", "sauce", "taboule", "pizza", "tarte", "quiche", "gratin", "hamburger", "wrap", "fait maison", "vente", "restaur", "snack", "aperitif", "boisson", "jus", "confiture", "pate a tartiner", "dessert", "salade composee", "meal", "bolognaise", "carbonara"];
// Bonus pour les formes brutes (cru, sec) qui sont les références CIQUAL
const BONUS_BRUT = ["cru", "crues", "sec", "seche", "secs", "fraiche", "frais", "chair"];

function score(aliment: AlimentCiqual, tokensIng: string[]): number {
  const tokensAl = normaliser(aliment.nom);
  let s = 0;
  for (const t of tokensIng) {
    if (tokensAl.includes(t)) s += t.length; // poids = longueur du mot (évite les faux amis courts)
  }
  if (s === 0) return -1;
  const nomN = normaliser(aliment.nom).join(" ");
  for (const p of PENALITE_COMPOSE) if (nomN.includes(p)) s -= 30;
  for (const b of BONUS_BRUT) if (tokensAl.includes(b)) s += 4;
  return s;
}

/** Retrouve l'aliment CIQUAL le plus proche d'un nom d'ingrédient. */
export function alimentPour(nomIngredient: string): AlimentCiqual | null {
  const tokens = normaliser(nomIngredient);
  if (tokens.length === 0) return null;
  let best: AlimentCiqual | null = null;
  let bestScore = 0;
  for (const a of table()) {
    const s = score(a, tokens);
    if (s > bestScore) { bestScore = s; best = a; }
  }
  return bestScore > 0 ? best : null;
}

/* ---------- Poids unitaire (unité "p") et densité (unité "ml") ---------- */

// Poids moyen d'une pièce, en grammes (repères usuels ; ex. œuf moyen = 53-63 g).
const POIDS_PIECE: Array<[string[], number]> = [
  [["oeuf"], 55],
  [["citron"], 60],
  [["tomate"], 120],
  [["oignon"], 100],
  [["ail"], 5],       // une gousse
  [["pomme"], 150],
  [["poire"], 150],
  [["pate brisee", "pate a tarte"], 230],
  [["pate a pizza"], 250],
  [["pain pita"], 60],
  [["galette"], 50],
  [["pain a burger", "burger"], 75],
  [["pain de mie"], 25], // une tranche
  [["pain"], 40],        // une tranche de pain classique
];

function poidsPiece(nom: string): number {
  const n = normaliser(nom).join(" ");
  for (const [mots, p] of POIDS_PIECE) if (mots.some((m) => n.includes(m))) return p;
  return 100; // défaut : 100 g
}

// Densité (g/ml) pour convertir les ml en grammes.
function densite(nom: string): number {
  const n = normaliser(nom).join(" ");
  if (n.includes("huile")) return 0.92;
  if (n.includes("lait") || n.includes("creme")) return 1.03;
  return 1.0; // eau, vin, bouillon, jus, sauce...
}

/* ---------- Calcul des kcal d'un plat ---------- */

export interface BilanNutrition {
  kcal: number;
  prot: number;
  gluc: number;
  lip: number;
  /** noms d'ingrédients non reconnus dans CIQUAL */
  nonReconnus: string[];
}

/** Calcule le bilan nutritionnel d'une portion à partir des ingrédients (valeurs CIQUAL/100 g). */
export function bilanPortion(ingredients: Ingredient[]): BilanNutrition {
  let kcal = 0, prot = 0, gluc = 0, lip = 0;
  const nonReconnus: string[] = [];
  for (const ing of ingredients) {
    const a = alimentPour(ing.nom);
    if (!a) { nonReconnus.push(ing.nom); continue; }
    let grammes: number;
    if (ing.unite === "p") grammes = ing.quantite * poidsPiece(ing.nom);
    else if (ing.unite === "ml") grammes = ing.quantite * densite(ing.nom);
    else grammes = ing.quantite; // "g" et assimilés
    const f = grammes / 100;
    kcal += a.kcal * f;
    prot += a.prot * f;
    gluc += a.gluc * f;
    lip += a.lip * f;
  }
  return { kcal: Math.round(kcal), prot: Math.round(prot * 10) / 10, gluc: Math.round(gluc * 10) / 10, lip: Math.round(lip * 10) / 10, nonReconnus };
}
