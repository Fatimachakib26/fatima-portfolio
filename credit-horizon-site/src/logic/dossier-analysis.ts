// Moteur d'analyse des dossiers TPE (module 4).
// Outille le contrôle C01 et la « grille simple de vérification des dossiers » (rapport, tableau 5.5).
// IMPORTANT : ce moteur NE PREND AUCUNE DÉCISION D'OCTROI. Il produit une aide à l'analyse,
// transmise à la fonction risques pour avis, puis à l'instance délégataire (contrôle C02).

export type DocStatus = "oui" | "non" | "na" | "";

export interface DossierInput {
  id?: string;
  company: {
    name?: string;
    legal_form?: string;
    rc_number?: string;
    ice?: string;
    creation_date?: string;
    sector?: string;
    activity?: string;
    city?: string;
    manager_name?: string;
    employees?: number | string;
    name_on_documents?: string;
  };
  request: {
    product?: string;
    amount?: number | string;
    duration_months?: number | string;
    purpose?: string;
  };
  financials: {
    revenue_n?: number | string;
    revenue_n1?: number | string;
    revenue_bank?: number | string;
    net_result?: number | string;
    equity?: number | string;
    existing_debt?: number | string;
    existing_monthly_installments?: number | string;
    fiscal_year?: string;
  };
  documents: Record<string, DocStatus>;
  guarantees: { type?: string; value?: number | string; description?: string };
  observations?: string;
}

export const PRODUCTS = ["Crédit d'investissement", "Crédit d'équipement", "Crédit de fonctionnement", "Microcrédit"] as const;
export const GUARANTEE_TYPES = ["Aucune", "Caution personnelle du dirigeant", "Nantissement de fonds de commerce", "Nantissement de matériel", "Hypothèque", "Garantie d'un fonds de garantie public"] as const;

// Grille du rapport (tableau 5.5). stage "avant_avis" = exigé avant l'avis des risques ;
// "avant_decision" = exigé avant présentation à l'instance délégataire.
export const CHECKLIST = [
  { key: "doc_form", label: "Formulaire de demande signé", scope: "Tous", stage: "avant_avis" },
  { key: "doc_id", label: "Pièce d'identité du dirigeant / représentant", scope: "Tous", stage: "avant_avis" },
  { key: "doc_company", label: "Documents d'identification de l'entreprise (RC, ICE, statuts)", scope: "Tous", stage: "avant_avis" },
  { key: "doc_activity", label: "Justificatifs d'activité et de revenus", scope: "Tous", stage: "avant_avis" },
  { key: "doc_financial", label: "Relevés ou justificatifs financiers disponibles", scope: "Selon le produit", stage: "avant_avis" },
  { key: "doc_schedule", label: "Échéancier et objet du financement", scope: "Tous", stage: "avant_avis" },
  { key: "doc_guarantee", label: "Justificatifs des garanties, si applicables", scope: "Crédits garantis", stage: "avant_avis" },
  { key: "doc_contact", label: "Coordonnées et informations de contact", scope: "Tous", stage: "avant_avis" },
  { key: "check_concordance", label: "Concordance des noms, montants, dates et données", scope: "Tous", stage: "avant_avis" },
  { key: "check_mandatory", label: "Vérification des pièces obligatoires selon le type de crédit", scope: "Tous", stage: "avant_avis" },
  { key: "risk_opinion", label: "Avis de la fonction risques joint au dossier", scope: "Tous", stage: "avant_decision" },
  { key: "decision_delegation", label: "Décision et délégation d'autorisation conformes", scope: "Tous", stage: "avant_decision" },
] as const;

/**
 * Seuils INDICATIFS de démonstration, paramétrables.
 * Le rapport précise qu'aucun seuil chiffré n'est fixé par le cas : ces valeurs servent
 * uniquement à déclencher des points de vigilance et doivent être validées par la direction.
 */
export const DEMO_THRESHOLDS = {
  amountToRevenue: 0.5, // montant demandé / CA annuel
  debtServiceToRevenue: 0.3, // charges annuelles de remboursement / CA
  revenueGapBank: 0.2, // écart CA déclaré / CA relevés bancaires
  revenueDrop: 0.2, // baisse du CA N vs N-1
  leverage: 3, // (dettes existantes + montant) / fonds propres
  youngCompanyYears: 2,
  shortTermMaxMonths: 24, // crédit de fonctionnement : durée max cohérente
  indicativeRate: 0.08, // taux annuel indicatif pour estimer l'échéance
};

export type Severity = "info" | "attention" | "alerte";
export interface Finding {
  code: string;
  message: string;
  severity: Severity;
  risk?: string;
}

export interface DossierAnalysis {
  generatedAt: string;
  completeness: { rate: number; required: number; present: number; missingDocs: string[]; pendingBeforeDecision: string[] };
  missingInfo: Finding[];
  inconsistencies: Finding[];
  vigilance: Finding[];
  ratios: { label: string; value: string }[];
  linkedRisks: string[];
  blocking: boolean;
  status: string;
  synthesis: string;
  disclaimer: string;
}

const num = (v: unknown): number | null => {
  if (v === null || v === undefined || v === "") return null;
  const n = typeof v === "number" ? v : Number(String(v).replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
};
const fmt = (n: number) => new Intl.NumberFormat("fr-MA", { maximumFractionDigits: 0 }).format(n) + " MAD";
const pct = (n: number) => `${(n * 100).toFixed(1).replace(".", ",")} %`;
const norm = (s?: string) =>
  (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\b(sarl|sarlau|sa|sas|snc|au|ste|societe)\b/g, "")
    .replace(/[^a-z0-9]/g, "");

export function monthlyInstallment(amount: number, months: number, annualRate = DEMO_THRESHOLDS.indicativeRate) {
  if (months <= 0) return 0;
  const r = annualRate / 12;
  if (r === 0) return amount / months;
  return (amount * r) / (1 - Math.pow(1 + r, -months));
}

export function isRequired(key: string, d: DossierInput): boolean {
  const product = d.request.product || "";
  const gType = d.guarantees?.type || "Aucune";
  if (key === "doc_guarantee") return gType !== "Aucune" && gType !== "";
  if (key === "doc_financial") return product !== "Microcrédit";
  return true;
}

export function analyzeDossier(d: DossierInput, now = new Date()): DossierAnalysis {
  const docs = d.documents || {};
  const missingInfo: Finding[] = [];
  const inconsistencies: Finding[] = [];
  const vigilance: Finding[] = [];
  const ratios: { label: string; value: string }[] = [];
  const risks = new Set<string>();

  // 1. Complétude documentaire (C01)
  const requiredItems = CHECKLIST.filter((c) => c.stage === "avant_avis" && isRequired(c.key, d));
  const missingDocs = requiredItems.filter((c) => docs[c.key] !== "oui").map((c) => c.label);
  const present = requiredItems.length - missingDocs.length;
  const rate = requiredItems.length ? Math.round((present / requiredItems.length) * 100) : 0;
  const pendingBeforeDecision = CHECKLIST.filter((c) => c.stage === "avant_decision" && docs[c.key] !== "oui").map((c) => c.label);
  if (missingDocs.length) risks.add("R01");

  // 2. Informations manquantes
  const req: [unknown, string][] = [
    [d.company.name, "Raison sociale"],
    [d.company.legal_form, "Forme juridique"],
    [d.company.rc_number, "Numéro de registre de commerce"],
    [d.company.ice, "Identifiant commun de l'entreprise (ICE)"],
    [d.company.creation_date, "Date de création"],
    [d.company.sector, "Secteur d'activité"],
    [d.company.activity, "Description de l'activité"],
    [d.company.manager_name, "Nom du dirigeant"],
    [d.request.product, "Type de financement"],
    [num(d.request.amount), "Montant demandé"],
    [num(d.request.duration_months), "Durée du financement"],
    [d.request.purpose, "Objet du financement"],
    [num(d.financials.revenue_n), "Chiffre d'affaires du dernier exercice"],
    [num(d.financials.net_result), "Résultat net du dernier exercice"],
    [num(d.financials.equity), "Fonds propres"],
  ];
  for (const [v, label] of req) {
    if (v === null || v === undefined || v === "") missingInfo.push({ code: "MISSING", message: `${label} non renseigné(e).`, severity: "attention", risk: "R01" });
  }
  if (!d.guarantees?.type) missingInfo.push({ code: "MISSING_GUAR", message: "Nature de la garantie non précisée (indiquer « Aucune » le cas échéant).", severity: "attention", risk: "R01" });
  if (!d.observations || d.observations.trim().length < 20)
    missingInfo.push({ code: "MISSING_OBS", message: "Observations de l'analyste absentes ou trop succinctes : l'analyse doit être motivée et traçable.", severity: "info", risk: "R02" });
  if (missingInfo.length) risks.add("R01");

  const amount = num(d.request.amount);
  const months = num(d.request.duration_months);
  const ca = num(d.financials.revenue_n);
  const ca1 = num(d.financials.revenue_n1);
  const caBank = num(d.financials.revenue_bank);
  const result = num(d.financials.net_result);
  const equity = num(d.financials.equity);
  const debt = num(d.financials.existing_debt) ?? 0;
  const existingMonthly = num(d.financials.existing_monthly_installments) ?? 0;
  const gValue = num(d.guarantees?.value);
  const gType = d.guarantees?.type || "";

  // 3. Incohérences
  if (amount !== null && amount <= 0) inconsistencies.push({ code: "AMOUNT", message: "Le montant demandé doit être strictement positif.", severity: "alerte", risk: "R01" });
  if (months !== null && (months <= 0 || months > 240)) inconsistencies.push({ code: "DURATION", message: "Durée de financement hors bornes plausibles (1 à 240 mois).", severity: "alerte", risk: "R01" });
  if (d.company.creation_date) {
    const cd = new Date(d.company.creation_date);
    if (!isNaN(cd.getTime()) && cd > now) inconsistencies.push({ code: "CREATION_FUTURE", message: "La date de création de l'entreprise est postérieure à la date du jour.", severity: "alerte", risk: "R01" });
  }
  if (d.company.name_on_documents && d.company.name && norm(d.company.name_on_documents) !== norm(d.company.name))
    inconsistencies.push({ code: "NAME_MISMATCH", message: `La raison sociale figurant sur les pièces (« ${d.company.name_on_documents} ») diffère de celle du formulaire (« ${d.company.name} »).`, severity: "alerte", risk: "R01" });
  if (ca !== null && caBank !== null && ca > 0) {
    const gap = Math.abs(ca - caBank) / ca;
    ratios.push({ label: "Écart CA déclaré / CA relevés bancaires", value: pct(gap) });
    if (gap > DEMO_THRESHOLDS.revenueGapBank)
      inconsistencies.push({ code: "REVENUE_GAP", message: `Le chiffre d'affaires déclaré (${fmt(ca)}) s'écarte de ${pct(gap)} du chiffre d'affaires reconstitué à partir des relevés bancaires (${fmt(caBank)}).`, severity: "alerte", risk: "R01" });
  }
  if (ca !== null && result !== null && result > ca) inconsistencies.push({ code: "RESULT_GT_CA", message: "Le résultat net déclaré est supérieur au chiffre d'affaires : donnée incohérente.", severity: "alerte", risk: "R08" });
  if (existingMonthly > 0 && debt === 0) inconsistencies.push({ code: "DEBT_INCOH", message: "Des mensualités existantes sont déclarées alors que l'endettement existant est nul.", severity: "attention", risk: "R08" });
  if (gType && gType !== "Aucune" && (gValue === null || gValue <= 0)) inconsistencies.push({ code: "GUAR_VALUE", message: `Une garantie (« ${gType} ») est déclarée sans valeur estimée.`, severity: "attention", risk: "R01" });
  if ((gType === "Aucune" || !gType) && docs.doc_guarantee === "oui") inconsistencies.push({ code: "GUAR_DOC", message: "Un justificatif de garantie est coché alors qu'aucune garantie n'est déclarée.", severity: "attention", risk: "R01" });
  if (d.request.product === "Crédit de fonctionnement" && months !== null && months > DEMO_THRESHOLDS.shortTermMaxMonths)
    inconsistencies.push({ code: "PRODUCT_DURATION", message: `Durée de ${months} mois peu cohérente avec un crédit de fonctionnement (besoin à court terme) : vérifier l'objet du financement.`, severity: "attention", risk: "R06" });
  if (docs.check_concordance === "non") inconsistencies.push({ code: "CONCORDANCE", message: "La vérification de concordance des noms, montants et dates est déclarée non satisfaisante.", severity: "alerte", risk: "R01" });
  if (inconsistencies.length) risks.add("R01");

  // 4. Points de vigilance (seuils indicatifs de démonstration)
  if (amount && ca && ca > 0) {
    const r = amount / ca;
    ratios.push({ label: "Montant demandé / CA", value: pct(r) });
    if (r > DEMO_THRESHOLDS.amountToRevenue) vigilance.push({ code: "AMOUNT_CA", message: `Le montant demandé représente ${pct(r)} du chiffre d'affaires annuel.`, severity: "attention", risk: "R03" });
  }
  if (amount && months && months > 0) {
    const m = monthlyInstallment(amount, months);
    ratios.push({ label: "Échéance mensuelle estimée (taux indicatif 8 %)", value: fmt(m) });
    if (ca && ca > 0) {
      const ds = ((m + existingMonthly) * 12) / ca;
      ratios.push({ label: "Charges de remboursement annuelles / CA", value: pct(ds) });
      if (ds > DEMO_THRESHOLDS.debtServiceToRevenue) vigilance.push({ code: "DEBT_SERVICE", message: `Les remboursements annuels (existants + nouveau crédit) représenteraient ${pct(ds)} du chiffre d'affaires.`, severity: "alerte", risk: "R03" });
    }
    if (result !== null && result > 0 && m * 12 > result)
      vigilance.push({ code: "RESULT_COVER", message: `Le résultat net annuel (${fmt(result)}) ne couvre pas les échéances annuelles estimées du nouveau crédit (${fmt(m * 12)}).`, severity: "attention", risk: "R04" });
  }
  if (result !== null && result < 0) vigilance.push({ code: "LOSS", message: "Résultat net déficitaire sur le dernier exercice.", severity: "alerte", risk: "R03" });
  if (equity !== null && equity <= 0) vigilance.push({ code: "EQUITY", message: "Fonds propres nuls ou négatifs.", severity: "alerte", risk: "R03" });
  if (equity !== null && equity > 0 && amount) {
    const lev = (debt + amount) / equity;
    ratios.push({ label: "(Dettes existantes + montant) / fonds propres", value: lev.toFixed(2).replace(".", ",") });
    if (lev > DEMO_THRESHOLDS.leverage) vigilance.push({ code: "LEVERAGE", message: `Endettement post-financement élevé : ${lev.toFixed(1).replace(".", ",")} fois les fonds propres.`, severity: "attention", risk: "R03" });
  }
  if (ca && ca1 && ca1 > 0 && (ca1 - ca) / ca1 > DEMO_THRESHOLDS.revenueDrop)
    vigilance.push({ code: "CA_DROP", message: `Baisse du chiffre d'affaires de ${pct((ca1 - ca) / ca1)} par rapport à l'exercice précédent.`, severity: "attention", risk: "R03" });
  if (d.company.creation_date) {
    const cd = new Date(d.company.creation_date);
    const years = (now.getTime() - cd.getTime()) / (365.25 * 24 * 3600 * 1000);
    if (!isNaN(years) && years >= 0 && years < DEMO_THRESHOLDS.youngCompanyYears)
      vigilance.push({ code: "YOUNG", message: `Entreprise créée depuis moins de ${DEMO_THRESHOLDS.youngCompanyYears} ans : historique financier limité.`, severity: "info", risk: "R03" });
  }
  if ((!gType || gType === "Aucune") && amount) vigilance.push({ code: "NO_GUAR", message: "Aucune garantie proposée : point à apprécier par la fonction risques au regard de la charte.", severity: "info", risk: "R01" });
  if (gValue && amount && gValue < amount * 0.5 && gType !== "Aucune")
    vigilance.push({ code: "GUAR_LOW", message: `La valeur estimée de la garantie (${fmt(gValue)}) couvre moins de la moitié du montant demandé.`, severity: "info", risk: "R01" });
  vigilance.forEach((v) => v.risk && risks.add(v.risk));
  inconsistencies.forEach((v) => v.risk && risks.add(v.risk));

  const blocking = missingDocs.length > 0 || inconsistencies.some((i) => i.severity === "alerte");
  const status = blocking ? "Incomplet – présentation suspendue" : "Complet – transmissible pour avis risques";
  const linkedRisks = [...risks].sort();

  // 5. Synthèse
  const name = d.company.name || "L'entreprise";
  const parts: string[] = [];
  parts.push(
    `${name}${d.company.sector ? ` (secteur : ${d.company.sector})` : ""} sollicite ${amount ? fmt(amount) : "un montant non précisé"}${months ? ` sur ${months} mois` : ""}${d.request.product ? ` au titre d'un ${d.request.product.toLowerCase()}` : ""}${d.request.purpose ? ` pour : ${d.request.purpose}` : ""}.`,
  );
  parts.push(`Complétude documentaire : ${rate} % (${present}/${requiredItems.length} pièces requises avant avis).`);
  if (missingDocs.length) parts.push(`Pièces manquantes : ${missingDocs.join(" ; ")}.`);
  if (missingInfo.length) parts.push(`${missingInfo.length} information(s) à compléter.`);
  if (inconsistencies.length) parts.push(`${inconsistencies.length} incohérence(s) relevée(s), dont ${inconsistencies.filter((i) => i.severity === "alerte").length} significative(s).`);
  if (vigilance.length) parts.push(`${vigilance.length} point(s) de vigilance à examiner par la fonction risques.`);
  parts.push(
    blocking
      ? "Conformément à la règle de blocage de la grille de vérification (C01), la présentation du dossier est suspendue jusqu'à régularisation ; l'anomalie doit être inscrite au registre (C04)."
      : "Le dossier peut être transmis à la fonction risques pour avis indépendant, préalable à la décision de l'instance délégataire (C02).",
  );
  if (linkedRisks.length) parts.push(`Risques du registre concernés : ${linkedRisks.join(", ")}.`);

  return {
    generatedAt: now.toISOString(),
    completeness: { rate, required: requiredItems.length, present, missingDocs, pendingBeforeDecision },
    missingInfo,
    inconsistencies,
    vigilance,
    ratios,
    linkedRisks,
    blocking,
    status,
    synthesis: parts.join(" "),
    disclaimer:
      "Aide à l'analyse uniquement. Cette synthèse ne constitue en aucun cas une décision d'octroi : la décision relève de l'instance délégataire, après avis indépendant de la fonction risques (contrôle C02). Les seuils utilisés sont indicatifs et doivent être validés par la direction.",
  };
}
