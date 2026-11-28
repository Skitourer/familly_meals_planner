// Affichage du placard : recherche, filtre « à vider », tri et regroupement par rayon.
// Les choix de tri et de regroupement sont gardés sur l'appareil (pas sur le serveur : ce sont
// des préférences d'affichage, différentes d'un téléphone à un ordinateur).
// Aussi : valeurs du formulaire d'un article, commun au scan et à la modification.

import { AUTRE_PRODUIT } from './achats';
import type { ProduitPlacard, Stock } from './types';

/** Ce que la recherche, le filtre et le tri ont besoin de connaître d'un article. */
export interface ArticlePlacard {
	nom: string;
	quantite: number; // grammes pour un ingrédient, paquets pour un autre produit
	peremption: string | null; // ISO, comparable comme texte
	bientot_perime: boolean;
}

export type Tri = 'peremption' | 'nom' | 'quantite';

export interface ChoixAffichage {
	tri: Tri;
	parRayon: boolean;
}

export const CHOIX_PAR_DEFAUT: ChoixAffichage = { tri: 'peremption', parRayon: false };
export const CLE_CHOIX = 'placard-affichage';

const TRIS: readonly Tri[] = ['peremption', 'nom', 'quantite'];

/** Texte sans accents ni majuscules : « Crème » et « creme » se rejoignent. */
export function normaliser(texte: string): string {
	return texte
		.normalize('NFD')
		.replace(/\p{Diacritic}/gu, '')
		.toLocaleLowerCase('fr')
		.trim();
}

export function correspond(nom: string, recherche: string): boolean {
	return normaliser(nom).includes(normaliser(recherche));
}

const comparerNoms = (a: string, b: string) => a.localeCompare(b, 'fr', { sensitivity: 'base' });

/** Ordre d'affichage ; à égalité, par nom. Sans date limite, en dernier. */
function comparer<T extends ArticlePlacard>(tri: Tri): (a: T, b: T) => number {
	return (a, b) => {
		let ecart = 0;
		if (tri === 'quantite') ecart = a.quantite - b.quantite;
		else if (tri === 'peremption' && a.peremption !== b.peremption) {
			if (a.peremption === null) ecart = 1;
			else if (b.peremption === null) ecart = -1;
			else ecart = a.peremption < b.peremption ? -1 : 1;
		}
		return ecart || comparerNoms(a.nom, b.nom);
	};
}

/** Articles qui correspondent à la recherche (et à vider si demandé), dans l'ordre du tri. */
export function articlesAffiches<T extends ArticlePlacard>(
	articles: readonly T[],
	recherche: string,
	aViderSeulement: boolean,
	tri: Tri
): T[] {
	return articles
		.filter((a) => correspond(a.nom, recherche) && (!aViderSeulement || a.bientot_perime))
		.sort(comparer(tri));
}

/** Groupes par rayon, dans l'ordre du parcours du magasin (celui de la liste de courses). */
export function parRayon<T extends { rayon: string; rang_rayon: number }>(
	articles: readonly T[]
): [string, T[]][] {
	const groupes = new Map<string, { rang: number; articles: T[] }>();
	for (const article of articles) {
		const groupe = groupes.get(article.rayon) ?? { rang: article.rang_rayon, articles: [] };
		groupe.articles.push(article);
		groupes.set(article.rayon, groupe);
	}
	return [...groupes]
		.sort(([, a], [, b]) => a.rang - b.rang)
		.map(([rayon, groupe]) => [rayon, groupe.articles]);
}

export function lireChoix(stockage: Storage): ChoixAffichage {
	try {
		const lu = JSON.parse(stockage.getItem(CLE_CHOIX) ?? '{}') as Partial<ChoixAffichage>;
		return {
			tri: TRIS.includes(lu.tri as Tri) ? (lu.tri as Tri) : CHOIX_PAR_DEFAUT.tri,
			parRayon: typeof lu.parRayon === 'boolean' ? lu.parRayon : CHOIX_PAR_DEFAUT.parRayon
		};
	} catch {
		return CHOIX_PAR_DEFAUT; // stockage indisponible (navigation privée) ou illisible
	}
}

export function ecrireChoix(stockage: Storage, choix: ChoixAffichage): void {
	try {
		stockage.setItem(CLE_CHOIX, JSON.stringify(choix));
	} catch {
		// Stockage plein ou interdit : le choix vaut pour cette visite seulement.
	}
}

// --- Formulaire d'un article (scan et modification) ---------------------------------------

/** Champs du formulaire : ingrédient (en grammes) ou autre produit (en paquets). */
export interface ValeursArticle {
	ingredient_id: string; // AUTRE_PRODUIT pour un produit hors repas, '' tant que rien n'est choisi
	quantite_g: number;
	nom: string;
	categorie: string;
	paquets: number;
	peremption: string; // ISO, '' sans date
}

/** Article à corriger : un ingrédient du placard ou un autre produit. */
export type SourceArticle = { ingredient_id: string } | { produit_id: number };

const CATEGORIE_PAR_DEFAUT = 'Épicerie';

export function valeursDuStock(stock: Stock): ValeursArticle {
	return {
		ingredient_id: stock.ingredient_id,
		quantite_g: stock.quantite_g,
		nom: stock.nom, // proposé si l'ingrédient devient un autre produit
		categorie: CATEGORIE_PAR_DEFAUT,
		paquets: 1,
		peremption: stock.peremption
	};
}

export function valeursDuProduit(produit: ProduitPlacard): ValeursArticle {
	return {
		ingredient_id: AUTRE_PRODUIT,
		quantite_g: 100,
		nom: produit.nom,
		categorie: produit.categorie,
		paquets: produit.paquets,
		peremption: produit.peremption ?? ''
	};
}

export function articleValide(valeurs: ValeursArticle): boolean {
	if (!valeurs.ingredient_id) return false;
	if (valeurs.ingredient_id === AUTRE_PRODUIT)
		return valeurs.nom.trim() !== '' && valeurs.paquets >= 1 && valeurs.paquets <= 99;
	return valeurs.quantite_g > 0;
}

/** Corps de la requête de modification (POST /placard/modification). */
export function corpsModification(source: SourceArticle, valeurs: ValeursArticle) {
	const peremption = valeurs.peremption || null;
	const cible =
		valeurs.ingredient_id === AUTRE_PRODUIT
			? {
					type: 'produit' as const,
					nom: valeurs.nom.trim(),
					categorie: valeurs.categorie,
					paquets: valeurs.paquets,
					peremption
				}
			: {
					type: 'ingredient' as const,
					ingredient_id: valeurs.ingredient_id,
					quantite_g: valeurs.quantite_g,
					peremption
				};
	return { ...source, cible };
}
