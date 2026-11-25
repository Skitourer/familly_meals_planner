<!--
	Autres produits du placard (Nutella, céréales...) : hors repas, comptés en paquets et
	regroupés par catégorie. Les boutons − et + corrigent le nombre de paquets ; 0 retire le produit.
-->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import type { ProduitPlacard } from '#lib/types.ts';

	let {
		produits,
		categories,
		onModifie
	}: { produits: ProduitPlacard[]; categories: string[]; onModifie: () => Promise<void> } =
		$props();

	let erreur = $state('');
	let nom = $state('');
	let categorie = $state('Épicerie');
	let paquets = $state(1);
	let peremption = $state('');

	const groupes = $derived(
		categories
			.map((c) => [c, produits.filter((p) => p.categorie === c)] as const)
			.filter(([, liste]) => liste.length)
	);

	async function modifier(produit: ProduitPlacard, changement: Record<string, unknown>) {
		erreur = '';
		try {
			await api.modifier(`/placard/produits/${produit.id}`, changement);
			await onModifie();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	async function ajouter(event: SubmitEvent) {
		event.preventDefault();
		erreur = '';
		try {
			await api.creer('/placard/produits', {
				nom: nom.trim(),
				categorie,
				paquets,
				peremption: peremption || null
			});
			nom = '';
			paquets = 1;
			peremption = '';
			await onModifie();
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	const details = (p: ProduitPlacard) => [p.marque, p.contenu].filter(Boolean).join(' · ');
</script>

<section class="carte">
	<h2>Autres produits</h2>
	<p class="doux">Hors repas (petit-déjeuner, goûters, boissons…), comptés en paquets.</p>
	{#if erreur}<p class="erreur">{erreur}</p>{/if}
	{#if !produits.length}
		<p class="doux">Aucun pour l'instant : scannez-les ou ajoutez-les ci-dessous.</p>
	{/if}
	{#each groupes as [nomCategorie, liste] (nomCategorie)}
		<h3>{nomCategorie}</h3>
		<ul>
			{#each liste as produit (produit.id)}
				<li>
					<div class="nom">
						<strong>{produit.nom}</strong>
						{#if details(produit)}<span class="doux">{details(produit)}</span>{/if}
						{#if produit.bientot_perime}<span class="badge alerte">à vider</span>{/if}
					</div>
					<div class="ligne actions">
						<button
							class="discret"
							onclick={() => modifier(produit, { paquets: produit.paquets - 1 })}
							aria-label={`Un paquet de moins : ${produit.nom}`}
						>
							−
						</button>
						<span class="paquets" aria-label={`Paquets de ${produit.nom}`}>{produit.paquets}</span>
						<button
							class="discret"
							onclick={() => modifier(produit, { paquets: produit.paquets + 1 })}
							disabled={produit.paquets >= 99}
							aria-label={`Un paquet de plus : ${produit.nom}`}
						>
							+
						</button>
						<input
							type="date"
							value={produit.peremption ?? ''}
							aria-label={`Date limite de ${produit.nom}`}
							onchange={(e) =>
								modifier(produit, { peremption: (e.target as HTMLInputElement).value || null })}
						/>
						<button
							class="discret"
							onclick={() => modifier(produit, { paquets: 0 })}
							aria-label={`Retirer ${produit.nom}`}
						>
							🗑
						</button>
					</div>
				</li>
			{/each}
		</ul>
	{/each}

	<form class="ligne ajout" onsubmit={ajouter}>
		<input
			type="text"
			maxlength="120"
			placeholder="Ajouter un produit…"
			bind:value={nom}
			aria-label="Nom du produit à ajouter"
		/>
		<select bind:value={categorie} aria-label="Catégorie">
			{#each categories as c (c)}<option value={c}>{c}</option>{/each}
		</select>
		<input type="number" min="1" max="99" bind:value={paquets} aria-label="Nombre de paquets" />
		<input type="date" bind:value={peremption} aria-label="Date limite (facultatif)" />
		<button disabled={!nom.trim()}>Ajouter</button>
	</form>
</section>

<style>
	h3 {
		margin: 0.8rem 0 0.3rem;
		font-size: 0.9rem;
		color: var(--texte-doux);
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.5rem;
	}

	li {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: center;
		gap: 0.4rem;
		padding-bottom: 0.4rem;
		border-bottom: 1px solid var(--bordure);
	}

	.nom {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		align-items: baseline;
		min-width: 0;
	}

	.actions {
		gap: 0.3rem;
	}

	.paquets {
		min-width: 1.6rem;
		text-align: center;
		font-weight: 600;
	}

	.ajout {
		margin-top: 1rem;
	}

	.ajout input[type='number'] {
		width: 4.5rem;
	}
</style>
