<!-- Membres de la famille (besoins énergétiques) et réglages de l'algorithme. -->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import { donnees } from '#lib/donnees.svelte.ts';
	import type { Membre, MembreEntree, Reglages } from '#lib/types.ts';

	const MODES = {
		sedentaire: 'Sédentaire (assis la plupart du temps)',
		modere: 'Modéré (debout, trajets à pied ou à vélo)',
		actif: 'Actif (métier physique, enfant très actif)'
	};
	const COULEURS = ['#2f6b40', '#b4570f', '#2b5fa8', '#8a3fa0', '#b3362b', '#0f7c80'];
	const NIVEAUX = ['Ignoré', 'Faible', 'Moyen', 'Fort'];

	let edition = $state<(MembreEntree & { id?: number }) | null>(null);
	let reglages = $state<Reglages | null>(null);
	let erreur = $state('');
	let enregistre = $state(false);

	$effect(() => {
		donnees.chargerMembres().catch((e) => (erreur = messageErreur(e)));
		api.lire<Reglages>('/reglages').then((r) => (reglages = r));
	});

	function nouveau() {
		edition = {
			prenom: '',
			couleur: COULEURS[donnees.membres.length % COULEURS.length],
			date_naissance: '1990-01-01',
			sexe: 'F',
			poids_kg: 60,
			mode_de_vie: 'sedentaire',
			heures_sport_semaine: 0,
			actif: true
		};
	}

	function modifier(m: Membre) {
		const { id, prenom, couleur, date_naissance, sexe, poids_kg, mode_de_vie } = m;
		edition = { id, prenom, couleur, date_naissance, sexe, poids_kg, mode_de_vie,
			heures_sport_semaine: m.heures_sport_semaine, actif: m.actif }; // prettier-ignore
	}

	async function enregistrer(event: SubmitEvent) {
		event.preventDefault();
		if (!edition) return;
		const { id, ...corps } = edition;
		try {
			if (id) await api.modifier(`/membres/${id}`, corps);
			else await api.creer('/membres', corps);
			edition = null;
			await donnees.chargerMembres();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function supprimer() {
		if (!edition?.id) return;
		const message =
			`Supprimer définitivement ${edition.prenom} ? Ses notes seront effacées et il ou elle ` +
			`sera retiré(e) des repas planifiés.

Pour garder son historique, décochez plutôt ` +
			`« Mange à la maison ».`;
		if (!confirm(message)) return;
		try {
			await api.supprimer(`/membres/${edition.id}`);
			edition = null;
			await donnees.chargerMembres();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function enregistrerReglages() {
		if (!reglages) return;
		reglages = await api.modifier<Reglages>('/reglages', reglages);
		enregistre = true;
		setTimeout(() => (enregistre = false), 1500);
	}
</script>

<h1>La famille</h1>
<p class="doux">
	Âge, poids, sexe et activité physique servent à estimer le besoin énergétique de chacun (équations
	de Henry) : les portions de la liste de courses sont adaptées à chaque convive.
</p>

{#if erreur}<p class="erreur">{erreur}</p>{/if}

<div class="membres">
	{#each donnees.membres as m (m.id)}
		<article class="carte" class:inactif={!m.actif} style:--couleur={m.couleur}>
			<div class="ligne">
				<span class="rond">{m.prenom.slice(0, 1)}</span>
				<div>
					<strong>{m.prenom}</strong>
					<div class="doux">
						{m.age} ans · {m.poids_kg} kg · {m.heures_sport_semaine} h de sport/sem.
					</div>
				</div>
			</div>
			<p>
				<strong>{m.besoin_kcal} kcal/jour</strong>
				<span class="doux">· portion × {m.coefficient_portion.toLocaleString('fr-FR')}</span>
			</p>
			{#if !m.actif}<span class="badge">ne mange plus à la maison</span>{/if}
			<button class="discret" onclick={() => modifier(m)}>✏️ Modifier</button>
		</article>
	{/each}
	<button class="ajout" onclick={nouveau}>＋ Ajouter un membre</button>
</div>

{#if edition}
	<form class="carte formulaire" onsubmit={enregistrer}>
		<h2>{edition.id ? `Modifier ${edition.prenom}` : 'Nouveau membre'}</h2>
		<label>Prénom <input required maxlength="40" bind:value={edition.prenom} /></label>
		<label>
			Date de naissance <input type="date" required bind:value={edition.date_naissance} />
		</label>
		<label>
			Sexe
			<select bind:value={edition.sexe}>
				<option value="F">Femme</option>
				<option value="H">Homme</option>
			</select>
		</label>
		<label>
			Poids (kg) <input type="number" min="3" max="250" step="0.5" bind:value={edition.poids_kg} />
		</label>
		<label>
			Mode de vie
			<select bind:value={edition.mode_de_vie}>
				{#each Object.entries(MODES) as [valeur, texte] (valeur)}
					<option value={valeur}>{texte}</option>
				{/each}
			</select>
		</label>
		<label>
			Sport (heures par semaine)
			<input type="number" min="0" max="40" step="0.5" bind:value={edition.heures_sport_semaine} />
		</label>
		<label>Couleur <input type="color" bind:value={edition.couleur} /></label>
		<label class="case">
			<input type="checkbox" bind:checked={edition.actif} /> Mange à la maison (décocher s'il est parti)
		</label>
		<div class="ligne">
			<button class="principal">Enregistrer</button>
			<button type="button" onclick={() => (edition = null)}>Annuler</button>
			{#if edition.id}
				<button type="button" class="supprimer" onclick={supprimer}>🗑 Supprimer</button>
			{/if}
		</div>
	</form>
{/if}

{#if reglages}
	<section class="carte reglages">
		<h2>Réglages de l'algorithme</h2>
		<p class="doux">
			La nutrition reste toujours prioritaire ; ces réglages départagent les plats.
		</p>
		<label>
			Importance du budget : <strong>{NIVEAUX[reglages.priorite_budget]}</strong>
			<input
				type="range"
				min="0"
				max="3"
				bind:value={reglages.priorite_budget}
				onchange={enregistrerReglages}
			/>
		</label>
		<label>
			Importance de l'empreinte carbone : <strong>{NIVEAUX[reglages.priorite_carbone]}</strong>
			<input
				type="range"
				min="0"
				max="3"
				bind:value={reglages.priorite_carbone}
				onchange={enregistrerReglages}
			/>
		</label>
		<label>
			Envie de cuisiner en lot (soupes, mijotés) : <strong>
				{NIVEAUX[reglages.cuisine_en_lot]}
			</strong>
			<input
				type="range"
				min="0"
				max="3"
				bind:value={reglages.cuisine_en_lot}
				onchange={enregistrerReglages}
			/>
		</label>
		<label>
			Repas de restes au plus par semaine : <strong>{reglages.restes_max}</strong>
			<input
				type="range"
				min="0"
				max="8"
				bind:value={reglages.restes_max}
				onchange={enregistrerReglages}
			/>
		</label>
		{#if enregistre}<span class="badge vert">Enregistré</span>{/if}
	</section>
{/if}

<style>
	.membres {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.membres article {
		border-top: 4px solid var(--couleur);
	}

	.inactif {
		opacity: 0.6;
	}

	.rond {
		display: grid;
		place-items: center;
		width: 2.4rem;
		height: 2.4rem;
		border-radius: 50%;
		background: var(--couleur);
		color: white;
		font-weight: 700;
	}

	p {
		margin: 0.5rem 0;
	}

	.ajout {
		border-style: dashed;
		border-radius: var(--rayon);
		min-height: 6rem;
	}

	.formulaire,
	.reglages {
		display: grid;
		gap: 0.7rem;
		max-width: 520px;
		margin-bottom: 1rem;
	}

	.supprimer {
		margin-left: auto;
		color: var(--alerte);
		border-color: var(--alerte);
	}

	.case {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}
</style>
