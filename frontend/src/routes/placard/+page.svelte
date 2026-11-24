<!-- Placard : restes de paquets entamés, utilisés en priorité par l'algorithme. -->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import { depuisIso, dateCourte } from '#lib/dates.ts';
	import type { Ingredient, Stock } from '#lib/types.ts';

	let stock = $state<Stock[]>([]);
	let ingredients = $state<Ingredient[]>([]);
	let erreur = $state('');
	let nouvelIngredient = $state('');
	let nouvelleQuantite = $state(100);

	$effect(() => {
		charger();
	});

	async function charger() {
		try {
			[stock, ingredients] = await Promise.all([
				api.lire<Stock[]>('/placard'),
				ingredients.length ? Promise.resolve(ingredients) : api.lire<Ingredient[]>('/ingredients')
			]);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function ajuster(id: string, quantite: number) {
		try {
			await api.modifier(`/placard/${id}`, { quantite_g: Math.max(0, quantite) });
			await charger();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function ajouter(event: SubmitEvent) {
		event.preventDefault();
		if (!nouvelIngredient) return;
		const existant = stock.find((s) => s.ingredient_id === nouvelIngredient)?.quantite_g ?? 0;
		await ajuster(nouvelIngredient, existant + nouvelleQuantite);
		nouvelIngredient = '';
	}

	const unite = (u: string) => (u === 'ml' ? 'ml' : 'g');
</script>

<h1>Placard</h1>
<p class="doux">
	Les restes de paquets (150 g de pâtes sur un paquet de 500 g…) sont ajoutés automatiquement quand
	vous validez les courses. Les plats qui les utilisent sont favorisés.
</p>

{#if erreur}<p class="erreur">{erreur}</p>{/if}

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
								step="10"
								value={article.quantite_g}
								aria-label={`Quantité de ${article.nom}`}
								onchange={(e) =>
									ajuster(article.ingredient_id, Number((e.target as HTMLInputElement).value))}
							/>
							{unite(article.unite)}
						</td>
						<td>
							{dateCourte(depuisIso(article.peremption))}
							{#if article.bientot_perime}<span class="badge alerte">bientôt</span>{/if}
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
		<input type="number" min="1" step="10" bind:value={nouvelleQuantite} aria-label="Quantité" />
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

	td input {
		width: 5.5rem;
	}

	.ajout {
		margin-top: 1rem;
	}
</style>
