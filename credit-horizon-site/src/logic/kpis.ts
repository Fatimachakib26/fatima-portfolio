// Calcul des indicateurs (pur : utilisable côté serveur et navigateur)
export type SnapshotLike = { risks: any[]; controls: any[]; components: any[]; principles: any[]; recommendations: any[]; actions: any[]; anomalies: any[]; dossiers: any[]; history: any[]; generatedAt: string };

export function computeKpis(s: SnapshotLike) {
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
