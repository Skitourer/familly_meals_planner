// Achats réels au magasin : rapprochement d'un produit scanné avec la liste de courses.

import type { Ingredient, LigneCourses, ProduitScanne } from './types';

/** Choix « Autre achat » : compté dans le budget, sans ingrédient ni placard. */
export const AUTRE_ACHAT = 'autre-achat';

/** Article de la liste qui correspond le mieux au produit, sinon l'ingrédient proposé, sinon ''. */
export function articleCorrespondant(produit: ProduitScanne, lignes: LigneCourses[]): string {
	const surLaListe = new Set(lignes.map((l) => l.ingredient_id));
	const prevu = produit.propositions.find((p) => surLaListe.has(p.ingredient_id));
	return (prevu ?? produit.propositions[0])?.ingredient_id ?? '';
}

/** Choix proposés : articles de la liste, correspondances hors liste, autres ingrédients suivis. */
export function groupesDeChoix(
	produit: ProduitScanne,
	lignes: LigneCourses[],
	ingredients: Ingredient[]
): { surLaListe: LigneCourses[]; horsListe: { id: string; nom: string }[]; autres: Ingredient[] } {
	const prevus = new Set(lignes.map((l) => l.ingredient_id));
	const horsListe = produit.propositions
		.filter((p) => !prevus.has(p.ingredient_id))
		.map((p) => ({ id: p.ingredient_id, nom: p.nom }));
	const dejaProposes = new Set([...prevus, ...horsListe.map((p) => p.id)]);
	return {
		surLaListe: lignes,
		horsListe,
		autres: ingredients.filter((i) => !i.basique && !dejaProposes.has(i.id))
	};
}

/**
 * Prix proposé : le dernier prix payé pour ce produit, sinon l'estimation de la liste ramenée
 * à la quantité achetée, sinon le prix médian au kg de l'ingrédient (Open Prices).
 */
export function prixPropose(
	produit: ProduitScanne,
	ingredientId: string,
	lignes: LigneCourses[],
	quantiteG: number
): number {
	if (produit.dernier_prix_eur !== null) return produit.dernier_prix_eur;
	const ligne = lignes.find((l) => l.ingredient_id === ingredientId);
	if (ligne && ligne.achete_g > 0) {
		return Math.round((ligne.prix_eur * quantiteG * 100) / ligne.achete_g) / 100;
	}
	const proposition = produit.propositions.find((p) => p.ingredient_id === ingredientId);
	return proposition?.prix_estime_eur ?? 0;
}
