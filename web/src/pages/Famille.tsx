/**
 * Page Famille : profils (âge, taille, poids, sexe, activité) et besoin
 * énergétique calculé pour chacun.
 */
import { useState, useEffect } from "react";
import { api } from "../api.ts";
import type { Membre, Activite } from "@partage/types.ts";
import { ACTIVITES } from "@partage/types.ts";

type MembreAvecBesoin = Membre & { besoinKcal: number };

export default function FamillePage({ onError }: { onError: (e: unknown) => void }) {
  const [membres, setMembres] = useState<MembreAvecBesoin[]>([]);
  const [sale, setSale] = useState(false);

  useEffect(() => { api.membres().then(setMembres).catch(onError); }, []);

  const maj = (id: number, patch: Partial<Membre>) => {
    setMembres((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
    setSale(true);
  };

  const enregistrer = async () => {
    try {
      await Promise.all(membres.map((m) => api.majMembre(m.id, m)));
      setMembres(await api.membres());
      setSale(false);
    } catch (e) { onError(e); }
  };

  const ajouter = async () => {
    try {
      await api.ajouterMembre({ nom: "Nouveau membre", age: 30, sexe: "F", activite: "leger" });
      setMembres(await api.membres());
    } catch (e) { onError(e); }
  };

  const supprimer = async (id: number) => {
    try {
      await api.supprimerMembre(id);
      setMembres((prev) => prev.filter((m) => m.id !== id));
    } catch (e) { onError(e); }
  };

  return (
    <div>
      <p className="mention">L'âge, la taille, le poids et l'activité physique de chacun définissent son besoin alimentaire (formule Mifflin-St Jeor).</p>
      <div className="ligne" style={{ marginBottom: "1rem" }}>
        <button className={sale ? "action" : "discret"} onClick={enregistrer} disabled={!sale}>Enregistrer</button>
        <button className="discret" onClick={ajouter}>+ Ajouter un membre</button>
      </div>
      <div className="grille famille">
        {membres.map((m) => (
          <div className="carte" key={m.id}>
            <div className="ligne">
              <div>
                <label>Nom</label>
                <input value={m.nom} onChange={(e) => maj(m.id, { nom: e.target.value })} />
              </div>
              <div>
                <label>Âge</label>
                <input type="number" value={m.age} onChange={(e) => maj(m.id, { age: Number(e.target.value) || 0 })} />
              </div>
            </div>
            <div className="ligne" style={{ marginTop: "0.5rem" }}>
              <div>
                <label>Taille (cm)</label>
                <input type="number" value={m.tailleCm ?? ""} onChange={(e) => maj(m.id, { tailleCm: Number(e.target.value) || undefined })} />
              </div>
              <div>
                <label>Poids (kg)</label>
                <input type="number" value={m.poidsKg ?? ""} onChange={(e) => maj(m.id, { poidsKg: Number(e.target.value) || undefined })} />
              </div>
            </div>
            <div className="ligne" style={{ marginTop: "0.5rem" }}>
              <div>
                <label>Sexe (pour la formule)</label>
                <select value={m.sexe} onChange={(e) => maj(m.id, { sexe: e.target.value as "F" | "H" })}>
                  <option value="F">Femme</option>
                  <option value="H">Homme</option>
                </select>
              </div>
              <div>
                <label>Activité</label>
                <select value={m.activite} onChange={(e) => maj(m.id, { activite: e.target.value as Activite })}>
                  {Object.entries(ACTIVITES).map(([cle, a]) => <option key={cle} value={cle}>{a.label}</option>)}
                </select>
              </div>
            </div>
            <div className="meta" style={{ marginTop: "0.6rem" }}>
              <span className="saison">Besoin : {m.besoinKcal} kcal/jour</span>
              <button className="danger discret" onClick={() => supprimer(m.id)}>Supprimer</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
