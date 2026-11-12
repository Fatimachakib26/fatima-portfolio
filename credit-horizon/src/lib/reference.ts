// Référentiels de gouvernance issus du rapport (sections 4.4, 5.1) – utilisables côté client et serveur.

export type RaciCode = "R" | "A" | "C" | "I" | "A/R" | "–";

export const RACI_ACTORS = [
  { key: "ca", label: "Chargé d'affaires", group: "Service commercial" },
  { key: "dc", label: "Direction commerciale", group: "Service commercial" },
  { key: "fin", label: "Fonction finance", group: "Fonction Finance" },
  { key: "rsk", label: "Fonction risques", group: "Fonction Risques" },
  { key: "dg", label: "Direction générale / comité de crédit", group: "Direction" },
  { key: "ci", label: "Contrôle interne / audit", group: "Contrôle interne" },
] as const;

export type ActorKey = (typeof RACI_ACTORS)[number]["key"];

// block : bloc de séparation des tâches (constitution / contrôle / autorisation / exécution / suivi)
export const RACI_ACTIVITIES: { n: number; activity: string; block: string; roles: Record<ActorKey, RaciCode> }[] = [
  { n: 1, activity: "Réception de la demande", block: "Constitution", roles: { ca: "R", dc: "A", fin: "–", rsk: "I", dg: "–", ci: "–" } },
  { n: 2, activity: "Constitution du dossier", block: "Constitution", roles: { ca: "R", dc: "A", fin: "–", rsk: "C", dg: "–", ci: "–" } },
  { n: 3, activity: "Vérification des pièces", block: "Analyse / contrôle", roles: { ca: "C", dc: "C", fin: "–", rsk: "A/R", dg: "I", ci: "–" } },
  { n: 4, activity: "Analyse commerciale", block: "Constitution", roles: { ca: "R", dc: "A", fin: "C", rsk: "I", dg: "–", ci: "–" } },
  { n: 5, activity: "Analyse des risques", block: "Analyse / contrôle", roles: { ca: "C", dc: "I", fin: "C", rsk: "A/R", dg: "–", ci: "–" } },
  { n: 6, activity: "Avis de la fonction risques", block: "Analyse / contrôle", roles: { ca: "I", dc: "I", fin: "–", rsk: "A/R", dg: "I", ci: "–" } },
  { n: 7, activity: "Autorisation du crédit", block: "Autorisation", roles: { ca: "–", dc: "C", fin: "C", rsk: "C", dg: "A/R", ci: "I" } },
  { n: 8, activity: "Décaissement", block: "Exécution", roles: { ca: "I", dc: "I", fin: "A/R", rsk: "C", dg: "I", ci: "I" } },
  { n: 9, activity: "Suivi des remboursements", block: "Suivi", roles: { ca: "C", dc: "I", fin: "A/R", rsk: "I", dg: "I", ci: "–" } },
  { n: 10, activity: "Déclaration d'un incident", block: "Suivi", roles: { ca: "R", dc: "C", fin: "R", rsk: "A", dg: "I", ci: "I" } },
  { n: 11, activity: "Traitement des anomalies", block: "Suivi", roles: { ca: "C", dc: "R", fin: "R", rsk: "A", dg: "I", ci: "C" } },
  { n: 12, activity: "Priorisation des corrections", block: "Pilotage", roles: { ca: "–", dc: "C", fin: "C", rsk: "R", dg: "A", ci: "C" } },
  { n: 13, activity: "Suivi des recommandations", block: "Pilotage", roles: { ca: "I", dc: "R", fin: "R", rsk: "C", dg: "A", ci: "R" } },
  { n: 14, activity: "Révision des procédures", block: "Pilotage", roles: { ca: "–", dc: "C", fin: "C", rsk: "R", dg: "A", ci: "C" } },
];

/** Vérifie automatiquement la séparation des tâches : aucun acteur ne doit être R/A sur les trois blocs. */
export function segregationCheck() {
  const blocks = ["Constitution", "Analyse / contrôle", "Autorisation"];
  const isRA = (c: RaciCode) => c === "R" || c === "A" || c === "A/R";
  const singleA = RACI_ACTIVITIES.map((a) => ({
    n: a.n,
    activity: a.activity,
    count: Object.values(a.roles).filter((c) => c === "A" || c === "A/R").length,
  }));
  const actors = RACI_ACTORS.map((act) => {
    const covered = blocks.filter((b) => RACI_ACTIVITIES.some((a) => a.block === b && isRA(a.roles[act.key])));
    return { actor: act.label, blocks: covered, conflict: covered.length === blocks.length };
  });
  return { singleA, actors, ok: singleA.every((s) => s.count === 1) && actors.every((a) => !a.conflict) };
}

export const DELEGATION_MATRIX = [
  { decision: "Déclarer un incident", realise: "Collaborateur ou service qui détecte", valide: "Responsable du service concerné", informe: "Fonction risques" },
  { decision: "Prioriser une correction", realise: "Pilote du risque ou de l'action", valide: "Direction générale", informe: "Fonction de contrôle et acteurs concernés" },
  { decision: "Vérifier le suivi d'une correction", realise: "Fonction de contrôle désignée", valide: "Direction générale", informe: "Acteurs concernés" },
  { decision: "Vérifier le dossier avant décision", realise: "Chargé d'affaires (constitution) ; fonction risques (contrôle indépendant)", valide: "Responsable de la fonction risques (complétude)", informe: "Délégataire de crédit" },
  { decision: "Autoriser un financement", realise: "Comité de crédit : instruit le dossier et formule une proposition de décision", valide: "Délégataire habilité de niveau approprié, distinct de l'instructeur selon la délégation", informe: "Commercial, finance et fonction risques" },
  { decision: "Autoriser le décaissement opérationnel", realise: "Fonction finance", valide: "Responsable finance, après preuve d'autorisation", informe: "Commercial et risques" },
];

export const APPETITE_LEVELS = [
  {
    key: "acceptable",
    title: "Risques acceptables sous contrôle",
    color: "emerald",
    description:
      "Dossier complet, cohérent, analysé indépendamment et décidé dans la délégation, selon la grille commune. Erreurs résiduelles tolérées seulement si elles sont détectées, enregistrées, corrigées et suivies.",
    examples: ["Dossier complet et cohérent", "Avis risques favorable joint", "Décision dans la délégation", "Anomalie mineure tracée et régularisée"],
  },
  {
    key: "renforcee",
    title: "Risques nécessitant une autorisation renforcée",
    color: "amber",
    description:
      "Dossier présentant une dérogation motivée : décision au niveau supérieur, motivation écrite, inscription au registre et suivi. Un avis défavorable des risques impose un niveau supérieur (C02).",
    examples: ["Dérogation motivée à la grille commune", "Avis risques défavorable porté au niveau supérieur", "Signal de tension de liquidité", "Concentration sectorielle en hausse"],
  },
  {
    key: "inacceptable",
    title: "Risques inacceptables",
    color: "red",
    description: "Situations interdites quelle que soit la pression commerciale (article 9 de la charte).",
    examples: [
      "Dossier incomplet autorisé ou décaissé sans régularisation des pièces obligatoires",
      "Décision hors délégation ou hors circuit d'autorisation",
      "Avis défavorable de la fonction risques ignoré sans motivation écrite",
      "Cumul des rôles de constitution, d'analyse et d'autorisation par une même personne",
      "Dissimulation ou non-remontée volontaire d'une anomalie significative ; modification d'un dossier après avis sans trace",
    ],
  },
] as const;

export const CHARTER_PRINCIPLES = [
  "La qualité du portefeuille est privilégiée sur le volume à court terme.",
  "Aucun objectif commercial ne justifie une prise de risque non documentée.",
  "Toute décision respecte les délégations en vigueur.",
  "Toute dérogation est justifiée, validée au bon niveau et tracée.",
  "L'analyse indépendante des risques est préservée : l'avis de la fonction risques ne peut être modifié par la fonction commerciale.",
  "Les anomalies significatives sont remontées sans délai.",
  "La liquidité est suivie et protégée.",
];

export const APPETITE_BY_CATEGORY = [
  {
    category: "Crédit",
    appetite: "Accepter les demandes dont les informations sont complètes, cohérentes et analysables ; décider selon des critères homogènes.",
    limits: "Pièce obligatoire manquante ; information essentielle non fiable ; avis des risques contourné ; décision hors délégation ; dérogation non tracée.",
  },
  {
    category: "Liquidité",
    appetite: "Maintenir une visibilité régulière sur les encaissements, décaissements et engagements à échéance.",
    limits: "Absence de suivi des flux ; décaissement sans vérification des ressources ; tension non remontée.",
  },
  {
    category: "Opérationnel",
    appetite: "Tolérer des erreurs résiduelles seulement si elles sont détectées, enregistrées, corrigées et suivies.",
    limits: "Autorisation non habilitée ; modification non tracée ; dissimulation d'anomalie ; cumul incompatible de tâches sans mesure compensatoire.",
  },
];

export const ESCALATION = [
  { level: 1, title: "Niveau 1 – Enregistrement", text: "Toute anomalie ou dérogation est inscrite au registre le jour de sa détection." },
  { level: 2, title: "Niveau 2 – Direction des risques", text: "Anomalie non régularisée dans le délai fixé, ou répétée : remontée au Directeur des risques puis au Directeur commercial." },
  { level: 3, title: "Niveau 3 – Direction générale", text: "Anomalie significative, avis des risques contesté, dépassement de délégation ou signal de tension de liquidité : remontée immédiate à la direction générale." },
];

export const HYPOTHESES = [
  { id: "H1", text: "Crédit Horizon dispose d'une direction générale, d'une fonction commerciale, d'une fonction finance et d'une fonction risques distinctes." },
  { id: "H2", text: "Le statut juridique de Crédit Horizon n'est pas connu : les textes de Bank Al-Maghrib ne sont pas présumés applicables." },
  { id: "H3", text: "Une instance de décision (comité de crédit) peut être instituée ou existe déjà." },
  { id: "H4", text: "Une fonction de contrôle interne ou d'audit existe ou peut être créée, indépendante des trois autres fonctions." },
  { id: "H5", text: "Les objectifs commerciaux sont suivis par le volume, sans critère de qualité explicite." },
  { id: "H6", text: "Aucune donnée chiffrée sur le portefeuille n'est utilisée. Les cotes P et G sont qualitatives." },
];

export const DYSFUNCTIONS = [
  { id: "D1", text: "Dossiers présentant des pièces incomplètes" },
  { id: "D2", text: "Décisions prises selon des critères non harmonisés" },
  { id: "D3", text: "Suivi des anomalies insuffisamment formalisé" },
  { id: "D4", text: "Objectifs de volumes en tension avec la qualité du portefeuille" },
  { id: "D5", text: "Informations incohérentes et responsabilités d'autorisation imprécises" },
];
