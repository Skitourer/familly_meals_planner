/**
 * Fruits et légumes de saison en France, par mois (1 = janvier).
 * Donnée de référence intégrée au code (source : calendriers maraîchers français).
 * Les plats portent leur propre saison ; cette table sert d'affichage et de contrôle.
 */

export const FRUITS_LEGUMES_SAISON: Record<number, string[]> = {
  1: ["Poireau", "Chou-fleur", "Endives", "Épinards", "Citron", "Orange", "Kiwi", "Poire", "Pomme"],
  2: ["Poireau", "Chou-fleur", "Endives", "Épinards", "Citron", "Orange", "Kiwi", "Poire", "Pomme"],
  3: ["Épinards", "Poireau", "Radis", "Carottes", "Citron", "Orange", "Kiwi", "Pomme"],
  4: ["Asperges", "Épinards", "Radis", "Carottes", "Petits pois", "Fraise", "Rhubarbe"],
  5: ["Asperges", "Fèves", "Radis", "Salade", "Petits pois", "Fraise", "Cerise"],
  6: ["Courgette", "Fraise", "Cerise", "Salade", "Radis", "Abricot", "Petits pois"],
  7: ["Courgette", "Haricot vert", "Tomate", "Abricot", "Pêche", "Melon", "Framboise"],
  8: ["Courgette", "Haricot vert", "Tomate", "Aubergine", "Poivron", "Pêche", "Melon", "Pastèque", "Prune"],
  9: ["Courgette", "Tomate", "Aubergine", "Poivron", "Figue", "Raisin", "Prune", "Framboise"],
  10: ["Courge", "Potiron", "Champignons", "Poireau", "Châtaigne", "Figue", "Raisin", "Coing"],
  11: ["Courge butternut", "Poireau", "Brocolis", "Épinards", "Chou vert", "Endives", "Patate douce", "Carottes", "Champignons de Paris", "Kiwi", "Poire", "Orange", "Mandarine"],
  12: ["Courge", "Poireau", "Chou-fleur", "Endives", "Épinards", "Kiwi", "Poire", "Orange", "Clémentine"],
};

/** Liste des fruits/légumes de saison pour un mois donné (défaut : vide). */
export function saisonDuMois(mois: number): string[] {
  return FRUITS_LEGUMES_SAISON[mois] ?? [];
}
