# 4. Pas d'IA à l'exécution, import JSON à la place

*Date : 2026-11-24 — Statut : acceptée*

## Contexte

La famille souhaite pouvoir enrichir le catalogue avec des recettes proposées par une IA,
sans que l'application dépende d'un service d'IA (coût, confidentialité, disponibilité,
reproductibilité).

## Décision

- L'application ne contacte **aucune IA**.
- Elle produit un **fichier d'instructions** (Markdown) qui décrit le format JSON attendu et
  la liste à jour des ingrédients autorisés ; la famille le donne à l'IA de son choix.
- Le JSON obtenu est **importé et validé** : structure, unicité, ingrédients connus,
  plausibilité nutritionnelle. Les valeurs nutritionnelles, carbone, saison et prix sont
  toujours recalculées à partir des bases ouvertes, jamais reprises de l'IA.

## Conséquences

- Fonctionnement hors ligne et sans clé d'API.
- Une IA ne peut pas introduire de valeurs nutritionnelles fausses ; au pire, une recette est
  refusée ou signalée.
- Le fichier d'instructions est testé : son exemple doit s'importer sans erreur.
