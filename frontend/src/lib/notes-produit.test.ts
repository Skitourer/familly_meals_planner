import { describe, expect, it } from 'vitest';
import { pastillesNotes } from './notes-produit.ts';

describe('pastillesNotes', () => {
	it('affiche les trois notes connues', () => {
		const [nutri, nova, green] = pastillesNotes({ nutriscore: 'c', nova: 4, green_score: 'a' });
		expect([nutri.valeur, nova.valeur, green.valeur]).toEqual(['C', '4', 'A']);
		expect(nutri.texte).toBe('#3a2f00'); // lettre foncée sur le jaune
		expect(nova.detail).toBe('NOVA 4 : aliment ultra-transformé');
		expect(green.detail).toBe('Green-Score A : impact environnemental');
	});

	it('affiche « ? » pour les notes inconnues', () => {
		const pastilles = pastillesNotes({ nutriscore: null, nova: null, green_score: null });
		expect(pastilles.map((p) => p.valeur)).toEqual(['?', '?', '?']);
		expect(pastilles[1].detail).toBe('NOVA inconnu');
	});

	it('signale un Nutri-Score calculé sans produit scanné', () => {
		const [nutri] = pastillesNotes({
			nutriscore: 'a',
			nova: null,
			green_score: null,
			nutriscore_calcule: true
		});
		expect(nutri.detail).toContain('ingrédient brut');
	});

	it('ignore un groupe NOVA hors échelle', () => {
		expect(pastillesNotes({ nutriscore: null, nova: 7, green_score: null })[1].valeur).toBe('?');
	});
});
