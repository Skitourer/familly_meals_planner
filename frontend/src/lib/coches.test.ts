import { describe, expect, it } from 'vitest';
import {
	ajouterAFile,
	cleAncienStockage,
	cleFile,
	cochesAffichees,
	ecrireFile,
	lireFile,
	retirerEnvoyees
} from './coches';

const LUNDI = '2026-11-30';
const NEUF_HEURES = new Date('2026-12-05T09:00:00Z');
const NEUF_HEURES_UNE = new Date('2026-12-05T09:01:00Z');

/** Stockage en mémoire, avec la même interface que localStorage. */
function stockageMemoire(initial: Record<string, string> = {}): Storage {
	const donnees = new Map(Object.entries(initial));
	return {
		get length() {
			return donnees.size;
		},
		clear: () => donnees.clear(),
		getItem: (cle) => donnees.get(cle) ?? null,
		key: (index) => [...donnees.keys()][index] ?? null,
		removeItem: (cle) => void donnees.delete(cle),
		setItem: (cle, valeur) => void donnees.set(cle, valeur)
	};
}

describe('file des coches', () => {
	it("garde la dernière modification de chaque article et corrige l'état du serveur", () => {
		let file = ajouterAFile({}, 'riz', true, NEUF_HEURES);
		file = ajouterAFile(file, 'riz', false, NEUF_HEURES_UNE);
		file = ajouterAFile(file, 'lait', true, NEUF_HEURES_UNE);
		expect(Object.keys(file)).toEqual(['riz', 'lait']);
		expect([...cochesAffichees(['riz', 'pates'], file)].sort()).toEqual(['lait', 'pates']);
	});

	it("ne retire que les envois confirmés, pas un article recoché pendant l'envoi", () => {
		const envoi = ajouterAFile({}, 'riz', true, NEUF_HEURES);
		const pendant = ajouterAFile(envoi, 'riz', false, NEUF_HEURES_UNE);
		expect(retirerEnvoyees(pendant, Object.values(envoi))).toEqual(pendant);
		expect(retirerEnvoyees(envoi, Object.values(envoi))).toEqual({});
	});

	it("reprend une fois les coches de l'ancien stockage", () => {
		const stockage = stockageMemoire({ [cleAncienStockage(LUNDI)]: '["riz","pates"]' });
		const file = lireFile(stockage, LUNDI, NEUF_HEURES);
		expect(Object.values(file).map((m) => [m.ingredient_id, m.cochee])).toEqual([
			['riz', true],
			['pates', true]
		]);
		expect(stockage.getItem(cleAncienStockage(LUNDI))).toBeNull();
		expect(lireFile(stockage, LUNDI)).toEqual(file);
	});

	it('vide la clé quand la file est vide et tolère un stockage illisible', () => {
		const stockage = stockageMemoire();
		ecrireFile(stockage, LUNDI, ajouterAFile({}, 'riz', true, NEUF_HEURES));
		expect(stockage.getItem(cleFile(LUNDI))).not.toBeNull();
		ecrireFile(stockage, LUNDI, {});
		expect(stockage.getItem(cleFile(LUNDI))).toBeNull();
		expect(lireFile(stockageMemoire({ [cleFile(LUNDI)]: '{pas du json' }), LUNDI)).toEqual({});
	});
});
