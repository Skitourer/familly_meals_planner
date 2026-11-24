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
// Seules les réponses GET en succès (200) sont mises en cache : jamais les
// erreurs (401, 500…) ni les méthodes avec body (POST/PUT/DELETE), pour ne
// pas servir de données périmées ou faussement "déconnecté".
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return; // laisser passer tel quel
  e.respondWith(
    fetch(e.request)
      .then((rep) => {
        if (rep.ok) {
          const copie = rep.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copie)).catch(() => {});
        }
        return rep;
      })
      .catch(() => caches.match(e.request))
  );
});
