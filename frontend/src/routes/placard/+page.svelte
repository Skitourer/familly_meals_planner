<!--
	Placard : restes de paquets entamés et frigo à vider, utilisés en priorité par l'algorithme.
	Les produits à consommer dans la semaine proposent des idées de plats et un réajustement
	de la fin de la semaine en cours.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, messageErreur } from '#lib/api.ts';
	import { iso, lundiDe } from '#lib/dates.ts';
	import type { IdeeFrigo, Ingredient, Stock } from '#lib/types.ts';

	let stock = $state<Stock[]>([]);
	let ingredients = $state<Ingredient[]>([]);
	let idees = $state<IdeeFrigo[]>([]);
	let erreur = $state('');
	let enCours = $state(false);
	let nouvelIngredient = $state('');
	let nouvelleQuantite = $state(100);
	let nouvellePeremption = $state('');

	const aVider = $derived(stock.filter((s) => s.bientot_perime));

	$effect(() => {
		charger();
	});

	async function charger() {
		try {
			[stock, idees, ingredients] = await Promise.all([
				api.lire<Stock[]>('/placard'),
				api.lire<IdeeFrigo[]>('/placard/idees'),
				ingredients.length ? Promise.resolve(ingredients) : api.lire<Ingredient[]>('/ingredients')
			]);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function ajuster(id: string, quantite: number, peremption?: string) {
		try {
			await api.modifier(`/placard/${id}`, {
				quantite_g: Math.max(0, quantite),
				peremption: peremption || null
			});
			await charger();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function ajouter(event: SubmitEvent) {
		event.preventDefault();
		if (!nouvelIngredient) return;
		const existant = stock.find((s) => s.ingredient_id === nouvelIngredient)?.quantite_g ?? 0;
		await ajuster(nouvelIngredient, existant + nouvelleQuantite, nouvellePeremption);
		nouvelIngredient = '';
		nouvellePeremption = '';
	}

	/** Régénère les repas non verrouillés de la semaine en cours, d'aujourd'hui à dimanche. */
	async function reajusterSemaine() {
		const aujourdhui = new Date();
		const lundi = iso(lundiDe(aujourdhui));
		enCours = true;
		erreur = '';
		try {
			await api.creer(
				`/semaines/${lundi}/generer?varier=true&a_partir_du_jour=${(aujourdhui.getDay() + 6) % 7}`
			);
			await goto(`/?lundi=${lundi}`);
		} catch (e) {
			erreur = messageErreur(e);
		} finally {
			enCours = false;
		}
	}

	const unite = (u: string) => (u === 'ml' ? 'ml' : 'g');
</script>

<h1>Placard</h1>
<p class="doux">
	Les restes de paquets (150 g de pâtes sur un paquet de 500 g…) sont ajoutés automatiquement quand
	vous validez les courses. Ajoutez aussi ce qui reste dans le frigo, avec sa date limite : les
	plats qui utilisent le placard sont favorisés, et fortement ceux qui vident le frigo à temps.
</p>

{#if erreur}<p class="erreur">{erreur}</p>{/if}

{#if aVider.length}
	<section class="carte frigo">
		<h2>Frigo à vider</h2>
		<p>
			À consommer dans la semaine :
			{aVider.map((s) => s.nom.toLowerCase()).join(', ')}.
		</p>
		{#if idees.length}
			<p class="doux">Plats qui les utilisent le mieux :</p>
			<ul>
				{#each idees as idee (idee.plat)}
					<li>
						<a href={`/plats/${idee.plat}`}>{idee.nom}</a>
						<span class="doux">({idee.ingredients.join(', ').toLowerCase()})</span>
					</li>
				{/each}
			</ul>
		{/if}
		<div class="ligne">
			<button class="principal" onclick={reajusterSemaine} disabled={enCours}>
				{enCours ? 'Calcul en cours…' : '🔄 Réajuster la semaine en cours'}
			</button>
			<span class="doux">
				Les repas d'aujourd'hui à dimanche sont recalculés ; les repas verrouillés sont gardés.
			</span>
		</div>
	</section>
{/if}

<div class="carte">
	{#if !stock.length}
		<p class="doux">Le placard est vide.</p>
	{:else}
		<table>
			<thead>
				<tr><th>Ingrédient</th><th>Quantité</th><th>À utiliser avant</th><th></th></tr>
			</thead>
			<tbody>
				{#each stock as article (article.ingredient_id)}
					<tr>
						<td>{article.nom}</td>
						<td>
							<input
								type="number"
								min="0"
								step="any"
								value={article.quantite_g}
								aria-label={`Quantité de ${article.nom}`}
								onchange={(e) =>
									ajuster(article.ingredient_id, Number((e.target as HTMLInputElement).value))}
							/>
							{unite(article.unite)}
						</td>
						<td>
							<input
								type="date"
								value={article.peremption}
								aria-label={`Date limite de ${article.nom}`}
								onchange={(e) =>
									ajuster(
										article.ingredient_id,
										article.quantite_g,
										(e.target as HTMLInputElement).value
									)}
							/>
							{#if article.bientot_perime}<span class="badge alerte">à vider</span>{/if}
						</td>
						<td>
							<button
								class="discret"
								onclick={() => ajuster(article.ingredient_id, 0)}
								aria-label={`Retirer ${article.nom}`}
							>
								🗑
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}

	<form class="ligne ajout" onsubmit={ajouter}>
		<select bind:value={nouvelIngredient} aria-label="Ingrédient à ajouter">
			<option value="">Ajouter un ingrédient…</option>
			{#each ingredients.filter((i) => !i.basique) as ing (ing.id)}
				<option value={ing.id}>{ing.nom}</option>
			{/each}
		</select>
		<input type="number" min="1" step="any" bind:value={nouvelleQuantite} aria-label="Quantité" />
		<input
			type="date"
			bind:value={nouvellePeremption}
			aria-label="Date limite (facultatif)"
			title="Date limite : laissée vide, elle est estimée selon le produit"
		/>
		<button disabled={!nouvelIngredient}>Ajouter</button>
	</form>
</div>

<style>
	table {
		width: 100%;
		border-collapse: collapse;
	}

	th,
	td {
		text-align: left;
		padding: 0.4rem 0.3rem;
		border-bottom: 1px solid var(--bordure);
	}

	th {
		font-size: 0.8rem;
		color: var(--texte-doux);
		font-weight: 600;
	}

	td input[type='number'] {
		width: 5.5rem;
	}

	.frigo {
		margin-bottom: 1rem;
		border-left: 4px solid var(--attention);
	}

	.frigo h2 {
		margin-top: 0;
	}

	.ajout {
		margin-top: 1rem;
	}
</style>
