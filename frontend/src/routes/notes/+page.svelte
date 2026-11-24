<!--
	Avis sur les plats : repas à venir (envie ou pas envie) et repas passés (comment c'était ?).
	Les notes guident l'algorithme pour les membres présents aux repas. Un compte enfant ne
	note que pour lui-même ; un adulte peut noter pour toute la famille (utile pour les petits).
-->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import Etoiles from '#lib/composants/Etoiles.svelte';
	import { dateCourte, depuisIso, JOURS } from '#lib/dates.ts';
	import { donnees } from '#lib/donnees.svelte.ts';
	import { session } from '#lib/session.svelte.ts';
	import type { RepasANoter } from '#lib/types.ts';

	let repas = $state<RepasANoter[]>([]);
	let erreur = $state('');
	let charge = $state(false);

	$effect(() => {
		charger();
	});

	async function charger() {
		try {
			await donnees.charger();
			repas = await api.lire<RepasANoter[]>('/notes/a-noter?jours=14&jours_a_venir=7');
			charge = true;
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function noter(r: RepasANoter, membreId: number, valeur: number) {
		try {
			await api.modifier('/notes', {
				membre_id: membreId,
				creneau_id: r.creneau_id,
				recette_id: r.recette_id,
				valeur
			});
			r.notes = { ...r.notes, [membreId]: valeur };
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	function libelle(r: RepasANoter) {
		const date = depuisIso(r.date);
		return `${JOURS[(date.getDay() + 6) % 7]} ${dateCourte(date)}, ${r.moment}`;
	}

	/** Membres dont le compte connecté peut donner l'avis pour ce repas. */
	function votants(r: RepasANoter): number[] {
		if (session.estEnfant) return r.convives.filter((m) => m === session.etat?.membre_id);
		return r.convives;
	}

	const ordre = (r: RepasANoter) => `${r.date}-${r.moment === 'midi' ? 0 : 1}`;
	const aVenir = $derived(
		repas.filter((r) => r.a_venir).sort((a, b) => ordre(a).localeCompare(ordre(b)))
	);
	const passes = $derived(repas.filter((r) => !r.a_venir));
</script>

{#snippet carteRepas(r: RepasANoter)}
	{@const membres = votants(r)}
	{@const complet = membres.every((m) => r.notes[m])}
	<article class="carte" class:complet>
		<div class="titre">
			<a href={`/plats/${r.recette_id}`}><strong>{r.nom}</strong></a>
			<span class="doux">{libelle(r)}</span>
		</div>
		<ul>
			{#each membres as membreId (membreId)}
				{@const membre = donnees.membre(membreId)}
				{#if membre}
					<li>
						<span style:color={membre.couleur}>{membre.prenom}</span>
						<Etoiles
							valeur={r.notes[membreId] ?? 0}
							libelle={`Avis de ${membre.prenom}`}
							onchoix={(v) => noter(r, membreId, v)}
						/>
					</li>
				{/if}
			{/each}
		</ul>
	</article>
{/snippet}

<h1>Avis sur les repas</h1>
{#if erreur}<p class="erreur">{erreur}</p>{/if}

<section>
	<h2>À venir : envie ou pas envie ?</h2>
	<p class="doux">
		Donnez votre avis à l'avance sur les repas des 7 prochains jours (5 étoiles = très envie, 1 =
		pas du tout). L'algorithme en tiendra compte pour les semaines suivantes.
	</p>
	{#if charge && !aVenir.length}
		<p class="carte">Aucun repas planifié dans les 7 prochains jours.</p>
	{/if}
	<div class="liste">
		{#each aVenir as r (r.creneau_id)}{@render carteRepas(r)}{/each}
	</div>
</section>

<section>
	<h2>Comment c'était ?</h2>
	<p class="doux">
		Notez les plats des deux dernières semaines : les plats appréciés reviendront plus souvent, les
		autres moins. Chacun a sa voix (les restes ne se notent pas).
	</p>
	{#if charge && !passes.length}
		<p class="carte">Aucun repas récent à noter.</p>
	{/if}
	<div class="liste">
		{#each passes as r (r.creneau_id)}{@render carteRepas(r)}{/each}
	</div>
</section>

<style>
	section {
		margin-bottom: 1.5rem;
	}

	.liste {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 0.75rem;
	}

	.complet {
		opacity: 0.7;
	}

	.titre {
		display: grid;
		margin-bottom: 0.4rem;
	}

	.titre a {
		color: inherit;
		text-decoration: none;
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 0.2rem;
	}

	li {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-weight: 600;
	}
</style>
