// Manipulation des semaines (du lundi au dimanche), sans dépendance externe.

export const JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
const MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.',
	'nov.', 'déc.']; // prettier-ignore

/** Date au format AAAA-MM-JJ (heure locale). */
export function iso(date: Date): string {
	const mm = String(date.getMonth() + 1).padStart(2, '0');
	const jj = String(date.getDate()).padStart(2, '0');
	return `${date.getFullYear()}-${mm}-${jj}`;
}

export function depuisIso(texte: string): Date {
	const [a, m, j] = texte.split('-').map(Number);
	return new Date(a, m - 1, j);
}

export function ajouterJours(date: Date, jours: number): Date {
	const resultat = new Date(date);
	resultat.setDate(resultat.getDate() + jours);
	return resultat;
}

export function lundiDe(date: Date): Date {
	const decalage = (date.getDay() + 6) % 7; // lundi = 0
	return ajouterJours(new Date(date.getFullYear(), date.getMonth(), date.getDate()), -decalage);
}

/**
 * Semaine à planifier par défaut : à partir du vendredi, on prépare la semaine suivante
 * (scénario du vendredi soir) ; sinon, la semaine en cours.
 */
export function semaineParDefaut(aujourdhui = new Date()): string {
	const lundi = lundiDe(aujourdhui);
	const jour = (aujourdhui.getDay() + 6) % 7;
	return iso(jour >= 4 ? ajouterJours(lundi, 7) : lundi);
}

export function dateCourte(date: Date): string {
	return `${date.getDate()} ${MOIS[date.getMonth()]}`;
}

export function libelleSemaine(lundiIso: string): string {
	const lundi = depuisIso(lundiIso);
	return `du ${dateCourte(lundi)} au ${dateCourte(ajouterJours(lundi, 6))}`;
}
