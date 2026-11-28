<!-- Pastilles compactes Nutri-Score, NOVA et Green-Score ; détail au survol ou au toucher. -->
<script lang="ts">
	import { pastillesNotes, type NotesProduit } from '#lib/notes-produit.ts';

	let { notes }: { notes: NotesProduit } = $props();

	const pastilles = $derived(pastillesNotes(notes));
	let ouvert = $state(false);
</script>

<button
	type="button"
	class="notes"
	aria-expanded={ouvert}
	aria-label={pastilles.map((p) => p.detail).join(' ; ')}
	title={pastilles.map((p) => p.detail).join('\n')}
	onclick={() => (ouvert = !ouvert)}
>
	{#each pastilles as p (p.libelle)}
		<span class="pastille" style:--fond={p.fond} style:--texte={p.texte}>{p.valeur}</span>
	{/each}
</button>
{#if ouvert}
	<ul class="detail">
		{#each pastilles as p (p.libelle)}<li>{p.detail}</li>{/each}
	</ul>
{/if}

<style>
	.notes {
		display: inline-flex;
		gap: 0.15rem;
		padding: 0.1rem;
		border: none;
		background: none;
		cursor: pointer;
		vertical-align: middle;
	}

	.pastille {
		display: inline-grid;
		place-items: center;
		min-width: 1.15rem;
		height: 1.15rem;
		border-radius: 0.3rem;
		background: var(--fond);
		color: var(--texte);
		font-size: 0.7rem;
		font-weight: 700;
	}

	.detail {
		margin: 0.2rem 0 0;
		padding-left: 1rem;
		font-size: 0.8rem;
		color: var(--texte-doux);
	}
</style>
