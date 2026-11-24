<!--
	Histogramme simple, une barre par semaine (une seule série : pas de légende, le titre la
	nomme). Une valeur de référence facultative est tracée en pointillés gris sur chaque barre.
	Survol (ou focus clavier) : infobulle avec la valeur exacte.
-->
<script lang="ts">
	interface Point {
		libelle: string;
		valeur: number;
		reference?: number;
		detail?: string;
	}

	let {
		points,
		unite,
		libelleReference = ''
	}: { points: Point[]; unite: string; libelleReference?: string } = $props();

	const HAUTEUR = 140;
	const LARGEUR_BARRE = 22;
	const ECART = 10;
	const MARGE_BAS = 22;

	let survol = $state<number | null>(null);

	const maximum = $derived(
		Math.max(1, ...points.map((p) => Math.max(p.valeur, p.reference ?? 0))) * 1.1
	);
	const largeur = $derived(points.length * (LARGEUR_BARRE + ECART) + ECART);
	const y = (v: number) => HAUTEUR - MARGE_BAS - (v / maximum) * (HAUTEUR - MARGE_BAS - 8);
	// Sommet de la barre (au moins 4 px de haut pour garder l'arrondi lisible).
	const haut = (v: number) => Math.min(y(v), y(0) - 4);
	const format = (v: number) => v.toLocaleString('fr-FR', { maximumFractionDigits: 1 });
</script>

<div class="graphique">
	<svg
		viewBox={`0 0 ${largeur} ${HAUTEUR}`}
		role="img"
		aria-label={`Valeurs par semaine (${unite})`}
	>
		<line class="axe" x1="0" x2={largeur} y1={y(0)} y2={y(0)} />
		{#each points as p, i (p.libelle)}
			{@const x = ECART + i * (LARGEUR_BARRE + ECART)}
			<g
				role="button"
				tabindex="0"
				aria-label={`${p.libelle} : ${format(p.valeur)} ${unite}`}
				onmouseenter={() => (survol = i)}
				onmouseleave={() => (survol = null)}
				onfocus={() => (survol = i)}
				onblur={() => (survol = null)}
			>
				<!-- zone de survol plus large que la barre -->
				<rect
					class="cible"
					x={x - ECART / 2}
					y="0"
					width={LARGEUR_BARRE + ECART}
					height={HAUTEUR}
				/>
				<path
					class="barre"
					class:active={survol === i}
					d={`M${x},${y(0)} V${haut(p.valeur) + 4} q0,-4 4,-4 h${LARGEUR_BARRE - 8} q4,0 4,4 V${y(0)} Z`}
				/>
				{#if p.reference !== undefined}
					<line
						class="reference"
						x1={x - 3}
						x2={x + LARGEUR_BARRE + 3}
						y1={y(p.reference)}
						y2={y(p.reference)}
					/>
				{/if}
				<text class="etiquette" x={x + LARGEUR_BARRE / 2} y={HAUTEUR - 6}>{p.libelle}</text>
			</g>
		{/each}
	</svg>
	{#if survol !== null}
		{@const p = points[survol]}
		<div
			class="infobulle"
			style:left={`${((ECART + survol * (LARGEUR_BARRE + ECART) + LARGEUR_BARRE / 2) / largeur) * 100}%`}
		>
			<strong>{format(p.valeur)} {unite}</strong>
			<span>semaine du {p.libelle}</span>
			{#if p.reference !== undefined}<span>
					{libelleReference} : {format(p.reference)}
					{unite}
				</span>{/if}
			{#if p.detail}<span>{p.detail}</span>{/if}
		</div>
	{/if}
</div>
{#if libelleReference}
	<p class="legende"><span class="trait"></span> {libelleReference}</p>
{/if}

<style>
	.graphique {
		position: relative;
		overflow-x: auto;
	}

	svg {
		display: block;
		min-width: 100%;
		max-height: 180px;
	}

	.axe {
		stroke: var(--bordure);
		stroke-width: 1;
	}

	.cible {
		fill: transparent;
	}

	.barre {
		fill: var(--accent);
		opacity: 0.85;
	}

	.barre.active {
		opacity: 1;
	}

	.reference {
		stroke: var(--texte-doux);
		stroke-width: 2;
		stroke-dasharray: 3 2;
	}

	.etiquette {
		fill: var(--texte-doux);
		font-size: 8px;
		text-anchor: middle;
	}

	g:focus {
		outline: none;
	}

	g:focus-visible .barre {
		stroke: var(--texte);
		stroke-width: 1.5;
	}

	.infobulle {
		position: absolute;
		top: 0;
		transform: translateX(-50%);
		display: grid;
		gap: 0.1rem;
		padding: 0.35rem 0.55rem;
		background: var(--surface);
		border: 1px solid var(--bordure);
		border-radius: 8px;
		box-shadow: var(--ombre);
		font-size: 0.75rem;
		white-space: nowrap;
		pointer-events: none;
	}

	.infobulle span {
		color: var(--texte-doux);
	}

	.legende {
		margin: 0.25rem 0 0;
		font-size: 0.75rem;
		color: var(--texte-doux);
	}

	.trait {
		display: inline-block;
		width: 1rem;
		border-top: 2px dashed var(--texte-doux);
		vertical-align: middle;
	}
</style>
