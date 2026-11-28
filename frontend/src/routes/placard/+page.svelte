<!--
	Placard : restes de paquets entamés et frigo à vider, utilisés en priorité par l'algorithme,
	et autres produits hors repas (comptés en paquets).
	Les produits à consommer dans la semaine proposent des idées de plats et un réajustement
	de la fin de la semaine en cours.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { AUTRE_PRODUIT, ficheDuProduit } from '#lib/achats.ts';
	import { api, messageErreur } from '#lib/api.ts';
	import { iso, libelleSemaine, lundiDe, lundiSuivant } from '#lib/dates.ts';
	import AutresProduits from '#lib/composants/AutresProduits.svelte';
	import Modale from '#lib/composants/Modale.svelte';
	import NotesProduit from '#lib/composants/NotesProduit.svelte';
	import ScannerCodeBarres from '#lib/composants/ScannerCodeBarres.svelte';
	import {
		articlesAffiches,
		ecrireChoix,
		lireChoix,
		normaliser,
		parRayon,
		type Tri
	} from '#lib/placard.ts';
	import type { IdeeFrigo, Ingredient, ProduitPlacard, ProduitScanne, Stock } from '#lib/types.ts';

	let stock = $state<Stock[]>([]);
	let autres = $state<ProduitPlacard[]>([]);
	let categories = $state<string[]>([]);
	let ingredients = $state<Ingredient[]>([]);
	let idees = $state<IdeeFrigo[]>([]);
	let erreur = $state('');
	let enCours = $state(false);
	let nomNouvelIngredient = $state('');
	let nouvelleQuantite = $state(100);
	let nouvellePeremption = $state('');

	// Scan d'un produit : lecture du code-barres, puis confirmation avant l'ajout au placard.
	let scanOuvert = $state(false);
	let produit = $state<ProduitScanne | null>(null);
	let rechercheEnCours = $state(false);
	let messageScan = $state('');
	let ingredientScanne = $state('');
	let quantiteScannee = $state(100);
	let peremptionScannee = $state('');
	let nomProduit = $state('');
	let categorieProduit = $state('');
	let paquetsScannes = $state(1);

	const aVider = $derived([
		...stock.filter((s) => s.bientot_perime),
		...autres.filter((p) => p.bientot_perime)
	]);
	const suivis = $derived(ingredients.filter((i) => !i.basique));
	const autresIngredients = $derived(
		suivis.filter((i) => !produit?.propositions.some((p) => p.ingredient_id === i.id))
	);

	// Recherche et filtre : pour cette visite ; tri et regroupement : gardés sur l'appareil.
	let recherche = $state('');
	let aViderSeulement = $state(false);
	let choix = $state(lireChoix(localStorage));
	const TRIS: [Tri, string][] = [
		['peremption', 'Date limite'],
		['nom', 'Nom'],
		['quantite', 'Quantité']
	];
	// En-têtes du tableau, dans l'ordre des colonnes : toucher un en-tête trie par cette colonne.
	const COLONNES: [Tri, string][] = [
		['nom', 'Ingrédient'],
		['quantite', 'Quantité'],
		['peremption', 'À utiliser avant']
	];
	const stockAffiche = $derived(
		articlesAffiches(
			stock.map((s) => ({ ...s, quantite: s.quantite_g })),
			recherche,
			aViderSeulement,
			choix.tri
		)
	);
	const groupesStock = $derived<[string, typeof stockAffiche][]>(
		choix.parRayon ? parRayon(stockAffiche) : [['', stockAffiche]]
	);
	const autresAffiches = $derived(
		articlesAffiches(
			autres.map((p) => ({ ...p, quantite: p.paquets })),
			recherche,
			aViderSeulement,
			choix.tri
		)
	);
	const filtrage = $derived(aViderSeulement || recherche.trim() !== '');
	// Ajout manuel : le nom saisi doit être celui d'un ingrédient suivi (proposé par la liste).
	const nouvelIngredient = $derived(
		suivis.find((i) => normaliser(i.nom) === normaliser(nomNouvelIngredient))?.id ?? ''
	);

	$effect(() => {
		ecrireChoix(localStorage, choix);
	});

	$effect(() => {
		charger();
	});

	// Ingrédient fini : proposé « à racheter » sur la liste de la semaine suivante.
	let ingredientRetire = $state<Stock | null>(null);
	let messageRachat = $state('');

	async function retirer(article: Stock) {
		if (await ajuster(article.ingredient_id, 0)) {
			ingredientRetire = article;
			messageRachat = '';
		}
	}

	async function racheter(article: Stock) {
		const lundi = lundiSuivant();
		try {
			await api.creer(`/semaines/${lundi}/courses/ingredients-a-racheter`, {
				ingredient_id: article.ingredient_id
			});
			ingredientRetire = null;
			messageRachat = `${article.nom} : sur la liste de courses de la semaine ${libelleSemaine(lundi)}`;
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	function trierPar(tri: Tri) {
		choix.tri = tri;
	}

	async function charger() {
		try {
			[stock, autres, idees, ingredients, categories] = await Promise.all([
				api.lire<Stock[]>('/placard'),
				api.lire<ProduitPlacard[]>('/placard/produits'),
				api.lire<IdeeFrigo[]>('/placard/idees'),
				ingredients.length ? Promise.resolve(ingredients) : api.lire<Ingredient[]>('/ingredients'),
				categories.length ? Promise.resolve(categories) : api.lire<string[]>('/produits/categories')
			]);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	/** Enregistre la quantité d'un ingrédient ; renvoie false (erreur affichée) en cas d'échec. */
	async function ajuster(
		id: string,
		quantite: number,
		peremption?: string,
		notes?: Pick<ProduitScanne, 'nutriscore' | 'nova' | 'green_score'>
	): Promise<boolean> {
		try {
			await api.modifier(`/placard/${id}`, {
				quantite_g: Math.max(0, quantite),
				peremption: peremption || null,
				...(notes && {
					nutriscore: notes.nutriscore,
					nova: notes.nova,
					green_score: notes.green_score
				})
			});
			await charger();
			return true;
		} catch (e) {
			erreur = messageErreur(e);
			return false;
		}
	}

	async function ajouter(event: SubmitEvent) {
		event.preventDefault();
		if (!nouvelIngredient) return;
		const existant = stock.find((s) => s.ingredient_id === nouvelIngredient)?.quantite_g ?? 0;
		if (await ajuster(nouvelIngredient, existant + nouvelleQuantite, nouvellePeremption))
			nomNouvelIngredient = '';
		nouvellePeremption = '';
	}

	function ouvrirScan() {
		produit = null;
		messageScan = '';
		scanOuvert = true;
	}

	async function rechercherProduit(code: string) {
		rechercheEnCours = true;
		messageScan = '';
		try {
			produit = await api.lire<ProduitScanne>(`/produits/${code}`);
			// Sans ingrédient correspondant, c'est sans doute un produit hors repas (Nutella...).
			choisirIngredient(produit.propositions[0]?.ingredient_id ?? AUTRE_PRODUIT);
			peremptionScannee = '';
			nomProduit = produit.nom || 'Produit sans nom';
			categorieProduit = produit.categorie;
			paquetsScannes = 1;
		} catch (e) {
			messageScan = messageErreur(e);
		} finally {
			rechercheEnCours = false;
		}
	}

	/** Quantité pré-remplie : part comestible du paquet pour cet ingrédient, sinon contenu du paquet. */
	function choisirIngredient(id: string) {
		ingredientScanne = id;
		const proposition = produit?.propositions.find((p) => p.ingredient_id === id);
		quantiteScannee = Math.round(proposition?.quantite_g ?? produit?.quantite_g ?? 100);
	}

	async function ajouterProduitScanne(event: SubmitEvent) {
		event.preventDefault();
		if (!ingredientScanne || !produit) return;
		if (ingredientScanne === AUTRE_PRODUIT) {
			try {
				await api.creer('/placard/produits', {
					...ficheDuProduit(produit, nomProduit, categorieProduit),
					paquets: paquetsScannes,
					peremption: peremptionScannee || null
				});
				await charger();
			} catch (e) {
				messageScan = messageErreur(e);
				return;
			}
			messageScan = `Ajouté au placard : ${nomProduit.trim()}, ${paquetsScannes} paquet(s). Scannez le produit suivant.`;
			produit = null;
			return;
		}
		const existant = stock.find((s) => s.ingredient_id === ingredientScanne);
		// Sans date saisie, on garde celle du produit déjà rangé : le plus ancien d'abord.
		const ajoute = await ajuster(
			ingredientScanne,
			(existant?.quantite_g ?? 0) + quantiteScannee,
			peremptionScannee || existant?.peremption,
			produit
		);
		if (!ajoute) {
			messageScan = erreur;
			return;
		}
		const nom = ingredients.find((i) => i.id === ingredientScanne)?.nom ?? ingredientScanne;
		messageScan = `Ajouté au placard : ${nom}, ${quantiteScannee} g. Scannez le produit suivant.`;
		produit = null;
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
	<div class="ligne entete">
		<button class="principal" onclick={ouvrirScan}>📷 Scanner un produit</button>
		<span class="doux">Le code-barres remplit le produit et sa quantité.</span>
	</div>
	<div class="outils">
		<input
			type="search"
			placeholder="Rechercher au placard…"
			bind:value={recherche}
			aria-label="Rechercher au placard"
		/>
		<label>
			Trier par
			<select bind:value={choix.tri}>
				{#each TRIS as [tri, libelle] (tri)}<option value={tri}>{libelle}</option>{/each}
			</select>
		</label>
		<label><input type="checkbox" bind:checked={choix.parRayon} /> Par rayon</label>
		<label>
			<input type="checkbox" bind:checked={aViderSeulement} />
			À vider seulement ({aVider.length})
		</label>
	</div>

	<h2>Ingrédients</h2>
	{#if ingredientRetire}
		<p class="ligne rachat" role="status">
			<span>{ingredientRetire.nom} n'est plus au placard.</span>
			<button class="principal" onclick={() => ingredientRetire && racheter(ingredientRetire)}>
				🛒 À racheter
			</button>
			<button class="discret" onclick={() => (ingredientRetire = null)}>Non merci</button>
		</p>
	{:else if messageRachat}
		<p class="ligne rachat" role="status">
			<span>✓ {messageRachat}</span>
			<a href={`/courses?lundi=${lundiSuivant()}`}>Voir la liste</a>
		</p>
	{/if}
	{#if !stock.length}
		<p class="doux">Aucun ingrédient au placard.</p>
	{:else if !stockAffiche.length}
		<p class="doux">Aucun ingrédient ne correspond.</p>
	{:else}
		<table>
			<thead>
				<tr>
					{#each COLONNES as [tri, libelle] (tri)}
						<th aria-sort={choix.tri === tri ? 'ascending' : undefined}>
							<button class="tri" onclick={() => trierPar(tri)}>
								{libelle}
								{#if choix.tri === tri}▲{/if}
							</button>
						</th>
					{/each}
					<th></th>
				</tr>
			</thead>
			{#each groupesStock as [rayon, articles] (rayon)}
				<tbody>
					{#if rayon}
						<tr class="rayon"><th colspan="4" scope="rowgroup">{rayon}</th></tr>
					{/if}
					{#each articles as article (article.ingredient_id)}
						<tr>
							<td class="nom">{article.nom} <NotesProduit notes={article} /></td>
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
							<td class="actions">
								<button
									class="discret"
									onclick={() => racheter(article)}
									title="Mettre sur la liste de courses de la semaine suivante"
									aria-label={`À racheter : ${article.nom}`}
								>
									🛒
								</button>
								<button
									class="discret"
									onclick={() => retirer(article)}
									aria-label={`Retirer ${article.nom}`}
								>
									🗑
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			{/each}
		</table>
	{/if}

	<form class="ligne ajout" onsubmit={ajouter}>
		<input
			type="search"
			list="ingredients-suivis"
			placeholder="Ajouter un ingrédient…"
			bind:value={nomNouvelIngredient}
			aria-label="Ingrédient à ajouter"
		/>
		<datalist id="ingredients-suivis">
			{#each suivis as ing (ing.id)}<option value={ing.nom}></option>{/each}
		</datalist>
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

<AutresProduits produits={autresAffiches} {filtrage} {categories} onModifie={charger} />

<Modale titre="Scanner un produit" bind:ouverte={scanOuvert}>
	{#if messageScan}<p class:erreur={!messageScan.startsWith('Ajouté')}>{messageScan}</p>{/if}
	{#if rechercheEnCours}
		<p class="doux">Recherche dans Open Food Facts…</p>
	{:else if produit}
		<p>
			<strong>{produit.nom || 'Produit sans nom'}</strong>
			{#if produit.marque}<span class="doux">— {produit.marque}</span>{/if}
			{#if produit.quantite_g}<span class="doux">({produit.quantite_g} g)</span>{/if}
		</p>
		{#if ingredientScanne === AUTRE_PRODUIT}
			<p class="doux">
				Produit hors repas : rangé parmi les autres produits, compté en paquets. Choisissez un
				ingrédient si les repas peuvent l'utiliser.
			</p>
		{/if}
		<form class="formulaire-scan" onsubmit={ajouterProduitScanne}>
			<label>
				Ingrédient
				<select
					value={ingredientScanne}
					onchange={(e) => choisirIngredient((e.target as HTMLSelectElement).value)}
				>
					<option value="">Choisir…</option>
					{#if produit.propositions.length}
						<optgroup label="Correspondances">
							{#each produit.propositions as p (p.ingredient_id)}
								<option value={p.ingredient_id}>{p.nom}</option>
							{/each}
						</optgroup>
					{/if}
					<optgroup label="Autres ingrédients">
						{#each autresIngredients as ing (ing.id)}
							<option value={ing.id}>{ing.nom}</option>
						{/each}
					</optgroup>
					<option value={AUTRE_PRODUIT}>Autre produit (hors repas)</option>
				</select>
			</label>
			{#if ingredientScanne === AUTRE_PRODUIT}
				<label>
					Nom
					<input type="text" maxlength="120" bind:value={nomProduit} />
				</label>
				<label>
					Catégorie
					<select bind:value={categorieProduit}>
						{#each categories as c (c)}<option value={c}>{c}</option>{/each}
					</select>
				</label>
				<label>
					Paquets
					<input type="number" min="1" max="99" bind:value={paquetsScannes} />
				</label>
			{:else}
				<label>
					Quantité (g, part comestible)
					<input type="number" min="1" step="any" bind:value={quantiteScannee} />
				</label>
			{/if}
			<label>
				À utiliser avant (facultatif)
				<input type="date" bind:value={peremptionScannee} />
			</label>
			<div class="ligne">
				<button
					class="principal"
					disabled={!ingredientScanne ||
						(ingredientScanne === AUTRE_PRODUIT && (!nomProduit.trim() || paquetsScannes < 1))}
				>
					Ajouter au placard
				</button>
				<button type="button" onclick={() => (produit = null)}>Scanner un autre produit</button>
			</div>
		</form>
	{:else}
		<ScannerCodeBarres onCode={rechercherProduit} />
	{/if}
</Modale>

<style>
	.entete {
		margin-bottom: 1rem;
	}

	/* minmax(0, 1fr) : une longue option de liste ne doit pas élargir la fenêtre. */
	.formulaire-scan,
	.formulaire-scan label {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 0.8rem;
	}

	.formulaire-scan label {
		gap: 0.3rem;
	}

	.formulaire-scan :is(input, select) {
		width: 100%;
	}

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

	.rachat {
		align-items: center;
		padding: 0.5rem 0.7rem;
		border-radius: 0.5rem;
		background: var(--accent-doux);
	}

	td.actions {
		white-space: nowrap;
	}

	.outils {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1rem;
		margin-bottom: 0.5rem;
	}

	.outils input[type='search'] {
		flex: 1 1 14rem;
	}

	.outils label {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
	}

	h2 {
		margin: 1rem 0 0.3rem;
	}

	/* En-tête cliquable : même allure que le texte de l'en-tête. */
	button.tri {
		border: none;
		background: none;
		padding: 0;
		font: inherit;
		color: inherit;
		cursor: pointer;
	}

	/* Bandeau de rayon : même allure que les catégories des autres produits. */
	tr.rayon th {
		padding: 0.35rem 0.7rem;
		border-bottom: none;
		background: var(--surface-2);
		color: var(--texte-doux);
		font-size: 0.8rem;
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	/* Un peu d'air avant chaque rayon, sauf le premier. */
	tbody + tbody tr.rayon th {
		border-top: 0.9rem solid var(--surface);
	}

	/* Téléphone : une carte par ingrédient, sans en-têtes (le tri passe par « Trier par »). */
	@media (max-width: 640px) {
		thead {
			display: none;
		}

		tr:not(.rayon) {
			display: flex;
			flex-wrap: wrap;
			align-items: center;
			gap: 0.3rem 0.6rem;
			padding: 0.5rem 0;
			border-bottom: 1px solid var(--bordure);
		}

		td {
			border: none;
			padding: 0;
		}

		td.nom {
			flex-basis: 100%;
			font-weight: 600;
		}
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
