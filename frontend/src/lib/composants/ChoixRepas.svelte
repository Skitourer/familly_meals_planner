<!-- Remplacement d'un plat : meilleures alternatives calculées, ou choix libre dans le catalogue. -->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import { donnees } from '#lib/donnees.svelte.ts';
	import type { Alternative, Creneau } from '#lib/types.ts';

	let {
		lundi,
		creneau,
		onchoix
	}: {
		lundi: string;
		creneau: Creneau;
		onchoix: (modification: { plat_id?: string; dessert_id?: string }) => void;
	} = $props();

	let alternatives = $state<Alternative[] | null>(null);
	let erreur = $state('');
	let recherche = $state('');

	$effect(() => {
		api
			.lire<Alternative[]>(
				`/semaines/${lundi}/creneaux/${creneau.jour}/${creneau.moment}/alternatives`
			)
			.then((a) => (alternatives = a))
			.catch((e) => (erreur = messageErreur(e)));
	});

	const filtre = $derived(recherche.trim().toLowerCase());
	const plats = $derived(
		donnees.recettes.filter(
			(f) =>
				f.recette.type === 'plat' &&
				(creneau.joker || !f.recette.plaisir) &&
				f.recette.nom.toLowerCase().includes(filtre)
		)
	);
	const desserts = $derived(
		donnees.recettes.filter(
			(f) => f.recette.type === 'dessert' && (creneau.joker || !f.recette.plaisir)
		)
	);
</script>

<section>
	<h3>Les mieux adaptés à la semaine</h3>
	<p class="doux">Calculés en gardant les autres repas : nutrition, saison, goûts, carbone.</p>
	{#if erreur}
		<p class="erreur">{erreur}</p>
	{:else if !alternatives}
		<p class="doux">Calcul en cours…</p>
	{:else}
		<ul class="liste">
			{#each alternatives as alt, i (alt.plat_id)}
				{@const fiche = donnees.parId.get(alt.plat_id)}
				<li>
					<button onclick={() => onchoix({ plat_id: alt.plat_id })}>
						<span>{i === 0 ? '🥇 ' : ''}{fiche?.recette.nom}</span>
						<span class="doux">
							{fiche?.nutriments.energie_kcal.toFixed(0)} kcal · {fiche?.co2_kg.toFixed(1)} kg CO₂e
						</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<section>
	<h3>Ou choisir un autre plat</h3>
	<input type="search" placeholder="Rechercher un plat…" bind:value={recherche} />
	<ul class="liste defilante">
		{#each plats as fiche (fiche.recette.id)}
			<li>
				<button onclick={() => onchoix({ plat_id: fiche.recette.id })}>
					<span>
						{fiche.recette.nom}
						{#if !fiche.de_saison}<span class="badge alerte">hors saison</span>{/if}
						{#if fiche.recette.plaisir}<span class="badge joker">plaisir</span>{/if}
					</span>
					{#if fiche.note_famille}<span class="doux">★ {fiche.note_famille}</span>{/if}
				</button>
			</li>
		{/each}
	</ul>
</section>

<section>
	<h3>Dessert</h3>
	<select
		value={creneau.dessert_id}
		onchange={(e) => onchoix({ dessert_id: (e.target as HTMLSelectElement).value })}
	>
		{#each desserts as fiche (fiche.recette.id)}
			<option value={fiche.recette.id}>
				{fiche.recette.nom}{fiche.de_saison ? '' : ' (hors saison)'}
			</option>
		{/each}
	</select>
</section>

<style>
	section {
		margin-bottom: 1.2rem;
	}

	h3 {
		font-size: 1rem;
		margin-bottom: 0.2rem;
	}

	.liste {
		list-style: none;
		padding: 0;
		margin: 0.5rem 0 0;
		display: grid;
		gap: 0.3rem;
	}

	.defilante {
		max-height: 16rem;
		overflow-y: auto;
	}

	.liste button {
		width: 100%;
		display: flex;
		justify-content: space-between;
		gap: 0.5rem;
		text-align: left;
		border-radius: 8px;
	}

	input[type='search'] {
		width: 100%;
	}
</style>
