import "server-only";
import { q } from "./db";
import { levelFromScore } from "./scoring";

/** Vue consolidée de toutes les données de l'application (rapports, exports, contexte IA). */
export async function getSnapshot() {
  const [risks, controls, components, principles, recommendations, actions, anomalies, dossiers, history] = await Promise.all([
    q("select *, probability*gravity as score from risks order by id"),
    q("select * from controls order by id"),
    q("select * from coso_components order by id"),
    q("select * from coso_principles order by component_id, cast(substring(id from 2) as int)"),
    q("select * from recommendations order by id"),
    q("select * from actions order by priority, id"),
    q("select * from anomalies order by detected_on desc, id desc"),
    q("select id, company, request, financials, guarantees, observations, analysis, status, created_by, is_demo, created_at from dossiers order by created_at desc"),
    q("select risk_id, probability, gravity, score, recorded_at from risk_history order by recorded_at"),
  ]);
  for (const r of risks) {
    r.score = Number(r.score);
    r.level = levelFromScore(r.score);
  }
  return { risks, controls, components, principles, recommendations, actions, anomalies, dossiers, history, generatedAt: new Date().toISOString() };
}

export type Snapshot = Awaited<ReturnType<typeof getSnapshot>>;

export function computeKpis(s: Snapshot) {
  const total = s.risks.length;
  const critical = s.risks.filter((r: any) => r.level === "Critique").length;
  const high = s.risks.filter((r: any) => r.level === "Élevé").length;
  const avgScore = total ? s.risks.reduce((a: number, r: any) => a + r.score, 0) / total : 0;
  const pendingActions = s.actions.filter((a: any) => a.status !== "Terminé").length;
  const actionProgress = s.actions.length ? Math.round(s.actions.reduce((a: number, x: any) => a + Number(x.progress), 0) / s.actions.length) : 0;
  const openAnomalies = s.anomalies.filter((a: any) => a.status !== "Clôturée").length;
  const today = new Date().toISOString().slice(0, 10);
  const overdueAnomalies = s.anomalies.filter((a: any) => a.status !== "Clôturée" && a.due_on && a.due_on < today).length;
  const closedAnomalies = s.anomalies.filter((a: any) => a.status === "Clôturée").length;
  const operationalControls = s.controls.filter((c: any) => ["Opérationnel", "Efficace"].includes(c.status)).length;
  const coveredRisks = s.risks.filter((r: any) =>
    s.controls.some((c: any) => String(c.risk_ids).split(/[,;\s]+/).includes(r.id)),
  ).length;
  const deficientPrinciples = s.principles.filter((p: any) => p.assessment === "Déficient").length;
  const avgMaturity = s.components.length ? s.components.reduce((a: number, c: any) => a + Number(c.maturity), 0) / s.components.length : 0;
  const dossiersBlocked = s.dossiers.filter((d: any) => d.analysis?.blocking).length;
  return {
    total, critical, high, avgScore, pendingActions, actionProgress, openAnomalies, overdueAnomalies, closedAnomalies,
    operationalControls, totalControls: s.controls.length, coveredRisks, deficientPrinciples, avgMaturity,
    dossiers: s.dossiers.length, dossiersBlocked,
  };
}
