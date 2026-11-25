import { describe, expect, it } from 'vitest';
import { articleCorrespondant, prixPropose } from './achats';
import type { LigneCourses, ProduitScanne } from './types';

function ligne(ingredient_id: string, prix_eur = 0.9, achete_g = 500): LigneCourses {
	return {
		ingredient_id,
		nom: ingredient_id,
		achat: '1 × 500 g',
		besoin: '350 g',
		depuis_placard: null,
		surplus: '150 g',
		surplus_au_placard: true,
		prix_eur,
		achete_g,
		achat_reel: null,
		prix_reel_eur: null
	};
}

const produit: ProduitScanne = {
	code: '3000000000007',
	nom: 'Penne complètes',
	marque: 'Marque Exemple',
	quantite_g: 1000,
	propositions: [
		{ ingredient_id: 'pates-completes', nom: 'Pâtes complètes', quantite_g: 1000 },
		{ ingredient_id: 'pates', nom: 'Pâtes sèches', quantite_g: 1000 }
	],
	dernier_prix_eur: null
};

describe('achats', () => {
	it('choisit la proposition la plus précise présente sur la liste', () => {
		expect(articleCorrespondant(produit, [ligne('riz'), ligne('pates')])).toBe('pates');
		expect(articleCorrespondant(produit, [ligne('riz')])).toBe('');
	});

	it('propose le dernier prix payé, sinon l’estimation à la quantité achetée', () => {
		expect(prixPropose({ ...produit, dernier_prix_eur: 2.15 }, ligne('pates'), 1000)).toBe(2.15);
		expect(prixPropose(produit, ligne('pates', 0.9, 500), 1000)).toBe(1.8);
		expect(prixPropose(produit, undefined, 1000)).toBe(0);
		expect(prixPropose(produit, ligne('pates', 0.9, 0), 1000)).toBe(0);
	});
});
