<!--
	Fiche détaillée d'une recette : chiffres clés, ingrédients (pour le nombre de portions
	demandé), étapes, et lien vers une recette en ligne.
-->
<script lang="ts">
	import type { FicheRecette } from '#lib/types.ts';

	let { fiche, portions = 1 }: { fiche: FicheRecette; portions?: number } = $props();

	const r = $derived(fiche.recette);
	// Lien fourni par la recette, sinon une recherche sur un site de recettes.
	const lienExterne = $derived(
		r.lien ?? `https://www.marmiton.org/recettes/recherche.aspx?aqt=${encodeURIComponent(r.nom)}`
	);
	const f1 = (n: number) => n.toLocaleString('fr-FR', { maximumFractionDigits: 1 });

	function quantite(id: string, grammes: number): string {
		const total = grammes * portions;
		const unite = fiche.ingredients_unites?.[id] === 'ml' ? 'ml' : 'g';
		if (total >= 1000) return `${f1(total / 1000)} ${unite === 'ml' ? 'L' : 'kg'}`;
		return `${total < 10 ? f1(total) : Math.round(total / 5) * 5} ${unite}`;
	}
</script>

<p class="doux">
	Préparation {r.temps.preparation} min · cuisson {r.temps.cuisson} min
	{#if r.lot}
		· se cuisine en lot pour {r.lot.repas_max} repas ({r.lot.conservation_jours} j au frais)
	{/if}
</p>

<div class="chiffres">
	<div><strong>{fiche.nutriments.energie_kcal.toFixed(0)}</strong><span>kcal</span></div>
	<div><strong>{f1(fiche.nutriments.proteines_g)} g</strong><span>protéines</span></div>
	<div><strong>{f1(fiche.nutriments.fibres_g)} g</strong><span>fibres</span></div>
	<div><strong>{f1(fiche.nutriments.sel_g)} g</strong><span>sel</span></div>
	<div><strong>{fiche.fruits_legumes_g} g</strong><span>fruits et légumes</span></div>
	<div><strong>{f1(fiche.co2_kg)} kg</strong><span>CO₂e</span></div>
</div>
<p class="doux">Valeurs pour une portion adulte de référence.</p>

{#if fiche.hors_saison.length}
	<p class="badge alerte">Hors saison ce mois-ci : {fiche.hors_saison.join(', ')}</p>
{/if}

<h3>
	Ingrédients
	<span class="doux">
		({portions === 1 ? '1 portion adulte' : `${f1(portions)} portions adultes`})
	</span>
</h3>
<ul>
	{#each Object.entries(r.ingredients) as [id, grammes] (id)}
		<li>{fiche.ingredients_noms?.[id] ?? id} : <strong>{quantite(id, grammes)}</strong></li>
	{/each}
</ul>

{#if r.etapes.length}
	<h3>Préparation</h3>
	<ol>
		{#each r.etapes as etape, i (i)}<li>{etape}</li>{/each}
	</ol>
{/if}

<p>
	<a class="bouton" href={lienExterne} target="_blank" rel="noopener noreferrer">
		{r.lien ? '🔗 Voir la recette en ligne' : '🔎 Chercher cette recette sur Marmiton'}
	</a>
</p>
<p class="doux">
	Source : {r.source}. Valeurs nutritionnelles : CIQUAL (ANSES) ; carbone : Agribalyse (ADEME).
</p>

<style>
	.chiffres {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(95px, 1fr));
		gap: 0.5rem;
		margin: 0.75rem 0 0.25rem;
	}

	.chiffres div {
		display: grid;
		text-align: center;
		background: var(--surface-2);
		border-radius: 8px;
		padding: 0.4rem;
	}

	.chiffres span {
		font-size: 0.75rem;
		color: var(--texte-doux);
	}

	h3 {
		font-size: 1rem;
		margin-top: 1rem;
	}

	li {
		margin-bottom: 0.2rem;
	}
</style>
