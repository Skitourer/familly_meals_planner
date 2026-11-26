import { describe, expect, it } from 'vitest';
import {
	CHOIX_PAR_DEFAUT,
	CLE_CHOIX,
	articlesAffiches,
	correspond,
	ecrireChoix,
	lireChoix,
	parRayon
} from './placard';

const creme = {
	nom: 'Crème fraîche légère',
	quantite: 200,
	peremption: '2026-12-02',
	bientot_perime: true,
	rayon: 'Crèmerie, œufs, fromages',
	rang_rayon: 4
};
const riz = {
	nom: 'Riz',
	quantite: 400,
	peremption: '2027-06-01',
	bientot_perime: false,
	rayon: 'Épicerie salée',
	rang_rayon: 5
};
const pommes = {
	nom: 'Pommes',
	quantite: 1000,
	peremption: '2026-12-10',
	bientot_perime: false,
	rayon: 'Fruits et légumes',
	rang_rayon: 0
};
const biscuits = { ...riz, nom: 'biscuits', quantite: 2, peremption: null };

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

describe('recherche', () => {
	it('ignore les accents et la casse', () => {
		expect(correspond('Crème fraîche légère', 'creme')).toBe(true);
		expect(correspond('Crème fraîche légère', 'FRAICHE')).toBe(true);
		expect(correspond('Riz', 'creme')).toBe(false);
	});

	it('une recherche vide garde tout', () => {
		expect(articlesAffiches([riz, creme], '  ', false, 'nom')).toHaveLength(2);
	});
});

describe('tri et filtre', () => {
	const tous = [riz, pommes, creme, biscuits];
	const noms = (liste: { nom: string }[]) => liste.map((a) => a.nom);

	it('par date limite, les produits sans date en dernier', () => {
		expect(noms(articlesAffiches(tous, '', false, 'peremption'))).toEqual([
			'Crème fraîche légère',
			'Pommes',
			'Riz',
			'biscuits'
		]);
	});

	it('par nom, sans tenir compte des majuscules', () => {
		expect(noms(articlesAffiches(tous, '', false, 'nom'))).toEqual([
			'biscuits',
			'Crème fraîche légère',
			'Pommes',
			'Riz'
		]);
	});

	it('par quantité croissante', () => {
		expect(noms(articlesAffiches(tous, '', false, 'quantite'))).toEqual([
			'biscuits',
			'Crème fraîche légère',
			'Riz',
			'Pommes'
		]);
	});

	it('à égalité, par nom', () => {
		const autreRiz = { ...riz, nom: 'Pâtes' };
		expect(noms(articlesAffiches([riz, autreRiz], '', false, 'quantite'))).toEqual([
			'Pâtes',
			'Riz'
		]);
	});

	it('le filtre « à vider » se combine à la recherche', () => {
		expect(noms(articlesAffiches(tous, 'creme', true, 'nom'))).toEqual(['Crème fraîche légère']);
		expect(articlesAffiches(tous, 'riz', true, 'nom')).toEqual([]);
	});

	it('ne modifie pas la liste reçue', () => {
		const liste = [riz, creme];
		articlesAffiches(liste, '', false, 'nom');
		expect(liste).toEqual([riz, creme]);
	});
});

describe('regroupement par rayon', () => {
	it("suit l'ordre des rayons de la liste de courses, en gardant l'ordre du tri", () => {
		const groupes = parRayon([riz, creme, biscuits, pommes]);
		expect(groupes.map(([rayon]) => rayon)).toEqual([
			'Fruits et légumes',
			'Crèmerie, œufs, fromages',
			'Épicerie salée'
		]);
		expect(groupes[2]?.[1]).toEqual([riz, biscuits]);
	});
});

describe('choix mémorisés', () => {
	it("sont retrouvés d'une visite à l'autre", () => {
		const stockage = stockageMemoire();
		ecrireChoix(stockage, { tri: 'nom', parRayon: true });
		expect(lireChoix(stockage)).toEqual({ tri: 'nom', parRayon: true });
	});

	it('par défaut sans choix, ou avec un choix illisible', () => {
		expect(lireChoix(stockageMemoire())).toEqual(CHOIX_PAR_DEFAUT);
		expect(lireChoix(stockageMemoire({ [CLE_CHOIX]: '{' }))).toEqual(CHOIX_PAR_DEFAUT);
		expect(lireChoix(stockageMemoire({ [CLE_CHOIX]: '{"tri":"prix","parRayon":1}' }))).toEqual(
			CHOIX_PAR_DEFAUT
		);
	});

	it('un stockage interdit ne bloque pas la page', () => {
		const interdit = {
			...stockageMemoire(),
			getItem: () => {
				throw new Error('interdit');
			},
			setItem: () => {
				throw new Error('plein');
			}
		};
		expect(lireChoix(interdit)).toEqual(CHOIX_PAR_DEFAUT);
		expect(() => ecrireChoix(interdit, CHOIX_PAR_DEFAUT)).not.toThrow();
	});
});
