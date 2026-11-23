/**
 * Composant de navigation entre semaines (précédente / suivante / courante).
 * Un id de semaine est la date du lundi au format ISO "2026-11-23".
 */
import { idSemaine } from "@partage/dates.ts";

export default function ComposantSemaine({ semaine, setSemaine }: {
  semaine: string;
  setSemaine: (s: string) => void;
}) {
  const decale = (n: number) => {
    const lundi = new Date(`${semaine}T00:00:00`);
    lundi.setDate(lundi.getDate() + 7 * n);
    setSemaine(idSemaine(lundi));
  };
  return (
    <div className="tabs-journees">
      <button className="discret" onClick={() => decale(-1)}>← Semaine précédente</button>
      <strong style={{ margin: "0 0.5rem" }}>Semaine du {semaine}</strong>
      <button className="discret" onClick={() => decale(1)}>Semaine suivante →</button>
      <button className="discret" onClick={() => setSemaine(idSemaine(new Date()))}>Cette semaine</button>
    </div>
  );
}
