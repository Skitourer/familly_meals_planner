<!-- Mon compte : identité et changement de mot de passe (pour tous les comptes). -->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import { session } from '#lib/session.svelte.ts';

	let actuel = $state('');
	let nouveau = $state('');
	let confirmation = $state('');
	let message = $state('');
	let erreur = $state('');

	async function changer(event: SubmitEvent) {
		event.preventDefault();
		message = erreur = '';
		if (nouveau !== confirmation) {
			erreur = 'Les deux mots de passe ne correspondent pas.';
			return;
		}
		try {
			await api.modifier('/session/mot-de-passe', { actuel, nouveau });
			message = 'Mot de passe changé.';
			actuel = nouveau = confirmation = '';
		} catch (e) {
			erreur = messageErreur(e);
		}
	}
</script>

<h1>Mon compte</h1>
<p>
	Connecté en tant que <strong>{session.etat?.identifiant}</strong>
	({session.estAdulte ? 'adulte' : 'enfant'}{session.etat?.prenom
		? `, ${session.etat.prenom}`
		: ''}).
</p>

<form class="carte" onsubmit={changer}>
	<h2>Changer mon mot de passe</h2>
	<label>
		Mot de passe actuel
		<input type="password" bind:value={actuel} autocomplete="current-password" required />
	</label>
	<label>
		Nouveau mot de passe (6 caractères au moins)
		<input
			type="password"
			bind:value={nouveau}
			autocomplete="new-password"
			minlength="6"
			required
		/>
	</label>
	<label>
		Confirmation
		<input type="password" bind:value={confirmation} autocomplete="new-password" required />
	</label>
	{#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}
	{#if message}<p class="badge vert">{message}</p>{/if}
	<button class="principal">Enregistrer</button>
</form>

<style>
	form {
		display: grid;
		gap: 0.7rem;
		max-width: 420px;
	}
</style>
