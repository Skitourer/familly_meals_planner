<!-- Un repas de la semaine : présences, joker, plat proposé et actions. -->
<script lang="ts">
	import { donnees } from '#lib/donnees.svelte.ts';
	import { JOURS } from '#lib/dates.ts';
	import {
		categorieSuivante,
		descriptionExterieur,
		ICONES,
		type CategorieExterieur
	} from '#lib/repas-exterieur.ts';
	import type { Creneau } from '#lib/types.ts';
	import NutriScore from './NutriScore.svelte';
	import Pastille from './Pastille.svelte';

	let {
		creneau,
		onmodifier,
		onchanger,
		onexterieur,
		lectureSeule = false
	}: {
		creneau: Creneau;
		onmodifier: (modification: Partial<Creneau>) => void;
		onchanger: () => void;
		onexterieur?: (membreId: number, categorie: CategorieExterieur | null) => void;
		lectureSeule?: boolean; // compte enfant : consultation seulement
	} = $props();

	const personnes = $derived(creneau.convives.length + creneau.invites);
	const aLaMaison = $derived(personnes > 0);
	const fiche = $derived(creneau.plat_id ? donnees.parId.get(creneau.plat_id) : undefined);
	let details = $state(false);
	const nombre = (n: number) => n.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
	const euros = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

	// Portions du repas : somme des portions des convives (un invité compte pour un adulte).
	const portions = $derived(
		Math.round(
			(creneau.convives.reduce((s, id) => s + (donnees.membre(id)?.coefficient_portion ?? 1), 0) +
				creneau.invites) *
				100
		) / 100
	);

	// Membres absents et catégorie de leur repas pris dehors (inconnue par défaut).
	const absents = $derived(
		donnees.membresActifs
			.filter((m) => !creneau.convives.includes(m.id))
			.map((membre) => ({
				membre,
				categorie: creneau.exterieurs.find((e) => e.membre_id === membre.id)?.categorie ?? null
			}))
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
					onclick={lectureSeule ? undefined : () => basculer(membre.id)}
				/>
			{/each}
			{#if lectureSeule}
				{#if creneau.invites}<span class="badge">+{creneau.invites}</span>{/if}
			{:else}
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
			{/if}
		</div>
	</div>

	{#if absents.length && (!lectureSeule || absents.some((a) => a.categorie))}
		<div class="exterieurs">
			<span class="doux">Dehors :</span>
			{#each absents as { membre, categorie } (membre.id)}
				{#if !lectureSeule || categorie}
					<button
						class="discret exterieur"
						style:--couleur={membre.couleur}
						title={descriptionExterieur(membre.prenom, categorie) +
							(lectureSeule ? '' : ' (cliquer pour changer)')}
						aria-label={descriptionExterieur(membre.prenom, categorie)}
						disabled={lectureSeule}
						onclick={() => onexterieur?.(membre.id, categorieSuivante(categorie))}
					>
						<span class="initiale">{membre.prenom.slice(0, 1)}</span>{categorie
							? ICONES[categorie]
							: '?'}
					</button>
				{/if}
			{/each}
		</div>
	{/if}

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
			{#if creneau.infos}<NutriScore lettre={creneau.infos.nutriscore} taille="petite" />{/if}
			{#if creneau.verrouille}<span class="badge">🔒 choisi</span>{/if}
			{#if fiche && !fiche.de_saison}<span class="badge alerte">hors saison</span>{/if}
			{#if fiche}<span class="badge">
					⏱ {fiche.recette.temps.preparation + fiche.recette.temps.cuisson} min
				</span>{/if}
		</div>
		{#if details}
			<div class="details">
				{#if creneau.infos}
					{@const i = creneau.infos}
					<NutriScore lettre={i.nutriscore} />
					<dl>
						<dt>Énergie</dt>
						<dd>{i.energie_kcal} kcal</dd>
						<dt>Protéines</dt>
						<dd>{nombre(i.proteines_g)} g</dd>
						<dt>Fibres</dt>
						<dd>{nombre(i.fibres_g)} g</dd>
						<dt>Fruits et légumes</dt>
						<dd>{i.fruits_legumes_g} g</dd>
						<dt>Carbone</dt>
						<dd>{nombre(i.co2_kg)} kg CO₂e</dd>
						<dt>Coût estimé</dt>
						<dd>{euros(i.prix_eur)}</dd>
					</dl>
					<p class="note">
						Nutrition par portion adulte ; carbone et coût pour les {personnes} convives.
					</p>
				{/if}
				{#if creneau.raisons.length}
					<ul class="raisons">
						{#each creneau.raisons as raison (raison)}<li>{raison}</li>{/each}
					</ul>
				{/if}
			</div>
		{/if}
	{:else}
		<p class="doux">À générer</p>
	{/if}

	{#if aLaMaison}
		<div class="actions">
			{#if !lectureSeule}
				<button
					class="discret"
					class:actif={creneau.joker}
					onclick={() => onmodifier({ joker: !creneau.joker })}
					title="Joker : repas plaisir, contraintes nutritionnelles relâchées"
				>
					🎉 Joker
				</button>
			{:else if creneau.joker}
				<span class="badge joker">🎉 Joker</span>
			{/if}
			{#if creneau.plat_id}
				{#if !lectureSeule}
					<button
						class="discret"
						onclick={() => onmodifier({ verrouille: !creneau.verrouille })}
						title={creneau.verrouille ? 'Déverrouiller' : 'Garder ce plat si je régénère'}
					>
						{creneau.verrouille ? '🔓' : '🔒'}
					</button>
				{/if}
				<a
					class="bouton discret"
					href={`/plats/${creneau.plat_id}?portions=${portions}`}
					title="Recette avec les quantités pour ce repas"
				>
					📖 Recette
				</a>
				{#if !lectureSeule}
					<button class="discret" onclick={onchanger}>🔄 Changer</button>
				{/if}
			{/if}
		</div>
	{/if}
</article>

<style>
	.exterieurs {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
	}

	.exterieur {
		display: inline-flex;
		align-items: center;
		gap: 0.1rem;
		padding: 0.05rem 0.35rem;
		border-radius: 999px;
		border: 1px dashed var(--couleur);
		font-size: 0.75rem;
	}

	.exterieur .initiale {
		font-weight: 700;
		color: var(--couleur);
	}

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

	.details {
		display: grid;
		gap: 0.4rem;
		padding: 0.5rem;
		border-radius: 8px;
		background: var(--surface);
	}

	dl {
		display: grid;
		grid-template-columns: auto auto;
		gap: 0.1rem 0.6rem;
		margin: 0;
		font-size: 0.8rem;
	}

	dt {
		color: var(--texte-doux);
	}

	dd {
		margin: 0;
		text-align: right;
		font-weight: 600;
	}

	.note {
		margin: 0;
		font-size: 0.7rem;
		color: var(--texte-doux);
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
