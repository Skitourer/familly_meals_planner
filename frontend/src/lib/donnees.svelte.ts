// Données partagées entre les pages (membres, recettes), chargées une fois puis mises en cache.

import { api } from './api';
import type { FicheRecette, Membre } from './types';

class DonneesPartagees {
	membres = $state<Membre[]>([]);
	recettes = $state<FicheRecette[]>([]);

	/** Recettes indexées par identifiant. */
	parId = $derived(new Map(this.recettes.map((f) => [f.recette.id, f])));
	membresActifs = $derived(this.membres.filter((m) => m.actif));

	async chargerMembres() {
		this.membres = await api.lire<Membre[]>('/membres');
	}

	async chargerRecettes() {
		this.recettes = await api.lire<FicheRecette[]>('/recettes');
	}

	async charger(force = false) {
		const attentes = [];
		if (force || !this.membres.length) attentes.push(this.chargerMembres());
		if (force || !this.recettes.length) attentes.push(this.chargerRecettes());
		await Promise.all(attentes);
	}

	nomRecette(id: string | null): string {
		return (id && this.parId.get(id)?.recette.nom) || '—';
	}

	membre(id: number): Membre | undefined {
		return this.membres.find((m) => m.id === id);
	}
}

export const donnees = new DonneesPartagees();
