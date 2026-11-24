<!-- Bilan nutritionnel et carbone de la semaine (repas hors jokers, portion de référence). -->
<script lang="ts">
	import type { Bilan } from '#lib/types.ts';

	let { bilan }: { bilan: Bilan } = $props();

	const symboles = { ok: '✓', attention: '≈', hors_cible: '✗' };
	const economie = $derived(
		bilan.co2_reference_kg > 0 ? Math.round((1 - bilan.co2_kg / bilan.co2_reference_kg) * 100) : 0
	);
	const format = (n: number) => n.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
</script>

<section class="carte">
	<h2>Bilan de la semaine</h2>
	<div class="carbone">
		<div>
			<strong>{format(bilan.co2_kg)} kg CO₂e</strong>
			<span class="doux">pour toute la famille</span>
		</div>
		{#if economie > 0}
			<span class="badge vert">−{economie} % vs repas moyens</span>
		{/if}
	</div>
	<ul>
		{#each bilan.indicateurs as ind (ind.code)}
			<li class={ind.statut}>
				<span class="symbole" aria-hidden="true">{symboles[ind.statut]}</span>
				<span>{ind.libelle}</span>
				<span class="valeur">{format(ind.valeur)} {ind.unite}</span>
				<span class="doux cible">cible {ind.cible}</span>
			</li>
		{/each}
	</ul>
	<p class="doux">
		{bilan.nb_repas} repas à la maison, dont {bilan.nb_jokers} joker{bilan.nb_jokers > 1 ? 's' : ''}
		(non comptés dans les repères). Valeurs par repas pour un adulte de référence ; les portions sont
		adaptées à chacun.
	</p>
</section>

<style>
	.carbone {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		padding: 0.6rem 0.8rem;
		background: var(--accent-doux);
		border-radius: 8px;
		margin-bottom: 0.6rem;
	}

	.carbone div {
		display: grid;
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 0 0 0.6rem;
		display: grid;
		gap: 0.15rem;
	}

	li {
		display: grid;
		grid-template-columns: 1.2rem 1fr auto;
		gap: 0 0.4rem;
		align-items: baseline;
		font-size: 0.92rem;
	}

	.cible {
		grid-column: 2 / 4;
		font-size: 0.75rem;
	}

	.valeur {
		font-weight: 600;
	}

	.ok .symbole {
		color: var(--ok);
	}

	.attention .symbole,
	.attention .valeur {
		color: var(--attention);
	}

	.hors_cible .symbole,
	.hors_cible .valeur {
		color: var(--alerte);
	}
</style>
