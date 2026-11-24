/**
 * Page Plats : catalogue familial (création, édition, suppression) et
 * recherche de produits dans Open Food Facts pour pré-remplir un ingrédient.
 */
import { useState, useEffect } from "react";
import { api } from "../api.ts";
import type { Plat, Ingredient, Categorie } from "@partage/types.ts";
import { MOIS } from "@partage/mois.ts";

const CATEGORIES: Categorie[] = ["viande", "poisson", "volaille", "pates", "vegetarien", "autre"];

export default function PlatsPage({ onError }: { onError: (e: unknown) => void }) {
  const [plats, setPlats] = useState<Plat[]>([]);
  const [enEdition, setEnEdition] = useState<number | "nouveau" | null>(null);

  useEffect(() => { api.plats().then(setPlats).catch(onError); }, []);

  const supprimer = async (id: number) => {
    try {
      await api.supprimerPlat(id);
      setPlats((prev) => prev.filter((p) => p.id !== id));
    } catch (e) { onError(e); }
  };

  return (
    <div>
      <div className="ligne" style={{ marginBottom: "1rem" }}>
        <button className="action" onClick={() => setEnEdition("nouveau")}>+ Nouveau plat</button>
      </div>

      {/* Formulaire de création / édition */}
      {enEdition !== null && (
        <FormulairePlat
          plat={enEdition === "nouveau" ? null : plats.find((p) => p.id === enEdition) ?? null}
          onFerme={() => setEnEdition(null)}
          onSauve={async () => {
            setPlats(await api.plats());
            setEnEdition(null);
          }}
          onError={onError}
        />
      )}

      <div className="grille deux">
        {plats.map((p) => (
          <div className="carte" key={p.id}>
            <h2>{p.nom}</h2>
            <div className="meta">
              <span>{p.categorie}</span>
              <span>{p.kcalParPortion} kcal/portion</span>
              <span>{p.ingredients.length} ingrédients</span>
              <span className={p.saison.length ? "saison" : ""}>
                Saison : {p.saison.length ? p.saison.map((m) => MOIS[m - 1]).join(", ") : "toute l'année"}
              </span>
            </div>
            {p.lienRecette && (
              <p className="mention" style={{ marginTop: "0.4rem" }}>
                <a href={p.lienRecette} target="_blank" rel="noreferrer">📖 Voir la recette ↗</a>
              </p>
            )}
            <div className="ligne" style={{ marginTop: "0.6rem" }}>
              <button className="discret" onClick={() => setEnEdition(p.id)}>Modifier</button>
              <button className="discret danger" onClick={() => supprimer(p.id)}>Supprimer</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Formulaire d'un plat : champs principaux + ingrédients + recherche OFF. */
function FormulairePlat({ plat, onFerme, onSauve, onError }: {
  plat: Plat | null;
  onFerme: () => void;
  onSauve: () => Promise<void>;
  onError: (e: unknown) => void;
}) {
  const [nom, setNom] = useState(plat?.nom ?? "");
  const [categorie, setCategorie] = useState<Categorie>(plat?.categorie ?? "vegetarien");
  const [kcal, setKcal] = useState(plat?.kcalParPortion ?? 650);
  const [saison, setSaison] = useState<number[]>(plat?.saison ?? []);
  const [ingredients, setIngredients] = useState<Ingredient[]>(plat?.ingredients ?? []);
  const [lienRecette, setLienRecette] = useState(plat?.lienRecette ?? "");
  const [recherche, setRecherche] = useState("");
  const [produits, setProduits] = useState<Array<{ nom: string; marque: string; kcalPour100g: number | null; quantite: string }>>([]);

  const ajouterIngredient = (i: Ingredient) => setIngredients((prev) => [...prev, i]);

  const chercherOff = async () => {
    try {
      const r = await api.chercherProduits(recherche);
      setProduits(r.produits);
    } catch (e) { onError(e); }
  };

  const sauver = async () => {
    try {
      const corps = { nom, categorie, kcalParPortion: kcal, saison, ingredients, lienRecette: lienRecette || undefined };
      if (plat) await api.majPlat(plat.id, corps);
      else await api.ajouterPlat(corps);
      await onSauve();
    } catch (e) { onError(e); }
  };

  return (
    <div className="carte">
      <h2>{plat ? "Modifier le plat" : "Nouveau plat"}</h2>
      <div className="ligne">
        <div style={{ flex: 2 }}>
          <label>Nom</label>
          <input value={nom} onChange={(e) => setNom(e.target.value)} />
        </div>
        <div>
          <label>Catégorie</label>
          <select value={categorie} onChange={(e) => setCategorie(e.target.value as Categorie)}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label>kcal / portion</label>
          <input type="number" value={kcal} onChange={(e) => setKcal(Number(e.target.value) || 0)} />
        </div>
      </div>
      <div className="ligne" style={{ marginTop: "0.6rem" }}>
        <div style={{ flex: 1 }}>
          <label>Lien vers la recette (URL, optionnel)</label>
          <input placeholder="https://…" value={lienRecette} onChange={(e) => setLienRecette(e.target.value)} />
        </div>
      </div>

      {/* Saison : boutons de mois togglables */}
      <label style={{ marginTop: "0.6rem" }}>Mois de saison (aucun = toute l'année)</label>
      <div className="meta">
        {MOIS.map((m, i) => (
          <button key={m} className={saison.includes(i + 1) ? "action" : "discret"}
                  style={{ padding: "0.2rem 0.5rem", fontSize: "0.72rem" }}
                  onClick={() => setSaison((prev) => prev.includes(i + 1) ? prev.filter((x) => x !== i + 1) : [...prev, i + 1])}>
            {m.slice(0, 4)}.
          </button>
        ))}
      </div>

      {/* Ingrédients (quantité pour UNE portion) */}
      <h2 style={{ marginTop: "1rem" }}>Ingrédients (pour une portion)</h2>
      {ingredients.map((ing, i) => (
        <div className="ligne" key={i} style={{ marginBottom: "0.4rem" }}>
          <div style={{ flex: 2 }}>
            <input value={ing.nom} onChange={(e) => setIngredients((prev) => prev.map((x, k) => k === i ? { ...x, nom: e.target.value } : x))} />
          </div>
          <div>
            <input type="number" value={ing.quantite} onChange={(e) => setIngredients((prev) => prev.map((x, k) => k === i ? { ...x, quantite: Number(e.target.value) || 0 } : x))} />
          </div>
          <div>
            <select value={ing.unite} onChange={(e) => setIngredients((prev) => prev.map((x, k) => k === i ? { ...x, unite: e.target.value } : x))}>
              <option value="g">g</option>
              <option value="ml">ml</option>
              <option value="p">pièce(s)</option>
            </select>
          </div>
          <button className="discret danger" onClick={() => setIngredients((prev) => prev.filter((_, k) => k !== i))}>✕</button>
        </div>
      ))}
      <button className="discret" onClick={() => ajouterIngredient({ nom: "", quantite: 100, unite: "g" })}>+ Ingrédient</button>

      {/* Recherche Open Food Facts */}
      <h2 style={{ marginTop: "1rem" }}>🔍 Compléter avec Open Food Facts</h2>
      <div className="ligne">
        <div style={{ flex: 2 }}>
          <input placeholder="Produit (ex. riz basmati)" value={recherche} onChange={(e) => setRecherche(e.target.value)} />
        </div>
        <button className="action" onClick={chercherOff}>Chercher</button>
      </div>
      {produits.length > 0 && (
        <ul className="liste-courses" style={{ marginTop: "0.6rem" }}>
          {produits.slice(0, 10).map((p, i) => (
            <li key={i}>
              <span>{p.nom} <em className="mention">{p.marque} {p.quantite && `(${p.quantite})`}</em></span>
              <button className="discret" onClick={() => ajouterIngredient({ nom: p.nom, quantite: 100, unite: "g" })}>
                {p.kcalPour100g ? `${p.kcalPour100g} kcal/100g — ` : ""}Ajouter
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="ligne" style={{ marginTop: "1rem" }}>
        <button className="action" onClick={sauver}>{plat ? "Enregistrer" : "Créer"}</button>
        <button className="discret" onClick={onFerme}>Annuler</button>
      </div>
    </div>
  );
}
