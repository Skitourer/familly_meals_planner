import { describe, expect, it } from 'vitest';
import { articleCorrespondant, groupesDeChoix, prixPropose } from './achats';
import type { Ingredient, LigneCourses, ProduitScanne } from './types';

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

function ingredient(id: string, basique = false): Ingredient {
	return { id, nom: id, rayon: 'epicerie-salee', unite: 'g', conservation_jours: 365, basique };
}

const produit: ProduitScanne = {
	code: '3000000000007',
	nom: 'Penne complètes',
	marque: 'Marque Exemple',
	quantite_g: 1000,
	propositions: [
		{
			ingredient_id: 'pates-completes',
			nom: 'Pâtes complètes',
			quantite_g: 1000,
			prix_estime_eur: 2.6
		},
		{ ingredient_id: 'pates', nom: 'Pâtes sèches', quantite_g: 1000, prix_estime_eur: 1.8 }
	],
	dernier_prix_eur: null
};

describe('achats', () => {
	it('choisit la proposition présente sur la liste, sinon la plus précise', () => {
		expect(articleCorrespondant(produit, [ligne('riz'), ligne('pates')])).toBe('pates');
		expect(articleCorrespondant(produit, [ligne('riz')])).toBe('pates-completes');
		expect(articleCorrespondant({ ...produit, propositions: [] }, [ligne('riz')])).toBe('');
	});

	it('range les choix : liste, hors liste, autres ingrédients suivis', () => {
		const groupes = groupesDeChoix(
			produit,
			[ligne('pates')],
			[
				ingredient('pates'),
				ingredient('pates-completes'),
				ingredient('riz'),
				ingredient('sel', true)
			]
		);
		expect(groupes.surLaListe.map((l) => l.ingredient_id)).toEqual(['pates']);
		expect(groupes.horsListe.map((p) => p.id)).toEqual(['pates-completes']);
		expect(groupes.autres.map((i) => i.id)).toEqual(['riz']);
	});

	it('propose le dernier prix payé, sinon l’estimation de la liste, sinon le prix au kg', () => {
		const lignes = [ligne('pates', 0.9, 500)];
		expect(prixPropose({ ...produit, dernier_prix_eur: 2.15 }, 'pates', lignes, 1000)).toBe(2.15);
		expect(prixPropose(produit, 'pates', lignes, 1000)).toBe(1.8);
		expect(prixPropose(produit, 'pates-completes', lignes, 1000)).toBe(2.6);
		expect(prixPropose(produit, 'riz', lignes, 1000)).toBe(0);
	});
});
