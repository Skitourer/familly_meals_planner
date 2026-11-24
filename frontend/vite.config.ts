/// <reference types="node" />
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [
		sveltekit({
			// Application monopage : FastAPI sert index.html pour toutes les routes.
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	server: {
		// En développement, les appels /api sont relayés vers le serveur Python
		// (adresse modifiable : REPAS_API=http://127.0.0.1:8010 npm run dev).
		proxy: { '/api': process.env.REPAS_API ?? 'http://127.0.0.1:8000' }
	},
	test: {
		include: ['src/**/*.test.ts']
	}
});
