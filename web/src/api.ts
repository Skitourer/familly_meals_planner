/**
 * Client HTTP typé vers l'API (le proxy Vite route /api vers le serveur).
 * Gère l'erreur 401 en déclenchant l'écran de connexion.
 */
import type { Plat, Repas, Membre, NotePlat } from "@partage/types.ts";
import type { LigneCourse } from "@partage/courses.ts";

/** Erreur HTTP de l'API. `statut` vaut 401 quand la session est invalide. */
export class ErreurApi extends Error {
  statut: number;
  constructor(statut: number, message: string) {
    super(message);
    this.statut = statut;
  }
}

async function appel<T>(chemin: string, options: RequestInit = {}): Promise<T> {
  const rep = await fetch(`/api${chemin}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!rep.ok) {
    const corps = await rep.json().catch(() => ({ erreur: "Erreur serveur" })) as { erreur?: string };
    throw new ErreurApi(rep.status, corps.erreur ?? `Erreur HTTP ${rep.status}`);
  }
  return rep.json();
}

export const api = {
  /* ----- Session ----- */
  session: () => appel<{ connecte: boolean }>("/session"),
  connexion: (motDePasse: string) => appel<{ ok: boolean }>("/session", { method: "POST", body: JSON.stringify({ motDePasse }) }),
  deconnexion: () => appel<{ ok: boolean }>("/session", { method: "DELETE" }),

  /* ----- Membres ----- */
  membres: () => appel<Array<Membre & { besoinKcal: number }>>("/membres"),
  ajouterMembre: (m: Partial<Membre>) => appel<{ id: number }>("/membres", { method: "POST", body: JSON.stringify(m) }),
  majMembre: (id: number, m: Partial<Membre>) => appel<{ ok: boolean }>(`/membres/${id}`, { method: "PATCH", body: JSON.stringify(m) }),
  supprimerMembre: (id: number) => appel<{ ok: boolean }>(`/membres/${id}`, { method: "DELETE" }),

  /* ----- Plats ----- */
  plats: () => appel<Plat[]>("/plats"),
  ajouterPlat: (p: Partial<Plat>) => appel<{ id: number }>("/plats", { method: "POST", body: JSON.stringify(p) }),
  majPlat: (id: number, p: Partial<Plat>) => appel<{ ok: boolean }>(`/plats/${id}`, { method: "PATCH", body: JSON.stringify(p) }),
  supprimerPlat: (id: number) => appel<{ ok: boolean }>(`/plats/${id}`, { method: "DELETE" }),

  /* ----- Open Food Facts ----- */
  chercherProduits: (q: string) => appel<{ produits: Array<{ nom: string; marque: string; kcalPour100g: number | null; quantite: string }> }>(`/openfoodfacts?q=${encodeURIComponent(q)}`),

  /* ----- Semaine ----- */
  semaine: (id: string) => appel<{ repas: Repas[]; besoinTotal: number; besoinParRepas: number; saison: string[] }>(`/semaines/${id}`),
  enregistrerRepas: (id: string, repas: Repas[]) => appel<{ ok: boolean }>(`/semaines/${id}/repas`, { method: "PUT", body: JSON.stringify(repas) }),
  generer: (id: string) => appel<{ repas: Repas[] }>(`/semaines/${id}/generer`, { method: "POST" }),

  /* ----- Courses ----- */
  courses: (id: string) => appel<LigneCourse[]>(`/semaines/${id}/courses`),
  // Le PDF est un téléchargement direct (pas de JSON) : le navigateur gère le fichier
  urlPdf: (id: string) => `/api/semaines/${id}/courses.pdf`,

  /* ----- Notes et stats ----- */
  notes: (semaine: string) => appel<NotePlat[]>(`/notes/${semaine}`),
  noter: (n: Omit<NotePlat, "id">) => appel<{ id: number }>("/notes", { method: "POST", body: JSON.stringify(n) }),
  stats: () => appel<Array<{ id: number; nom: string; nb: number; moyenne: number }>>("/stats"),

  /* ----- Divers ----- */
  saison: (mois: number) => appel<string[]>(`/saison/${mois}`),
};
