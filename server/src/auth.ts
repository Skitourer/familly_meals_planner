/**
 * Authentification simple : un mot de passe partagé pour toute la famille.
 *
 * - Le mot de passe est stocké haché (SHA-256 avec sel) dans `parametres`.
 * - Une session est un cookie signé par HMAC (pas de table de sessions,
 *   le cookie reste valide tant que le secret ne change pas).
 * - Le secret de session est généré au premier lancement et persisté.
 */
import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { db } from "./db.ts";

const NOM_COOKIE = "session";

/** Lit un paramètre persisté (créé avec une valeur par défaut si absent). */
function parametre(cle: string, defaut: () => string): string {
  const r = db.prepare("SELECT valeur FROM parametres WHERE cle = ?").get(cle) as { valeur: string } | undefined;
  if (r) return r.valeur;
  const v = defaut();
  db.prepare("INSERT INTO parametres (cle, valeur) VALUES (?,?)").run(cle, v);
  return v;
}

/** Empreinte SHA-256 salée du mot de passe. */
function empreinte(motDePasse: string): string {
  const sel = parametre("sel", () => randomBytes(16).toString("hex"));
  return createHash("sha256").update(sel + motDePasse).digest("hex");
}

function empreinteCourant(): string {
  // Au premier lancement, le mot de passe par défaut est "menu-famille".
  return parametre("mot_de_passe_hash", () => empreinte("menu-famille"));
}

const secret = () => parametre("secret_session", () => randomBytes(32).toString("hex"));

/** Cookie de session valide = HMAC du secret sur une constante. */
function cookieValide(valeur: string | undefined): boolean {
  if (!valeur) return false;
  return valeur === jeton();
}
function jeton(): string {
  return createHmac("sha256", secret()).update("session-valide").digest("hex");
}

export async function routesAuth(app: FastifyInstance): Promise<void> {
  // Connexion : vérifie le mot de passe partagé
  app.post("/api/session", async (req, rep) => {
    const { motDePasse } = req.body as { motDePasse: string };
    const attendu = Buffer.from(empreinteCourant());
    const recu = Buffer.from(empreinte(motDePasse));
    if (recu.length !== attendu.length || !timingSafeEqual(recu, attendu)) {
      return rep.code(401).send({ erreur: "Mot de passe incorrect" });
    }
    rep.setCookie(NOM_COOKIE, jeton(), {
      path: "/", httpOnly: true, sameSite: "lax", maxAge: 30 * 24 * 3600,
    });
    return { ok: true };
  });

  // Déconnexion
  app.delete("/api/session", async (_req, rep) => {
    rep.clearCookie(NOM_COOKIE, { path: "/" });
    return { ok: true };
  });

  app.get("/api/session", async (req) => ({ connecte: cookieValide(req.cookies[NOM_COOKIE]) }));

  // Changement de mot de passe (nécessite une session active)
  app.put("/api/session/mot-de-passe", { preHandler: protege }, async (req) => {
    const { nouveau, ancien } = req.body as { nouveau: string; ancien: string };
    const a = Buffer.from(empreinteCourant());
    const r = Buffer.from(empreinte(ancien));
    if (r.length !== a.length || !timingSafeEqual(r, a)) {
      return { erreur: "Ancien mot de passe incorrect" };
    }
    db.prepare("UPDATE parametres SET valeur = ? WHERE cle = 'mot_de_passe_hash'").run(empreinte(nouveau));
    return { ok: true };
  });
}

/** Hook Fastify : refuse les requêtes sans session valide. */
export function protege(req: FastifyRequest, rep: FastifyReply, done: () => void): void {
  if (cookieValide(req.cookies[NOM_COOKIE])) return done();
  rep.code(401).send({ erreur: "Non authentifié" });
}
