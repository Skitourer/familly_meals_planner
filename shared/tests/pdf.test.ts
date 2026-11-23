/**
 * Tests du générateur PDF minimal (aucune dépendance).
 * Vérifie la structure du fichier : en-tête, offsets xref, objets, accents, pagination.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { construirePdf } from "../../server/src/pdf.ts";

test("PDF valide : en-tête, fin de fichier, nombre d'objets", () => {
  const octets = construirePdf("Liste de courses", "Semaine du 2026-11-23", [
    { gauche: "Spaghetti", droite: "800 g -> 1 kg" },
    { gauche: "Courge butternut", droite: "1.2 kg", separateur: true },
  ]);
  const texte = Buffer.from(octets).toString("latin1");
  assert.ok(texte.startsWith("%PDF-1.4\n"));
  assert.ok(texte.endsWith("%%EOF\n"));
  assert.equal((texte.match(/\d+ 0 obj/g) ?? []).length, 6);
});

test("PDF valide : les offsets de la table xref pointent sur les objets", () => {
  const texte = Buffer.from(construirePdf("T", "S", [{ gauche: "a" }])).toString("latin1");
  // startxref indique la position de la table
  const startxref = Number(texte.match(/startxref\n(\d+)/)![1]);
  assert.ok(texte.slice(startxref, startxref + 4) === "xref");
  // Chaque offset de la table doit pointer sur "N 0 obj"
  // (l'entrée 0 est la case libre "65535 f" : on saute les 3 premières lignes)
  const lignes = texte.slice(startxref).split("\n").slice(3, 3 + 6);
  lignes.forEach((ligne, i) => {
    const offset = Number(ligne.slice(0, 10));
    assert.ok(texte.slice(offset, offset + 8).startsWith(`${i + 1} 0 obj`), `objet ${i + 1} mal positionné`);
  });
});

test("PDF valide : accents Latin-1 et caractères spéciaux sécurisés", () => {
  const octets = construirePdf("Liste de courses — été (crème)", "", [{ gauche: "Épinards → 300 g" }]);
  const texte = Buffer.from(octets).toString("latin1");
  // Les caractères hors Latin-1 sont convertis (tiret long, flèche)
  assert.ok(texte.includes("Liste de courses - "));
  assert.ok(texte.includes("pinards -> 300 g"));
  // Les parenthèses du texte sont échappées pour ne pas casser les chaînes PDF
  // (dans le fichier, on trouve littéralement "\(crème\)")
  assert.ok(texte.includes("\\(crème\\)"));
});

test("PDF valide : une longue liste crée une deuxième page sans déborder", () => {
  const lignesPdf = Array.from({ length: 42 }, (_, i) => ({ gauche: `Article ${i}` }));
  const texte = Buffer.from(construirePdf("T", "S", lignesPdf)).toString("latin1");
  // Deux pages sont créées (la pagination a bien coupé la liste)
  assert.ok(/\/Count 2\b/.test(texte), "42 lignes -> 2 pages attendues");
  // Toutes les ordonnées "x y Td" des flux doivent rester >= 40 pt
  const ordonnees = [...texte.matchAll(/(\d+) (\d+) Td/g)].map((m) => Number(m[2]));
  assert.ok(ordonnees.length >= 44); // 42 articles + en-têtes de pages
  assert.ok(Math.min(...ordonnees) >= 40, "la liste déborde de la page");
});
