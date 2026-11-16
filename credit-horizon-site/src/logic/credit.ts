// Mesure du risque de crédit — posture de l'analyste risque crédit : « Quel est le risque, et comment le maîtriser ? »
// Pertes attendues : EL = PD × LGD × EAD. Paramètres calibrés sur le portefeuille de référence SBA 7(a)
// (données publiques vérifiées) : PD annuelle par taux d'incidence actuariel, LGD rapportée au montant initial.
// Il s'agit de repères externes indicatifs : ils ne remplacent ni une calibration sur l'historique propre
// de Crédit Horizon, ni une décision d'octroi.
import marts from "../../../data-pipeline/data/marts/sba_marts.json";

type Row = Record<string, any>;
const M: any = marts;
const O = M.overview;
const T = M.tables;

export const BASE_PD: number = O.pd_annual;
export const BASE_LGD: number = O.lgd;
export const SECTORS: string[] = (T.by_sector as Row[]).filter((s) => s.resolved >= 1000).map((s) => s.sector);
const sectorRow = (s: string) => (T.by_sector as Row[]).find((r) => r.sector === s);
const coll = (v: boolean) => (T.by_collateral as Row[]).find((r) => r.collateral === v)!;
export function termBand(months: number): string {
  return months <= 12 ? "≤ 1 an" : months <= 60 ? "1–5 ans" : months <= 120 ? "5–10 ans" : "> 10 ans";
}
const termRow = (months: number) => (T.by_term as Row[]).find((r) => r.term_band === termBand(months))!;

export interface RiskInput {
  sector: string;
  months: number;
  collateralShare: number; // 0 à 1
}
export interface RiskParams {
  pd: number; // PD à 12 mois
  lgd: number;
  pdLife: number; // PD cumulée sur la durée
  factors: { label: string; value: number }[];
}

/** PD et LGD d'une exposition : PD de base × risques relatifs (secteur, garantie, durée), plafonnée. */
export function riskParams(i: RiskInput): RiskParams {
  const sr = sectorRow(i.sector);
  const relSector = sr?.pd_annual ? sr.pd_annual / BASE_PD : 1;
  const cy = coll(true), cn = coll(false);
  const relColl = (i.collateralShare * cy.pd_annual + (1 - i.collateralShare) * cn.pd_annual) / BASE_PD;
  const relTerm = termRow(i.months).pd_annual / BASE_PD;
  const pd = Math.min(0.95, BASE_PD * relSector * relColl * relTerm);
  const lgdSector = sr?.lgd ?? BASE_LGD;
  const lgdColl = (i.collateralShare * cy.lgd + (1 - i.collateralShare) * cn.lgd) / BASE_LGD;
  const lgd = Math.min(1, lgdSector * lgdColl);
  const years = Math.max(1, i.months / 12);
  return {
    pd, lgd, pdLife: 1 - Math.pow(1 - pd, years),
    factors: [
      { label: "PD annuelle de référence (tous prêts)", value: BASE_PD },
      { label: `Facteur secteur (${i.sector})`, value: relSector },
      { label: `Facteur garantie (${Math.round(i.collateralShare * 100)} % garanti)`, value: relColl },
      { label: `Facteur durée (${termBand(i.months)})`, value: relTerm },
    ],
  };
}

export interface Segment {
  id: string;
  sector: string;
  ead: number; // encours en MAD
  collateral: number; // % garanti
  term: number; // durée moyenne en mois
  stage2: number; // % de l'encours en stade 2 (risque significativement dégradé)
  stage3: number; // % de l'encours en stade 3 (en défaut)
}
export interface SegmentResult extends Segment {
  pd: number;
  lgd: number;
  el12: number;
  provision: number;
}
export interface Stress {
  pdMult: number; // multiplicateur de PD
  lgdAdd: number; // points de LGD ajoutés (0,10 = +10 pts)
  sector: string; // secteur choqué
  sectorMult: number; // multiplicateur de PD du secteur choqué
  singleDefault: number; // défaut d'une contrepartie (MAD) en plus
}
export const NO_STRESS: Stress = { pdMult: 1, lgdAdd: 0, sector: "", sectorMult: 1, singleDefault: 0 };

/** Provisions IFRS 9 : stade 1 = pertes à 12 mois, stade 2 = pertes sur la durée de vie, stade 3 = LGD × encours en défaut. */
export function evaluate(segments: Segment[], stress: Stress = NO_STRESS) {
  const rows: SegmentResult[] = segments.map((s) => {
    const p = riskParams({ sector: s.sector, months: s.term, collateralShare: s.collateral / 100 });
    const mult = stress.pdMult * (stress.sector && stress.sector === s.sector ? stress.sectorMult : 1);
    const pd = Math.min(0.95, p.pd * mult);
    const lgd = Math.min(1, p.lgd + stress.lgdAdd);
    const pdLife = 1 - Math.pow(1 - pd, Math.max(1, s.term / 12));
    const e1 = s.ead * (1 - (s.stage2 + s.stage3) / 100), e2 = (s.ead * s.stage2) / 100, e3 = (s.ead * s.stage3) / 100;
    const el12 = s.ead * pd * lgd;
    const provision = e1 * pd * lgd + e2 * pdLife * lgd + e3 * lgd;
    return { ...s, pd, lgd, el12, provision };
  });
  const ead = rows.reduce((a, r) => a + r.ead, 0);
  const el12 = rows.reduce((a, r) => a + r.el12, 0);
  const singleLoss = stress.singleDefault > 0 ? stress.singleDefault * Math.min(1, BASE_LGD + stress.lgdAdd) : 0;
  const provision = rows.reduce((a, r) => a + r.provision, 0) + singleLoss;
  const shares = rows.map((r) => r.ead / (ead || 1));
  return { rows, ead, el12, provision, coverage: provision / (ead || 1), singleLoss, hhi: shares.reduce((a, s) => a + s * s, 0), top3: [...shares].sort((a, b) => b - a).slice(0, 3).reduce((a, s) => a + s, 0) };
}

/** Portefeuille FICTIF de démonstration : 500 M MAD (cf. exemple « portefeuille de 500 M » de la fiche de l'analyste risque crédit). */
export const DEMO_PORTFOLIO: Segment[] = [
  { id: "S01", sector: "Commerce de détail", ead: 110_000_000, collateral: 55, term: 60, stage2: 8, stage3: 3 },
  { id: "S02", sector: "Hébergement et restauration", ead: 80_000_000, collateral: 65, term: 84, stage2: 10, stage3: 4 },
  { id: "S03", sector: "Construction", ead: 70_000_000, collateral: 50, term: 72, stage2: 12, stage3: 4 },
  { id: "S04", sector: "Industrie manufacturière", ead: 60_000_000, collateral: 70, term: 84, stage2: 6, stage3: 2 },
  { id: "S05", sector: "Transport et entreposage", ead: 50_000_000, collateral: 60, term: 60, stage2: 9, stage3: 3 },
  { id: "S06", sector: "Services professionnels, scientifiques et techniques", ead: 45_000_000, collateral: 35, term: 48, stage2: 5, stage3: 2 },
  { id: "S07", sector: "Santé et action sociale", ead: 35_000_000, collateral: 60, term: 84, stage2: 4, stage3: 1 },
  { id: "S08", sector: "Agriculture, sylviculture, pêche et chasse", ead: 30_000_000, collateral: 75, term: 96, stage2: 7, stage3: 2 },
  { id: "S09", sector: "Autres services", ead: 20_000_000, collateral: 40, term: 48, stage2: 8, stage3: 3 },
];

export const ANALYST_ROLE: [string, string][] = [
  ["Mission principale", "Évaluer, mesurer et maîtriser le risque de non-remboursement"],
  ["Orientation", "Maîtrise du risque"],
  ["Approche", "Analyse individuelle et globale du portefeuille"],
  ["Analyse financière", "Oui, avec un focus sur le risque"],
  ["Garanties", "Oui"],
  ["Probabilité de défaut (PD)", "Oui : outil clé"],
  ["Suivi des impayés", "Oui : suivi rapproché"],
  ["Analyse du portefeuille", "Approfondie : concentration, secteurs"],
  ["Provisions et pertes attendues", "Important : modélisation des pertes"],
  ["Reporting", "Important : indicateurs de risque"],
  ["Compétences clés", "Analyse des risques, modèles (PD, LGD, EAD), réglementation (Bâle II/III, IFRS 9)"],
  ["Exemple concret", "Mesurer l'impact d'un défaut sur le portefeuille de 500 M et ajuster les provisions"],
];
