// Achats réels au magasin : rapprochement d'un produit scanné avec la liste de courses.

import type { LigneCourses, ProduitScanne } from './types';

/** Article de la liste qui correspond le mieux au produit, ou '' si aucun. */
export function articleCorrespondant(produit: ProduitScanne, lignes: LigneCourses[]): string {
	const surLaListe = new Set(lignes.map((l) => l.ingredient_id));
	return produit.propositions.find((p) => surLaListe.has(p.ingredient_id))?.ingredient_id ?? '';
}

/**
 * Prix proposé : le dernier prix payé pour ce produit, sinon l'estimation de la liste
 * (prix médian Open Prices) ramenée à la quantité achetée.
 */
export function prixPropose(
	produit: ProduitScanne,
	ligne: LigneCourses | undefined,
	quantiteG: number
): number {
	if (produit.dernier_prix_eur !== null) return produit.dernier_prix_eur;
	if (!ligne || ligne.achete_g <= 0) return 0;
	return Math.round((ligne.prix_eur * quantiteG * 100) / ligne.achete_g) / 100;
}
