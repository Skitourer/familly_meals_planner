<!-- Initiale colorée d'un membre ; cliquable pour indiquer sa présence à un repas. -->
<script lang="ts">
	import type { Membre } from '#lib/types.ts';

	let {
		membre,
		present = true,
		onclick
	}: { membre: Membre; present?: boolean; onclick?: () => void } = $props();
</script>

<button
	class="pastille"
	class:absent={!present}
	style:--couleur={membre.couleur}
	{onclick}
	disabled={!onclick}
	aria-pressed={present}
	title={`${membre.prenom} : ${present ? 'présent' : 'absent'}`}
>
	{membre.prenom.slice(0, 1)}
</button>

<style>
	.pastille {
		width: 1.8rem;
		height: 1.8rem;
		padding: 0;
		border-radius: 50%;
		border: 2px solid var(--couleur);
		background: var(--couleur);
		color: white;
		font-weight: 700;
		font-size: 0.8rem;
	}

	.pastille.absent {
		background: transparent;
		color: var(--couleur);
		opacity: 0.45;
		border-style: dashed;
	}

	.pastille:disabled {
		cursor: default;
		opacity: 1;
	}
</style>
