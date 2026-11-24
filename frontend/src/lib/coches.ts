// Coches de la liste de courses : file d'attente locale, envoyée au serveur dès que possible.
// Au magasin sans réseau, chaque coche est gardée sur l'appareil avec son heure ; au retour de
// la connexion, le serveur applique la plus récente de chaque article (voir domaine/coches.py).

/** Un article coché ou décoché, à une heure donnée (ISO 8601 avec fuseau). */
export interface ModificationCoche {
	ingredient_id: string;
	cochee: boolean;
	modifiee_le: string;
}

/** Modifications pas encore confirmées par le serveur, une par article (la dernière). */
export type FileCoches = Record<string, ModificationCoche>;

export function cleFile(lundi: string): string {
	return `courses-file-${lundi}`;
}

/** Ancienne clé (coches gardées seulement sur l'appareil), reprise une fois puis supprimée. */
export function cleAncienStockage(lundi: string): string {
	return `courses-cochees-${lundi}`;
}

export function ajouterAFile(
	file: FileCoches,
	ingredientId: string,
	cochee: boolean,
	quand: Date
): FileCoches {
	return {
		...file,
		[ingredientId]: { ingredient_id: ingredientId, cochee, modifiee_le: quand.toISOString() }
	};
}

/** Articles affichés comme cochés : état du serveur, corrigé par la file d'attente. */
export function cochesAffichees(serveur: string[], file: FileCoches): Set<string> {
	const resultat = new Set(serveur);
	for (const modification of Object.values(file)) {
		if (modification.cochee) resultat.add(modification.ingredient_id);
		else resultat.delete(modification.ingredient_id);
	}
	return resultat;
}

/** Retire de la file ce que le serveur a confirmé, sauf les articles modifiés entre-temps. */
export function retirerEnvoyees(file: FileCoches, envoyees: ModificationCoche[]): FileCoches {
	const resultat = { ...file };
	for (const envoyee of envoyees) {
		if (resultat[envoyee.ingredient_id]?.modifiee_le === envoyee.modifiee_le) {
			delete resultat[envoyee.ingredient_id];
		}
	}
	return resultat;
}

/** Convertit les coches de l'ancien stockage en file d'attente. */
export function depuisAncienStockage(ids: string[], quand: Date): FileCoches {
	return ids.reduce<FileCoches>((file, id) => ajouterAFile(file, id, true, quand), {});
}

/** Lit la file d'attente (et reprend l'ancien stockage) ; vide si le stockage est indisponible. */
export function lireFile(stockage: Storage, lundi: string, quand = new Date()): FileCoches {
	try {
		const file = JSON.parse(stockage.getItem(cleFile(lundi)) ?? '{}') as FileCoches;
		const ancien = stockage.getItem(cleAncienStockage(lundi));
		if (ancien === null) return file;
		const reprise = { ...depuisAncienStockage(JSON.parse(ancien) as string[], quand), ...file };
		ecrireFile(stockage, lundi, reprise);
		stockage.removeItem(cleAncienStockage(lundi));
		return reprise;
	} catch {
		return {}; // stockage indisponible (navigation privée) ou illisible : file vide
	}
}

export function ecrireFile(stockage: Storage, lundi: string, file: FileCoches): void {
	try {
		if (Object.keys(file).length) stockage.setItem(cleFile(lundi), JSON.stringify(file));
		else stockage.removeItem(cleFile(lundi));
	} catch {
		/* stockage indisponible : la coche reste en mémoire jusqu'à l'envoi */
	}
}
