// Lecteur de codes-barres de secours (ADR 8) pour les navigateurs sans BarcodeDetector
// (Firefox) : ZXing compilé en WebAssembly, chargé seulement à l'ouverture du scanner.
// Le fichier .wasm est servi par l'application (pas de CDN : CSP et confidentialité).
import { BarcodeDetector, prepareZXingModule } from 'barcode-detector/ponyfill';
import urlWasm from 'zxing-wasm/reader/zxing_reader.wasm?url';

prepareZXingModule({
	overrides: {
		locateFile: (chemin: string, prefixe: string) =>
			chemin.endsWith('.wasm') ? urlWasm : prefixe + chemin
	}
});

export { BarcodeDetector };
