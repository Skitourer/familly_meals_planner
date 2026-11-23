/**
 * Point d'entrée du serveur : Fastify + cookie + routes.
 * Port par défaut : 3000 (configurable via la variable d'environnement PORT).
 */
import Fastify from "fastify";
import cookie from "@fastify/cookie";
import { routesAuth } from "./auth.ts";
import { routesApi } from "./routes.ts";

const app = Fastify({ logger: true });
await app.register(cookie);

// Connexion / déconnexion (publiques), puis toutes les routes API protégées.
await routesAuth(app);
await routesApi(app);

// Ce serveur ne sert QUE l'API : en production, un reverse proxy (Caddy, Nginx)
// sert le build statique de `web/dist` et transmet /api vers le port 3000.
const port = Number(process.env.PORT ?? 3000);
app.listen({ port, host: "0.0.0.0" }).then(() => {
  app.log.info(`API Menu Famille sur le port ${port}`);
});
