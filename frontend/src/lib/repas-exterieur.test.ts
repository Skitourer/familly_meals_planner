import { describe, expect, it } from 'vitest';
import { categorieSuivante, descriptionExterieur } from './repas-exterieur.ts';

describe('categorieSuivante', () => {
	it('parcourt les catégories puis revient à « inconnu »', () => {
		expect(categorieSuivante(null)).toBe('poisson');
		expect(categorieSuivante('poisson')).toBe('viande');
		expect(categorieSuivante('viande')).toBe('vegetarien');
		expect(categorieSuivante('vegetarien')).toBeNull();
	});
});

describe('descriptionExterieur', () => {
	it('nomme la catégorie ou signale un repas inconnu', () => {
		expect(descriptionExterieur('Léo', 'vegetarien')).toBe('Léo mange dehors : végétarien');
		expect(descriptionExterieur('Léo', null)).toContain('inconnu');
	});
});
