<!-- Note de 1 à 5 étoiles, cliquable. -->
<script lang="ts">
	let {
		valeur = 0,
		libelle,
		onchoix
	}: { valeur?: number; libelle: string; onchoix: (note: number) => void } = $props();
</script>

<div class="etoiles" role="radiogroup" aria-label={libelle}>
	{#each [1, 2, 3, 4, 5] as note (note)}
		<button
			class="discret"
			class:pleine={note <= valeur}
			role="radio"
			aria-checked={note === valeur}
			aria-label={`${note} sur 5`}
			onclick={() => onchoix(note)}
		>
			★
		</button>
	{/each}
</div>

<style>
	.etoiles {
		display: inline-flex;
	}

	button {
		font-size: 1.4rem;
		padding: 0 0.1rem;
		color: var(--bordure);
		line-height: 1;
	}

	button.pleine {
		color: #e0a100;
	}
</style>
