<!-- Pastille Nutri-Score (couleurs officielles), avec la lettre écrite : jamais la couleur seule. -->
<script lang="ts">
	import type { LettreNutriScore } from '#lib/types.ts';

	let { lettre, taille = 'normale' }: { lettre: LettreNutriScore; taille?: 'normale' | 'petite' } =
		$props();

	const COULEURS: Record<LettreNutriScore, string> = {
		A: '#038141',
		B: '#85bb2f',
		C: '#fecb02',
		D: '#ee8100',
		E: '#e63e11'
	};
</script>

<span
	class="nutriscore {taille}"
	style:--fond={COULEURS[lettre]}
	style:--texte={lettre === 'C' ? '#3a2f00' : '#ffffff'}
	title={`Nutri-Score ${lettre} (indicatif, calculé pour le repas)`}
>
	<span class="libelle">Nutri-Score</span>
	<strong>{lettre}</strong>
</span>

<style>
	.nutriscore {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		border-radius: 999px;
		padding: 0.1rem 0.15rem 0.1rem 0.55rem;
		background: var(--surface-2);
		font-size: 0.75rem;
		color: var(--texte-doux);
	}

	strong {
		display: inline-grid;
		place-items: center;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		background: var(--fond);
		color: var(--texte);
		font-size: 0.85rem;
	}

	.petite {
		padding: 0;
		background: none;
	}

	.petite .libelle {
		display: none;
	}

	.petite strong {
		width: 1.25rem;
		height: 1.25rem;
		font-size: 0.75rem;
	}
</style>
