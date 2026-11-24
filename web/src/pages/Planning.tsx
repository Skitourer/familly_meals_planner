/**
 * Page Planning : les 7 jours de la semaine sélectionnée, midi et soir.
 * - Sélection de la semaine (précédente / suivante / cette semaine)
 * - Génération algorithmique des repas manquants
 * - Choix d'un plat par créneau, nombre de convives, 0 = repas hors maison
 * - Enregistrement en une opération (PUT)
 */
import { useState, useEffect } from "react";
import { api } from "../api.ts";
import type { Plat, Repas } from "@partage/types.ts";
import { joursDeSemaine, libelleJour, moisDeSemaine } from "@partage/dates.ts";
import { saisonDuMois } from "@partage/saison.ts";
import ComposantSemaine from "../composants/ChoixSemaine.tsx";

export default function PlanningPage({ semaine, setSemaine, onError }: {
  semaine: string;
  setSemaine: (s: string) => void;
  onError: (e: unknown) => void;
}) {
  const [repas, setRepas] = useState<Repas[]>([]);
  const [plats, setPlats] = useState<Plat[]>([]);
  const [infos, setInfos] = useState<{ besoinTotal: number; besoinParRepas: number; saison: string[] }>({ besoinTotal: 0, besoinParRepas: 0, saison: [] });
  const [sale, setSale] = useState(false); // modifications non enregistrées

  // Chargement initial : catalogue + repas de la semaine
  useEffect(() => {
    Promise.all([api.plats(), api.semaine(semaine)])
      .then(([p, s]) => {
        setPlats(p);
        setRepas(s.repas);
        setInfos({ besoinTotal: s.besoinTotal, besoinParRepas: s.besoinParRepas, saison: s.saison });
      })
      .catch(onError);
  }, [semaine]);

  const creneau = (jour: number, service: "midi" | "soir") =>
    repas.find((r) => r.jour === jour && r.service === service);

  const maj = (jour: number, service: "midi" | "soir", patch: Partial<Repas>) => {
    setRepas((prev) => prev.map((r) => (r.jour === jour && r.service === service ? { ...r, ...patch } : r)));
    setSale(true);
  };

  const enregistrer = async () => {
    try {
      await api.enregistrerRepas(semaine, repas);
      setSale(false);
    } catch (e) { onError(e); }
  };

  const generer = async () => {
    try {
      const r = await api.generer(semaine);
      setRepas(r.repas);
      await api.enregistrerRepas(semaine, r.repas);
      setSale(false);
    } catch (e) { onError(e); }
  };

  const jours = joursDeSemaine(semaine);
  const mois = moisDeSemaine(semaine);

  return (
    <div>
      {/* Choix de la semaine */}
      <ComposantSemaine semaine={semaine} setSemaine={setSemaine} />
      <div className="badges" style={{ marginBottom: "1rem" }}>
        <span className="badge">Besoin familial : {infos.besoinTotal} kcal/jour</span>
        <span className="badge">≈ {infos.besoinParRepas} kcal par repas</span>
        <span className="badge">Saison : {saisonDuMois(mois).slice(0, 5).join(", ")}…</span>
      </div>

      {/* Actions */}
      <div className="ligne" style={{ marginBottom: "1rem" }}>
        <button className="action" onClick={generer}>✨ Générer la semaine</button>
        <button className={sale ? "action" : "discret"} onClick={enregistrer} disabled={!sale}>
          Enregistrer
        </button>
        {sale && <span className="mention">Modifications non enregistrées</span>}
      </div>

      {/* Les 7 jours — attendre le chargement des 14 créneaux avant de rendre
          (sinon creneau() renvoie undefined et le rendu plante) */}
      {repas.length < 14 ? (
        <p className="mention">Chargement de la semaine…</p>
      ) : jours.map((date, jour) => (
        <section className="jour" key={jour}>
          <p className="titre">{libelleJour(date)}</p>
          <div className="grille deux">
            {(["midi", "soir"] as const).map((service) => {
              const r = creneau(jour, service)!;
              const plat = r.platId ? plats.find((p) => p.id === r.platId) : undefined;
              return (
                <div key={service} className={`creneau ${r.convives === 0 ? "absent" : ""}`}>
                  <div className="creneau-titre">
                    <span className="service">{service === "midi" ? "🌞 Midi" : "🌙 Soir"}</span>
                    <span>
                      <span className="mention">convives</span>{" "}
                      <input className="peti" type="number" min={0} max={15} value={r.convives}
                             onChange={(e) => maj(jour, service, { convives: Math.max(0, Number(e.target.value) || 0) })} />
                    </span>
                  </div>
                  <select value={r.platId ?? ""} onChange={(e) => maj(jour, service, { platId: e.target.value === "" ? null : Number(e.target.value) })}>
                    <option value="">— Pas de plat —</option>
                    {plats.map((p) => <option key={p.id} value={p.id}>{p.nom}</option>)}
                  </select>
                  {r.convives === 0 && <p className="mention">🍷 Repas hors maison — exclu de la liste de courses</p>}
                  {plat && (
                    <div className="meta">
                      <span>{plat.categorie}</span>
                      <span>{plat.kcalParPortion} kcal/portion</span>
                      {plat.saison.includes(mois) && <span className="saison">🌱 de saison</span>}
                      {plat.lienRecette && (
                        <a href={plat.lienRecette} target="_blank" rel="noreferrer" className="lien-recette"
                           title="Lien renseigné dans la fiche du plat (onglet Plats)">
                          📖 recette ↗
                        </a>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
