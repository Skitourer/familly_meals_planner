// Tests de bout en bout : l'API Python sert l'interface compilée (comme en production),
// sur une base SQLite neuve à chaque lancement. Commande : npm run e2e
import { defineConfig, devices } from '@playwright/test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const PORT = 8020;
const dossierTemporaire = mkdtempSync(join(tmpdir(), 'menu-famille-e2e-'));

export default defineConfig({
	testDir: 'e2e',
	// Une seule base partagée : les parcours s'exécutent l'un après l'autre.
	workers: 1,
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: 0,
	timeout: 60_000,
	reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
	use: {
		baseURL: `http://127.0.0.1:${PORT}`,
		screenshot: 'only-on-failure',
		trace: 'retain-on-failure',
		locale: 'fr-FR',
		timezoneId: 'Europe/Paris'
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
	webServer: {
		command: `uv run uvicorn repas.application:creer_application --factory --port ${PORT}`,
		cwd: resolve('../backend'),
		url: `http://127.0.0.1:${PORT}/api/sante`,
		reuseExistingServer: false,
		timeout: 120_000,
		env: {
			REPAS_DOSSIER_INTERFACE: resolve('build'),
			REPAS_BASE_DE_DONNEES: join(dossierTemporaire, 'e2e.db'),
			REPAS_MOT_DE_PASSE: 'mot-de-passe-e2e',
			REPAS_CLE_SECRETE: 'cle-de-session-des-tests-de-bout-en-bout'
		}
	}
});
