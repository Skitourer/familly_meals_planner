/** Écran de connexion : un seul mot de passe partagé pour toute la famille. */
import { useState } from "react";
import { api } from "../api.ts";

export default function Connexion({ onConnecte }: { onConnecte: () => void }) {
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");

  const soumettre = async (e: React.FormEvent) => {
    e.preventDefault();
    setErreur("");
    try {
      await api.connexion(motDePasse);
      onConnecte();
    } catch {
      setErreur("Mot de passe incorrect.");
    }
  };

  return (
    <div className="connexion carte">
      <h1>🥗 Menu Famille</h1>
      <p className="mention">Entre le mot de passe partagé de la famille.</p>
      <form onSubmit={soumettre}>
        <label htmlFor="mdp">Mot de passe</label>
        <input id="mdp" type="password" value={motDePasse} autoFocus
               onChange={(e) => setMotDePasse(e.target.value)} />
        <p className="erreur">{erreur}</p>
        <button className="action" type="submit">Se connecter</button>
      </form>
      <p className="mention" style={{ marginTop: "1rem" }}>
        Valeur par défaut au premier lancement : « menu-famille »
        (à changer via l'API PUT /api/session/mot-de-passe).
      </p>
    </div>
  );
}
