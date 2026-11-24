<!-- Notes a posteriori : chaque convive note les plats ; l'algorithme en tient compte. -->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import Etoiles from '#lib/composants/Etoiles.svelte';
	import { dateCourte, depuisIso, JOURS } from '#lib/dates.ts';
	import { donnees } from '#lib/donnees.svelte.ts';
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
			repas = await api.lire<RepasANoter[]>('/notes/a-noter?jours=14');
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
</script>

<h1>Comment c'était ?</h1>
<p class="doux">
	Notez les plats des deux dernières semaines : les plats appréciés reviendront plus souvent, les
	autres moins. Chaque membre a sa voix (les restes ne se notent pas).
</p>

{#if erreur}<p class="erreur">{erreur}</p>{/if}
{#if charge && !repas.length}
	<p class="carte">Aucun repas récent à noter.</p>
{/if}

<div class="liste">
	{#each repas as r (r.creneau_id)}
		{@const complet = r.convives.every((m) => r.notes[m])}
		<article class="carte" class:complet>
			<div class="titre">
				<strong>{r.nom}</strong>
				<span class="doux">{libelle(r)}</span>
			</div>
			<ul>
				{#each r.convives as membreId (membreId)}
					{@const membre = donnees.membre(membreId)}
					{#if membre}
						<li>
							<span style:color={membre.couleur}>{membre.prenom}</span>
							<Etoiles
								valeur={r.notes[membreId] ?? 0}
								libelle={`Note de ${membre.prenom}`}
								onchoix={(v) => noter(r, membreId, v)}
							/>
						</li>
					{/if}
				{/each}
			</ul>
		</article>
	{/each}
</div>

<style>
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
