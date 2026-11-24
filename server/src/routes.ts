/**
 * Routes de l'API Menu Famille.
 * Toutes les routes (sauf /api/session) exigent une session valide (hook `protege`).
 */
import type { FastifyInstance } from "fastify";
import { db } from "./db.ts";
import { protege } from "./auth.ts";
import { besoinKcal, besoinParRepas } from "../../shared/besoins.ts";
import type { Membre, Plat, Repas, Activite } from "../../shared/types.ts";
import { genererSemaine } from "../../shared/generation.ts";
import { construireListe, type Emballage } from "../../shared/courses.ts";
import { saisonDuMois } from "../../shared/saison.ts";
import { moisDeSemaine } from "../../shared/dates.ts";
import { construirePdf, type LignePdf } from "./pdf.ts";

/* ---------- Conversion lignes SQL -> objets du domaine ---------- */

type LignePlat = { id: number; nom: string; categorie: Plat["categorie"]; kcal_par_portion: number; saison: string; ingredients: string; lien_recette: string | null };
function versPlat(l: LignePlat): Plat {
  return {
    id: l.id, nom: l.nom, categorie: l.categorie, kcalParPortion: l.kcal_par_portion,
    saison: JSON.parse(l.saison), ingredients: JSON.parse(l.ingredients),
    lienRecette: l.lien_recette ?? undefined,
  };
}
type LigneMembre = { id: number; nom: string; age: number; taille_cm: number | null; poids_kg: number | null; sexe: "F" | "H"; activite: Activite };
function versMembre(l: LigneMembre): Membre {
  return { id: l.id, nom: l.nom, age: l.age, tailleCm: l.taille_cm ?? undefined, poidsKg: l.poids_kg ?? undefined, sexe: l.sexe, activite: l.activite };
}

function lireMembres(): Membre[] {
  return (db.prepare("SELECT * FROM membres ORDER BY id").all() as LigneMembre[]).map(versMembre);
}
function lirePlats(): Plat[] {
  return (db.prepare("SELECT * FROM plats ORDER BY nom").all() as LignePlat[]).map(versPlat);
}
function lireEmballages(): Emballage[] {
  return (db.prepare("SELECT motifs, pas FROM emballages").all() as Array<{ motifs: string; pas: number }>)
    .map((e) => ({ motifs: JSON.parse(e.motifs) as string[], pas: e.pas }));
}
/** Moyenne des notes par plat (pour favoriser les favoris à la génération). */
function notesMoyennes(): Record<number, number> {
  const lignes = db.prepare("SELECT plat_id, AVG(note) AS m FROM notes GROUP BY plat_id").all() as Array<{ plat_id: number; m: number }>;
  return Object.fromEntries(lignes.map((l) => [l.plat_id, Math.round(l.m * 10) / 10]));
}

/** Charge les 14 créneaux d'une semaine (valeurs par défaut si absents). */
function repasDeSemaine(idSemaine: string): Repas[] {
  const lignes = db.prepare("SELECT * FROM repas WHERE semaine_id = ?").all(idSemaine) as Array<{ jour: number; service: "midi" | "soir"; plat_id: number | null; convives: number }>;
  const par = new Map(lignes.map((l) => [`${l.jour}|${l.service}`, l]));
  const convivesDefaut = Math.max(1, lireMembres().length);
  return Array.from({ length: 7 }, (_, jour) =>
    (["midi", "soir"] as const).map((service) => {
      const l = par.get(`${jour}|${service}`);
      return { jour, service, platId: l?.plat_id ?? null, convives: l?.convives ?? convivesDefaut };
    })
  ).flat();
}

export async function routesApi(app: FastifyInstance): Promise<void> {
  app.addHook("preHandler", protege);

  /* ----- Fruits & légumes de saison ----- */
  app.get("/api/saison/:mois", async (req) => {
    const { mois } = req.params as { mois: string };
    return saisonDuMois(Number(mois));
  });

  /* ----- Membres ----- */
  app.get("/api/membres", async () => {
    // On renvoie le besoin calculé à côté du profil
    return lireMembres().map((m) => ({ ...m, besoinKcal: besoinKcal(m) }));
  });

  app.post("/api/membres", async (req, rep) => {
    const b = req.body as Partial<Membre>;
    const r = db.prepare(
      "INSERT INTO membres (nom, age, taille_cm, poids_kg, sexe, activite) VALUES (?,?,?,?,?,?)"
    ).run(b.nom ?? "Nouveau", b.age ?? 30, b.tailleCm ?? null, b.poidsKg ?? null, b.sexe ?? "F", b.activite ?? "leger");
    rep.code(201);
    return { id: Number(r.lastInsertRowid) };
  });

  app.patch("/api/membres/:id", async (req) => {
    const { id } = req.params as { id: string };
    const b = req.body as Partial<Membre>;
    const actuel = versMembre(db.prepare("SELECT * FROM membres WHERE id = ?").get(Number(id)) as LigneMembre);
    db.prepare("UPDATE membres SET nom=?, age=?, taille_cm=?, poids_kg=?, sexe=?, activite=? WHERE id=?").run(
      b.nom ?? actuel.nom, b.age ?? actuel.age, b.tailleCm ?? actuel.tailleCm ?? null,
      b.poidsKg ?? actuel.poidsKg ?? null, b.sexe ?? actuel.sexe, b.activite ?? actuel.activite, Number(id));
    return { ok: true };
  });

  app.delete("/api/membres/:id", async (req) => {
    db.prepare("DELETE FROM membres WHERE id = ?").run(Number((req.params as { id: string }).id));
    return { ok: true };
  });

  /* ----- Plats ----- */
  app.get("/api/plats", async () => lirePlats());

  app.post("/api/plats", async (req, rep) => {
    const { nom, categorie, kcalParPortion, saison = [], ingredients = [], lienRecette } = req.body as Partial<Plat>;
    const r = db.prepare(
      "INSERT INTO plats (nom, categorie, kcal_par_portion, saison, ingredients, lien_recette) VALUES (?,?,?,?,?,?)"
    ).run(nom!, categorie!, kcalParPortion!, JSON.stringify(saison), JSON.stringify(ingredients), lienRecette ?? null);
    rep.code(201);
    return { id: Number(r.lastInsertRowid) };
  });

  app.patch("/api/plats/:id", async (req) => {
    const { id } = req.params as { id: string };
    const b = req.body as Partial<Plat>;
    const actuel = versPlat(db.prepare("SELECT * FROM plats WHERE id = ?").get(Number(id)) as LignePlat);
    db.prepare("UPDATE plats SET nom=?, categorie=?, kcal_par_portion=?, saison=?, ingredients=?, lien_recette=? WHERE id=?").run(
      b.nom ?? actuel.nom, b.categorie ?? actuel.categorie, b.kcalParPortion ?? actuel.kcalParPortion,
      JSON.stringify(b.saison ?? actuel.saison), JSON.stringify(b.ingredients ?? actuel.ingredients),
      b.lienRecette ?? actuel.lienRecette ?? null, Number(id));
    return { ok: true };
  });

  app.delete("/api/plats/:id", async (req) => {
    db.prepare("DELETE FROM plats WHERE id = ?").run(Number((req.params as { id: string }).id));
    return { ok: true };
  });

  /* ----- Open Food Facts : recherche de produits (proxy serveur) ----- */
  app.get("/api/openfoodfacts", async (req) => {
    const { q } = req.query as { q: string };
    const url = `https://world.openfoodfacts.org/cgi/search.pl?search_terms=${encodeURIComponent(q)}&search_simple=1&action=process&json=1&page_size=20`;
    const reponse = await fetch(url, { headers: { "User-Agent": "MenuFamille/1.0 (usage familial)" } });
    if (!reponse.ok) return { produits: [] };
    const data = (await reponse.json()) as { products?: Array<{ product_name?: string; brands?: string; nutriments?: { "energy-kcal_100g"?: number }; quantity?: string }> };
    // On ne garde que les champs utiles pour pré-remplir un ingrédient
    const produits = (data.products ?? [])
      .filter((p) => p.product_name)
      .map((p) => ({
        nom: p.product_name,
        marque: p.brands ?? "",
        kcalPour100g: p.nutriments?.["energy-kcal_100g"] ?? null,
        quantite: p.quantity ?? "",
      }));
    return { produits };
  });

  /* ----- Semaines et repas ----- */
  app.get("/api/semaines/:id", async (req) => {
    const { id } = req.params as { id: string };
    const membres = lireMembres();
    return {
      repas: repasDeSemaine(id),
      besoinTotal: membres.reduce((t, m) => t + besoinKcal(m), 0),
      besoinParRepas: besoinParRepas(membres),
      saison: saisonDuMois(moisDeSemaine(id)),
    };
  });

  // Enregistre les repas d'une semaine (remplacement complet, transaction)
  app.put("/api/semaines/:id/repas", async (req) => {
    const { id } = req.params as { id: string };
    const repas = req.body as Repas[];
    const up = db.prepare("INSERT OR REPLACE INTO repas (semaine_id, jour, service, plat_id, convives) VALUES (?,?,?,?,?)");
    db.transaction(() => {
      db.prepare("DELETE FROM repas WHERE semaine_id = ?").run(id);
      for (const r of repas) up.run(id, r.jour, r.service, r.platId, r.convives);
    })();
    return { ok: true };
  });

  // Génère les repas manquants de la semaine (algorithme, voir shared/generation.ts)
  app.post("/api/semaines/:id/generer", async (req) => {
    const { id } = req.params as { id: string };
    const membres = lireMembres();
    const repas = repasDeSemaine(id);
    const parConvive = membres.length ? besoinParRepas(membres) / membres.length : 650;
    const resultats = genererSemaine(lirePlats(), repas, {
      mois: moisDeSemaine(id),
      besoinMoyen: Math.round(parConvive),
      notes: notesMoyennes(),
    });
    const up = db.prepare("INSERT OR REPLACE INTO repas (semaine_id, jour, service, plat_id, convives) VALUES (?,?,?,?,?)");
    db.transaction(() => {
      for (const r of resultats) up.run(id, r.jour, r.service, r.platId, r.convives);
    })();
    return { repas: resultats };
  });

  /* ----- Liste de courses ----- */
  app.get("/api/semaines/:id/courses", async (req) => {
    const { id } = req.params as { id: string };
    const plats = new Map(lirePlats().map((p) => [p.id, p]));
    return construireListe(repasDeSemaine(id), plats, lireEmballages());
  });

  /**
   * Export PDF de la liste de courses (généré sans dépendance, voir pdf.ts).
   * Le navigateur télécharge le fichier grâce à Content-Disposition.
   */
  app.get("/api/semaines/:id/courses.pdf", async (req, rep) => {
    const { id } = req.params as { id: string };
    const plats = new Map(lirePlats().map((p) => [p.id, p]));
    const liste = construireListe(repasDeSemaine(id), plats, lireEmballages());

    // Mise en page : article à gauche, besoin -> achat à droite
    const lignes: LignePdf[] = liste.map((l) => ({
      gauche: l.nom,
      droite: l.arrondi
        ? `${Math.round(l.besoin)} ${l.unite} -> ${Math.round(l.achat)} ${l.unite}`
        : (l.unite === "p" ? `${Math.round(l.achat)} pc(s)` : `${Math.round(l.achat)} ${l.unite}`),
    }));
    const octets = construirePdf("Liste de courses", `Semaine du ${id} - ${liste.length} articles`, lignes);
    rep.header("Content-Type", "application/pdf");
    rep.header("Content-Disposition", `attachment; filename="courses-${id}.pdf"`);
    return rep.send(Buffer.from(octets));
  });

  /* ----- Notes ----- */
  app.get("/api/notes/:semaine", async (req) => {
    const { semaine } = req.params as { semaine: string };
    return db.prepare("SELECT * FROM notes WHERE semaine_id = ? ORDER BY id DESC").all(semaine);
  });

  app.post("/api/notes", async (req, rep) => {
    const { semaine, platId, note, commentaire } = req.body as { semaine: string; platId: number; note: number; commentaire?: string };
    if (note < 1 || note > 5) { rep.code(400); return { erreur: "Note entre 1 et 5" }; }
    const r = db.prepare("INSERT INTO notes (semaine_id, plat_id, note, commentaire) VALUES (?,?,?,?)")
      .run(semaine, platId, note, commentaire ?? null);
    rep.code(201);
    return { id: Number(r.lastInsertRowid) };
  });

  /* ----- Statistiques (favoris) ----- */
  app.get("/api/stats", async () => {
    const parPlat = db.prepare(
      "SELECT p.id, p.nom, COUNT(n.id) AS nb, AVG(n.note) AS moyenne FROM plats p JOIN notes n ON n.plat_id = p.id GROUP BY p.id ORDER BY moyenne DESC"
    ).all() as Array<{ id: number; nom: string; nb: number; moyenne: number }>;
    return parPlat.map((p) => ({ ...p, moyenne: Math.round(p.moyenne * 10) / 10 }));
  });
}
