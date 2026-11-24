// Compte connecté (adulte ou enfant), partagé par toutes les pages.

import { api } from './api.ts';

export interface EtatSession {
	connecte: boolean;
	identifiant: string | null;
	role: 'adulte' | 'enfant' | null;
	membre_id: number | null;
	prenom: string | null;
}

// Pages accessibles à un compte enfant (les autres sont réservées aux adultes).
const PAGES_ENFANT = ['/', '/notes', '/plats', '/compte'];

class Session {
	etat = $state<EtatSession | null>(null);

	estAdulte = $derived(this.etat?.role === 'adulte');
	estEnfant = $derived(this.etat?.role === 'enfant');

	async charger(): Promise<EtatSession> {
		this.etat = await api.lire<EtatSession>('/session');
		return this.etat;
	}

	async connecter(identifiant: string, motDePasse: string): Promise<void> {
		this.etat = await api.creer<EtatSession>('/session', {
			identifiant,
			mot_de_passe: motDePasse
		});
	}

	async deconnecter(): Promise<void> {
		await api.supprimer('/session');
		this.etat = null;
	}

	/** Le compte connecté peut-il ouvrir cette page ? */
	autorise(chemin: string): boolean {
		if (this.estAdulte) return true;
		return PAGES_ENFANT.some((p) => chemin === p || (p !== '/' && chemin.startsWith(p + '/')));
	}
}

export const session = new Session();
