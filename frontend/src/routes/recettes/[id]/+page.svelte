<!--
	Page d'une recette : /recettes/<id>?portions=3.4
	Depuis le planning, `portions` est la somme des portions des convives du repas.
-->
<script lang="ts">
	import { page } from '$app/state';
	import { messageErreur } from '#lib/api.ts';
	import DetailRecette from '#lib/composants/DetailRecette.svelte';
	import { donnees } from '#lib/donnees.svelte.ts';

	let erreur = $state('');

	$effect(() => {
		donnees.charger().catch((e) => (erreur = messageErreur(e)));
	});

	const fiche = $derived(donnees.parId.get(page.params.id ?? ''));
	const portions = $derived.by(() => {
		const valeur = Number(page.url.searchParams.get('portions'));
		return Number.isFinite(valeur) && valeur > 0 ? valeur : 1;
	});
</script>

<p>
	<a href="/recettes" onclick={(e) => history.length > 1 && (e.preventDefault(), history.back())}>
		← Retour
	</a>
</p>

{#if erreur}<p class="erreur">{erreur}</p>{/if}

{#if fiche}
	<article class="carte">
		<h1>{fiche.recette.nom}</h1>
		<DetailRecette {fiche} {portions} />
	</article>
{:else if donnees.recettes.length}
	<p class="erreur">Recette introuvable.</p>
{/if}

<style>
	article {
		max-width: 760px;
	}
</style>
