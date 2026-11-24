# 2. Planification par optimisation CP-SAT

*Date : 2026-11-24 — Statut : acceptée*

## Contexte

Les exigences sont nombreuses et couplées : repères nutritionnels **hebdomadaires**,
non-répétition, plats cuisinés en lot sur plusieurs jours, jokers, préférences de chacun,
saison, carbone, budget, placard. Un algorithme glouton (choisir repas par repas) ne peut pas
garantir l'équilibre de la semaine.

## Décision

Formuler la semaine comme un **programme linéaire en nombres entiers** et le résoudre avec
**CP-SAT** (OR-Tools, Apache 2.0). La nutrition est exprimée en contraintes souples à très
forte pénalité, les préférences en objectif pondéré (voir
[Algorithme](../technique/algorithme.md)).

## Conséquences

- Solutions optimales en quelques secondes, explicables (chaque terme de l'objectif est
  nommé) et testables (les écarts aux repères sont renvoyés).
- Ajouter une règle revient à ajouter une contrainte, sans réécrire l'algorithme.
- Dépendance binaire OR-Tools (~30 Mo), disponible pour amd64 et arm64 (Raspberry Pi).
