<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, messageErreur } from '#lib/api.ts';

	let motDePasse = $state('');
	let erreur = $state('');
	let enCours = $state(false);

	async function connecter(event: SubmitEvent) {
		event.preventDefault();
		enCours = true;
		erreur = '';
		try {
			await api.creer('/session', { mot_de_passe: motDePasse });
			await goto('/');
		} catch (e) {
			erreur = messageErreur(e);
		} finally {
			enCours = false;
		}
	}
</script>

<div class="page">
	<form class="carte" onsubmit={connecter}>
		<div class="logo" aria-hidden="true">🥗</div>
		<h1>Menu Famille</h1>
		<p class="doux">Des repas équilibrés, de saison et bas carbone.</p>
		<label>
			Mot de passe de la famille
			<!-- svelte-ignore a11y_autofocus -->
			<input type="password" bind:value={motDePasse} autocomplete="current-password" autofocus />
		</label>
		{#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}
		<button class="principal" disabled={enCours || !motDePasse}>Entrer</button>
	</form>
</div>

<style>
	.page {
		min-height: 100vh;
		display: grid;
		place-items: center;
		padding: 1rem;
	}

	form {
		display: grid;
		gap: 0.9rem;
		width: min(360px, 100%);
		text-align: center;
	}

	.logo {
		font-size: 3rem;
	}

	label {
		text-align: left;
	}
</style>
