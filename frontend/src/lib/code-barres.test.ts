import { describe, expect, it } from 'vitest';
import { codeDetecte, codePlausible, nettoyerCode } from './code-barres';

describe('code-barres', () => {
	it('nettoie une saisie manuelle', () => {
		expect(nettoyerCode(' 3 000000-000007 ')).toBe('3000000000007');
	});

	it('reconnaît les longueurs de code-barres', () => {
		expect(codePlausible('3000000000007')).toBe(true);
		expect(codePlausible('12345670')).toBe(true);
		expect(codePlausible('1234567')).toBe(false);
		expect(codePlausible('30000000000a7')).toBe(false);
		expect(codePlausible('')).toBe(false);
	});

	it('convertit un UPC-A en EAN-13 et rejette les autres lectures', () => {
		expect(codeDetecte('036000291452', 'upc_a')).toBe('0036000291452');
		expect(codeDetecte('3000000000007', 'ean_13')).toBe('3000000000007');
		expect(codeDetecte('https://exemple.fr', 'qr_code')).toBeNull();
	});
});
