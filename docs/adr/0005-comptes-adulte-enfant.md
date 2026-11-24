# 5. Comptes adulte et enfant

*Date : 2026-11-24 — Statut : acceptée (remplace le mot de passe unique de la v1)*

## Contexte

Les enfants veulent consulter le menu et donner leur avis, sans pouvoir modifier la
planification, les courses ou la famille. Un mot de passe unique ne permet pas de
distinguer ces droits.

## Décision

- Des **comptes** (identifiant + mot de passe haché avec scrypt, bibliothèque standard),
  avec deux rôles : **adulte** (tous les droits) et **enfant** (relié à un membre : lecture
  du menu et des plats, avis sur ses propres repas passés et à venir).
- Les droits sont appliqués **côté serveur** par des dépendances FastAPI
  (`exiger_connexion`, `exiger_adulte`) ; l'interface masque en plus ce qui n'est pas permis.
- **Compatibilité** : au premier démarrage sans compte, un compte adulte `famille` est créé
  avec l'ancien mot de passe (`REPAS_MOT_DE_PASSE`).
- Les avis « à venir » sont des notes posées à l'avance sur les repas planifiés : ils
  alimentent les préférences sans nouveau modèle de données.

## Conséquences

- Pas de dépendance supplémentaire ni de service d'identité externe.
- Il doit toujours rester un compte adulte actif (contrôlé par l'API).
- Le blocage après échecs est en mémoire : il est remis à zéro au redémarrage, ce qui est
  suffisant pour une application familiale.
