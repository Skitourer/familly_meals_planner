<script lang="ts">
	import '../app.css';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';

	let { children } = $props();

	const liens = [
		{ href: '/', libelle: 'Semaine', icone: '📅' },
		{ href: '/courses', libelle: 'Courses', icone: '🛒' },
		{ href: '/notes', libelle: 'Notes', icone: '⭐' },
		{ href: '/placard', libelle: 'Placard', icone: '🥫' },
		{ href: '/recettes', libelle: 'Recettes', icone: '📖' },
		{ href: '/famille', libelle: 'Famille', icone: '👪' }
	];

	let verifie = $state(false);
	const surConnexion = $derived(page.url.pathname === '/connexion');

	$effect(() => {
		api.lire<{ connecte: boolean }>('/session').then(({ connecte }) => {
			verifie = true;
			if (!connecte && !surConnexion) goto('/connexion');
		});
	});

	async function deconnecter() {
		await api.supprimer('/session');
		await goto('/connexion');
	}
</script>

{#if surConnexion}
	{@render children()}
{:else if verifie}
	<header>
		<a class="marque" href="/">🥗 Menu Famille</a>
		<nav aria-label="Navigation principale">
			{#each liens as lien (lien.href)}
				<a href={lien.href} aria-current={page.url.pathname === lien.href ? 'page' : undefined}>
					<span aria-hidden="true">{lien.icone}</span>
					<span>{lien.libelle}</span>
				</a>
			{/each}
		</nav>
		<button class="discret deconnexion" onclick={deconnecter} title="Se déconnecter">⎋</button>
	</header>
	<main>
		{@render children()}
	</main>
{/if}

<style>
	header {
		position: sticky;
		top: 0;
		z-index: 10;
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.5rem 1rem;
		background: var(--surface);
		border-bottom: 1px solid var(--bordure);
	}

	.marque {
		font-weight: 700;
		text-decoration: none;
		color: var(--accent);
		white-space: nowrap;
	}

	nav {
		display: flex;
		gap: 0.25rem;
		flex: 1;
	}

	nav a {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.4rem 0.75rem;
		border-radius: 999px;
		text-decoration: none;
		color: var(--texte-doux);
	}

	nav a[aria-current='page'] {
		background: var(--accent-doux);
		color: var(--accent);
		font-weight: 600;
	}

	main {
		max-width: 1200px;
		margin: 0 auto;
		padding: 1rem 1rem 6rem;
	}

	/* Téléphone : barre de navigation en bas de l'écran, comme une application. */
	@media (max-width: 760px) {
		header {
			justify-content: space-between;
		}

		nav {
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			justify-content: space-around;
			background: var(--surface);
			border-top: 1px solid var(--bordure);
			padding: 0.25rem 0 calc(0.25rem + env(safe-area-inset-bottom));
		}

		nav a {
			flex-direction: column;
			gap: 0;
			font-size: 0.7rem;
			padding: 0.3rem 0.4rem;
		}

		nav a span:first-child {
			font-size: 1.2rem;
		}
	}
</style>
