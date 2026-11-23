import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

/**
 * Configuration Vite :
 * - alias "@partage" vers le dossier ../shared (logique métier commune)
 * - proxy /api vers le serveur Fastify en dev
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@partage": fileURLToPath(new URL("../shared", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:3000",
    },
  },
  build: {
    outDir: "dist",
  },
});
