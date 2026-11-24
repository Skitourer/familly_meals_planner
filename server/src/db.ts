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
    lien_recette     TEXT,                             -- URL vers la recette détaillée
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

// Migration : bases créées avant l'ajout du lien de recette
{
  const colonnes = db.prepare("PRAGMA table_info(plats)").all() as Array<{ name: string }>;
  if (!colonnes.some((c) => c.name === "lien_recette")) {
    db.exec("ALTER TABLE plats ADD COLUMN lien_recette TEXT");
  }
}

// ---------- Données initiales ----------
// Lien par défaut = recherche Marmiton (plusieurs recettes possibles) : ce n'est
// PAS la source des ingrédients. Les quantités ci-dessous sont des ESTIMATIONS de
// portions (ordres de grandeur) servant uniquement au calcul de la liste de courses ;
// la famille remplace le lien par sa propre recette dans l'interface.
const marmiton = (nom: string) =>
  `https://www.marmiton.org/recettes/recherche.aspx?aqt=${encodeURIComponent(nom)}`;

const TOUTE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
const HIVER = [11, 12, 1, 2];
const PRINTEMPS = [3, 4, 5];
const ETE = [6, 7, 8];
const AUTOMNE = [9, 10, 11];

// [nom, catégorie, kcal/portion, mois de saison, ingrédients [nom, qté, unité], lien recette]
type PlatDemo = [string, string, number, number[], Array<[string, number, string]>, string];
const CATALOGUE: PlatDemo[] = [
  // ---- Viande ----
  ["Bœuf bourguignon", "viande", 750, HIVER, [["Bœuf à bourguignon", 200, "g"], ["Carottes", 150, "g"], ["Oignons", 100, "g"], ["Vin rouge", 100, "ml"], ["Lardons", 50, "g"]], marmiton("bœuf bourguignon")],
  ["Steak frites maison", "viande", 800, TOUTE, [["Steak haché bœuf", 150, "g"], ["Pommes de terre", 300, "g"], ["Beurre", 15, "g"], ["Salade", 60, "g"]], marmiton("steak frites")],
  ["Hachis Parmentier", "viande", 720, TOUTE, [["Viande hachée bœuf", 150, "g"], ["Pommes de terre", 300, "g"], ["Lait", 50, "ml"], ["Fromage râpé", 30, "g"]], marmiton("hachis parmentier")],
  ["Chili con carne au maïs", "viande", 710, AUTOMNE.concat([12, 1]), [["Viande hachée bœuf", 120, "g"], ["Haricots rouges", 120, "g"], ["Tomates concassées", 200, "g"], ["Maïs", 80, "g"]], marmiton("chili con carne")],
  ["Côtes de porc à la moutarde", "viande", 680, TOUTE, [["Côte de porc", 180, "g"], ["Moutarde", 15, "g"], ["Crème fraîche", 40, "g"], ["Pommes de terre", 250, "g"]], marmiton("côtes de porc moutarde")],
  ["Rôti de porc aux herbes", "viande", 690, TOUTE, [["Rôti de porc", 180, "g"], ["Pommes de terre", 300, "g"], ["Ail", 10, "g"], ["Thym", 5, "g"]], marmiton("rôti de porc")],
  ["Entrecôte grillée et salade", "viande", 750, PRINTEMPS.concat(ETE, AUTOMNE), [["Entrecôte", 200, "g"], ["Salade", 80, "g"], ["Tomates", 100, "g"], ["Huile d'olive", 10, "ml"]], marmiton("entrecôte grillée")],
  ["Bœuf stroganoff", "viande", 730, HIVER, [["Bœuf à sauté", 180, "g"], ["Champignons de Paris", 150, "g"], ["Crème fraîche", 60, "g"], ["Riz", 80, "g"]], marmiton("bœuf stroganoff")],
  // ---- Poisson ----
  ["Pavé de saumon, patates douces", "poisson", 680, AUTOMNE.concat([12, 1]), [["Pavé de saumon", 150, "g"], ["Patate douce", 250, "g"], ["Poireau", 80, "g"]], marmiton("pavé de saumon patate douce")],
  ["Dos de cabillaud, endives braisées", "poisson", 580, HIVER, [["Dos de cabillaud", 160, "g"], ["Endives", 200, "g"], ["Beurre", 20, "g"]], marmiton("dos de cabillaud endives")],
  ["Saumon en papillote aux légumes", "poisson", 620, TOUTE, [["Pavé de saumon", 150, "g"], ["Courgette", 100, "g"], ["Carottes", 80, "g"], ["Citron", 1, "p"]], marmiton("saumon en papillote")],
  ["Dos de lieu noir, sauce tomate", "poisson", 590, TOUTE, [["Lieu noir", 170, "g"], ["Tomates concassées", 150, "g"], ["Riz", 80, "g"], ["Ail", 10, "g"]], marmiton("lieu noir sauce tomate")],
  ["Thon à la tomate et aux olives", "poisson", 610, ETE.concat(AUTOMNE), [["Thon frais", 160, "g"], ["Tomates concassées", 150, "g"], ["Olives noires", 30, "g"], ["Pâtes", 80, "g"]], marmiton("thon tomate olives")],
  ["Maquereaux grillés, purée", "poisson", 640, AUTOMNE.concat(HIVER), [["Maquereaux", 200, "g"], ["Pommes de terre", 300, "g"], ["Beurre", 15, "g"], ["Citron", 1, "p"]], marmiton("maquereaux grillés")],
  ["Brandade de morue", "poisson", 660, HIVER, [["Morue dessalée", 200, "g"], ["Pommes de terre", 300, "g"], ["Lait", 80, "ml"], ["Ail", 10, "g"]], marmiton("brandade de morue")],
  ["Curry de poisson au lait de coco", "poisson", 650, TOUTE, [["Poisson blanc", 170, "g"], ["Lait de coco", 100, "ml"], ["Pâte de curry", 20, "g"], ["Riz", 80, "g"]], marmiton("curry de poisson lait de coco")],
  // ---- Volaille ----
  ["Poulet rôti, riz et brocolis", "volaille", 700, TOUTE, [["Blanc de poulet", 180, "g"], ["Riz", 80, "g"], ["Brocolis", 150, "g"]], marmiton("poulet rôti riz brocolis")],
  ["Poulet au curry et lait de coco", "volaille", 720, TOUTE, [["Blanc de poulet", 180, "g"], ["Lait de coco", 80, "ml"], ["Pâte de curry", 20, "g"], ["Riz", 80, "g"]], marmiton("poulet curry lait de coco")],
  ["Poulet basquaise", "volaille", 680, ETE.concat(AUTOMNE), [["Poulet", 180, "g"], ["Poivrons", 150, "g"], ["Tomates concassées", 150, "g"], ["Riz", 80, "g"]], marmiton("poulet basquaise")],
  ["Escalopes de dinde à la crème", "volaille", 640, TOUTE, [["Escalope de dinde", 170, "g"], ["Crème fraîche", 50, "g"], ["Champignons de Paris", 100, "g"], ["Pâtes", 80, "g"]], marmiton("escalopes de dinde crème champignons")],
  ["Cuisses de poulet au citron et thym", "volaille", 690, TOUTE, [["Cuisse de poulet", 200, "g"], ["Citron", 1, "p"], ["Pommes de terre", 300, "g"], ["Thym", 5, "g"]], marmiton("cuisses de poulet citron thym")],
  ["Coq au vin", "volaille", 740, HIVER, [["Coq", 200, "g"], ["Vin rouge", 100, "ml"], ["Champignons de Paris", 100, "g"], ["Lardons", 60, "g"], ["Pâtes", 80, "g"]], marmiton("coq au vin")],
  ["Magret de canard au miel", "volaille", 760, AUTOMNE.concat(HIVER), [["Magret de canard", 180, "g"], ["Miel", 20, "g"], ["Pommes de terre", 250, "g"], ["Thym", 5, "g"]], marmiton("magret de canard miel")],
  ["Wok de poulet aux légumes", "volaille", 620, TOUTE, [["Blanc de poulet", 160, "g"], ["Nouilles asiatiques", 80, "g"], ["Carottes", 100, "g"], ["Poireaux", 80, "g"], ["Sauce soja", 15, "ml"]], marmiton("wok de poulet légumes")],
  // ---- Pâtes ----
  ["Spaghetti bolognaise", "pates", 720, AUTOMNE.concat(HIVER), [["Spaghetti", 100, "g"], ["Viande hachée bœuf", 120, "g"], ["Tomates concassées", 200, "g"], ["Carottes", 60, "g"]], marmiton("spaghetti bolognaise")],
  ["Quiche poireaux-lardons et salade", "pates", 640, HIVER.concat([3]), [["Pâte brisée", 1, "p"], ["Poireau", 150, "g"], ["Lardons", 70, "g"], ["Oeufs", 2, "p"], ["Salade", 60, "g"]], marmiton("quiche poireaux lardons")],
  ["Lasagnes bolognaise", "pates", 780, TOUTE, [["Pâtes à lasagnes", 80, "g"], ["Viande hachée bœuf", 140, "g"], ["Tomates concassées", 200, "g"], ["Béchamel", 100, "g"], ["Fromage râpé", 40, "g"]], marmiton("lasagnes bolognaise")],
  ["Pâtes à la carbonara", "pates", 760, TOUTE, [["Spaghetti", 100, "g"], ["Lardons", 80, "g"], ["Oeufs", 2, "p"], ["Parmesan", 30, "g"]], marmiton("pâtes carbonara")],
  ["Penne à la sauce tomate basilic", "pates", 640, TOUTE, [["Penne", 100, "g"], ["Tomates concassées", 200, "g"], ["Ail", 10, "g"], ["Basilic", 5, "g"], ["Huile d'olive", 10, "ml"]], marmiton("penne sauce tomate")],
  ["Gratin de coquillettes au jambon", "pates", 700, TOUTE, [["Coquillettes", 100, "g"], ["Jambon blanc", 100, "g"], ["Crème fraîche", 60, "g"], ["Fromage râpé", 40, "g"]], marmiton("gratin de pâtes jambon")],
  ["Nouilles sautées aux légumes", "pates", 610, TOUTE, [["Nouilles asiatiques", 90, "g"], ["Carottes", 80, "g"], ["Poireaux", 80, "g"], ["Oeufs", 1, "p"], ["Sauce soja", 15, "ml"]], marmiton("nouilles sautées légumes")],
  ["Risotto aux champignons", "pates", 680, AUTOMNE.concat(HIVER), [["Riz arborio", 90, "g"], ["Champignons de Paris", 150, "g"], ["Parmesan", 30, "g"], ["Bouillon de légumes", 200, "ml"]], marmiton("risotto champignons")],
  // ---- Végétarien ----
  ["Gratin de courge au fromage", "vegetarien", 650, AUTOMNE.concat(HIVER), [["Courge butternut", 300, "g"], ["Pommes de terre", 200, "g"], ["Crème fraîche", 50, "g"], ["Fromage râpé", 40, "g"]], marmiton("gratin de courge")],
  ["Dal de lentilles corail aux épinards", "vegetarien", 620, HIVER.concat([3]), [["Lentilles corail", 90, "g"], ["Épinards", 120, "g"], ["Lait de coco", 80, "ml"], ["Riz basmati", 70, "g"]], marmiton("dal de lentilles corail")],
  ["Omelette aux champignons et cresson", "vegetarien", 560, AUTOMNE.concat(HIVER), [["Oeufs", 3, "p"], ["Champignons de Paris", 150, "g"], ["Cresson", 50, "g"], ["Beurre", 10, "g"]], marmiton("omelette champignons")],
  ["Ratatouille et semoule", "vegetarien", 480, ETE.concat(AUTOMNE), [["Courgette", 150, "g"], ["Aubergine", 150, "g"], ["Poivron", 100, "g"], ["Tomates concassées", 200, "g"], ["Semoule", 80, "g"]], marmiton("ratatouille")],
  ["Curry de légumes au lait de coco", "vegetarien", 560, TOUTE, [["Lait de coco", 100, "ml"], ["Carottes", 120, "g"], ["Courgettes", 120, "g"], ["Pois chiches", 120, "g"], ["Riz", 80, "g"]], marmiton("curry de légumes lait de coco")],
  ["Tarte aux légumes du soleil", "vegetarien", 620, ETE, [["Pâte brisée", 1, "p"], ["Courgette", 120, "g"], ["Tomates", 150, "g"], ["Chèvre frais", 60, "g"], ["Oeufs", 1, "p"]], marmiton("tarte aux légumes chèvre")],
  ["Gratin dauphinois au fromage", "vegetarien", 700, HIVER, [["Pommes de terre", 300, "g"], ["Crème fraîche", 100, "ml"], ["Lait", 50, "ml"], ["Fromage râpé", 40, "g"], ["Ail", 5, "g"]], marmiton("gratin dauphinois")],
  ["Falafels, houmous et pain pita", "vegetarien", 640, TOUTE, [["Pois chiches", 120, "g"], ["Houmous", 60, "g"], ["Pain pita", 2, "p"], ["Salade", 60, "g"], ["Tomates", 80, "g"]], marmiton("falafels houmous")],
  ["Chili sin carne", "vegetarien", 580, TOUTE, [["Haricots rouges", 140, "g"], ["Maïs", 80, "g"], ["Tomates concassées", 200, "g"], ["Riz", 80, "g"], ["Poivron", 80, "g"]], marmiton("chili végétarien")],
  ["Soupe de légumes et croûtons", "vegetarien", 380, HIVER, [["Carottes", 150, "g"], ["Poireaux", 100, "g"], ["Pommes de terre", 150, "g"], ["Bouillon de légumes", 300, "ml"], ["Pain", 60, "g"]], marmiton("soupe de légumes")],
  ["Croque-monsieur chèvre-épinards", "vegetarien", 590, TOUTE, [["Pain de mie", 4, "p"], ["Chèvre frais", 80, "g"], ["Épinards", 100, "g"], ["Béchamel", 60, "g"]], marmiton("croque monsieur végétarien")],
  ["Pizza maison jambon-fromage", "vegetarien", 820, TOUTE, [["Pâte à pizza", 1, "p"], ["Sauce tomate", 80, "g"], ["Jambon blanc", 100, "g"], ["Mozzarella", 120, "g"]], marmiton("pizza maison")],
  // ---- Autre ----
  ["Tartiflette", "autre", 850, HIVER, [["Pommes de terre", 300, "g"], ["Reblochon", 150, "g"], ["Lardons", 100, "g"], ["Oignons", 80, "g"]], marmiton("tartiflette")],
  ["Croque-monsieur classique", "autre", 680, TOUTE, [["Pain de mie", 4, "p"], ["Jambon blanc", 100, "g"], ["Emmental râpé", 60, "g"], ["Béchamel", 50, "g"]], marmiton("croque monsieur")],
  ["Hamburgers maison, frites au four", "autre", 840, TOUTE, [["Steak haché bœuf", 150, "g"], ["Pain à burger", 2, "p"], ["Cheddar", 40, "g"], ["Pommes de terre", 250, "g"], ["Salade", 50, "g"], ["Tomates", 60, "g"]], marmiton("hamburger maison")],
  ["Wraps de poulet froid", "autre", 560, PRINTEMPS.concat(ETE, AUTOMNE), [["Galette de blé", 2, "p"], ["Blanc de poulet", 120, "g"], ["Salade", 60, "g"], ["Tomates", 80, "g"], ["Sauce yaourt", 40, "g"]], marmiton("wrap poulet")],
];

function initialise() {
  const insPlat = db.prepare(
    "INSERT INTO plats (nom, categorie, kcal_par_portion, saison, ingredients, lien_recette) VALUES (?,?,?,?,?,?)"
  );
  // Insère les plats du catalogue dont le nom n'existe pas encore (idempotent :
  // les plats ajoutés/édités par la famille ne sont jamais écrasés).
  const nomsExistants = new Set(
    (db.prepare("SELECT nom FROM plats").all() as Array<{ nom: string }>).map((r) => r.nom)
  );
  for (const [nom, cat, kcal, saison, ings, lien] of CATALOGUE) {
    if (nomsExistants.has(nom)) continue;
    insPlat.run(nom, cat, kcal, JSON.stringify(saison),
      JSON.stringify(ings.map(([n2, q, u]) => ({ nom: n2, quantite: q, unite: u }))), lien);
  }
  // Plat existant sans lien de recette (ex. plats de la toute première version) :
  // lien Marmiton par défaut basé sur le nom.
  const sansLien = db.prepare("SELECT id, nom FROM plats WHERE lien_recette IS NULL").all() as Array<{ id: number; nom: string }>;
  const majLien = db.prepare("UPDATE plats SET lien_recette = ? WHERE id = ?");
  for (const p of sansLien) majLien.run(marmiton(p.nom), p.id);

  // Conditionnements par défaut (éditables ensuite directement en base)
  const embVide = db.prepare("SELECT COUNT(*) AS n FROM emballages").get() as { n: number };
  if (embVide.n > 0) return;
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
