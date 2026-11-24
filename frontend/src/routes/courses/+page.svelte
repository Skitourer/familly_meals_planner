<!-- Liste de courses de la semaine : par rayon, arrondie aux conditionnements du magasin. -->
<script lang="ts">
	import { page } from '$app/state';
	import { api, messageErreur } from '#lib/api.ts';
	import ChoixSemaine from '#lib/composants/ChoixSemaine.svelte';
	import { lundiDepuisUrl } from '#lib/semaine.ts';
	import type { Courses } from '#lib/types.ts';

	const lundi = $derived(lundiDepuisUrl(page.url));
	let courses = $state<Courses | null>(null);
	let erreur = $state('');
	let coches = $state<Set<string>>(new Set());

	// Les cases cochées sont mémorisées sur l'appareil (utile au magasin, même hors connexion).
	const cleStockage = $derived(`courses-cochees-${lundi}`);

	$effect(() => {
		charger(lundi);
	});

	async function charger(date: string) {
		erreur = '';
		try {
			courses = await api.lire<Courses>(`/semaines/${date}/courses`);
		} catch (e) {
			erreur = messageErreur(e);
		}
		try {
			coches = new Set(JSON.parse(localStorage.getItem(cleStockage) ?? '[]'));
		} catch {
			coches = new Set();
		}
	}

	function cocher(id: string) {
		const nouveau = new Set(coches);
		if (nouveau.has(id)) nouveau.delete(id);
		else nouveau.add(id);
		coches = nouveau;
		try {
			localStorage.setItem(cleStockage, JSON.stringify([...nouveau]));
		} catch {
			/* stockage indisponible : sans conséquence */
		}
	}

	async function valider() {
		if (!confirm('Courses faites ? Les restes de paquets seront ajoutés au placard.')) return;
		try {
			await api.creer(`/semaines/${lundi}/courses/valider`);
			await charger(lundi);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	const nbLignes = $derived(courses?.rayons.reduce((n, [, lignes]) => n + lignes.length, 0) ?? 0);
	const euros = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
</script>

<div class="entete">
	<div>
		<h1>Liste de courses</h1>
		<ChoixSemaine {lundi} />
	</div>
	{#if courses && nbLignes}
		<div class="ligne">
			<a class="bouton" href={`/api/semaines/${lundi}/courses.pdf`} target="_blank" rel="noopener">
				🖨 Imprimer (PDF)
			</a>
			{#if !courses.validees}
				<button class="principal" onclick={valider}>✅ Courses faites</button>
			{:else}
				<span class="badge vert">Courses faites, placard à jour</span>
			{/if}
		</div>
	{/if}
</div>

{#if erreur}<p class="erreur">{erreur}</p>{/if}

{#if courses}
	{#if !nbLignes}
		<p class="carte">
			Rien à acheter : <a href={`/?lundi=${lundi}`}>générez d'abord les repas de la semaine</a>.
		</p>
	{:else}
		<p class="doux">
			{coches.size} / {nbLignes} articles · budget estimé
			<strong>{euros(courses.total_eur)}</strong>
			(prix médians Open Prices)
		</p>
		<div class="rayons">
			{#each courses.rayons as [rayon, lignes] (rayon)}
				<section class="carte">
					<h2>{rayon}</h2>
					<ul>
						{#each lignes as ligne (ligne.ingredient_id)}
							<li class:coche={coches.has(ligne.ingredient_id)}>
								<label>
									<input
										type="checkbox"
										checked={coches.has(ligne.ingredient_id)}
										onchange={() => cocher(ligne.ingredient_id)}
									/>
									<span class="nom">{ligne.nom}</span>
									<span class="achat">{ligne.achat}</span>
								</label>
								<span class="detail doux">
									besoin {ligne.besoin}{#if ligne.depuis_placard}, dont {ligne.depuis_placard} du placard{/if}{#if ligne.surplus}
										· reste {ligne.surplus}{ligne.surplus_au_placard
											? ' → placard'
											: ' ⚠️ à consommer'}{/if}
								</span>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
			{#if courses.a_verifier.length}
				<section class="carte">
					<h2>À vérifier dans le placard</h2>
					<p class="doux">{courses.a_verifier.join(', ')}</p>
				</section>
			{/if}
		</div>
	{/if}
{/if}

<style>
	.entete {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.rayons {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 0.75rem;
		align-items: start;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.5rem;
	}

	label {
		display: grid;
		grid-template-columns: auto 1fr auto;
		gap: 0.5rem;
		align-items: center;
		color: var(--texte);
		font-size: 1rem;
	}

	input[type='checkbox'] {
		width: 1.2rem;
		height: 1.2rem;
		accent-color: var(--accent);
	}

	.nom {
		font-weight: 600;
	}

	.achat {
		text-align: right;
	}

	.detail {
		display: block;
		padding-left: 1.7rem;
		font-size: 0.78rem;
	}

	.coche .nom,
	.coche .achat {
		text-decoration: line-through;
		opacity: 0.5;
	}
</style>
