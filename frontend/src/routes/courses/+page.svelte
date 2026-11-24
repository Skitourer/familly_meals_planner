<!--
	Liste de courses de la semaine : par rayon, arrondie aux conditionnements du magasin.
	Les coches sont partagées entre appareils ; sans réseau, elles attendent sur l'appareil
	et partent au retour de la connexion (voir lib/coches.ts).
-->
<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/state';
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
	import { lundiDepuisUrl } from '#lib/semaine.ts';
	import type { Courses } from '#lib/types.ts';

	const lundi = $derived(lundiDepuisUrl(page.url));
	let courses = $state<Courses | null>(null);
	let erreur = $state('');
	let file = $state<FileCoches>({});
	let enLigne = $state(true);
	let envoiEnCours = false;

	const coches = $derived(cochesAffichees(courses?.coches ?? [], file));
	const enAttente = $derived(Object.keys(file).length);

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
				<button class="principal" onclick={valider} disabled={!enLigne}>✅ Courses faites</button>
			{:else}
				<span class="badge vert">Courses faites, placard à jour</span>
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
