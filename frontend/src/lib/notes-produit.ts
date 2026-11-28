// Pastilles Nutri-Score, NOVA et Green-Score d'un produit du placard (#49).
import type { Note } from '#lib/types.ts';

export interface NotesProduit {
	nutriscore: Note | null;
	nova: number | null;
	green_score: Note | null;
	nutriscore_calcule?: boolean; // calculé depuis CIQUAL (aucun produit scanné)
}

export interface PastilleNote {
	libelle: string;
	valeur: string; // lettre, chiffre, ou « ? » si inconnue
	fond: string;
	texte: string;
	detail: string;
}

const INCONNU = { fond: '#d9d4cc', texte: '#3d3a35' };

// Couleurs des échelles officielles (Santé publique France, Open Food Facts).
const COULEURS_LETTRES: Record<Note, string> = {
	a: '#038141',
	b: '#85bb2f',
	c: '#fecb02',
	d: '#ee8100',
	e: '#e63e11'
};
const COULEURS_NOVA = ['#038141', '#fecb02', '#ee8100', '#e63e11'];

const SENS_NOVA = [
	'aliment pas ou peu transformé',
	'ingrédient culinaire transformé',
	'aliment transformé',
	'aliment ultra-transformé'
];

function pastilleLettre(libelle: string, note: Note | null, detail: string): PastilleNote {
	if (!note) return { libelle, valeur: '?', ...INCONNU, detail: `${libelle} inconnu` };
	return {
		libelle,
		valeur: note.toUpperCase(),
		fond: COULEURS_LETTRES[note],
		texte: note === 'c' ? '#3a2f00' : '#ffffff',
		detail: `${libelle} ${note.toUpperCase()}${detail}`
	};
}

/** Les trois pastilles d'un produit, dans l'ordre Nutri-Score, NOVA, Green-Score. */
export function pastillesNotes(notes: NotesProduit): PastilleNote[] {
	const origine = notes.nutriscore_calcule
		? ' (calculé pour l’ingrédient brut, sans produit scanné)'
		: '';
	const nova: PastilleNote =
		notes.nova && notes.nova >= 1 && notes.nova <= 4
			? {
					libelle: 'NOVA',
					valeur: String(notes.nova),
					fond: COULEURS_NOVA[notes.nova - 1],
					texte: notes.nova === 2 ? '#3a2f00' : '#ffffff',
					detail: `NOVA ${notes.nova} : ${SENS_NOVA[notes.nova - 1]}`
				}
			: { libelle: 'NOVA', valeur: '?', ...INCONNU, detail: 'NOVA inconnu' };
	return [
		pastilleLettre('Nutri-Score', notes.nutriscore, origine),
		nova,
		pastilleLettre('Green-Score', notes.green_score, ' : impact environnemental')
	];
}
