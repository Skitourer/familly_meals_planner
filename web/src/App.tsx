/**
 * Composant racine : écran de connexion, puis navigation par onglets.
 * État minimal : session + onglet courant + semaine sélectionnée (id = lundi ISO).
 */
import { useState, useEffect } from "react";
import { api, ErreurApi } from "./api.ts";
import { idSemaine } from "@partage/dates.ts";
import Connexion from "./pages/Connexion.tsx";
import PlanningPage from "./pages/Planning.tsx";
import CoursesPage from "./pages/Courses.tsx";
import FamillePage from "./pages/Famille.tsx";
import PlatsPage from "./pages/Plats.tsx";
import NotesPage from "./pages/Notes.tsx";

const ONGLETS = [
  { cle: "planning", libelle: "📅 Planning" },
  { cle: "courses", libelle: "🛒 Courses" },
  { cle: "famille", libelle: "👨‍👩‍👧‍👦 Famille" },
  { cle: "plats", libelle: "📖 Plats" },
  { cle: "notes", libelle: "⭐ Notes" },
] as const;

export default function App() {
  const [connecte, setConnecte] = useState<boolean | null>(null); // null = vérification en cours
  const [onglet, setOnglet] = useState<(typeof ONGLETS)[number]["cle"]>("planning");
  const [semaine, setSemaine] = useState<string>(() => idSemaine(new Date()));

  // Vérifie la session au chargement (le service worker peut avoir gardé le cookie)
  useEffect(() => {
    api.session().then((s) => setConnecte(s.connecte)).catch(() => setConnecte(false));
  }, []);

  // Seule une erreur 401 (session expirée) déconnecte ; les autres erreurs
  // (400, 500…) sont remontées à la console sans jeter l'utilisateur dehors.
  const surveille = (e: unknown) => {
    if (e instanceof ErreurApi && e.statut === 401) setConnecte(false);
    else console.error(e);
  };

  if (connecte === null) return <p style={{ textAlign: "center", marginTop: "3rem" }}>Chargement…</p>;

  if (!connecte) {
    return <Connexion onConnecte={() => setConnecte(true)} />;
  }

  return (
    <div className="app">
      <header className="entete">
        <div>
          <h1>🥗 Menu Famille</h1>
          <p className="mention">Le vendredi, planifie la semaine à venir</p>
        </div>
        <div className="ligne">
          <button className="discret" onClick={() => api.deconnexion().then(() => setConnecte(false))}>
            Se déconnecter
          </button>
        </div>
      </header>

      <nav className="onglets">
        {ONGLETS.map((o) => (
          <button key={o.cle} className={onglet === o.cle ? "actif" : ""} onClick={() => setOnglet(o.cle)}>
            {o.libelle}
          </button>
        ))}
      </nav>

      {onglet === "planning" && <PlanningPage semaine={semaine} setSemaine={setSemaine} onError={surveille} />}
      {onglet === "courses" && <CoursesPage semaine={semaine} setSemaine={setSemaine} onError={surveille} />}
      {onglet === "famille" && <FamillePage onError={surveille} />}
      {onglet === "plats" && <PlatsPage onError={surveille} />}
      {onglet === "notes" && <NotesPage semaine={semaine} setSemaine={setSemaine} onError={surveille} />}
    </div>
  );
}
