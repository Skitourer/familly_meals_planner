// Types des réponses de l'API (voir backend/src/repas/api/). Documentation : /api/docs

export type Moment = 'midi' | 'soir';

export interface Membre {
	id: number;
	prenom: string;
	couleur: string;
	date_naissance: string;
	sexe: 'F' | 'H';
	poids_kg: number;
	mode_de_vie: 'sedentaire' | 'modere' | 'actif';
	heures_sport_semaine: number;
	actif: boolean;
	age: number;
	besoin_kcal: number;
	coefficient_portion: number;
}

export type MembreEntree = Omit<Membre, 'id' | 'age' | 'besoin_kcal' | 'coefficient_portion'>;

export interface Creneau {
	id: number;
	cle: string;
	jour: number;
	moment: Moment;
	convives: number[];
	invites: number;
	joker: boolean;
	verrouille: boolean;
	plat_id: string | null;
	dessert_id: string | null;
	restes_de: string | null;
	raisons: string[];
	infos: InfosRepas | null;
}

export type LettreNutriScore = 'A' | 'B' | 'C' | 'D' | 'E';

export interface InfosRepas {
	nutriscore: LettreNutriScore;
	nutriscore_points: number;
	energie_kcal: number;
	proteines_g: number;
	fibres_g: number;
	fruits_legumes_g: number;
	vegetarien: boolean;
	co2_kg: number;
	co2_kg_portion: number;
	prix_eur: number;
}

export interface Semaine {
	lundi: string;
	generee_le: string | null;
	courses_validees_le: string | null;
	ecarts: Record<string, number>;
	creneaux: Creneau[];
}

export interface Nutriments {
	energie_kcal: number;
	proteines_g: number;
	glucides_g: number;
	lipides_g: number;
	ags_g: number;
	sucres_g: number;
	fibres_g: number;
	sel_g: number;
	calcium_mg: number;
	fer_mg: number;
	vitamine_c_mg: number;
	folates_ug: number;
	epa_dha_g: number;
}

export interface Recette {
	id: string;
	nom: string;
	type: 'plat' | 'dessert';
	plaisir: boolean;
	temps: { preparation: number; cuisson: number };
	lot: { repas_max: number; conservation_jours: number } | null;
	etiquettes: string[];
	ingredients: Record<string, number>;
	etapes: string[];
	source: string;
	lien: string | null;
}

export interface FicheRecette {
	recette: Recette;
	nutriments: Nutriments;
	co2_kg: number;
	prix_eur: number;
	fruits_legumes_g: number;
	proteine_principale: string;
	de_saison: boolean;
	hors_saison: string[];
	note_famille: number | null;
	nombre_notes: number;
	importee: boolean;
	ingredients_noms: Record<string, string>;
	ingredients_unites: Record<string, string>;
}

export interface Indicateur {
	code: string;
	libelle: string;
	valeur: number;
	cible: string;
	unite: string;
	statut: 'ok' | 'attention' | 'hors_cible';
}

export interface Bilan {
	indicateurs: Indicateur[];
	co2_kg: number;
	co2_reference_kg: number;
	nb_repas: number;
	nb_jokers: number;
}

export interface Alternative {
	plat_id: string;
	perte_score: number;
}

export interface LigneCourses {
	ingredient_id: string;
	nom: string;
	achat: string;
	besoin: string;
	depuis_placard: string | null;
	surplus: string | null;
	surplus_au_placard: boolean;
	prix_eur: number;
}

export interface Courses {
	rayons: [string, LigneCourses[]][];
	a_verifier: string[];
	total_eur: number;
	validees: boolean;
}

export interface Stock {
	ingredient_id: string;
	nom: string;
	quantite_g: number;
	unite: string;
	peremption: string;
	bientot_perime: boolean;
}

/** Plat qui consomme les produits du placard à vider (frigo à vider). */
export interface IdeeFrigo {
	plat: string;
	nom: string;
	ingredients: string[];
	part_videe: number;
}

export interface Ingredient {
	id: string;
	nom: string;
	rayon: string;
	unite: string;
	conservation_jours: number;
	basique: boolean;
}

export interface RepasANoter {
	creneau_id: number;
	date: string;
	moment: Moment;
	recette_id: string;
	nom: string;
	convives: number[];
	notes: Record<string, number>;
	a_venir: boolean;
}

export interface Compte {
	id: number;
	identifiant: string;
	role: 'adulte' | 'enfant';
	membre_id: number | null;
	actif: boolean;
}

export interface Reglages {
	priorite_budget: number;
	priorite_carbone: number;
	cuisine_en_lot: number;
	restes_max: number;
}

export interface RapportImport {
	erreur_fichier: string | null;
	nb_acceptees: number;
	applique: boolean;
	recettes: {
		id: string;
		nom: string;
		acceptee: boolean;
		erreurs: string[];
		avertissements: string[];
	}[];
}

export interface BilanHebdo {
	lundi: string;
	nb_repas: number;
	nutriscore_moyen: LettreNutriScore;
	nutriscore_repartition: Partial<Record<LettreNutriScore, number>>;
	reperes: Record<string, { valeur: number; statut: Indicateur['statut'] }>;
	co2_kg: number;
	co2_reference_kg: number;
	budget_eur: number;
	budget_estime: boolean;
	cout_par_repas_personne_eur: number;
	part_saison: number;
	part_vegetarien: number;
	legumes_differents: number;
	proteines: Record<string, number>;
}

export interface BilanMembre {
	id: number;
	prenom: string;
	couleur: string;
	repas_a_la_maison: number;
	repas_dehors: number;
	couverture: {
		code: string;
		libelle: string;
		unite: string;
		apport_par_repas: number;
		reference_par_repas: number;
		pourcentage: number;
	}[];
	preferes: [string, number][];
	moins_aimes: [string, number][];
}

export interface BilanPeriode {
	semaines: BilanHebdo[];
	membres: BilanMembre[];
	a_redecouvrir: string[];
	jamais_servis: string[];
	nb_plats_differents: number;
	gaspillage: {
		depuis_placard_kg: number;
		surplus_placard_kg: number;
		surplus_perdu_kg: number;
		semaines_validees: number;
		perimes: string[];
	};
	co2_total_kg: number;
	co2_economise_kg: number;
	equivalent_km_voiture: number;
	budget_total_eur: number;
}
