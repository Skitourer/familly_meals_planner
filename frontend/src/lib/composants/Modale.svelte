<!-- Fenêtre modale accessible (élément <dialog> natif). -->
<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		titre,
		ouverte = $bindable(false),
		children
	}: { titre: string; ouverte: boolean; children: Snippet } = $props();

	let dialogue: HTMLDialogElement;

	$effect(() => {
		if (ouverte && !dialogue.open) dialogue.showModal();
		if (!ouverte && dialogue.open) dialogue.close();
	});
</script>

<dialog bind:this={dialogue} onclose={() => (ouverte = false)}>
	<header>
		<h2>{titre}</h2>
		<button class="discret" onclick={() => (ouverte = false)} aria-label="Fermer">✕</button>
	</header>
	{#if ouverte}
		<div class="contenu">{@render children()}</div>
	{/if}
</dialog>

<style>
	dialog {
		width: min(680px, calc(100vw - 2rem));
		max-height: calc(100vh - 3rem);
		border: 1px solid var(--bordure);
		border-radius: var(--rayon);
		background: var(--surface);
		color: var(--texte);
		padding: 0;
	}

	dialog::backdrop {
		background: rgb(0 0 0 / 40%);
	}

	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.8rem 1rem;
		border-bottom: 1px solid var(--bordure);
		position: sticky;
		top: 0;
		background: var(--surface);
	}

	h2 {
		margin: 0;
	}

	.contenu {
		padding: 1rem;
	}
</style>
