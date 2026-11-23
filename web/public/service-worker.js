/* Service worker minimal : cache "network first" pour un usage hors ligne
   (consultation du planning et de la liste de courses au supermarché). */
const CACHE = "menu-famille-v1";
const RESSOURCES = ["/", "/manifest.webmanifest", "/icone.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(RESSOURCES)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  // Nettoyage des anciens caches
  e.waitUntil(caches.keys().then((cles) => Promise.all(cles.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
});

// Stratégie : réseau d'abord ; repli sur le cache si hors ligne.
// Les réponses /api ne sont mises en cache qu'en cas de succès, pour ne pas
// servir des données périmées quand le réseau est disponible.
self.addEventListener("fetch", (e) => {
  e.respondWith(
    fetch(e.request)
      .then((rep) => {
        const copie = rep.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copie)).catch(() => {});
        return rep;
      })
      .catch(() => caches.match(e.request))
  );
});
