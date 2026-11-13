// Données de la plateforme. Point de départ : le contenu du rapport EMSI (aucune donnée inventée).
import seed from "./seed.json";
import { levelFromScore } from "./logic/scoring";

const KEY = "credit-horizon-v2";
export type Row = Record<string, any>;
export const BASELINE_DATE = "2026-11-01";
export const ORIGIN = "Rapport EMSI · nov. 2026";

export interface State {
  version: 2;
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

export function baseline(): State {
  const s: any = seed;
  return {
    version: 2,
    risks: s.risks.map((r: Row) => ({ ...r, origin: ORIGIN, updated_at: BASELINE_DATE })),
    history: s.risks.map((r: Row) => ({ risk_id: r.id, probability: r.probability, gravity: r.gravity, score: r.probability * r.gravity, recorded_at: BASELINE_DATE })),
    // Le rapport PROPOSE ces contrôles : aucun n'est encore déployé.
    controls: s.controls.map((c: Row) => ({ ...c, status: "Proposé", last_review: "", origin: ORIGIN })),
    components: s.coso_components.map((c: Row) => ({ ...c, origin: ORIGIN })),
    principles: s.coso_principles.map((p: Row) => ({ ...p, origin: ORIGIN })),
    recommendations: s.recommendations.map((r: Row) => ({ ...r, status: "À lancer", origin: ORIGIN })),
    actions: s.actions.map((a: Row) => ({ ...a, status: "À faire", progress: 0, origin: ORIGIN })),
    anomalies: [],
    dossiers: [],
    audit: [],
  };
}

function loadLocal(): State {
  try {
    const p = JSON.parse(localStorage.getItem(KEY) || "null");
    if (p && p.version === 2 && Array.isArray(p.risks)) return p;
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
    if (p && p.version === 2 && Array.isArray(p.risks)) {
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
