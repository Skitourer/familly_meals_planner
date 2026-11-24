// Semaine affichée : lue dans l'URL (?lundi=AAAA-MM-JJ), sinon semaine par défaut.

import { semaineParDefaut } from './dates';

export function lundiDepuisUrl(url: { searchParams: { get(nom: string): string | null } }): string {
	const valeur = url.searchParams.get('lundi');
	return valeur && /^\d{4}-\d{2}-\d{2}$/.test(valeur) ? valeur : semaineParDefaut();
}
