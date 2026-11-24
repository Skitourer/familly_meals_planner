// Client HTTP de l'API. En cas de session expirée (401), on renvoie vers la connexion.

import { goto } from '$app/navigation';

export class ErreurApi extends Error {
	constructor(
		public statut: number,
		message: string
	) {
		super(message);
	}
}

async function requete<T>(methode: string, chemin: string, corps?: unknown): Promise<T> {
	const options: RequestInit = { method: methode, credentials: 'same-origin', headers: {} };
	if (corps instanceof FormData) {
		options.body = corps;
	} else if (corps !== undefined) {
		options.body = JSON.stringify(corps);
		options.headers = { 'Content-Type': 'application/json' };
	}
	const reponse = await fetch(`/api${chemin}`, options);
	if (reponse.status === 401 && !chemin.startsWith('/session')) {
		await goto('/connexion');
		throw new ErreurApi(401, 'Connexion requise');
	}
	if (!reponse.ok) {
		let message = `Erreur ${reponse.status}`;
		try {
			const detail = (await reponse.json()).detail;
			message = typeof detail === 'string' ? detail : JSON.stringify(detail);
		} catch {
			/* réponse sans JSON */
		}
		throw new ErreurApi(reponse.status, message);
	}
	return reponse.status === 204 ? (undefined as T) : ((await reponse.json()) as T);
}

export const api = {
	lire: <T>(chemin: string) => requete<T>('GET', chemin),
	creer: <T>(chemin: string, corps?: unknown) => requete<T>('POST', chemin, corps),
	modifier: <T>(chemin: string, corps: unknown) => requete<T>('PUT', chemin, corps),
	supprimer: (chemin: string) => requete<void>('DELETE', chemin)
};

/** Message lisible pour une erreur quelconque. */
export function messageErreur(erreur: unknown): string {
	return erreur instanceof Error ? erreur.message : String(erreur);
}
