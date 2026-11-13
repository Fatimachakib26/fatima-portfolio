// Données de la plateforme. Point de départ : le contenu du rapport EMSI (aucune donnée inventée).
import seed from "./seed.json";
import { levelFromScore } from "./logic/scoring";
import { analyzeDossier } from "./logic/dossier-analysis";

const KEY = "credit-horizon-v3";
export type Row = Record<string, any>;
export const BASELINE_DATE = "2026-11-01";
export const ORIGIN = "Rapport EMSI · nov. 2026";

export interface State {
  version: 3;
  risks: Row[];
  history: Row[];
  controls: Row[];
  components: Row[];
  principles: Row[];
  recommendations: Row[];
  actions: Row[];
  anomalies: Row[];
  dossiers: Row[];
  audit: Row[];
}

export const SEED: any = seed;

// Jeu de démonstration : contenu du rapport + données fictives de la première version
// (anomalies, dossiers TPE, avancement, statuts des contrôles, historique des cotations).
export function baseline(): State {
  const s: any = seed;
  const now = new Date().toISOString().slice(0, 10);
  const history: Row[] = [];
  for (const r of s.risks)
    (s.history[r.id] || []).forEach(([p, g]: number[], i: number) =>
      history.push({ risk_id: r.id, probability: p, gravity: g, score: p * g, recorded_at: `${s.history_months[i]}-01` }),
    );
  return {
    version: 3,
    risks: s.risks.map((r: Row) => ({ ...r, is_demo: true, updated_at: BASELINE_DATE })),
    history,
    controls: s.controls.map((c: Row) => ({ ...c, last_review: "", is_demo: true })),
    components: s.coso_components.map((c: Row) => ({ ...c, is_demo: true })),
    principles: s.coso_principles.map((p: Row) => ({ ...p, is_demo: true })),
    recommendations: s.recommendations.map((r: Row) => ({ ...r, is_demo: true })),
    actions: s.actions.map((a: Row) => ({ ...a, is_demo: true })),
    anomalies: s.anomalies.map((a: Row) => ({ ...a, declared_by: "Données de démonstration", is_demo: true })),
    dossiers: s.dossiers.map((d: Row) => {
      const analysis = analyzeDossier(d as any);
      return { ...d, analysis, status: analysis.status, created_by: "Données de démonstration", created_at: now, is_demo: true };
    }),
    audit: [],
  };
}

function loadLocal(): State {
  try {
    const p = JSON.parse(localStorage.getItem(KEY) || "null");
    if (p && p.version === 3 && Array.isArray(p.risks)) return p;
  } catch {
    /* stockage indisponible */
  }
  return baseline();
}

export const state: State = loadLocal();

let persist: (json: string) => void = () => {};
export function setPersist(fn: (json: string) => void) {
  persist = fn;
}

export function save() {
  let json = JSON.stringify(state);
  if (json.length > 220_000) {
    state.audit = state.audit.slice(0, 60);
    json = JSON.stringify(state);
  }
  try {
    localStorage.setItem(KEY, json);
  } catch {
    /* mode privé */
  }
  persist(json);
}

export function replaceState(json: string): boolean {
  try {
    const p = JSON.parse(json);
    if (p && p.version === 3 && Array.isArray(p.risks)) {
      Object.assign(state, p);
      try {
        localStorage.setItem(KEY, json);
      } catch {}
      return true;
    }
  } catch {}
  return false;
}

export function resetBaseline() {
  Object.assign(state, baseline());
}

export function audit(who: string, action: string, entity: string, id: string, details = "") {
  state.audit.unshift({ at: new Date().toISOString(), who, action, entity, id, details: details.slice(0, 240) });
  state.audit = state.audit.slice(0, 250);
}

export function nextId(rows: Row[], prefix: string, pad: number, sep = "") {
  let max = 0;
  for (const r of rows) {
    if (!String(r.id).startsWith(prefix + sep)) continue;
    const n = parseInt(String(r.id).slice(prefix.length + sep.length), 10);
    if (!Number.isNaN(n) && n > max) max = n;
  }
  return `${prefix}${sep}${String(max + 1).padStart(pad, "0")}`;
}

export const splitIds = (v: unknown) => String(v ?? "").split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);

const ASSESS_SCORE: Record<string, number> = { Déficient: 1, Partiel: 2.5, Satisfaisant: 4.5 };
/** Maturité d'une composante COSO calculée à partir de l'appréciation de ses principes (1 à 5). */
export function maturity(componentId: number): number | null {
  const v = state.principles.filter((p) => p.component_id === componentId && ASSESS_SCORE[p.assessment]).map((p) => ASSESS_SCORE[p.assessment]);
  return v.length ? Math.round((v.reduce((a, b) => a + b, 0) / v.length) * 10) / 10 : null;
}

export function snapshot() {
  const risks: Row[] = state.risks
    .map((r): Row => {
      const score = Number(r.probability) * Number(r.gravity);
      return { ...r, score, level: levelFromScore(score) };
    })
    .sort((a, b) => a.id.localeCompare(b.id));
  return {
    risks,
    controls: state.controls,
    components: state.components.map((c) => ({ ...c, maturity: maturity(c.id) ?? 0 })),
    principles: state.principles,
    recommendations: state.recommendations,
    actions: [...state.actions].sort((a, b) => (a.priority + a.id).localeCompare(b.priority + b.id)),
    anomalies: [...state.anomalies].sort((a, b) => (b.detected_on + b.id).localeCompare(a.detected_on + a.id)),
    dossiers: state.dossiers,
    history: state.history,
    generatedAt: new Date().toISOString(),
  };
}
