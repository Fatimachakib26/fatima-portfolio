// Données et persistance de la version « site autonome » (stockage local du navigateur).
import seed from "./seed.json";
import { analyzeDossier } from "./logic/dossier-analysis";
import { levelFromScore } from "./logic/scoring";
import { queueCloudSave } from "./platform";

const KEY = "credit-horizon-site-v1";
export type Row = Record<string, any>;

export interface State {
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
  user: Row | null;
}

const now = () => new Date().toISOString();

function seedState(user: Row | null = null): State {
  const s: any = seed;
  const history: Row[] = [];
  for (const r of s.risks)
    (s.history[r.id] || []).forEach(([p, g]: number[], i: number) =>
      history.push({ risk_id: r.id, probability: p, gravity: g, score: p * g, recorded_at: `${s.history_months[i]}-01T09:00:00Z` }),
    );
  return {
    risks: s.risks.map((r: Row) => ({ ...r, is_demo: true })),
    history,
    controls: s.controls.map((c: Row) => ({ ...c, last_review: "", is_demo: true })),
    components: s.coso_components.map((c: Row) => ({ ...c, is_demo: true })),
    principles: s.coso_principles.map((p: Row) => ({ ...p, is_demo: true })),
    recommendations: s.recommendations.map((r: Row) => ({ ...r, is_demo: true })),
    actions: s.actions.map((a: Row) => ({ ...a, is_demo: true })),
    anomalies: s.anomalies.map((a: Row) => ({ ...a, declared_by: "Données de démonstration", is_demo: true })),
    dossiers: s.dossiers.map((d: Row) => {
      const analysis = analyzeDossier(d as any);
      return { ...d, analysis, status: analysis.status, created_by: "Données de démonstration", created_at: now(), is_demo: true };
    }),
    audit: [],
    user,
  };
}

function load(): State {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const p = JSON.parse(raw);
      if (p && Array.isArray(p.risks)) return p;
    }
  } catch {
    /* stockage indisponible : données en mémoire */
  }
  return seedState();
}

export const state: State = load();

export function save() {
  let json = JSON.stringify(state);
  if (json.length > 230_000) {
    state.audit = state.audit.slice(0, 50); // limite d'un document de stockage
    json = JSON.stringify(state);
  }
  try {
    localStorage.setItem(KEY, json);
  } catch {
    /* mode privé ou quota : les données restent en mémoire pour la session */
  }
  queueCloudSave(json);
}

/** Remplace l'état par la copie enregistrée dans l'espace privé de l'utilisateur. */
export function loadRemote(json: string): boolean {
  try {
    const p = JSON.parse(json);
    if (p && Array.isArray(p.risks)) {
      Object.assign(state, p);
      try { localStorage.setItem(KEY, json); } catch {}
      return true;
    }
  } catch {}
  return false;
}

export function resetDemo() {
  const fresh = seedState(state.user);
  Object.assign(state, fresh);
  audit("Réinitialisation", "Données de démonstration", "*");
  save();
}

export function audit(action: string, entity: string, id: string, details = "") {
  state.audit.unshift({ at: now(), user: state.user?.name ?? "système", role: state.user?.role ?? "", action, entity, id, details: details.slice(0, 300) });
  state.audit = state.audit.slice(0, 300);
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

/** Vue consolidée calculée (score, niveau) utilisée par les indicateurs et l'assistant. */
export function snapshot() {
  const risks = [...state.risks]
    .map((r) => {
      const score = Number(r.probability) * Number(r.gravity);
      return { ...r, score, level: levelFromScore(score) };
    })
    .sort((a, b) => a.id.localeCompare(b.id));
  return {
    risks,
    controls: state.controls,
    components: state.components,
    principles: state.principles,
    recommendations: state.recommendations,
    actions: [...state.actions].sort((a, b) => (a.priority + a.id).localeCompare(b.priority + b.id)),
    anomalies: [...state.anomalies].sort((a, b) => (b.detected_on + b.id).localeCompare(a.detected_on + a.id)),
    dossiers: state.dossiers,
    history: state.history,
    generatedAt: now(),
  };
}

export const SEED: any = seed;
