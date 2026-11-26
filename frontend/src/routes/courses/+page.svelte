<!--
	Liste de courses de la semaine : par rayon, arrondie aux conditionnements du magasin.
	Les coches sont partagées entre appareils ; sans réseau, elles attendent sur l'appareil
	et partent au retour de la connexion (voir lib/coches.ts).
	Un produit scanné au magasin coche son article et enregistre la quantité et le prix payés ;
	hors liste, il rejoint le placard à la validation ; un autre produit (hors repas) est rangé
	parmi les autres produits du placard, sauf s'il est marqué « ne pas ranger ».
	Les produits « à racheter » (autres produits finis au placard) se cochent et se scannent
	comme le reste ; cochés, ils rejoignent le placard à la validation.
-->
<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import {
		articleCorrespondant,
		AUTRE_PRODUIT,
		ficheDuProduit,
		groupesDeChoix,
		prixPropose,
		rachatScanne
	} from '#lib/achats.ts';
	import { api, ErreurApi, messageErreur } from '#lib/api.ts';
	import {
		ajouterAFile,
		cochesAffichees,
		ecrireFile,
		lireFile,
		retirerEnvoyees,
		type FileCoches
	} from '#lib/coches.ts';
	import ChoixSemaine from '#lib/composants/ChoixSemaine.svelte';
	import Modale from '#lib/composants/Modale.svelte';
	import ScannerCodeBarres from '#lib/composants/ScannerCodeBarres.svelte';
	import { lundiDepuisUrl } from '#lib/semaine.ts';
	import type { Courses, Ingredient, LigneCourses, ProduitScanne } from '#lib/types.ts';

	const lundi = $derived(lundiDepuisUrl(page.url));
	let courses = $state<Courses | null>(null);
	let erreur = $state('');
	let file = $state<FileCoches>({});
	let enLigne = $state(true);
	let envoiEnCours = false;

	// Scan au magasin : produit lu, puis article de la liste, quantité et prix payés.
	let scanOuvert = $state(false);
	let produit = $state<ProduitScanne | null>(null);
	let rechercheEnCours = $state(false);
	let messageScan = $state('');
	let article = $state('');
	let quantiteAchetee = $state(0);
	let prixPaye = $state(0);
	let nomProduit = $state('');
	let categorie = $state('');
	let ranger = $state(true);
	let ingredients = $state<Ingredient[]>([]);
	let categories = $state<string[]>([]);

	// Validation : articles ni cochés ni scannés, à confirmer comme achetés ou non.
	let confirmationOuverte = $state(false);
	let nonCoches = $state<{ cle: string; nom: string }[]>([]);

	const coches = $derived(cochesAffichees(courses?.coches ?? [], file));
	const lignes = $derived<LigneCourses[]>(courses?.rayons.flatMap(([, l]) => l) ?? []);
	const enAttente = $derived(Object.keys(file).length);
	const choix = $derived(produit ? groupesDeChoix(produit, lignes, ingredients) : null);
	const nomsIngredients = $derived(new Map(ingredients.map((i) => [i.id, i.nom])));

	// Recharger seulement quand la semaine change (charger lit et modifie la file d'attente).
	$effect(() => {
		const date = lundi;
		untrack(() => charger(date));
	});

	// Au retour du réseau ou de l'application au premier plan : envoyer la file, relire la liste.
	$effect(() => {
		enLigne = navigator.onLine;
		const reconnecte = () => {
			enLigne = true;
			charger(lundi);
		};
		const deconnecte = () => (enLigne = false);
		const visible = () =>
			document.visibilityState === 'visible' && navigator.onLine && charger(lundi);
		window.addEventListener('online', reconnecte);
		window.addEventListener('offline', deconnecte);
		document.addEventListener('visibilitychange', visible);
		return () => {
			window.removeEventListener('online', reconnecte);
			window.removeEventListener('offline', deconnecte);
			document.removeEventListener('visibilitychange', visible);
		};
	});

	async function charger(date: string) {
		erreur = '';
		file = lireFile(localStorage, date);
		await envoyer(date);
		try {
			courses = await api.lire<Courses>(`/semaines/${date}/courses`);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	function cocher(id: string) {
		file = ajouterAFile(file, id, !coches.has(id), new Date());
		ecrireFile(localStorage, lundi, file);
		envoyer(lundi);
	}

	/** Envoie la file d'attente ; sans réseau, elle reste sur l'appareil pour plus tard. */
	async function envoyer(date: string) {
		const lot = Object.values(file);
		if (!lot.length || envoiEnCours) return;
		envoiEnCours = true;
		try {
			const cochees = await api.modifier<string[]>(`/semaines/${date}/courses/coches`, lot);
			if (courses) courses.coches = cochees;
			file = retirerEnvoyees(file, lot);
			ecrireFile(localStorage, date, file);
			enLigne = true;
		} catch (e) {
			if (e instanceof ErreurApi) erreur = messageErreur(e);
			else enLigne = false; // réseau indisponible : nouvel essai au retour de la connexion
		} finally {
			envoiEnCours = false;
		}
	}

	async function ouvrirScan() {
		produit = null;
		messageScan = '';
		scanOuvert = true;
		if (!ingredients.length) {
			try {
				[ingredients, categories] = await Promise.all([
					api.lire<Ingredient[]>('/ingredients'),
					api.lire<string[]>('/produits/categories')
				]);
			} catch (e) {
				messageScan = messageErreur(e);
			}
		}
	}

	async function rechercherProduit(code: string) {
		rechercheEnCours = true;
		messageScan = '';
		try {
			produit = await api.lire<ProduitScanne>(`/produits/${code}`);
			quantiteAchetee = Math.round(produit.quantite_g ?? 0);
			nomProduit = produit.nom || 'Produit sans nom';
			categorie = produit.categorie;
			ranger = true;
			const rachat = rachatScanne(produit, courses?.a_racheter ?? []);
			if (rachat) {
				nomProduit = rachat.nom;
				categorie = rachat.categorie;
			}
			choisirArticle(
				rachat ? AUTRE_PRODUIT : articleCorrespondant(produit, lignes) || AUTRE_PRODUIT
			);
		} catch (e) {
			messageScan = messageErreur(e);
		} finally {
			rechercheEnCours = false;
		}
	}

	function choisirArticle(id: string) {
		article = id;
		if (!produit) return;
		const ligne = lignes.find((l) => l.ingredient_id === id);
		if (!quantiteAchetee && ligne) quantiteAchetee = ligne.achete_g;
		prixPaye = prixPropose(produit, id, lignes, quantiteAchetee);
	}

	async function enregistrerAchat(event: SubmitEvent) {
		event.preventDefault();
		if (!produit || !article) return;
		const autre = article === AUTRE_PRODUIT;
		try {
			await api.creer(
				`/semaines/${lundi}/courses/${autre ? 'autres-achats' : 'achats'}`,
				autre
					? { ...ficheDuProduit(produit, nomProduit, categorie), prix_eur: prixPaye, ranger }
					: {
							ingredient_id: article,
							quantite_g: quantiteAchetee,
							prix_eur: prixPaye,
							code: produit.code
						}
			);
		} catch (e) {
			messageScan = messageErreur(e);
			return;
		}
		const prevu = lignes.some((l) => l.ingredient_id === article);
		if (prevu && !coches.has(article)) cocher(article);
		const rachat = autre ? rachatScanne(produit, courses?.a_racheter ?? []) : undefined;
		if (rachat && !coches.has(rachat.cle)) cocher(rachat.cle);
		const nom = autre ? nomProduit : (nomsIngredients.get(article) ?? article);
		messageScan = `Enregistré : ${nom}, ${euros(prixPaye)}. Scannez le produit suivant.`;
		produit = null;
		await charger(lundi);
	}

	/** Annule un achat scanné : `achats/{ingrédient}` ou `autres-achats/{id}`. */
	async function annulerAchat(chemin: string) {
		try {
			await api.supprimer(`/semaines/${lundi}/courses/${chemin}`);
			await charger(lundi);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	/** Courses faites : demande quoi faire des articles ni cochés ni scannés, s'il en reste. */
	async function valider() {
		await envoyer(lundi);
		if (Object.keys(file).length) {
			erreur = 'Des coches attendent encore le réseau : validez une fois la connexion revenue.';
			return;
		}
		nonCoches = [
			...lignes
				.filter((l) => !coches.has(l.ingredient_id) && !l.achat_reel)
				.map((l) => ({ cle: l.ingredient_id, nom: l.nom })),
			...(courses?.a_racheter ?? [])
				.filter((r) => !coches.has(r.cle) && !r.scanne)
				.map((r) => ({ cle: r.cle, nom: r.nom }))
		];
		if (nonCoches.length) {
			confirmationOuverte = true;
		} else if (confirm('Courses faites ? Les restes de paquets seront ajoutés au placard.')) {
			await envoyerValidation(true);
		}
	}

	async function toutAchete() {
		const maintenant = new Date();
		for (const article of nonCoches) file = ajouterAFile(file, article.cle, true, maintenant);
		ecrireFile(localStorage, lundi, file);
		await envoyer(lundi);
		await envoyerValidation(true);
	}

	async function envoyerValidation(toutAcheteConfirme: boolean) {
		confirmationOuverte = false;
		try {
			await api.creer(`/semaines/${lundi}/courses/valider`, { tout_achete: toutAcheteConfirme });
			await charger(lundi);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function retirerRachat(id: number) {
		try {
			await api.supprimer(`/semaines/${lundi}/courses/a-racheter/${id}`);
			await charger(lundi);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function rouvrir() {
		const message =
			'Rouvrir les courses ? Ce que la validation a changé dans le placard et le budget est défait ; vos corrections faites depuis sont gardées.';
		if (!confirm(message)) return;
		try {
			await api.creer(`/semaines/${lundi}/courses/rouvrir`);
			await charger(lundi);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	// Articles de la liste : ingrédients des repas et produits à racheter.
	const nbLignes = $derived(
		(courses?.rayons.reduce((n, [, lignes]) => n + lignes.length, 0) ?? 0) +
			(courses?.a_racheter.length ?? 0)
	);
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
				<button onclick={ouvrirScan} disabled={!enLigne}>📷 Scanner</button>
				<button class="principal" onclick={valider} disabled={!enLigne}>✅ Courses faites</button>
			{:else}
				<span class="badge vert">Courses faites, placard à jour</span>
				<button onclick={rouvrir} disabled={!enLigne}>↩ Rouvrir les courses</button>
			{/if}
		</div>
	{/if}
</div>

{#if erreur}<p class="erreur">{erreur}</p>{/if}
{#if !enLigne && !enAttente}
	<p class="badge attente" role="status">
		📵 Hors ligne : liste telle qu'elle était à la dernière connexion.
	</p>
{:else if !enLigne || enAttente}
	<p class="badge attente" role="status">
		{enLigne ? '⏳' : '📵 Hors ligne :'}
		{enAttente}
		{enAttente > 1 ? 'coches en attente' : 'coche en attente'}, envoyées dès le retour du réseau.
	</p>
{/if}

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
			{#if courses.nb_achats_reels}
				· avec les prix payés <strong>{euros(courses.total_reel_eur)}</strong>
				({courses.nb_achats_reels}
				{courses.nb_achats_reels > 1 ? 'articles scannés' : 'article scanné'})
			{/if}
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
										disabled={courses.validees}
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
								{#if ligne.achat_reel}
									<span class="detail reel">
										✓ acheté {ligne.achat_reel} · {euros(ligne.prix_reel_eur ?? 0)}
										{#if !courses.validees}
											<button
												class="discret"
												onclick={() => annulerAchat(`achats/${ligne.ingredient_id}`)}
												aria-label={`Annuler l'achat de ${ligne.nom}`}
											>
												✕
											</button>
										{/if}
									</span>
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/each}
			{#if courses.a_racheter.length}
				<section class="carte">
					<h2>À racheter</h2>
					<ul>
						{#each courses.a_racheter as rachat (rachat.id)}
							<li class:coche={coches.has(rachat.cle) || rachat.scanne}>
								<label>
									<input
										type="checkbox"
										checked={coches.has(rachat.cle) || rachat.scanne}
										disabled={courses.validees || rachat.scanne}
										onchange={() => cocher(rachat.cle)}
									/>
									<span class="nom">{rachat.nom}</span>
									<span class="achat">1 paquet</span>
								</label>
								<span class="detail doux">
									{[rachat.marque, rachat.contenu].filter(Boolean).join(' · ') || rachat.categorie}
									{#if rachat.prix_eur !== null}· environ {euros(rachat.prix_eur)}{/if}
									{#if !courses.validees && !rachat.scanne}
										<button
											class="discret"
											onclick={() => retirerRachat(rachat.id)}
											aria-label={`Retirer ${rachat.nom} de la liste`}
										>
											✕
										</button>
									{/if}
								</span>
								{#if rachat.scanne}
									<span class="detail reel">✓ scanné (voir « Hors liste »)</span>
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}
			{#if courses.hors_liste.length || courses.autres_achats.length}
				<section class="carte">
					<h2>Hors liste</h2>
					<ul>
						{#each courses.hors_liste as ligne (ligne.ingredient_id)}
							<li>
								<span class="nom">{ligne.nom}</span>
								<span class="detail reel">
									✓ acheté {ligne.achat_reel} · {euros(ligne.prix_reel_eur ?? 0)} → placard
									{#if !courses.validees}
										<button
											class="discret"
											onclick={() => annulerAchat(`achats/${ligne.ingredient_id}`)}
											aria-label={`Annuler l'achat de ${ligne.nom}`}
										>
											✕
										</button>
									{/if}
								</span>
							</li>
						{/each}
						{#each courses.autres_achats as autre (autre.id)}
							<li>
								<span class="nom">{autre.nom}</span>
								<span class="detail reel">
									✓ {autre.contenu ? `${autre.contenu} · ` : ''}{euros(autre.prix_eur)}
									{autre.ranger ? '→ placard' : '· budget seulement'}
									{#if !courses.validees}
										<button
											class="discret"
											onclick={() => annulerAchat(`autres-achats/${autre.id}`)}
											aria-label={`Annuler l'achat de ${autre.nom}`}
										>
											✕
										</button>
									{/if}
								</span>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
			{#if courses.a_verifier.length}
				<section class="carte">
					<h2>À vérifier dans le placard</h2>
					<p class="doux">{courses.a_verifier.join(', ')}</p>
				</section>
			{/if}
		</div>
	{/if}
{/if}

<Modale titre="Courses faites ?" bind:ouverte={confirmationOuverte}>
	<p>
		{nonCoches.length}
		{nonCoches.length > 1 ? 'articles ne sont pas cochés' : "article n'est pas coché"} :
		{nonCoches.map((l) => l.nom).join(', ')}.
	</p>
	<div class="ligne">
		<button class="principal" onclick={toutAchete}>Tout a été acheté</button>
		<button onclick={() => envoyerValidation(false)}>Ils n'ont pas été achetés</button>
		<button class="discret" onclick={() => (confirmationOuverte = false)}>Annuler</button>
	</div>
	<p class="doux">
		Non achetés : rien n'est ajouté au placard ni au budget pour eux. Vous pourrez rouvrir les
		courses pour corriger.
	</p>
</Modale>

<Modale titre="Scanner un produit acheté" bind:ouverte={scanOuvert}>
	{#if messageScan}
		<p class:erreur={!messageScan.startsWith('Enregistré')}>{messageScan}</p>
	{/if}
	{#if rechercheEnCours}
		<p class="doux">Recherche dans Open Food Facts…</p>
	{:else if produit}
		<p>
			<strong>{produit.nom || 'Produit sans nom'}</strong>
			{#if produit.marque}<span class="doux">— {produit.marque}</span>{/if}
		</p>
		{#if !article}
			<p class="doux">Choisissez l'article.</p>
		{:else if article === AUTRE_PRODUIT}
			<p class="doux">
				Produit hors repas : compté dans le budget et rangé parmi les autres produits du placard
				quand les courses seront validées.
			</p>
		{:else if !lignes.some((l) => l.ingredient_id === article)}
			<p class="doux">Hors liste : il rejoindra le placard quand les courses seront validées.</p>
		{/if}
		<form class="formulaire-scan" onsubmit={enregistrerAchat}>
			<label>
				Article
				<select
					value={article}
					onchange={(e) => choisirArticle((e.target as HTMLSelectElement).value)}
				>
					<option value="">Choisir…</option>
					{#if choix}
						<optgroup label="Sur la liste">
							{#each choix.surLaListe as l (l.ingredient_id)}
								<option value={l.ingredient_id}>{l.nom} ({l.achat})</option>
							{/each}
						</optgroup>
						{#if choix.horsListe.length}
							<optgroup label="Hors liste : correspondances">
								{#each choix.horsListe as p (p.id)}
									<option value={p.id}>{p.nom}</option>
								{/each}
							</optgroup>
						{/if}
						<optgroup label="Hors liste : autres ingrédients">
							{#each choix.autres as i (i.id)}
								<option value={i.id}>{i.nom}</option>
							{/each}
						</optgroup>
					{/if}
					<option value={AUTRE_PRODUIT}>Autre produit (hors repas)</option>
				</select>
			</label>
			{#if article === AUTRE_PRODUIT}
				<label>
					Nom
					<input type="text" maxlength="120" bind:value={nomProduit} />
				</label>
				<label>
					Catégorie
					<select bind:value={categorie}>
						{#each categories as c (c)}<option value={c}>{c}</option>{/each}
					</select>
				</label>
				<label class="case">
					<input type="checkbox" bind:checked={ranger} />
					Ranger au placard (décocher pour un produit consommé tout de suite)
				</label>
			{:else}
				<label>
					Quantité achetée (g ou ml)
					<input type="number" min="1" step="any" bind:value={quantiteAchetee} />
				</label>
			{/if}
			<label>
				Prix payé (€)
				<input type="number" min="0" step="0.01" bind:value={prixPaye} />
				<span class="doux">
					{produit.dernier_prix_eur !== null ? 'Dernier prix payé' : 'Estimation'}, à corriger selon
					l'étiquette.
				</span>
			</label>
			<div class="ligne">
				<button
					class="principal"
					disabled={!article ||
						(article === AUTRE_PRODUIT ? !nomProduit.trim() || !categorie : quantiteAchetee <= 0)}
				>
					Enregistrer
				</button>
				<button type="button" onclick={() => (produit = null)}>Scanner un autre produit</button>
			</div>
		</form>
	{:else}
		<ScannerCodeBarres onCode={rechercherProduit} />
	{/if}
</Modale>

<style>
	.reel {
		color: var(--texte);
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

	.formulaire-scan :is(input:not([type='checkbox']), select) {
		width: 100%;
	}

	.formulaire-scan label.case {
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
	}

	.attente {
		display: inline-block;
		margin: 0.5rem 0;
		/* Phrase complète : elle doit revenir à la ligne sur un écran de téléphone. */
		white-space: normal;
		border-radius: 8px;
	}

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

	li label {
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
