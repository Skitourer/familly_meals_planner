<!-- Un repas de la semaine : présences, joker, plat proposé et actions. -->
<script lang="ts">
	import { donnees } from '#lib/donnees.svelte.ts';
	import { JOURS } from '#lib/dates.ts';
	import type { Creneau } from '#lib/types.ts';
	import Pastille from './Pastille.svelte';

	let {
		creneau,
		onmodifier,
		onchanger
	}: {
		creneau: Creneau;
		onmodifier: (modification: Partial<Creneau>) => void;
		onchanger: () => void;
	} = $props();

	const personnes = $derived(creneau.convives.length + creneau.invites);
	const aLaMaison = $derived(personnes > 0);
	const fiche = $derived(creneau.plat_id ? donnees.parId.get(creneau.plat_id) : undefined);
	let details = $state(false);

	// Portions du repas : somme des portions des convives (un invité compte pour un adulte).
	const portions = $derived(
		Math.round(
			(creneau.convives.reduce((s, id) => s + (donnees.membre(id)?.coefficient_portion ?? 1), 0) +
				creneau.invites) *
				100
		) / 100
	);

	function basculer(id: number) {
		const convives = creneau.convives.includes(id)
			? creneau.convives.filter((c) => c !== id)
			: [...creneau.convives, id];
		onmodifier({ convives });
	}

	function origineRestes(cle: string): string {
		const [jour, moment] = cle.split('-');
		return `${JOURS[Number(jour)].toLowerCase()} ${moment}`;
	}
</script>

<article class="creneau" class:joker={creneau.joker} class:absent={!aLaMaison}>
	<div class="entete">
		<span class="moment">{creneau.moment === 'midi' ? '☀️ Midi' : '🌙 Soir'}</span>
		<div class="presences">
			{#each donnees.membresActifs as membre (membre.id)}
				<Pastille
					{membre}
					present={creneau.convives.includes(membre.id)}
					onclick={() => basculer(membre.id)}
				/>
			{/each}
			<button
				class="discret invites"
				title="Invités (clic : +1, clic droit : −1)"
				onclick={() => onmodifier({ invites: creneau.invites + 1 })}
				oncontextmenu={(e) => {
					e.preventDefault();
					onmodifier({ invites: Math.max(0, creneau.invites - 1) });
				}}
			>
				+{creneau.invites || ''}
			</button>
		</div>
	</div>

	{#if !aLaMaison}
		<p class="doux">Personne à la maison</p>
	{:else if creneau.plat_id}
		<button class="plat discret" onclick={() => (details = !details)} aria-expanded={details}>
			<strong>{donnees.nomRecette(creneau.plat_id)}</strong>
			<span class="doux">+ {donnees.nomRecette(creneau.dessert_id)}</span>
		</button>
		<div class="ligne badges">
			{#if creneau.restes_de}<span class="badge">
					♻️ restes du {origineRestes(creneau.restes_de)}
				</span>{/if}
			{#if fiche?.recette.lot && !creneau.restes_de}<span class="badge vert">🍲 en lot</span>{/if}
			{#if creneau.verrouille}<span class="badge">🔒 choisi</span>{/if}
			{#if fiche && !fiche.de_saison}<span class="badge alerte">hors saison</span>{/if}
			{#if fiche}<span class="badge">
					⏱ {fiche.recette.temps.preparation + fiche.recette.temps.cuisson} min
				</span>{/if}
		</div>
		{#if details && creneau.raisons.length}
			<ul class="raisons">
				{#each creneau.raisons as raison (raison)}<li>{raison}</li>{/each}
			</ul>
		{/if}
	{:else}
		<p class="doux">À générer</p>
	{/if}

	{#if aLaMaison}
		<div class="actions">
			<button
				class="discret"
				class:actif={creneau.joker}
				onclick={() => onmodifier({ joker: !creneau.joker })}
				title="Joker : repas plaisir, contraintes nutritionnelles relâchées"
			>
				🎉 Joker
			</button>
			{#if creneau.plat_id}
				<button
					class="discret"
					onclick={() => onmodifier({ verrouille: !creneau.verrouille })}
					title={creneau.verrouille ? 'Déverrouiller' : 'Garder ce plat si je régénère'}
				>
					{creneau.verrouille ? '🔓' : '🔒'}
				</button>
				<a
					class="bouton discret"
					href={`/plats/${creneau.plat_id}?portions=${portions}`}
					title="Recette avec les quantités pour ce repas"
				>
					📖 Recette
				</a>
				<button class="discret" onclick={onchanger}>🔄 Changer</button>
			{/if}
		</div>
	{/if}
</article>

<style>
	.creneau {
		display: grid;
		gap: 0.4rem;
		padding: 0.6rem;
		border-radius: 10px;
		background: var(--surface-2);
		min-height: 9rem;
		align-content: start;
	}

	.creneau.joker {
		background: var(--joker-doux);
		outline: 1px dashed var(--joker);
	}

	.creneau.absent {
		opacity: 0.65;
		min-height: auto;
	}

	.entete {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.3rem;
		flex-wrap: wrap;
	}

	.moment {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--texte-doux);
	}

	.presences {
		display: flex;
		gap: 0.2rem;
		align-items: center;
	}

	.invites {
		font-size: 0.8rem;
		padding: 0.1rem 0.35rem;
	}

	.plat {
		display: grid;
		text-align: left;
		padding: 0;
		border-radius: 6px;
		line-height: 1.3;
	}

	.badges {
		gap: 0.25rem;
	}

	.raisons {
		margin: 0;
		padding-left: 1.1rem;
		font-size: 0.8rem;
		color: var(--texte-doux);
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.1rem;
		font-size: 0.8rem;
		margin-top: auto;
	}

	.actions button,
	.actions a {
		font-size: 0.8rem;
	}

	.actions .actif {
		color: var(--joker);
		font-weight: 700;
	}
</style>
