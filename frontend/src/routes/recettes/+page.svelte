<!-- Catalogue des recettes (nutrition, carbone, saison, notes) et import JSON. -->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import Modale from '#lib/composants/Modale.svelte';
	import { donnees } from '#lib/donnees.svelte.ts';
	import type { FicheRecette, RapportImport } from '#lib/types.ts';

	let recherche = $state('');
	let type = $state<'plat' | 'dessert'>('plat');
	let seulementSaison = $state(false);
	let fiche = $state<FicheRecette | null>(null);
	let ficheOuverte = $state(false);
	let erreur = $state('');

	let fichier = $state<File | null>(null);
	let rapport = $state<RapportImport | null>(null);

	$effect(() => {
		donnees.charger().catch((e) => (erreur = messageErreur(e)));
	});

	const filtre = $derived(recherche.trim().toLowerCase());
	const liste = $derived(
		donnees.recettes.filter(
			(f) =>
				f.recette.type === type &&
				(!seulementSaison || f.de_saison) &&
				(f.recette.nom.toLowerCase().includes(filtre) ||
					f.recette.etiquettes.some((e) => e.includes(filtre)))
		)
	);

	function ouvrir(f: FicheRecette) {
		fiche = f;
		ficheOuverte = true;
	}

	async function analyser(appliquer: boolean) {
		if (!fichier) return;
		const formulaire = new FormData();
		formulaire.append('fichier', fichier);
		try {
			rapport = await api.creer<RapportImport>(
				`/import/recettes?appliquer=${appliquer}`,
				formulaire
			);
			if (rapport.applique) await donnees.chargerRecettes();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function supprimer(f: FicheRecette) {
		if (!confirm(`Supprimer la recette importée « ${f.recette.nom} » ?`)) return;
		try {
			await api.supprimer(`/recettes/${f.recette.id}`);
			ficheOuverte = false;
			await donnees.chargerRecettes();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	const f1 = (n: number) => n.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
</script>

<h1>Recettes</h1>
{#if erreur}<p class="erreur">{erreur}</p>{/if}

<div class="filtres ligne">
	<div class="onglets" role="tablist">
		<button role="tab" aria-selected={type === 'plat'} onclick={() => (type = 'plat')}>
			Plats
		</button>
		<button role="tab" aria-selected={type === 'dessert'} onclick={() => (type = 'dessert')}>
			Desserts
		</button>
	</div>
	<input type="search" placeholder="Rechercher (nom, étiquette…)" bind:value={recherche} />
	<label class="case"><input type="checkbox" bind:checked={seulementSaison} /> De saison</label>
	<span class="doux">{liste.length} recettes</span>
</div>

<div class="grille">
	{#each liste as f (f.recette.id)}
		<button class="carte recette" onclick={() => ouvrir(f)}>
			<strong>{f.recette.nom}</strong>
			<span class="ligne">
				{#if f.recette.plaisir}<span class="badge joker">plaisir</span>{/if}
				{#if !f.de_saison}<span class="badge alerte">hors saison</span>{/if}
				{#if f.recette.lot}<span class="badge vert">en lot</span>{/if}
				{#if f.importee}<span class="badge">importée</span>{/if}
				{#if f.note_famille}<span class="badge">★ {f1(f.note_famille)}</span>{/if}
			</span>
			<span class="doux">
				{f.nutriments.energie_kcal.toFixed(0)} kcal · {f1(f.co2_kg)} kg CO₂e · {f1(f.prix_eur)} €
			</span>
		</button>
	{/each}
</div>

<section class="carte import">
	<h2>Ajouter des recettes avec une IA</h2>
	<ol>
		<li>
			Téléchargez le <a href="/api/import/instructions-ia.md" download>fichier d'instructions</a>
			(il contient la liste à jour des ingrédients autorisés).
		</li>
		<li>
			Donnez-le à l'assistant IA de votre choix avec votre demande (« 10 plats d'hiver rapides »…)
			et enregistrez sa réponse dans un fichier <code>.json</code>.
		</li>
		<li>Importez le fichier : chaque recette est vérifiée avant d'être ajoutée.</li>
	</ol>
	<div class="ligne">
		<input
			type="file"
			accept="application/json,.json"
			onchange={(e) => {
				fichier = (e.target as HTMLInputElement).files?.[0] ?? null;
				rapport = null;
			}}
		/>
		<button disabled={!fichier} onclick={() => analyser(false)}>Vérifier</button>
		{#if rapport && rapport.nb_acceptees && !rapport.applique}
			<button class="principal" onclick={() => analyser(true)}>
				Importer {rapport.nb_acceptees} recette{rapport.nb_acceptees > 1 ? 's' : ''}
			</button>
		{/if}
	</div>
	{#if rapport}
		{#if rapport.erreur_fichier}<p class="erreur">{rapport.erreur_fichier}</p>{/if}
		{#if rapport.applique}<p class="badge vert">
				{rapport.nb_acceptees} recette(s) ajoutée(s) !
			</p>{/if}
		<ul class="rapport">
			{#each rapport.recettes as r, i (i)}
				<li>
					{r.acceptee ? '✅' : '❌'} <strong>{r.nom}</strong> <code>{r.id}</code>
					{#each r.erreurs as e (e)}<div class="erreur">{e}</div>{/each}
					{#each r.avertissements as a (a)}<div class="doux">⚠️ {a}</div>{/each}
				</li>
			{/each}
		</ul>
	{/if}
</section>

<Modale titre={fiche?.recette.nom ?? ''} bind:ouverte={ficheOuverte}>
	{#if fiche}
		{@const r = fiche.recette}
		<p class="doux">
			Préparation {r.temps.preparation} min · cuisson {r.temps.cuisson} min
			{#if r.lot}· se cuisine en lot pour {r.lot.repas_max} repas ({r.lot.conservation_jours} j au frais){/if}
		</p>
		<div class="chiffres">
			<div><strong>{fiche.nutriments.energie_kcal.toFixed(0)}</strong><span>kcal</span></div>
			<div><strong>{f1(fiche.nutriments.proteines_g)} g</strong><span>protéines</span></div>
			<div><strong>{f1(fiche.nutriments.fibres_g)} g</strong><span>fibres</span></div>
			<div><strong>{f1(fiche.nutriments.sel_g)} g</strong><span>sel</span></div>
			<div><strong>{fiche.fruits_legumes_g} g</strong><span>fruits et légumes</span></div>
			<div><strong>{f1(fiche.co2_kg)} kg</strong><span>CO₂e</span></div>
		</div>
		{#if fiche.hors_saison.length}
			<p class="badge alerte">Hors saison ce mois-ci : {fiche.hors_saison.join(', ')}</p>
		{/if}
		<h3>Ingrédients (1 portion adulte)</h3>
		<ul>
			{#each Object.entries(r.ingredients) as [id, grammes] (id)}
				<li>{fiche.ingredients_noms[id]} : {grammes} g</li>
			{/each}
		</ul>
		{#if r.etapes.length}
			<h3>Préparation</h3>
			<ol>
				{#each r.etapes as etape, i (i)}<li>{etape}</li>{/each}
			</ol>
		{/if}
		<p class="doux">
			Source : {r.source}. Valeurs nutritionnelles : CIQUAL (ANSES) ; carbone : Agribalyse (ADEME).
		</p>
		{#if fiche.importee}
			<button onclick={() => fiche && supprimer(fiche)}>🗑 Supprimer cette recette importée</button>
		{/if}
	{/if}
</Modale>

<style>
	.filtres {
		margin-bottom: 1rem;
	}

	.onglets {
		display: inline-flex;
		border: 1px solid var(--bordure);
		border-radius: 999px;
		overflow: hidden;
	}

	.onglets button {
		border: none;
		border-radius: 0;
	}

	.onglets button[aria-selected='true'] {
		background: var(--accent);
		color: var(--accent-texte);
	}

	.case {
		display: flex;
		align-items: center;
		gap: 0.3rem;
	}

	.grille {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 0.75rem;
	}

	.recette {
		display: grid;
		gap: 0.35rem;
		text-align: left;
		border-radius: var(--rayon);
	}

	.import {
		margin-top: 1.5rem;
	}

	.rapport {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 0.5rem;
	}

	.chiffres {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(95px, 1fr));
		gap: 0.5rem;
		margin: 0.75rem 0;
	}

	.chiffres div {
		display: grid;
		text-align: center;
		background: var(--surface-2);
		border-radius: 8px;
		padding: 0.4rem;
	}

	.chiffres span {
		font-size: 0.75rem;
		color: var(--texte-doux);
	}

	h3 {
		font-size: 1rem;
		margin-top: 1rem;
	}
</style>
