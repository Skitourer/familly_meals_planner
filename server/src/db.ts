/**
 * Accès à la base SQLite (fichier unique, sans ORM pour rester léger).
 * Le schéma est créé au démarrage ; les tables sont idempotentes.
 */
import Database from "better-sqlite3";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync } from "node:fs";

const CHEMIN_DB = process.env.DB_CHEMIN ?? join(dirname(fileURLToPath(import.meta.url)), "../../donnees/menu.db");
mkdirSync(join(CHEMIN_DB, ".."), { recursive: true });

export const db = new Database(CHEMIN_DB);
db.pragma("journal_mode = WAL");
db.pragma("foreign_keys = ON");

// ---------- Schéma ----------
db.exec(`
  -- Paramètres applicatifs (mot de passe, secret de session)
  CREATE TABLE IF NOT EXISTS parametres (
    cle     TEXT PRIMARY KEY,
    valeur  TEXT NOT NULL
  );

  -- Membres de la famille
  CREATE TABLE IF NOT EXISTS membres (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nom       TEXT NOT NULL,
    age       INTEGER NOT NULL,
    taille_cm INTEGER,
    poids_kg  INTEGER,
    sexe      TEXT NOT NULL CHECK (sexe IN ('F','H')),
    activite  TEXT NOT NULL CHECK (activite IN ('sedentaire','leger','modere','intense'))
  );

  -- Catalogue de plats. Les colonnes saison et ingredients sont en JSON
  -- (échelle familiale : pas besoin de normalisation lourde).
  CREATE TABLE IF NOT EXISTS plats (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nom              TEXT NOT NULL,
    categorie        TEXT NOT NULL CHECK (categorie IN ('viande','poisson','volaille','pates','vegetarien','autre')),
    kcal_par_portion INTEGER NOT NULL,
    saison           TEXT NOT NULL DEFAULT '[]',
    ingredients      TEXT NOT NULL DEFAULT '[]',
    source           TEXT NOT NULL DEFAULT 'manuel'  -- 'manuel' | 'openfoodfacts'
  );

  -- Repas planifiés d'une semaine (clé : semaine + créneau)
  CREATE TABLE IF NOT EXISTS repas (
    semaine_id TEXT NOT NULL,
    jour       INTEGER NOT NULL CHECK (jour BETWEEN 0 AND 6),
    service    TEXT NOT NULL CHECK (service IN ('midi','soir')),
    plat_id    INTEGER REFERENCES plats(id) ON DELETE SET NULL,
    convives   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (semaine_id, jour, service)
  );

  -- Notes a posteriori (1 à 5 étoiles)
  CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    semaine_id  TEXT NOT NULL,
    plat_id     INTEGER NOT NULL REFERENCES plats(id) ON DELETE CASCADE,
    note        INTEGER NOT NULL CHECK (note BETWEEN 1 AND 5),
    commentaire TEXT,
    cree_le     TEXT NOT NULL DEFAULT (datetime('now'))
  );

  -- Conditionnements magasin (pour l'arrondi de la liste de courses)
  CREATE TABLE IF NOT EXISTS emballages (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    motifs TEXT NOT NULL,  -- JSON : liste de mots-clés
    pas    INTEGER NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_notes_plat ON notes(plat_id);
`);

// ---------- Données initiales (au premier lancement uniquement) ----------
function initialise() {
  const vide = db.prepare("SELECT COUNT(*) AS n FROM plats").get() as { n: number };
  if (vide.n > 0) return;

  const insPlat = db.prepare(
    "INSERT INTO plats (nom, categorie, kcal_par_portion, saison, ingredients) VALUES (?,?,?,?,?)"
  );
  // [nom, catégorie, kcal/portion, mois de saison, ingrédients (nom, quantité, unité)]
  const platsDemo: Array<[string, string, number, number[], Array<[string, number, string]>]> = [
    ["Gratin de courge au fromage", "vegetarien", 650, [10, 11, 12, 1], [
      ["Courge butternut", 300, "g"], ["Pommes de terre", 200, "g"], ["Crème fraîche", 50, "g"], ["Fromage râpé", 40, "g"]]],
    ["Poulet rôti, riz et brocolis", "volaille", 700, [11], [
      ["Blanc de poulet", 180, "g"], ["Riz", 80, "g"], ["Brocolis", 150, "g"]]],
    ["Pavé de saumon, patates douces", "poisson", 680, [10, 11, 12], [
      ["Pavé de saumon", 150, "g"], ["Patate douce", 250, "g"], ["Poireau", 80, "g"]]],
    ["Spaghetti bolognaise", "pates", 720, [9, 10, 11, 12, 1, 2], [
      ["Spaghetti", 100, "g"], ["Viande hachée boeuf", 120, "g"], ["Tomates concassées", 200, "g"], ["Carottes", 60, "g"]]],
    ["Dal de lentilles corail aux épinards", "vegetarien", 620, [11, 12, 1, 2], [
      ["Lentilles corail", 90, "g"], ["Épinards", 120, "g"], ["Lait de coco", 80, "ml"], ["Riz basmati", 70, "g"]]],
    ["Poelee de choux et lardons", "viande", 690, [10, 11, 12, 1], [
      ["Chou vert", 250, "g"], ["Lardons", 90, "g"], ["Pommes de terre", 200, "g"]]],
    ["Dos de cabillaud, endives braisées", "poisson", 580, [10, 11, 12, 1], [
      ["Dos de cabillaud", 160, "g"], ["Endives", 200, "g"], ["Beurre", 20, "g"]]],
    ["Quiche poireaux-lardons et salade", "pates", 640, [10, 11, 12, 1, 2], [
      ["Pâte brisée", 1, "p"], ["Poireau", 150, "g"], ["Lardons", 70, "g"], ["Oeufs", 2, "p"], ["Salade", 60, "g"]]],
    ["Chili con carne au maïs", "viande", 710, [10, 11, 0], [
      ["Viande hachée boeuf", 120, "g"], ["Haricots rouges", 120, "g"], ["Tomates concassées", 200, "g"], ["Maïs", 80, "g"]]],
    ["Omelette aux champignons et cresson", "vegetarien", 560, [10, 11, 12], [
      ["Oeufs", 3, "p"], ["Champignons de Paris", 150, "g"], ["Cresson", 50, "g"]]],
  ];
  for (const [nom, cat, kcal, saison, ings] of platsDemo) {
    insPlat.run(nom, cat, kcal, JSON.stringify(saison),
      JSON.stringify(ings.map(([n2, q, u]) => ({ nom: n2, quantite: q, unite: u }))));
  }

  // Conditionnements par défaut (éditables ensuite directement en base)
  const insEmb = db.prepare("INSERT INTO emballages (motifs, pas) VALUES (?,?)");
  const emb: Array<[string[], number]> = [
    [["spaghetti", "penne", "macaroni", "farfalle", "pâtes", "riz", "lentille", "haricot sec", "semoule"], 500],
    [["viande hachée", "blanc de poulet", "lardons", "jambon"], 250],
    [["tomates concassées", "tomate pelée", "maïs", "haricots rouges", "pois chiches"], 400],
    [["lait de coco"], 200],
    [["crème"], 20],
    [["farine", "sucre"], 500],
  ];
  for (const [motifs, pas] of emb) insEmb.run(JSON.stringify(motifs), pas);
}
initialise();
