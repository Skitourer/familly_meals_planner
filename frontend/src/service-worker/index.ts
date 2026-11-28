// Service worker : l'application et la liste de courses s'ouvrent sans réseau (au magasin).
// Les règles (quoi garder, comment) sont dans lib/hors-ligne.ts ; voir docs/adr/0006-hors-ligne.md.

import { version } from '$app/env';
import { assets, immutable } from '$app/manifest';
import { self } from '$app/service-worker';
import {
	CACHE_DONNEES,
	PAGE_APPLICATION,
	cachesPerimes,
	estSessionFermee,
	nomCacheApplication,
	strategie
} from '#lib/hors-ligne.ts';

const cacheApplication = nomCacheApplication(version);
// Le lecteur de codes-barres de secours (.wasm, ~1 Mo) n'est pas gardé hors ligne : il ne
// sert qu'au scan, qui demande de toute façon le réseau (Open Food Facts).
const fichiersApplication = [...immutable, ...assets]
	.filter(({ path }) => !path.endsWith('.wasm'))
	.map(({ path }) => new URL(path, self.registration.scope).pathname);
const fichiersConnus = new Set(fichiersApplication);

self.addEventListener('install', (evenement) => {
	evenement.waitUntil(
		caches
			.open(cacheApplication)
			.then((cache) => cache.addAll([...fichiersApplication, PAGE_APPLICATION]))
	);
});

self.addEventListener('activate', (evenement) => {
	evenement.waitUntil(
		caches
			.keys()
			.then((noms) => Promise.all(cachesPerimes(noms, version).map((nom) => caches.delete(nom))))
	);
});

self.addEventListener('fetch', (evenement) => {
	const requete = evenement.request;
	const url = new URL(requete.url);
	const choix = strategie(
		{ methode: requete.method, url, navigation: requete.mode === 'navigate' },
		self.location.origin,
		fichiersConnus
	);
	if (choix === 'application') evenement.respondWith(depuisApplication(requete));
	else if (choix === 'page') evenement.respondWith(page(requete));
	else if (choix === 'donnee') evenement.respondWith(donnee(requete, url.pathname));
});

async function depuisApplication(requete: Request): Promise<Response> {
	const cache = await caches.open(cacheApplication);
	return (await cache.match(requete)) ?? fetch(requete);
}

async function page(requete: Request): Promise<Response> {
	try {
		return await fetch(requete);
	} catch (erreur) {
		// Sans réseau : la page gardée à l'installation, cohérente avec les fichiers en cache.
		const cache = await caches.open(cacheApplication);
		const gardee = await cache.match(PAGE_APPLICATION);
		if (gardee) return gardee;
		throw erreur;
	}
}

async function donnee(requete: Request, chemin: string): Promise<Response> {
	let reponse: Response;
	try {
		reponse = await fetch(requete);
	} catch (erreur) {
		// Sans réseau : la dernière réponse reçue ; sinon l'échec réseau, que l'interface affiche.
		const gardee = await caches.match(requete, { cacheName: CACHE_DONNEES });
		if (gardee) return gardee;
		throw erreur;
	}
	// Un cache plein ou indisponible ne doit pas empêcher l'usage en ligne : erreur journalisée.
	await garder(requete, chemin, reponse.clone()).catch((erreur: unknown) =>
		console.error('Réponse non gardée pour le hors-ligne', chemin, erreur)
	);
	return reponse;
}

async function garder(requete: Request, chemin: string, reponse: Response): Promise<void> {
	if (!reponse.ok) return;
	if (estSessionFermee(chemin, await reponse.clone().json())) {
		await caches.delete(CACHE_DONNEES); // session expirée : plus rien à montrer hors ligne
		return;
	}
	const cache = await caches.open(CACHE_DONNEES);
	await cache.put(requete, reponse);
}
