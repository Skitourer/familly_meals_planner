<!--
	Page principale : planification de la semaine (scénario du vendredi soir).
	1. Indiquer qui mange à chaque repas et choisir les jokers ;
	2. Générer les repas ; 3. Ajuster un repas si besoin ; 4. Passer aux courses.
-->
<script lang="ts">
	import { page } from '$app/state';
	import { api, messageErreur } from '#lib/api.ts';
	import BilanSemaine from '#lib/composants/BilanSemaine.svelte';
	import CarteCreneau from '#lib/composants/CarteCreneau.svelte';
	import ChoixRepas from '#lib/composants/ChoixRepas.svelte';
	import ChoixSemaine from '#lib/composants/ChoixSemaine.svelte';
	import Modale from '#lib/composants/Modale.svelte';
	import { ajouterJours, dateCourte, depuisIso, JOURS } from '#lib/dates.ts';
	import { donnees } from '#lib/donnees.svelte.ts';
	import { lundiDepuisUrl } from '#lib/semaine.ts';
	import type { Bilan, Creneau, Semaine } from '#lib/types.ts';

	const lundi = $derived(lundiDepuisUrl(page.url));
	let semaine = $state<Semaine | null>(null);
	let bilan = $state<Bilan | null>(null);
	let erreur = $state('');
	let enCours = $state(false);
	let aChanger = $state<Creneau | null>(null);
	let modaleOuverte = $state(false);

	const LIBELLES_ECARTS: Record<string, string> = {
		fibres_min: 'fibres',
		sel_max: 'sel',
		fruits_legumes_min: 'fruits et légumes',
		poisson_min: 'poisson',
		poisson_gras_min: 'poisson gras',
		legumineuses_min: 'légumineuses',
		viande_rouge_max: 'viande rouge',
		charcuterie_max: 'charcuterie',
		proteines_min: 'protéines',
		proteines_max: 'protéines',
		lipides_max: 'lipides',
		ags_max: 'graisses saturées'
	};

	$effect(() => {
		charger(lundi);
	});

	async function charger(date: string) {
		erreur = '';
		try {
			await donnees.charger();
			semaine = await api.lire<Semaine>(`/semaines/${date}`);
			await chargerBilan();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function chargerBilan() {
		bilan = semaine?.generee_le ? await api.lire<Bilan>(`/semaines/${lundi}/bilan`) : null;
	}

	async function generer(varier: boolean) {
		enCours = true;
		erreur = '';
		try {
			semaine = await api.creer<Semaine>(`/semaines/${lundi}/generer?varier=${varier}`);
			await chargerBilan();
		} catch (e) {
			erreur = messageErreur(e);
		} finally {
			enCours = false;
		}
	}

	async function modifier(creneau: Creneau, modification: Partial<Creneau>) {
		try {
			semaine = await api.modifier<Semaine>(
				`/semaines/${lundi}/creneaux/${creneau.jour}/${creneau.moment}`,
				modification
			);
			await chargerBilan();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	function ouvrirChoix(creneau: Creneau) {
		aChanger = creneau;
		modaleOuverte = true;
	}

	const ecarts = $derived(
		Object.keys(semaine?.ecarts ?? {})
			.filter((cle) => !cle.startsWith('energie'))
			.map((cle) => LIBELLES_ECARTS[cle] ?? cle)
	);
	const parJour = $derived(
		JOURS.map((nom, jour) => ({
			nom,
			date: dateCourte(ajouterJours(depuisIso(lundi), jour)),
			creneaux: semaine?.creneaux.filter((c) => c.jour === jour) ?? []
		}))
	);
</script>

<div class="entete">
	<div>
		<h1>Les repas de la semaine</h1>
		<ChoixSemaine {lundi} />
	</div>
	<div class="ligne">
		{#if semaine?.generee_le}
			<button onclick={() => generer(true)} disabled={enCours}>🎲 Autre proposition</button>
			<a class="bouton" href={`/api/semaines/${lundi}/menu.pdf`} target="_blank" rel="noopener">
				🖨 Menu PDF
			</a>
			<a class="bouton principal" href={`/courses?lundi=${lundi}`}>🛒 Liste de courses</a>
		{:else}
			<button class="principal" onclick={() => generer(false)} disabled={enCours || !semaine}>
				✨ Générer les repas
			</button>
		{/if}
	</div>
</div>

{#if !donnees.membresActifs.length && semaine}
	<p class="carte">
		👋 Commencez par <a href="/famille">ajouter les membres de la famille</a> : leurs besoins servent
		à calculer les portions.
	</p>
{/if}

<p class="doux aide">
	Cliquez sur les initiales pour indiquer qui mange à la maison, « + » pour des invités, et 🎉 pour
	un repas joker. Les plats verrouillés 🔒 sont conservés quand vous régénérez.
</p>

{#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}
{#if enCours}<p class="doux">Recherche de la meilleure combinaison de repas…</p>{/if}
{#if ecarts.length}
	<p class="erreur">
		Certains repères ne sont pas atteints cette semaine ({ecarts.join(', ')}) : essayez une autre
		proposition ou ajoutez des plats.
	</p>
{/if}

<div class="mise-en-page">
	<div class="grille">
		{#each parJour as jour (jour.nom)}
			<section class="jour">
				<h2>{jour.nom} <span class="doux">{jour.date}</span></h2>
				{#each jour.creneaux as creneau (creneau.id)}
					<CarteCreneau
						{creneau}
						onmodifier={(m) => modifier(creneau, m)}
						onchanger={() => ouvrirChoix(creneau)}
					/>
				{/each}
			</section>
		{/each}
	</div>
	{#if bilan}
		<aside><BilanSemaine {bilan} /></aside>
	{/if}
</div>

<Modale titre="Changer ce repas" bind:ouverte={modaleOuverte}>
	{#if aChanger}
		<ChoixRepas
			{lundi}
			creneau={aChanger}
			onchoix={async (m) => {
				if (aChanger) await modifier(aChanger, m);
				if (m.plat_id) modaleOuverte = false;
			}}
		/>
	{/if}
</Modale>

<style>
	.entete {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		flex-wrap: wrap;
		gap: 1rem;
		margin-bottom: 0.5rem;
	}

	.aide {
		margin: 0.5rem 0 1rem;
	}

	.mise-en-page {
		display: grid;
		grid-template-columns: 1fr 300px;
		gap: 1rem;
		align-items: start;
	}

	.grille {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 0.75rem;
	}

	.jour {
		display: grid;
		gap: 0.4rem;
		align-content: start;
	}

	.jour h2 {
		font-size: 1rem;
		margin: 0;
	}

	aside {
		position: sticky;
		top: 4rem;
	}

	@media (max-width: 1000px) {
		.mise-en-page {
			grid-template-columns: 1fr;
		}

		aside {
			position: static;
		}
	}
</style>
