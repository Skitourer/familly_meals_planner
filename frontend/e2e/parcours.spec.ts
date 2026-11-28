// Parcours critiques de l'interface (#28) : chacun sur sa propre semaine pour rester
// indépendant des autres, avec une date figée et sans accès réseau externe.
import { expect, test } from '@playwright/test';
import { ajouterMembre, preparer, seConnecter } from './outils.ts';

test('connexion puis ajout d’un membre', async ({ page }) => {
	await preparer(page, '2026-03-04');
	await seConnecter(page);

	await page.goto('/famille');
	await page.getByRole('button', { name: /Ajouter un membre/ }).click();
	await page.getByLabel('Prénom').fill('Camille');
	await page.getByLabel('Date de naissance').fill('2015-06-20');
	await page.getByLabel('Poids (kg)').fill('35');
	await page.getByRole('button', { name: 'Enregistrer' }).click();

	await expect(page.getByText('Camille').first()).toBeVisible();
	await page.reload();
	await expect(page.getByText('Camille').first()).toBeVisible();
});

test('génération d’une semaine puis fiche d’un plat', async ({ page }) => {
	await preparer(page, '2026-05-13');
	await seConnecter(page);
	await ajouterMembre(page, 'Alex');

	await page.goto('/');
	await page.getByRole('button', { name: /Générer les repas|Autre proposition/ }).click();
	const plat = page.locator('a[href^="/plats/"]').first();
	await expect(plat).toBeVisible({ timeout: 30_000 });

	const cible = (await plat.getAttribute('href'))?.split('?')[0] ?? '';
	await plat.click();
	await expect(page).toHaveURL((url) => url.pathname === cible);
	await expect(page.getByRole('heading', { level: 1 })).not.toBeEmpty();
	await expect(page.getByText(/Ingrédients/).first()).toBeVisible();
});

test('liste de courses puis export PDF', async ({ page }) => {
	await preparer(page, '2026-09-16');
	await seConnecter(page);
	await ajouterMembre(page, 'Sam');

	await page.goto('/');
	await page.getByRole('button', { name: /Générer les repas|Autre proposition/ }).click();
	await expect(page.locator('a[href^="/plats/"]').first()).toBeVisible({ timeout: 30_000 });

	await page.getByRole('link', { name: /Liste de courses/ }).click();
	await expect(page.getByRole('heading', { name: 'Liste de courses' })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2 }).first()).toBeVisible();

	const lien = page.locator('a[href$="/courses.pdf"]');
	const pdf = await page.request.get((await lien.getAttribute('href')) ?? '');
	expect(pdf.status()).toBe(200);
	expect(pdf.headers()['content-type']).toBe('application/pdf');
	expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-');
});

test('modification d’un article du placard', async ({ page }) => {
	await preparer(page, '2026-09-16');
	await seConnecter(page);
	const reponse = await page.request.put('/api/placard/riz', {
		headers: { 'X-Menu-Famille': '1' },
		data: { quantite_g: 400 }
	});
	expect(reponse.ok()).toBeTruthy();

	await page.goto('/placard');
	await page.getByRole('button', { name: 'Modifier Riz basmati' }).click();
	const fenetre = page.getByRole('dialog');
	await expect(fenetre.getByRole('spinbutton').first()).toHaveValue('400');

	// Le riz était en fait du riz au lait pour le goûter : il devient un autre produit.
	await fenetre.getByLabel('Ingrédient').selectOption({ label: 'Autre produit (hors repas)' });
	await fenetre.getByLabel('Nom').fill('Riz au lait');
	await fenetre.getByLabel('Catégorie').selectOption('Biscuits et goûters');
	await fenetre.getByRole('button', { name: 'Enregistrer' }).click();

	await expect(fenetre).toBeHidden();
	await expect(page.getByText('Aucun ingrédient au placard.')).toBeVisible();
	await expect(page.getByText('Riz au lait')).toBeVisible();
});

test('coches d’un autre appareil visibles sans recharger', async ({ browser }) => {
	const [moi, conjoint] = await Promise.all([browser.newPage(), browser.newPage()]);
	for (const page of [moi, conjoint]) {
		await preparer(page, '2026-10-14');
		await seConnecter(page);
	}
	await ajouterMembre(moi, 'Alex');
	await moi.goto('/');
	await moi.getByRole('button', { name: /Générer les repas|Autre proposition/ }).click();
	await expect(moi.locator('a[href^="/plats/"]').first()).toBeVisible({ timeout: 30_000 });

	const lien = moi.getByRole('link', { name: /Liste de courses/ });
	const adresse = (await lien.getAttribute('href')) ?? '/courses';
	await Promise.all([moi.goto(adresse), conjoint.goto(adresse)]);
	const premiere = (page: typeof moi) => page.locator('li input[type=checkbox]').first();
	await expect(premiere(conjoint)).not.toBeChecked();

	await premiere(moi).check();
	// Relue toutes les 5 s par la liste ouverte, sans action sur l'autre appareil.
	await expect(premiere(conjoint)).toBeChecked({ timeout: 10_000 });
	await expect(conjoint.locator('li.recente')).toHaveCount(1);
	await Promise.all([moi.context().close(), conjoint.context().close()]);
});
