<!--
	Lecture d'un code-barres de produit : caméra arrière avec l'API BarcodeDetector du navigateur
	quand elle existe, saisie des chiffres sous le code-barres sinon (toujours proposée).
	La caméra exige HTTPS (ou localhost) ; elle est coupée dès qu'un code est lu.
-->
<script lang="ts">
	import { codeDetecte, codePlausible, FORMATS_PRODUITS, nettoyerCode } from '#lib/code-barres.ts';

	// API récente, absente des types du DOM fournis par TypeScript.
	interface CodeLu {
		rawValue: string;
		format: string;
	}
	interface Detecteur {
		detect(source: HTMLVideoElement): Promise<CodeLu[]>;
	}
	interface ClasseDetecteur {
		new (options: { formats: string[] }): Detecteur;
		getSupportedFormats(): Promise<string[]>;
	}

	let { onCode }: { onCode: (code: string) => void } = $props();

	const INTERVALLE_MS = 250; // assez fréquent pour un geste naturel, sans chauffer le téléphone

	let video = $state<HTMLVideoElement>();
	let etat = $state<'demarrage' | 'lecture' | 'indisponible' | 'refusee'>('demarrage');
	let saisie = $state('');
	const codeSaisi = $derived(nettoyerCode(saisie));

	$effect(() => {
		let flux: MediaStream | undefined;
		let minuteur: ReturnType<typeof setInterval> | undefined;
		let actif = true;

		async function demarrer() {
			const Classe = (window as unknown as { BarcodeDetector?: ClasseDetecteur }).BarcodeDetector;
			if (!Classe || !navigator.mediaDevices?.getUserMedia) {
				etat = 'indisponible';
				return;
			}
			const formats = (await Classe.getSupportedFormats()).filter((f) =>
				FORMATS_PRODUITS.includes(f)
			);
			if (!formats.length) {
				etat = 'indisponible';
				return;
			}
			try {
				flux = await navigator.mediaDevices.getUserMedia({
					video: { facingMode: 'environment' },
					audio: false
				});
			} catch {
				etat = 'refusee';
				return;
			}
			if (!actif || !video) return arreter();
			video.srcObject = flux;
			await video.play();
			etat = 'lecture';
			const detecteur = new Classe({ formats });
			minuteur = setInterval(async () => {
				if (!video || video.readyState < 2) return;
				const lus = await detecteur.detect(video).catch(() => []);
				for (const lu of lus) {
					const code = codeDetecte(lu.rawValue, lu.format);
					if (code && actif) {
						arreter();
						onCode(code);
						return;
					}
				}
			}, INTERVALLE_MS);
		}

		function arreter() {
			actif = false;
			clearInterval(minuteur);
			flux?.getTracks().forEach((piste) => piste.stop());
		}

		demarrer();
		return arreter;
	});

	function valider(event: SubmitEvent) {
		event.preventDefault();
		if (codePlausible(codeSaisi)) onCode(codeSaisi);
	}
</script>

{#if etat === 'demarrage' || etat === 'lecture'}
	<!-- svelte-ignore a11y_media_has_caption : flux de la caméra, sans son -->
	<video bind:this={video} muted playsinline class:cachee={etat !== 'lecture'}></video>
	<p class="doux">
		{etat === 'lecture' ? 'Visez le code-barres du produit.' : 'Ouverture de la caméra…'}
	</p>
{:else if etat === 'indisponible'}
	<p class="doux">
		Ce navigateur ne sait pas lire les codes-barres avec la caméra : saisissez les chiffres imprimés
		sous le code-barres.
	</p>
{:else}
	<p class="doux">
		Caméra inaccessible (autorisation refusée, ou page sans HTTPS) : saisissez les chiffres imprimés
		sous le code-barres.
	</p>
{/if}

<form class="ligne" onsubmit={valider}>
	<input
		type="text"
		inputmode="numeric"
		autocomplete="off"
		placeholder="ex. 3017620422003"
		bind:value={saisie}
		aria-label="Chiffres du code-barres"
	/>
	<button disabled={!codePlausible(codeSaisi)}>Rechercher</button>
</form>

<style>
	video {
		width: 100%;
		max-height: 50vh;
		border-radius: var(--rayon);
		background: #000;
		object-fit: cover;
	}

	.cachee {
		display: none;
	}
</style>
