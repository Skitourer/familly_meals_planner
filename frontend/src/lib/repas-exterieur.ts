// Catégorie du repas pris dehors par un membre absent d'un créneau (cantine...) (#14).

export type CategorieExterieur = 'poisson' | 'viande' | 'vegetarien';

export interface RepasExterieur {
	membre_id: number;
	categorie: CategorieExterieur;
}

/** Ordre du cycle au clic ; null = inconnu (supposé équilibré). */
const CYCLE: (CategorieExterieur | null)[] = [null, 'poisson', 'viande', 'vegetarien'];

export const ICONES: Record<CategorieExterieur, string> = {
	poisson: '🐟',
	viande: '🍖',
	vegetarien: '🥕'
};

export const LIBELLES: Record<CategorieExterieur, string> = {
	poisson: 'poisson',
	viande: 'viande',
	vegetarien: 'végétarien'
};

/** Catégorie suivante au clic : inconnu → poisson → viande → végétarien → inconnu. */
export function categorieSuivante(actuelle: CategorieExterieur | null): CategorieExterieur | null {
	return CYCLE[(CYCLE.indexOf(actuelle) + 1) % CYCLE.length];
}

/** Texte d'aide d'un membre absent. */
export function descriptionExterieur(prenom: string, categorie: CategorieExterieur | null): string {
	const repas = categorie ? LIBELLES[categorie] : 'repas inconnu (supposé équilibré)';
	return `${prenom} mange dehors : ${repas}`;
}
