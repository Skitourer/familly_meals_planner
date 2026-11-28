<!--
	Onglet Bilan : nutrition dans le temps, carbone et budget, goûts et variété,
	saison et anti-gaspillage, sur les dernières semaines.
-->
<script lang="ts">
	import { api, messageErreur } from '#lib/api.ts';
	import BarresHebdo from '#lib/composants/BarresHebdo.svelte';
	import NutriScore from '#lib/composants/NutriScore.svelte';
	import { dateCourte, depuisIso } from '#lib/dates.ts';
	import type { BilanPeriode } from '#lib/types.ts';

	const PERIODES = [
		{ semaines: 4, libelle: '4 semaines' },
		{ semaines: 12, libelle: '3 mois' },
		{ semaines: 26, libelle: '6 mois' },
		{ semaines: 52, libelle: '1 an' }
	];
	const REPERES: [string, string][] = [
		['energie', 'Énergie'],
		['proteines', 'Protéines'],
		['lipides', 'Lipides'],
		['ags', 'Graisses saturées'],
		['fibres', 'Fibres'],
		['sel', 'Sel'],
		['fruits_legumes', 'Fruits et légumes'],
		['poisson', 'Poisson'],
		['legumineuses', 'Légumineuses'],
		['laitiers', 'Produits laitiers'],
		['viande_rouge', 'Viande rouge'],
		['charcuterie', 'Charcuterie']
	];
	const SYMBOLES = { ok: '✓', attention: '≈', hors_cible: '✗' };
	const PROTEINES: Record<string, string> = {
		legumineuse: 'Légumineuses',
		poisson: 'Poisson',
		volaille: 'Volaille',
		viande: 'Viande',
		oeuf: 'Œufs',
		fromage: 'Fromage, laitages',
		vegetal: 'Végétal'
	};

	let periode = $state(12);
	let bilan = $state<BilanPeriode | null>(null);
	let erreur = $state('');

	$effect(() => {
		charger(periode);
	});

	async function charger(semaines: number) {
		erreur = '';
		try {
			bilan = await api.lire<BilanPeriode>(`/bilan?semaines=${semaines}`);
		} catch (e) {
			erreur = messageErreur(e);
		}
	}

	const f1 = (n: number) => n.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
	const euros = (n: number) => n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
	const court = (iso: string) => dateCourte(depuisIso(iso));
	const moyenne = (valeurs: number[]) =>
		valeurs.length ? valeurs.reduce((a, b) => a + b, 0) / valeurs.length : 0;

	const semaines = $derived(bilan?.semaines ?? []);
	const conformite = $derived(
		REPERES.map(([code, libelle]) => {
			const presentes = semaines.filter((s) => s.reperes[code]);
			const ok = presentes.filter((s) => s.reperes[code].statut === 'ok').length;
			return { code, libelle, pourcentage: presentes.length ? (100 * ok) / presentes.length : 0 };
		})
	);
	const proteinesTotal = $derived.by(() => {
		const total: Record<string, number> = {};
		// Les repas pris dehors de catégorie connue (un par membre) s'ajoutent à ceux de la maison.
		for (const s of semaines)
			for (const [cle, n] of [
				...Object.entries(s.proteines),
				...Object.entries(s.proteines_exterieur ?? {})
			])
				total[cle] = (total[cle] ?? 0) + n;
		const somme = Object.values(total).reduce((a, b) => a + b, 0) || 1;
		return Object.entries(total)
			.sort((a, b) => b[1] - a[1])
			.map(([cle, n]) => ({ libelle: PROTEINES[cle] ?? cle, pourcentage: (100 * n) / somme }));
	});
	const nbRepas = $derived(semaines.reduce((n, s) => n + s.nb_repas, 0));
	const nbRepasDehors = $derived(
		semaines.reduce(
			(n, s) => n + Object.values(s.proteines_exterieur ?? {}).reduce((a, b) => a + b, 0),
			0
		)
	);
</script>

<div class="entete">
	<h1>Bilan</h1>
	<div class="onglets" role="tablist" aria-label="Période">
		{#each PERIODES as p (p.semaines)}
			<button
				role="tab"
				aria-selected={periode === p.semaines}
				onclick={() => (periode = p.semaines)}
			>
				{p.libelle}
			</button>
		{/each}
	</div>
</div>

{#if erreur}<p class="erreur">{erreur}</p>{/if}

{#if bilan && !semaines.length}
	<p class="carte">
		Pas encore de semaine planifiée sur cette période : <a href="/">générez des repas</a> pour voir apparaître
		le bilan.
	</p>
{:else if bilan}
	<!-- Chiffres clés -->
	<section class="tuiles">
		<div class="carte tuile">
			<span class="doux">Repas planifiés</span>
			<strong>{nbRepas}</strong>
			<span class="doux">{bilan.nb_plats_differents} plats différents</span>
		</div>
		<div class="carte tuile">
			<span class="doux">Nutri-Score moyen</span>
			<NutriScore lettre={semaines[semaines.length - 1].nutriscore_moyen} taille="normale" />
			<span class="doux">dernière semaine</span>
		</div>
		<div class="carte tuile">
			<span class="doux">CO₂ évité</span>
			<strong>{f1(bilan.co2_economise_kg)} kg</strong>
			<span class="doux">≈ {bilan.equivalent_km_voiture} km en voiture</span>
		</div>
		<div class="carte tuile">
			<span class="doux">Budget courses</span>
			<strong>{euros(bilan.budget_total_eur)}</strong>
			<span class="doux">
				{euros(moyenne(semaines.map((s) => s.cout_par_repas_personne_eur)))} par repas et par personne
			</span>
		</div>
	</section>

	<!-- 1. Nutrition dans le temps -->
	<section class="carte">
		<h2>Nutrition dans le temps</h2>
		<p class="doux">Repères ANSES / PNNS par semaine (repas hors jokers, portion de référence).</p>
		<div class="tableau-defilant">
			<table class="reperes">
				<thead>
					<tr>
						<th scope="col">Repère</th>
						{#each semaines as s (s.lundi)}<th scope="col">{court(s.lundi)}</th>{/each}
						<th scope="col">Conforme</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<th scope="row">Nutri-Score moyen</th>
						{#each semaines as s (s.lundi)}
							<td><NutriScore lettre={s.nutriscore_moyen} taille="petite" /></td>
						{/each}
						<td></td>
					</tr>
					{#each conformite as r (r.code)}
						<tr>
							<th scope="row">{r.libelle}</th>
							{#each semaines as s (s.lundi)}
								{@const valeur = s.reperes[r.code]}
								<td class={valeur?.statut ?? ''} title={valeur ? f1(valeur.valeur) : ''}>
									{valeur ? SYMBOLES[valeur.statut] : '–'}
								</td>
							{/each}
							<td class="pourcentage">{Math.round(r.pourcentage)} %</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<p class="doux">✓ atteint · ≈ proche (moins de 10 % d'écart) · ✗ hors cible</p>

		<h3>Couverture des besoins par membre</h3>
		<p class="doux">
			Apport moyen d'un déjeuner ou dîner pris à la maison, comparé à 30 % de la référence
			journalière (ANSES / EFSA) selon l'âge et le sexe. En dessous de 70 % : point d'attention (le
			petit-déjeuner et le goûter complètent). Les repas pris dehors (cantine...) sont supposés
			équilibrés et ne sont pas comptés. Valeurs des aliments crus : la cuisson réduit la vitamine C
			et les folates (souvent de 30 à 50 %).
		</p>
		<div class="membres">
			{#each bilan.membres as m (m.id)}
				<div class="membre" style:--couleur={m.couleur}>
					<strong>{m.prenom}</strong>
					<span class="doux">
						{m.repas_a_la_maison} repas à la maison · {m.repas_dehors} dehors
					</span>
					{#each m.couverture as n (n.code)}
						<div
							class="jauge"
							title={`${f1(n.apport_par_repas)} ${n.unite} par repas (repère : ${f1(n.reference_par_repas)} ${n.unite})`}
						>
							<span>{n.libelle}</span>
							<meter min="0" max="150" low="70" high="150" optimum="120" value={n.pourcentage}
							></meter>
							<span class:faible={n.pourcentage < 70}>{n.pourcentage} %</span>
						</div>
					{/each}
				</div>
			{/each}
		</div>
	</section>

	<!-- 2. Carbone et budget -->
	<section class="deux-colonnes">
		<div class="carte">
			<h2>Empreinte carbone</h2>
			<p class="doux">
				Total {f1(bilan.co2_total_kg)} kg CO₂e pour la famille ; des repas moyens auraient émis
				{f1(bilan.co2_total_kg + bilan.co2_economise_kg)} kg.
			</p>
			<BarresHebdo
				unite="kg CO₂e"
				libelleReference="Repas moyens (2 kg CO₂e par repas)"
				points={semaines.map((s) => ({
					libelle: court(s.lundi),
					valeur: s.co2_kg,
					reference: s.co2_reference_kg
				}))}
			/>
		</div>
		<div class="carte">
			<h2>Budget</h2>
			<p class="doux">
				Courses estimées par semaine (prix médians Open Prices). Les semaines dont les courses ont
				été validées utilisent la liste réellement achetée.
			</p>
			<BarresHebdo
				unite="€"
				points={semaines.map((s) => ({
					libelle: court(s.lundi),
					valeur: s.budget_eur,
					detail: `${euros(s.cout_par_repas_personne_eur)} par repas et par personne${s.budget_estime ? ' (estimation)' : ''}`
				}))}
			/>
		</div>
	</section>

	<!-- 3. Goûts et variété -->
	<section class="carte">
		<h2>Goûts et variété</h2>
		<div class="grille-gouts">
			{#each bilan.membres as m (m.id)}
				<div>
					<h3 style:color={m.couleur}>{m.prenom}</h3>
					{#if m.preferes.length}
						<p class="doux">Préférés</p>
						<ul>
							{#each m.preferes as [nom, note] (nom)}<li>
									{nom} <span class="doux">★ {f1(note)}</span>
								</li>{/each}
						</ul>
					{/if}
					{#if m.moins_aimes.length}
						<p class="doux">Moins aimés</p>
						<ul>
							{#each m.moins_aimes as [nom, note] (nom)}<li>
									{nom} <span class="doux">★ {f1(note)}</span>
								</li>{/each}
						</ul>
					{/if}
					{#if !m.preferes.length && !m.moins_aimes.length}
						<p class="doux">Pas encore de notes : <a href="/notes">noter les repas</a>.</p>
					{/if}
				</div>
			{/each}
		</div>

		<div class="chiffres">
			<div>
				<strong>{f1(moyenne(semaines.map((s) => s.part_vegetarien)))} %</strong>
				<span>de repas végétariens</span>
			</div>
			<div>
				<strong>{f1(moyenne(semaines.map((s) => s.legumes_differents)))}</strong>
				<span>légumes différents par semaine</span>
			</div>
			<div>
				<strong>{bilan.nb_plats_differents}</strong><span>plats différents servis</span>
			</div>
		</div>

		<h3>Sources de protéines</h3>
		{#if nbRepasDehors}
			<p class="doux">
				Y compris {nbRepasDehors} repas pris dehors dont la catégorie a été indiquée.
			</p>
		{/if}
		<ul class="repartition">
			{#each proteinesTotal as p (p.libelle)}
				<li>
					<span>{p.libelle}</span>
					<span class="barre-horizontale" style:width={`${p.pourcentage}%`}></span>
					<span class="valeur">{Math.round(p.pourcentage)} %</span>
				</li>
			{/each}
		</ul>

		{#if bilan.a_redecouvrir.length}
			<h3>À redécouvrir</h3>
			<p class="doux">Plats bien notés qui n'ont pas été servis depuis un mois :</p>
			<p>{bilan.a_redecouvrir.join(' · ')}</p>
		{/if}
		<details>
			<summary>{bilan.jamais_servis.length} plats jamais servis sur la période</summary>
			<p>{bilan.jamais_servis.join(' · ')}</p>
		</details>
	</section>

	<!-- 4. Saison et anti-gaspillage -->
	<section class="deux-colonnes">
		<div class="carte">
			<h2>Saisonnalité</h2>
			<p class="doux">Part des fruits et légumes frais achetés en saison (en poids).</p>
			<BarresHebdo
				unite="%"
				points={semaines.map((s) => ({ libelle: court(s.lundi), valeur: s.part_saison }))}
			/>
		</div>
		<div class="carte">
			<h2>Anti-gaspillage</h2>
			<dl class="gaspillage">
				<dt>Repris dans le placard plutôt qu'achetés</dt>
				<dd>{f1(bilan.gaspillage.depuis_placard_kg)} kg</dd>
				<dt>Restes de paquets rangés au placard</dt>
				<dd>{f1(bilan.gaspillage.surplus_placard_kg)} kg</dd>
				<dt>Surplus de produits frais (à consommer vite)</dt>
				<dd>{f1(bilan.gaspillage.surplus_perdu_kg)} kg</dd>
			</dl>
			<p class="doux">
				Sur {bilan.gaspillage.semaines_validees} semaine(s) dont les courses ont été validées.
			</p>
			{#if bilan.gaspillage.perimes.length}
				<p class="erreur">
					Périmés au placard : {bilan.gaspillage.perimes.join(', ')} —
					<a href="/placard">mettre à jour</a>
				</p>
			{/if}
		</div>
	</section>
{/if}

<style>
	.entete {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	section {
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

	.tuiles {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 0.75rem;
	}

	.tuile {
		display: grid;
		gap: 0.2rem;
		justify-items: start;
	}

	.tuile strong {
		font-size: 1.6rem;
	}

	.deux-colonnes {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
		gap: 0.75rem;
	}

	.tableau-defilant {
		overflow-x: auto;
	}

	table.reperes {
		border-collapse: collapse;
		font-size: 0.85rem;
	}

	.reperes th,
	.reperes td {
		padding: 0.25rem 0.45rem;
		text-align: center;
		border-bottom: 1px solid var(--bordure);
		white-space: nowrap;
	}

	.reperes th[scope='row'] {
		text-align: left;
		font-weight: 500;
	}

	.reperes thead th {
		font-size: 0.75rem;
		color: var(--texte-doux);
		font-weight: 600;
	}

	td.ok {
		color: var(--ok);
	}

	td.attention {
		color: var(--attention);
		font-weight: 700;
	}

	td.hors_cible {
		color: var(--alerte);
		font-weight: 700;
	}

	.pourcentage {
		font-weight: 600;
	}

	h3 {
		font-size: 1rem;
		margin: 1rem 0 0.25rem;
	}

	.membres {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
		gap: 0.75rem;
	}

	.membre {
		display: grid;
		gap: 0.25rem;
		border-left: 4px solid var(--couleur);
		padding-left: 0.6rem;
	}

	.jauge {
		display: grid;
		grid-template-columns: 8.5rem 1fr 3.2rem;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.8rem;
	}

	meter {
		width: 100%;
	}

	.faible {
		color: var(--attention);
		font-weight: 700;
	}

	.grille-gouts {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 0.75rem;
	}

	.grille-gouts ul {
		margin: 0;
		padding-left: 1.1rem;
		font-size: 0.9rem;
	}

	.grille-gouts p {
		margin: 0.3rem 0 0.1rem;
	}

	.chiffres {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 0.5rem;
		margin-top: 1rem;
	}

	.chiffres div {
		display: grid;
		background: var(--surface-2);
		border-radius: 8px;
		padding: 0.5rem 0.7rem;
	}

	.chiffres strong {
		font-size: 1.3rem;
	}

	.chiffres span {
		font-size: 0.8rem;
		color: var(--texte-doux);
	}

	.repartition {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 0.3rem;
	}

	.repartition li {
		display: grid;
		grid-template-columns: 9rem 1fr 3rem;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.85rem;
	}

	.barre-horizontale {
		height: 0.7rem;
		background: var(--accent);
		border-radius: 0 4px 4px 0;
		min-width: 2px;
	}

	.valeur {
		text-align: right;
		font-weight: 600;
	}

	.gaspillage {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 0.3rem 0.75rem;
		margin: 0 0 0.5rem;
	}

	.gaspillage dd {
		margin: 0;
		font-weight: 600;
		text-align: right;
	}

	details {
		margin-top: 0.75rem;
	}
</style>
