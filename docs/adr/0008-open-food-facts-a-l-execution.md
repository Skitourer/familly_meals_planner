# 8. Open Food Facts consulté à l'exécution pour les produits scannés

*Date : 2026-11-25 — Statut : acceptée*

## Contexte

La famille veut remplir le placard en scannant le code-barres des produits (#16). Un
code-barres ne dit rien du produit : il faut une base de produits. Jusqu'ici, les bases
ouvertes n'étaient lues qu'à l'import (`repas-import`), jamais par l'application en marche.

## Décision

- Le serveur interroge l'API produit d'**Open Food Facts** (`/api/v2/product/{code}`) quand
  un adulte scanne un produit : nom, marque, contenu du paquet et catégories.
- Seul le **code-barres** est envoyé, avec le User-Agent de l'application ; aucune donnée de
  la famille. Le code est validé (chiffres, longueur, clé de contrôle) avant l'appel.
- L'ingrédient est proposé grâce à la catégorie Open Food Facts déjà renseignée dans le
  référentiel (`categorie_off`), la plus précise d'abord ; la personne confirme toujours.
- Lecture par la caméra avec l'API **BarcodeDetector** du navigateur, sans bibliothèque ;
  la saisie des chiffres reste toujours possible.

## Conséquences

- Le scan exige le réseau ; sans réseau ou si Open Food Facts ne répond pas en 6 s, un
  message invite à saisir le produit à la main. Le reste de l'application n'en dépend pas.
- BarcodeDetector n'existe pas partout (Safari sur iPhone, Firefox) : ces navigateurs n'ont
  que la saisie des chiffres. Une bibliothèque de lecture (ZXing) pourra être ajoutée si
  le besoin est confirmé.

## Alternatives écartées

- **Copie locale d'Open Food Facts** : plusieurs Go, à tenir à jour, disproportionné.
- **Appel direct depuis le navigateur** : il exposerait chaque appareil à un site tiers et
  dupliquerait la validation ; le serveur garde la main sur le délai et les erreurs.
