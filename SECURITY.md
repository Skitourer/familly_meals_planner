# Sécurité

Application familiale auto-hébergée, accessible par comptes adulte et enfant. Elle suit
l'OWASP ASVS niveau 1 (audit #29, décisions dans
[l'ADR 9](docs/adr/0009-securite-http-sans-double-authentification.md)).

## Avant la mise en service

- Changez `REPAS_CLE_SECRETE` (l'application refuse de démarrer en production avec la
  valeur par défaut) et `REPAS_MOT_DE_PASSE`, puis le mot de passe dans l'application.
- Exposez l'application uniquement derrière HTTPS (Tailscale ou reverse proxy, voir
  `docs/exploitation/deploiement.md`) et activez `REPAS_COOKIE_SECURISE=true`.
- Pas de double authentification : l'accès par Tailscale en tient lieu. Une exposition
  directe sur Internet demande de revoir ce choix.

## Protections en place

- Mots de passe hachés avec scrypt ; connexion bloquée une minute après 5 échecs.
- Cookie de session signé, `HttpOnly`, `SameSite=Lax`, `Secure` derrière HTTPS ; droits
  vérifiés côté serveur sur chaque route (adulte ou enfant).
- Requêtes modifiantes protégées contre le CSRF (en-tête `X-Menu-Famille` exigé) ; aucune
  autorisation CORS ; corps des requêtes limité à 3 Mo.
- En-têtes CSP, HSTS (derrière HTTPS), `X-Content-Type-Options`, `frame-ancestors`.
- Erreurs renvoyées sans trace ; aucun mot de passe ni donnée personnelle dans les journaux.
- Conteneur sans root sur image `slim`.
- CI : gitleaks (tout l'historique), règles de sécurité ruff (`S`), `pip-audit`,
  `npm audit` ; *secret scanning* et *push protection* GitHub.

## Signaler une faille

Utilisez les [avis de sécurité privés GitHub](../../security/advisories/new) plutôt
qu'une issue publique.
