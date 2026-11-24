<!-- Navigation d'une semaine à l'autre ; la semaine choisie est gardée dans l'URL (?lundi=). -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { ajouterJours, depuisIso, iso, libelleSemaine } from '#lib/dates.ts';

	let { lundi }: { lundi: string } = $props();

	function aller(decalage: number) {
		const cible = iso(ajouterJours(depuisIso(lundi), 7 * decalage));
		goto(`${page.url.pathname}?lundi=${cible}`);
	}
</script>

<div class="choix">
	<button class="discret" onclick={() => aller(-1)} aria-label="Semaine précédente">◀</button>
	<strong>Semaine {libelleSemaine(lundi)}</strong>
	<button class="discret" onclick={() => aller(1)} aria-label="Semaine suivante">▶</button>
</div>

<style>
	.choix {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		background: var(--surface);
		border: 1px solid var(--bordure);
		border-radius: 999px;
		padding: 0.1rem 0.3rem;
	}
</style>
