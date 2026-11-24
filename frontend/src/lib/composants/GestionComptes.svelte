<!--
	Comptes de connexion (adultes seulement) : un compte adulte a tous les droits ; un compte
	enfant, relié à un membre, consulte le menu et donne son avis sur les repas.
-->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import { donnees } from '#lib/donnees.svelte.ts';
	import { session } from '#lib/session.svelte.ts';
	import type { Compte } from '#lib/types.ts';

	interface Edition {
		id?: number;
		identifiant: string;
		role: 'adulte' | 'enfant';
		membre_id: number | null;
		actif: boolean;
		mot_de_passe: string;
	}

	let comptes = $state<Compte[]>([]);
	let edition = $state<Edition | null>(null);
	let erreur = $state('');

	$effect(() => {
		charger();
	});

	async function charger() {
		try {
			comptes = await api.lire<Compte[]>('/comptes');
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	function nouveau(role: 'adulte' | 'enfant') {
		edition = { identifiant: '', role, membre_id: null, actif: true, mot_de_passe: '' };
	}

	function modifier(c: Compte) {
		edition = { ...c, mot_de_passe: '' };
	}

	async function enregistrer(event: SubmitEvent) {
		event.preventDefault();
		if (!edition) return;
		const { id, ...corps } = edition;
		const envoi = { ...corps, mot_de_passe: corps.mot_de_passe || null };
		erreur = '';
		try {
			if (id) await api.modifier(`/comptes/${id}`, envoi);
			else await api.creer('/comptes', envoi);
			edition = null;
			await charger();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function supprimer(c: Compte) {
		if (!confirm(`Supprimer le compte « ${c.identifiant} » ?`)) return;
		try {
			await api.supprimer(`/comptes/${c.id}`);
			edition = null;
			await charger();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	const prenom = (id: number | null) => (id ? (donnees.membre(id)?.prenom ?? '?') : '—');
</script>

<section class="carte">
	<h2>Comptes de connexion</h2>
	<p class="doux">
		Chaque adulte peut avoir son compte (tous les droits). Un compte <strong>enfant</strong>, relié
		à un membre, peut seulement consulter le menu et donner son avis sur les repas passés et à
		venir.
	</p>
	{#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}

	<table>
		<thead>
			<tr><th>Identifiant</th><th>Type</th><th>Membre</th><th></th></tr>
		</thead>
		<tbody>
			{#each comptes as c (c.id)}
				<tr class:inactif={!c.actif}>
					<td>
						{c.identifiant}
						{#if c.identifiant === session.etat?.identifiant}<span class="badge">vous</span>{/if}
						{#if !c.actif}<span class="badge">désactivé</span>{/if}
					</td>
					<td>{c.role === 'adulte' ? '🧑 Adulte' : '🧒 Enfant'}</td>
					<td>{prenom(c.membre_id)}</td>
					<td class="actions">
						<button class="discret" onclick={() => modifier(c)}>✏️</button>
						{#if c.identifiant !== session.etat?.identifiant}
							<button class="discret" onclick={() => supprimer(c)} aria-label="Supprimer">🗑</button>
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>

	<div class="ligne ajout">
		<button onclick={() => nouveau('adulte')}>＋ Compte adulte</button>
		<button onclick={() => nouveau('enfant')}>＋ Compte enfant</button>
	</div>

	{#if edition}
		<form class="formulaire" onsubmit={enregistrer}>
			<h3>{edition.id ? `Modifier « ${edition.identifiant} »` : 'Nouveau compte'}</h3>
			<label>
				Identifiant (lettres, chiffres, . _ -)
				<input
					bind:value={edition.identifiant}
					required
					minlength="2"
					maxlength="40"
					pattern="[A-Za-z0-9._\-]+"
					autocapitalize="none"
				/>
			</label>
			<label>
				Type
				<select bind:value={edition.role}>
					<option value="adulte">Adulte (tous les droits)</option>
					<option value="enfant">Enfant (menu et avis)</option>
				</select>
			</label>
			<label>
				Membre de la famille {edition.role === 'enfant' ? '(obligatoire)' : '(facultatif)'}
				<select bind:value={edition.membre_id} required={edition.role === 'enfant'}>
					<option value={null}>—</option>
					{#each donnees.membres as m (m.id)}
						<option value={m.id}>{m.prenom}</option>
					{/each}
				</select>
			</label>
			<label>
				{edition.id ? 'Nouveau mot de passe (laisser vide pour ne pas changer)' : 'Mot de passe'}
				<input
					type="password"
					bind:value={edition.mot_de_passe}
					autocomplete="new-password"
					minlength="6"
					required={!edition.id}
				/>
			</label>
			<label class="case">
				<input type="checkbox" bind:checked={edition.actif} /> Compte actif
			</label>
			<div class="ligne">
				<button class="principal">Enregistrer</button>
				<button type="button" onclick={() => (edition = null)}>Annuler</button>
			</div>
		</form>
	{/if}
</section>

<style>
	section {
		max-width: 720px;
		margin-bottom: 1rem;
	}

	table {
		width: 100%;
		border-collapse: collapse;
	}

	th,
	td {
		text-align: left;
		padding: 0.4rem 0.3rem;
		border-bottom: 1px solid var(--bordure);
	}

	th {
		font-size: 0.8rem;
		color: var(--texte-doux);
	}

	.actions {
		text-align: right;
		white-space: nowrap;
	}

	.inactif {
		opacity: 0.6;
	}

	.ajout {
		margin-top: 0.75rem;
	}

	.formulaire {
		display: grid;
		gap: 0.6rem;
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--bordure);
	}

	h3 {
		font-size: 1rem;
		margin: 0;
	}

	.case {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}
</style>
