# 9. Protections HTTP, sans double authentification

*Date : 2026-11-28 — Statut : acceptée*

## Contexte

L'audit OWASP ASVS niveau 1 (#29) devait trancher la double authentification (TOTP,
passkeys) et compléter les protections HTTP. L'application est hébergée à la maison et
n'est joignable que par Tailscale : seuls les appareils autorisés du réseau y accèdent.

## Décision

- **Pas de double authentification** : l'appartenance au réseau Tailscale (appareil
  enregistré, compte Tailscale protégé) joue le rôle de second facteur. Mot de passe haché
  avec scrypt et limitation des essais restent la première barrière.
- **CSRF** : en plus du cookie `SameSite=Lax`, les requêtes modifiantes de l'API exigent
  l'en-tête `X-Menu-Famille`, qu'un site tiers ne peut pas ajouter sans CORS (jamais
  accordé). Pas de jeton CSRF à gérer.
- **En-têtes** sur toutes les réponses : CSP stricte (scripts de la même origine, script
  en ligne de l'interface autorisé par son empreinte calculée au démarrage),
  `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy` et HSTS derrière HTTPS.
- **Corps des requêtes** limité à 3 Mo ; clé de session par défaut refusée en production.

## Conséquences

- Si l'application est un jour exposée directement sur Internet (VPS), cette décision est
  à revoir : TOTP pour les comptes adultes devient alors nécessaire.
- Tout appel modifiant l'API hors de l'interface (script, test) doit envoyer l'en-tête.

## Alternatives écartées

- **TOTP ou passkeys dès maintenant** : écran d'enrôlement, récupération en cas de perte
  du téléphone et dépendance en plus, pour un risque déjà couvert par Tailscale.
- **Jeton CSRF synchronisé** : plus de code côté interface pour une protection équivalente
  à l'en-tête personnalisé dans une application monopage.
