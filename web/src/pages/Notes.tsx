/**
 * Page Notes : notation des repas de la semaine a posteriori (1 à 5 étoiles)
 * et classement des plats favoris (moyennes cumulées).
 */
import { useState, useEffect } from "react";
import { api } from "../api.ts";
import type { Plat } from "@partage/types.ts";
import ComposantSemaine from "../composants/ChoixSemaine.tsx";

export default function NotesPage({ semaine, setSemaine, onError }: {
  semaine: string;
  setSemaine: (s: string) => void;
  onError: (e: unknown) => void;
}) {
  const [plats, setPlats] = useState<Plat[]>([]);
  const [notes, setNotes] = useState<Record<number, number>>({}); // platId -> note donnée
  const [favoris, setFavoris] = useState<Array<{ id: number; nom: string; nb: number; moyenne: number }>>([]);

  useEffect(() => {
    Promise.all([api.plats(), api.notes(semaine), api.stats()])
      .then(([p, n, s]) => {
        setPlats(p);
        const deja = new Map((n as Array<{ plat_id: number; note: number }>).map((x) => [x.plat_id, x.note]));
        setNotes(Object.fromEntries(deja));
        setFavoris(s);
      })
      .catch(onError);
  }, [semaine]);

  const noter = async (platId: number, note: number) => {
    if (notes[platId] === note) return; // pas de changement
    setNotes((prev) => ({ ...prev, [platId]: note }));
    try {
      await api.noter({ semaine, platId, note });
      setFavoris(await api.stats());
    } catch (e) { onError(e); }
  };

  return (
    <div>
      <ComposantSemaine semaine={semaine} setSemaine={setSemaine} />
      <p className="mention">Note les repas de la semaine après les avoir faits. Les moyennes influencent les générations futures.</p>

      <div className="carte">
        <h2>Notes de la semaine du {semaine}</h2>
        {/* Tout le catalogue est notable ; la génération privilégiera les favoris. */}
        {plats.map((p) => (
          <div className="ligne" key={p.id} style={{ justifyContent: "space-between", borderBottom: "1px solid var(--bord)", padding: "0.4rem 0" }}>
            <span>{p.nom}</span>
            <span className="etoiles">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} className={n <= (notes[p.id] ?? 0) ? "pleine" : "vide"}
                        onClick={() => noter(p.id, n)} aria-label={`Noter ${n} sur 5`}>★</button>
              ))}
            </span>
          </div>
        ))}
        {plats.length === 0 && <p className="mention">Aucun plat au catalogue : commence par « Plats ».</p>}
      </div>

      <div className="carte">
        <h2>🏆 Favoris cumulés</h2>
        {favoris.length === 0 ? (
          <p className="mention">Pas encore de note enregistrée.</p>
        ) : (
          <ul className="liste-courses">
            {favoris.map((f) => (
              <li key={f.id}>
                <span>{f.nom} <em className="mention">({f.nb} note(s))</em></span>
                <strong>{"★".repeat(Math.round(f.moyenne))} {f.moyenne}/5</strong>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
