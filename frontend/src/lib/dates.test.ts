import { describe, expect, it } from 'vitest';
import {
	ajouterJours,
	iso,
	libelleSemaine,
	lundiDe,
	lundiSuivant,
	semaineParDefaut
} from './dates';

describe('semaines', () => {
	it('trouve le lundi de la semaine', () => {
		expect(iso(lundiDe(new Date(2026, 10, 26)))).toBe('2026-11-23'); // jeudi
		expect(iso(lundiDe(new Date(2026, 10, 29)))).toBe('2026-11-23'); // dimanche
		expect(iso(lundiDe(new Date(2026, 10, 23)))).toBe('2026-11-23'); // lundi
	});

	it('propose la semaine suivante à partir du vendredi', () => {
		expect(semaineParDefaut(new Date(2026, 10, 25))).toBe('2026-11-23'); // mercredi
		expect(semaineParDefaut(new Date(2026, 10, 27))).toBe('2026-11-30'); // vendredi
		expect(semaineParDefaut(new Date(2026, 10, 29))).toBe('2026-11-30'); // dimanche
	});

	it('change de mois correctement', () => {
		expect(iso(ajouterJours(new Date(2026, 10, 30), 2))).toBe('2026-12-02');
		expect(libelleSemaine('2026-11-30')).toBe('du 30 nov. au 6 déc.');
	});
});

describe('semaine suivante', () => {
	it('même le dimanche, le lundi qui vient', () => {
		expect(lundiSuivant(new Date(2026, 10, 26))).toBe('2026-11-30'); // jeudi
		expect(lundiSuivant(new Date(2026, 10, 29))).toBe('2026-11-30'); // dimanche
		expect(lundiSuivant(new Date(2026, 10, 30))).toBe('2026-12-07'); // lundi
	});
});
