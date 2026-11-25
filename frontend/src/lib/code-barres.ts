// Lecture des codes-barres des produits : saisie manuelle et détection par la caméra.

/** Formats de code-barres des produits alimentaires (API BarcodeDetector). */
export const FORMATS_PRODUITS = ['ean_13', 'ean_8', 'upc_a'];

const LONGUEURS = [8, 12, 13, 14];

/** Chiffres d'un code saisi à la main (« 3 017620 422003 » → « 3017620422003 »). */
export function nettoyerCode(saisie: string): string {
	return saisie.replace(/[\s.-]/g, '');
}

/** Vrai si la saisie ressemble à un code-barres ; la clé de contrôle est vérifiée par l'API. */
export function codePlausible(code: string): boolean {
	return /^\d+$/.test(code) && LONGUEURS.includes(code.length);
}

/**
 * Code lu par la caméra, sous la forme qu'utilise Open Food Facts (un UPC-A américain devient
 * un EAN-13 en ajoutant un 0 devant), ou null si la lecture n'est pas un code de produit.
 */
export function codeDetecte(valeur: string, format: string): string | null {
	const code = nettoyerCode(valeur);
	if (!codePlausible(code)) return null;
	return format === 'upc_a' ? `0${code}` : code;
}
