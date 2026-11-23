/**
 * Tests du cœur métier (node:test, aucune dépendance externe).
 * Exécution : npm test  (ou node --test)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { besoinKcal, besoinParRepas } from "../besoins.ts";
import { genererSemaine } from "../generation.ts";
import { construireListe, pasDAchat, EMBALLAGES_DEFAUT } from "../courses.ts";
import { idSemaine, lundiDe, moisDeSemaine } from "../dates.ts";
import type { Membre, Plat, Repas } from "../types.ts";

/* ---------- Fixtures ---------- */

const mere: Membre = { id: 1, nom: "Sophie", age: 40, tailleCm: 168, poidsKg: 62, sexe: "F", activite: "leger" };
const pere: Membre = { id: 2, nom: "Boris", age: 42, tailleCm: 178, poidsKg: 78, sexe: "H", activite: "modere" };

const platA: Plat = {
  id: 1, nom: "Gratin de courge", categorie: "vegetarien", kcalParPortion: 650,
  saison: [11], ingredients: [{ nom: "Courge butternut", quantite: 300, unite: "g" }, { nom: "Crème fraîche", quantite: 50, unite: "g" }],
};
const platB: Plat = {
  id: 2, nom: "Spaghetti bolognaise", categorie: "pates", kcalParPortion: 720,
  saison: [11, 12], ingredients: [{ nom: "Spaghetti", quantite: 100, unite: "g" }, { nom: "Viande hachée boeuf", quantite: 120, unite: "g" }],
};

const plats = [platA, platB];

function semaineVide(convives = 4): Repas[] {
  const out: Repas[] = [];
  for (let j = 0; j < 7; j++)
    for (const s of ["midi", "soir"] as const)
      out.push({ jour: j, service: s, platId: null, convives });
  return out;
}

/* ---------- Besoins ---------- */

test("besoinKcal applique Mifflin-St Jeor + coefficient d'activité", () => {
  // Mifflin-St Jeor : 10x62 + 6,25x168 - 5x40 - 161 = 1349 kcal de base
  const base = 10 * 62 + 6.25 * 168 - 5 * 40 - 161;
  assert.equal(besoinKcal(mere), Math.round((base * 1.375) / 10) * 10);
});

test("besoinParRepas = 45 % du total familial", () => {
  const total = besoinKcal(mere) + besoinKcal(pere);
  assert.equal(besoinParRepas([mere, pere]), Math.round(total * 0.45));
});

/* ---------- Génération ---------- */

test("génération : remplit les 14 créneaux avec les plats disponibles", () => {
  const resultat = genererSemaine(plats, semaineVide(), { mois: 11, besoinMoyen: 700, hasard: () => 0 });
  assert.equal(resultat.filter((r) => r.platId !== null).length, 14);
  // Avec seulement 2 plats disponibles, un second cycle les réutilise
  assert.ok(resultat.every((r) => r.platId === 1 || r.platId === 2));
});

test("génération : respecte les absences et les choix déjà faits", () => {
  const s = semaineVide();
  s[0].platId = 1;   // lundi midi déjà choisi
  s[1].convives = 0; // lundi soir : repas hors maison
  const resultat = genererSemaine([...plats], [...s], { mois: 11, besoinMoyen: 700, hasard: () => 0 });
  assert.equal(resultat[0].platId, 1);
  assert.equal(resultat[1].convives, 0);
  assert.equal(resultat[1].platId, null);
});

test("génération : fonctionne hors saison sans crash", () => {
  // En juillet (mois 7), aucun des deux plats n'est de saison : complétude quand même
  const resultat = genererSemaine(plats, semaineVide(), { mois: 7, besoinMoyen: 700, hasard: () => 0 });
  assert.equal(resultat.filter((r) => r.platId !== null).length, 14);
});

test("génération : jamais trois fois la même catégorie d'affilée si possible", () => {
  // 6 plats de catégories différentes : on ne doit jamais avoir 3 mêmes catégories
  const plats6: Plat[] = Array.from({ length: 6 }, (_, i) => ({
    id: i + 1, nom: `Plat ${i + 1}`,
    categorie: (["viande", "poisson", "volaille", "pates", "vegetarien", "autre"] as const)[i],
    kcalParPortion: 700, saison: [11], ingredients: [],
  }));
  const resultat = genererSemaine(plats6, semaineVide(), { mois: 11, besoinMoyen: 700, hasard: () => 0 });
  const cats = resultat.filter((r) => r.platId).map((r) => plats6.find((p) => p.id === r.platId)!.categorie);
  for (let i = 0; i + 2 < cats.length; i++) {
    assert.ok(!(cats[i] === cats[i + 1] && cats[i + 1] === cats[i + 2]));
  }
});

/* ---------- Courses ---------- */

test("pasDAchat : reconnaît les paquets de 500 g", () => {
  assert.equal(pasDAchat("Spaghetti", "g", EMBALLAGES_DEFAUT), 500);
  assert.equal(pasDAchat("Pommes de terre", "g", EMBALLAGES_DEFAUT), 1);
  assert.equal(pasDAchat("Oeufs", "p", EMBALLAGES_DEFAUT), 1);
});

test("construireListe : agrège par convives et ignore les absences", () => {
  const repas: Repas[] = [
    { jour: 0, service: "midi", platId: 2, convives: 4 },
    { jour: 0, service: "soir", platId: 2, convives: 0 }, // hors maison
    { jour: 1, service: "midi", platId: 1, convives: 2 },
  ];
  const liste = construireListe(repas, new Map(plats.map((p) => [p.id, p])));
  const spaghetti = liste.find((l) => l.nom === "Spaghetti")!;
  assert.equal(spaghetti.besoin, 400); // 100 g x 4 convives
  const creme = liste.find((l) => l.nom === "Crème fraîche")!;
  assert.equal(creme.besoin, 100);     // 50 g x 2 convives
});

test("construireListe : arrondit au conditionnement magasin", () => {
  // 400 g nécessaires de spaghetti -> 1 paquet de 500 g
  const repas: Repas[] = [{ jour: 0, service: "midi", platId: 2, convives: 4 }];
  const liste = construireListe(repas, new Map(plats.map((p) => [p.id, p])));
  const spaghetti = liste.find((l) => l.nom === "Spaghetti")!;
  assert.equal(spaghetti.achat, 500);
  assert.ok(spaghetti.arrondi);
  const courge = liste.find((l) => l.nom === "Courge butternut");
  assert.equal(courge, undefined); // plat 2 non pris
});

/* ---------- Dates ---------- */

test("lundiDe et idSemaine : vendredi 27 nov 2026 -> lundi 23 nov", () => {
  // 27 novembre 2026 est un vendredi
  const vendredi = new Date("2026-11-27T14:30:00");
  assert.equal(idSemaine(vendredi), "2026-11-23");
  assert.equal(lundiDe(vendredi).getDay(), 1);
});

test("moisDeSemaine : mois du mercredi", () => {
  // Semaine du 23 nov 2026 : mercredi 25 novembre -> mois 11
  assert.equal(moisDeSemaine("2026-11-23"), 11);
});
