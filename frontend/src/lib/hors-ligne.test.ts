import { describe, expect, it } from 'vitest';
import {
	cachesPerimes,
	estDonneeHorsLigne,
	estSessionFermee,
	nomCacheApplication,
	strategie
} from './hors-ligne';

const ORIGINE = 'https://menu.exemple.ts.net';
const FICHIERS = new Set(['/_app/immutable/entry/app.abc123.js', '/icone.svg']);

function requete(chemin: string, options: { methode?: string; navigation?: boolean } = {}) {
	return {
		methode: options.methode ?? 'GET',
		url: new URL(chemin, ORIGINE),
		navigation: options.navigation ?? false
	};
}

describe('estDonneeHorsLigne', () => {
	it('garde la session et la liste de courses', () => {
		expect(estDonneeHorsLigne('/api/session')).toBe(true);
		expect(estDonneeHorsLigne('/api/semaines/2026-11-30/courses')).toBe(true);
	});

	it('ne garde pas le reste de l’API', () => {
		expect(estDonneeHorsLigne('/api/membres')).toBe(false);
		expect(estDonneeHorsLigne('/api/semaines/2026-11-30')).toBe(false);
		expect(estDonneeHorsLigne('/api/semaines/2026-11-30/courses.pdf')).toBe(false);
		expect(estDonneeHorsLigne('/api/semaines/2026-11-30/courses/coches')).toBe(false);
	});
});

describe('strategie', () => {
	it('lit les fichiers de l’application dans le cache', () => {
		expect(strategie(requete('/_app/immutable/entry/app.abc123.js'), ORIGINE, FICHIERS)).toBe(
			'application'
		);
	});

	it('sert la page gardée pour une navigation sans réseau', () => {
		expect(strategie(requete('/courses', { navigation: true }), ORIGINE, FICHIERS)).toBe('page');
	});

	it('passe par le cache de données pour la liste de courses', () => {
		const courses = requete('/api/semaines/2026-11-30/courses');
		expect(strategie(courses, ORIGINE, FICHIERS)).toBe('donnee');
	});

	it('laisse au réseau les écritures, le PDF et les autres sites', () => {
		const coches = requete('/api/semaines/2026-11-30/courses/coches', { methode: 'PUT' });
		const pdf = requete('/api/semaines/2026-11-30/courses.pdf', { navigation: true });
		const autreSite = { ...requete('/'), url: new URL('https://prices.openfoodfacts.org/') };
		expect(strategie(coches, ORIGINE, FICHIERS)).toBe('reseau');
		expect(strategie(pdf, ORIGINE, FICHIERS)).toBe('reseau');
		expect(strategie(autreSite, ORIGINE, FICHIERS)).toBe('reseau');
		expect(strategie(requete('/api/membres'), ORIGINE, FICHIERS)).toBe('reseau');
	});
});

describe('cachesPerimes', () => {
	it('supprime les anciennes versions et garde les données', () => {
		const noms = [nomCacheApplication('1'), nomCacheApplication('2'), 'menu-famille-donnees'];
		expect(cachesPerimes(noms, '2')).toEqual([nomCacheApplication('1')]);
	});
});

describe('estSessionFermee', () => {
	it('reconnaît une session non connectée', () => {
		expect(estSessionFermee('/api/session', { connecte: false })).toBe(true);
	});

	it('ignore une session ouverte et les autres données', () => {
		expect(estSessionFermee('/api/session', { connecte: true })).toBe(false);
		expect(estSessionFermee('/api/semaines/2026-11-30/courses', { connecte: false })).toBe(false);
		expect(estSessionFermee('/api/session', null)).toBe(false);
	});
});
