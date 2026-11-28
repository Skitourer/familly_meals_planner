# 8. Open Food Facts consulté à l'exécution pour les produits scannés

*Date : 2026-11-25, mise à jour le 2026-11-28 — Statut : acceptée*

## Contexte

La famille veut scanner le code-barres des produits pour remplir le placard et suivre les
courses réelles (#16). Un
code-barres ne dit rien du produit : il faut une base de produits. Jusqu'ici, les bases
ouvertes n'étaient lues qu'à l'import (`repas-import`), jamais par l'application en marche.

## Décision

- Le serveur interroge l'API produit d'**Open Food Facts** (`/api/v2/product/{code}`) quand
  un adulte scanne un produit : nom, marque, contenu du paquet et catégories.
- Seul le **code-barres** est envoyé, avec le User-Agent de l'application ; aucune donnée de
  la famille. Le code est validé (chiffres, longueur, clé de contrôle) avant l'appel.
- L'ingrédient est proposé grâce à la catégorie Open Food Facts déjà renseignée dans le
  référentiel (`categorie_off`), la plus précise d'abord ; la personne confirme toujours.
- Aux courses, la quantité et le prix payés sont enregistrés par article ; le dernier prix
  payé pour chaque code-barres est gardé **dans la base de la famille** pour être proposé
  au scan suivant. Rien n'est envoyé à Open Prices.
- Lecture par la caméra avec l'API **BarcodeDetector** du navigateur quand elle existe
  (Chrome sur Android) ; sinon (Firefox), lecteur de secours **barcode-detector**
  (polyfill MIT de la même API, basé sur zxing-cpp compilé en WebAssembly). La saisie des
  chiffres reste toujours possible.

## Conséquences

- Le scan exige le réseau ; sans réseau ou si Open Food Facts ne répond pas en 6 s, un
  message invite à saisir le produit à la main. Le reste de l'application n'en dépend pas.
- Le lecteur de secours (#41) n'est chargé qu'à l'ouverture du scanner, et seulement sans
  BarcodeDetector natif. Son fichier `.wasm` (~1 Mo, 415 Ko compressé) est servi par
  l'application, jamais par un CDN ; il n'est pas gardé hors ligne (le scan demande le
  réseau). La CSP autorise `'wasm-unsafe-eval'` (compilation WebAssembly), pas `eval`.
- Dépendance retenue : maintenue activement, licence MIT, même API que le navigateur (le
  code du scanner ne change presque pas). Écartée : `@zxing/library` (JavaScript pur, plus
  lent et peu maintenu). Safari (iPhone) emprunte le même chemin mais n'est pas encore
  vérifié.

## Alternatives écartées

- **Copie locale d'Open Food Facts** : plusieurs Go, à tenir à jour, disproportionné.
- **Appel direct depuis le navigateur** : il exposerait chaque appareil à un site tiers et
  dupliquerait la validation ; le serveur garde la main sur le délai et les erreurs.
