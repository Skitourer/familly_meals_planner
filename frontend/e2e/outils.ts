// Outils communs aux parcours : date figée, réseau externe bloqué, connexion.
import { expect, type Page } from '@playwright/test';

export const MOT_DE_PASSE = 'mot-de-passe-e2e';

/** Fige l'horloge du navigateur (semaine affichée stable) et bloque tout site externe. */
export async function preparer(page: Page, date: string): Promise<void> {
	await page.clock.setFixedTime(new Date(`${date}T10:00:00`));
	await page.route(
		(url) => url.hostname !== '127.0.0.1',
		(route) => route.abort()
	);
}

export async function seConnecter(page: Page): Promise<void> {
	await page.goto('/connexion');
	await page.getByRole('textbox').first().fill('famille');
	await page.locator('input[type=password]').fill(MOT_DE_PASSE);
	await page.getByRole('button', { name: 'Entrer' }).click();
	await expect(page).not.toHaveURL(/connexion/);
}

/** Ajoute un membre par l'API (même session que la page). */
export async function ajouterMembre(page: Page, prenom: string): Promise<void> {
	const reponse = await page.request.post('/api/membres', {
		headers: { 'X-Menu-Famille': '1' },
		data: {
			prenom,
			date_naissance: '1985-04-12',
			sexe: 'F',
			poids_kg: 62,
			mode_de_vie: 'actif',
			heures_sport_semaine: 2
		}
	});
	expect(reponse.ok()).toBeTruthy();
}
