# 7. Thème « bol rigolo » et polices hébergées par l'application

*Date : 2026-11-24 — Statut : acceptée*

## Contexte

L'application est utilisée en famille, enfants compris, surtout sur téléphone. L'icône et le
thème vert d'origine étaient sobres mais peu reconnaissables parmi les autres applications.

## Décision

- Icône : un bol de soupe souriant sur fond tomate, avec ses variantes Android (adaptative,
  monochrome pour les icônes à thème) et iPhone (`frontend/icones/`).
- Thème : tomate, moutarde, basilic sur crème, en clair et en sombre (variables de
  `frontend/src/app.css`) ; chaque couleur de texte a un contraste d'au moins 4,5:1.
- Polices Fredoka (titres) et Nunito (texte), fichiers `woff2` copiés dans
  `frontend/static/polices/` avec leur licence SIL OFL 1.1 (sous-ensemble latin).

## Conséquences

- Aucun appel à Google Fonts : pas de donnée envoyée à un tiers, polices disponibles hors
  ligne (le service worker les garde avec les autres fichiers).
- Environ 70 ko de polices ; une mise à jour se fait à la main (rare).

## Alternatives écartées

- **Google Fonts en ligne** : appel externe à chaque visite, pas de hors-ligne.
- **Paquets `@fontsource`** : dépendance npm pour deux fichiers qui changent rarement.
- **Proposition sobre** (icône actuelle affinée) : moins reconnaissable, moins adaptée aux
  enfants.
