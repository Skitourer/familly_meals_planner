import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./styles.css";

// Enregistrement du service worker (PWA : usage hors ligne)
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js").catch(() => {});
}

createRoot(document.getElementById("racine")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
