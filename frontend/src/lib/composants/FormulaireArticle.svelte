<!--
	Formulaire d'un article du placard, commun au scan et à la modification : un ingrédient
	(quantité en grammes comestibles) ou un autre produit hors repas (nom, catégorie, paquets),
	avec une date limite facultative.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { AUTRE_PRODUIT } from '#lib/achats.ts';
	import { articleValide, type ValeursArticle } from '#lib/placard.ts';
	import type { Ingredient, PropositionProduit } from '#lib/types.ts';

	let {
		valeurs = $bindable(),
		ingredients,
		categories,
		propositions = [],
		quantitePour,
		libelleValider,
		onValider,
		actions
	}: {
		valeurs: ValeursArticle;
		ingredients: Ingredient[];
		categories: string[];
		propositions?: PropositionProduit[]; // correspondances d'un produit scanné
		quantitePour?: (ingredientId: string) => number; // quantité proposée au choix d'un ingrédient
		libelleValider: string;
		onValider: (valeurs: ValeursArticle) => void;
		actions?: Snippet; // boutons après le bouton de validation
	} = $props();

	const autresIngredients = $derived(
		ingredients.filter((i) => !propositions.some((p) => p.ingredient_id === i.id))
	);

	function choisirIngredient(id: string) {
		valeurs.ingredient_id = id;
		if (quantitePour) valeurs.quantite_g = quantitePour(id);
	}

	function valider(event: SubmitEvent) {
		event.preventDefault();
		if (articleValide(valeurs)) onValider(valeurs);
	}
</script>

{#if valeurs.ingredient_id === AUTRE_PRODUIT}
	<p class="doux">
		Produit hors repas : rangé parmi les autres produits, compté en paquets. Choisissez un
		ingrédient si les repas peuvent l'utiliser.
	</p>
{/if}
<form class="formulaire-article" onsubmit={valider}>
	<label>
		Ingrédient
		<select
			value={valeurs.ingredient_id}
			onchange={(e) => choisirIngredient((e.target as HTMLSelectElement).value)}
		>
			<option value="">Choisir…</option>
			{#if propositions.length}
				<optgroup label="Correspondances">
					{#each propositions as p (p.ingredient_id)}
						<option value={p.ingredient_id}>{p.nom}</option>
					{/each}
				</optgroup>
			{/if}
			<optgroup label="Autres ingrédients">
				{#each autresIngredients as ing (ing.id)}
					<option value={ing.id}>{ing.nom}</option>
				{/each}
			</optgroup>
			<option value={AUTRE_PRODUIT}>Autre produit (hors repas)</option>
		</select>
	</label>
	{#if valeurs.ingredient_id === AUTRE_PRODUIT}
		<label>
			Nom
			<input type="text" maxlength="120" bind:value={valeurs.nom} />
		</label>
		<label>
			Catégorie
			<select bind:value={valeurs.categorie}>
				{#each categories as c (c)}<option value={c}>{c}</option>{/each}
			</select>
		</label>
		<label>
			Paquets
			<input type="number" min="1" max="99" bind:value={valeurs.paquets} />
		</label>
	{:else}
		<label>
			Quantité (g, part comestible)
			<input type="number" min="1" step="any" bind:value={valeurs.quantite_g} />
		</label>
	{/if}
	<label>
		À utiliser avant (facultatif)
		<input type="date" bind:value={valeurs.peremption} />
	</label>
	<div class="ligne">
		<button class="principal" disabled={!articleValide(valeurs)}>{libelleValider}</button>
		{@render actions?.()}
	</div>
</form>

<style>
	/* minmax(0, 1fr) : une longue option de liste ne doit pas élargir la fenêtre. */
	.formulaire-article,
	.formulaire-article label {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 0.8rem;
	}

	.formulaire-article label {
		gap: 0.3rem;
	}

	.formulaire-article :is(input, select) {
		width: 100%;
	}
</style>
