/**
 * Générateur PDF minimal, sans dépendance externe.
 *
 * Produit un PDF valide (adapté à une liste de courses) :
 * police Helvetica, encodage WinAnsi (Latin-1) pour les accents français,
 * pagination automatique des listes longues.
 */

/** Caractère -> octet WinAnsi ; les caractères non représentables sont remplacés. */
function versWinAnsi(texte: string): string {
  const remplacements: Record<string, string> = { "→": "->", "—": "-", "’": "'", "…": "..." };
  let s = "";
  for (const c of texte) {
    const r = remplacements[c] ?? c;
    for (const ch of r) {
      const code = ch.codePointAt(0)!;
      s += code <= 0xff ? ch : "?"; // hors Latin-1 : point d'interrogation
    }
  }
  return s;
}

/** Échappe les délimiteurs de chaîne PDF : ( ) \ */
function echappe(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

export interface LignePdf {
  /** texte principal (ex. "Spaghetti") */
  gauche: string;
  /** information alignée à droite (ex. "800 g -> 1 kg"), optionnel */
  droite?: string;
  /** trait de séparation au-dessus (pseudo tableau) */
  separateur?: boolean;
}

/**
 * Construit le PDF. Retourne les octets prêts à être envoyés
 * (Content-Type: application/pdf).
 */
export function construirePdf(titre: string, sousTitre: string, lignes: LignePdf[]): Uint8Array {
  const marge = 50;

  // ---------- Découpage en pages (A4 : on écrit entre 40 et 800 pt) ----------
  const margeHaute = 800;
  const margeBasse = 40;
  const hauteurLigne = 18;
  const capacite = Math.floor((margeHaute - margeBasse - 48) / hauteurLigne); // 48 = titre + sous-titre

  // Une "page" = son flux de contenu (opérateurs PDF), reconstruit indépendamment.
  function page(bloc: LignePdf[], avecEnTete: boolean): string {
    let flux = "";
    let y = margeHaute;
    const ecrire = (police: string, taille: number, x: number, texte: string) => {
      flux += `BT /${police} ${taille} Tf ${x} ${y} Td (${echappe(versWinAnsi(texte))}) Tj ET\n`;
    };
    if (avecEnTete) {
      ecrire("F2", 20, marge, titre);
      y -= 22;
      ecrire("F1", 10, marge, sousTitre);
      y -= 26;
    } else {
      // Pages de suite : en-tête réduit
      ecrire("F1", 9, marge, `${titre} (suite)`);
      y -= 20;
    }
    for (const l of bloc) {
      if (l.separateur) {
        y += 4;
        flux += `0.8 w ${marge} ${y} m 545 ${y} l S\n`;
        y -= 6;
      }
      ecrire("F1", 11, marge, l.gauche);
      if (l.droite) ecrire("F1", 11, 380, l.droite);
      y -= hauteurLigne;
    }
    return flux;
  }

  // Première page avec en-tête, suivantes sans (capacité réduite car sans titre)
  const pages: string[] = [page(lignes.slice(0, capacite), true)];
  let curseur = capacite;
  const capaciteSuite = Math.floor((margeHaute - margeBasse - 20) / hauteurLigne);
  while (curseur < lignes.length) {
    pages.push(page(lignes.slice(curseur, curseur + capaciteSuite), false));
    curseur += capaciteSuite;
  }

  // ---------- Assemblage des objets PDF ----------
  // Objets 1 (catalogue) et 2 (pages), puis par page : objet page + objet contenu,
  // puis les deux polices en fin de fichier.
  const objets: string[] = [];
  objets[1] = "<< /Type /Catalog /Pages 2 0 R >>";
  const idsPolices = [3, 4];
  const idPage = (i: number) => 5 + i * 2; // premier id de page : 5
  const idsPages = pages.map((_, i) => idPage(i));
  objets[2] = `<< /Type /Pages /Kids [${idsPages.map((id) => `${id} 0 R`).join(" ")}] /Count ${pages.length} >>`;
  objets[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>";
  objets[4] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>";
  pages.forEach((flux, i) => {
    objets[idPage(i)] = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${idsPolices[0]} 0 R /F2 ${idsPolices[1]} 0 R >> >> /Contents ${idPage(i) + 1} 0 R >>`;
    objets[idPage(i) + 1] = `<< /Length ${Buffer.byteLength(flux, "latin1")} >>\nstream\n${flux}endstream`;
  });
  const nbObjets = idPage(pages.length - 1) + 1; // dernier id utilisé

  // ---------- Sérialisation avec table xref correcte ----------
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [0];
  for (let i = 1; i <= nbObjets; i++) {
    if (!objets[i]) continue;
    offsets[i] = Buffer.byteLength(pdf, "latin1");
    pdf += `${i} 0 obj\n${objets[i]}\nendobj\n`;
  }
  const debutXref = Buffer.byteLength(pdf, "latin1");
  pdf += `xref\n0 ${nbObjets + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i <= nbObjets; i++) {
    pdf += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${nbObjets + 1} /Root 1 0 R >>\nstartxref\n${debutXref}\n%%EOF\n`;

  return new Uint8Array(Buffer.from(pdf, "latin1"));
}
