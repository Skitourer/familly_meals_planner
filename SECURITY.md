# Sécurité

Application familiale auto-hébergée, protégée par un mot de passe unique.

- Changez `REPAS_MOT_DE_PASSE` et `REPAS_CLE_SECRETE` avant toute exposition sur Internet.
- Exposez l'application uniquement derrière HTTPS (voir `docs/deploiement.md`) et activez
  `REPAS_COOKIE_SECURISE=true`.

Pour signaler une faille, utilisez les
[avis de sécurité privés GitHub](../../security/advisories/new) plutôt qu'une issue publique.
