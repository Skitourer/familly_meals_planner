/** Page Courses : liste agrégée avec arrondi aux conditionnements magasin + export PDF. */
import { useState, useEffect } from "react";
import { api } from "../api.ts";
import type { LigneCourse } from "@partage/courses.ts";
import ComposantSemaine from "../composants/ChoixSemaine.tsx";

export default function CoursesPage({ semaine, setSemaine, onError }: {
  semaine: string;
  setSemaine: (s: string) => void;
  onError: (e: unknown) => void;
}) {
  const [liste, setListe] = useState<LigneCourse[]>([]);

  useEffect(() => {
    api.courses(semaine).then(setListe).catch(onError);
  }, [semaine]);

  return (
    <div>
      <ComposantSemaine semaine={semaine} setSemaine={setSemaine} />
      <div className="carte">
        <h2>Liste de courses — semaine du {semaine} ({liste.length} articles)</h2>
        <p className="mention">
          Besoin exact barré + quantité à acheter en magasin (arrondie au conditionnement).
        </p>
        {liste.length === 0 ? (
          <p className="mention">Aucun repas planifié : va dans « Planning » et génère la semaine.</p>
        ) : (
          <div className="liste-courses">
            <ul>
              {liste.map((l) => (
                <li key={l.nom + l.unite}>
                  <span>{l.nom}</span>
                  {l.arrondi ? (
                    <span>
                      <span className="barrer">{Math.round(l.besoin)} {l.unite}</span>{" "}
                      <strong>→ {Math.round(l.achat)} {l.unite}</strong>
                    </span>
                  ) : (
                    <strong>
                      {l.unite === "p" ? `${Math.round(l.achat)} pc(s)` : `${Math.round(l.achat)} ${l.unite}`}
                    </strong>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        {/* Export PDF : le serveur génère le fichier, le navigateur le télécharge */}
        <div className="ligne" style={{ marginTop: "1rem" }}>
          <a className="action" href={api.urlPdf(semaine)} download>
            📄 Exporter en PDF
          </a>
        </div>
      </div>
    </div>
  );
}
