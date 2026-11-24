// Règles du service worker (src/service-worker) : ce qui est gardé sur l'appareil pour que
// la liste de courses s'ouvre au magasin sans réseau. Voir docs/adr/0006-hors-ligne.md.

/** Données de l'API gardées pour le hors-ligne ; vidé à la déconnexion. */
export const CACHE_DONNEES = 'menu-famille-donnees';

const PREFIXE_CACHE_APPLICATION = 'menu-famille-application-';

/** Page d'accueil gardée en cache : l'application monopage sert la même pour toutes les routes. */
export const PAGE_APPLICATION = '/';

/** Fichiers de l'application (code compilé, icônes) d'une version donnée. */
export function nomCacheApplication(version: string): string {
	return PREFIXE_CACHE_APPLICATION + version;
}

/** Caches d'une ancienne version de l'application, à supprimer à l'activation. */
export function cachesPerimes(noms: string[], version: string): string[] {
	return noms.filter(
		(nom) => nom.startsWith(PREFIXE_CACHE_APPLICATION) && nom !== nomCacheApplication(version)
	);
}

// Seules la session et la liste de courses servent au magasin : le reste de l'API exige le
// réseau, ce qui limite les données familiales stockées sur l'appareil.
const DONNEES_HORS_LIGNE = [/^\/api\/session$/, /^\/api\/semaines\/\d{4}-\d{2}-\d{2}\/courses$/];

export function estDonneeHorsLigne(chemin: string): boolean {
	return DONNEES_HORS_LIGNE.some((motif) => motif.test(chemin));
}

/**
 * - `application` : fichier de l'application, lu dans le cache (il ne change pas pour une version) ;
 * - `page` : navigation, réseau d'abord puis page d'accueil en cache ;
 * - `donnee` : réseau d'abord, réponse gardée, cache si le réseau manque ;
 * - `reseau` : non interceptée (écritures, PDF, autres données, autres sites).
 */
export type Strategie = 'application' | 'page' | 'donnee' | 'reseau';

export interface RequeteInterceptee {
	methode: string;
	url: URL;
	navigation: boolean;
}

export function strategie(
	requete: RequeteInterceptee,
	origine: string,
	fichiersApplication: ReadonlySet<string>
): Strategie {
	const { methode, url, navigation } = requete;
	if (methode !== 'GET' || url.origin !== origine) return 'reseau';
	if (fichiersApplication.has(url.pathname)) return 'application';
	if (url.pathname.startsWith('/api/')) {
		return estDonneeHorsLigne(url.pathname) ? 'donnee' : 'reseau';
	}
	return navigation ? 'page' : 'reseau';
}

/** Une réponse « non connecté » de la session signifie que les données gardées sont périmées. */
export function estSessionFermee(chemin: string, corps: unknown): boolean {
	return (
		chemin === '/api/session' &&
		typeof corps === 'object' &&
		corps !== null &&
		(corps as { connecte?: unknown }).connecte === false
	);
}
