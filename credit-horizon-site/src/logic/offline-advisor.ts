import { computeKpis, type SnapshotLike as Snapshot } from "./kpis";
import { LEVEL_TREATMENT, levelFromScore, PROBABILITY_SCALE, GRAVITY_SCALE } from "./scoring";

/**
 * Moteur d'analyse déterministe utilisé lorsque aucun modèle génératif n'est configuré
 * (ou en cas d'indisponibilité de l'API). Il ne produit que des contenus calculés à partir
 * des données réelles de la plateforme – aucune information n'est inventée.
 */

const ids = (v: unknown) => String(v ?? "").split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);
const norm = (s: string) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

function chainTable(s: Snapshot, riskIds?: string[]) {
  const recs = (s.recommendations as any[]).filter((r) => !riskIds || riskIds.includes(r.risk_id));
  const rows: string[] = [];
  for (const r of recs) {
    const risk = (s.risks as any[]).find((x) => x.id === r.risk_id);
    rows.push(`| **${r.risk_id}** – ${risk?.title ?? "risque non trouvé"} (${risk ? `${risk.score}, ${risk.level}` : "–"}) | ${r.coso_gap} | ${r.action} | ${r.owner} | ${r.indicator} |`);
  }
  // Risques sans recommandation : chaîne construite à partir du registre et du diagnostic COSO
  const covered = new Set(recs.map((r) => r.risk_id));
  for (const risk of (s.risks as any[]).filter((x) => (!riskIds || riskIds.includes(x.id)) && !covered.has(x.id))) {
    const princ = ids(risk.coso_principles);
    const gap = princ.length
      ? princ.map((p) => {
          const pr = (s.principles as any[]).find((x) => x.id === p);
          return pr ? `${p} ${pr.title} (${pr.nature})` : p;
        }).join(" ; ")
      : "Principe COSO non renseigné dans le registre – à compléter";
    rows.push(`| **${risk.id}** – ${risk.title} (${risk.score}, ${risk.level}) | ${gap} | ${risk.recommendation || "Recommandation à définir"} | ${risk.owner || "à désigner"} | ${controlsIndicators(s, risk)} |`);
  }
  if (!rows.length) return "_Aucune donnée correspondante dans la plateforme._";
  return `| RISQUE | LACUNE COSO | ACTION CORRECTIVE | RESPONSABLE | INDICATEUR DE SUIVI |\n|---|---|---|---|---|\n${rows.join("\n")}`;
}

function controlsIndicators(s: Snapshot, risk: any) {
  const cs = (s.controls as any[]).filter((c) => ids(c.risk_ids).includes(risk.id));
  return cs.length ? cs.map((c) => `${c.id} : ${c.indicator}`).join(" ; ") : "Indicateur à définir (aucun contrôle associé)";
}

function riskSheet(s: Snapshot, r: any) {
  const p = PROBABILITY_SCALE.find((x) => x.v === Number(r.probability));
  const g = GRAVITY_SCALE.find((x) => x.v === Number(r.gravity));
  const cs = (s.controls as any[]).filter((c) => ids(c.risk_ids).includes(r.id));
  const an = (s.anomalies as any[]).filter((a) => a.risk_id === r.id);
  const ac = (s.actions as any[]).filter((a) => ids(a.risk_ids).includes(r.id));
  return [
    `### ${r.id} – ${r.title}`,
    `- **Catégorie** : ${r.category} · **Fondement** : ${r.basis}`,
    `- **Événement** : ${r.event}`,
    `- **Causes** : ${r.causes || "non renseignées"}`,
    `- **Conséquences** : ${r.consequences || "non renseignées"}`,
    "",
    `**Explication du score P × G** : P = ${r.probability} (${p?.label} – ${p?.desc}) × G = ${r.gravity} (${g?.label} – ${g?.desc}) = **${r.score}** → niveau **${r.level}**.`,
    `Traitement attendu : ${LEVEL_TREATMENT[r.level as keyof typeof LEVEL_TREATMENT]}`,
    r.justification ? `Justification enregistrée : ${r.justification}` : "",
    "",
    `**Contrôles associés** : ${cs.length ? cs.map((c) => `${c.id} ${c.name} (${c.status})`).join(" ; ") : "aucun – risque non couvert, contrôle à concevoir"}`,
    `**Actions du plan** : ${ac.length ? ac.map((a) => `${a.id} ${a.title} (${a.status}, ${a.progress} %)`).join(" ; ") : "aucune"}`,
    `**Anomalies liées** : ${an.length ? an.map((a) => `${a.id} (${a.status}, ${a.severity})`).join(" ; ") : "aucune"}`,
  ].filter((x) => x !== undefined).join("\n");
}

export function offlineAnswer(s: Snapshot, question: string, focus?: string): string {
  const qn = norm(question);
  const k = computeKpis(s);
  const risks = [...(s.risks as any[])].sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const mentioned = Array.from(new Set((question.toUpperCase().match(/\bR\d{2,3}\b/g) || []))).filter((id) => risks.some((r) => r.id === id));
  const dossierIds = Array.from(new Set(question.toUpperCase().match(/TPE-\d{4}-\d{3}/g) || []));
  if (focus && !dossierIds.includes(focus)) dossierIds.push(focus);
  const out: string[] = [];
  const has = (...w: string[]) => w.some((x) => qn.includes(x));

  if (dossierIds.length || has("dossier", "documentaire", "incoheren", "piece")) {
    const ds = (s.dossiers as any[]).filter((d) => !dossierIds.length || dossierIds.includes(d.id));
    out.push("## Analyse documentaire des dossiers TPE");
    if (!ds.length) out.push("_Aucun dossier correspondant n'est enregistré dans la plateforme._");
    for (const d of ds) {
      const a = d.analysis || {};
      out.push(`### ${d.id} – ${d.company?.name}${d.is_demo ? " _(démo)_" : ""}`);
      out.push(`- **Statut** : ${d.status} · **Complétude** : ${a.completeness?.rate ?? "?"} %`);
      if (a.completeness?.missingDocs?.length) out.push(`- **Pièces manquantes** : ${a.completeness.missingDocs.join(" ; ")}`);
      if (a.inconsistencies?.length) out.push(`- **Incohérences** :\n${a.inconsistencies.map((i: any) => `  - ${i.message} _(risque ${i.risk})_`).join("\n")}`);
      if (a.missingInfo?.length) out.push(`- **Informations manquantes** : ${a.missingInfo.map((i: any) => i.message).join(" ; ")}`);
      if (a.vigilance?.length) out.push(`- **Points de vigilance** :\n${a.vigilance.map((i: any) => `  - ${i.message}`).join("\n")}`);
      out.push(`- **Risques du registre concernés** : ${(a.linkedRisks || []).join(", ") || "aucun"}`);
    }
    out.push("\n> Aide à l'analyse uniquement : aucune décision d'octroi n'est formulée. Le dossier suit le circuit avis risques → instance délégataire (C02).");
  }

  if (mentioned.length) {
    for (const id of mentioned) out.push(riskSheet(s, risks.find((r) => r.id === id)));
    out.push("\n#### Chaîne de recommandation\n" + chainTable(s, mentioned));
  }

  if (!mentioned.length && has("prioritaire", "priorite", "top", "critique", "plus grave", "principaux risques", "analyse les risques", "analyser les risques", "registre")) {
    out.push("## Risques prioritaires (classement par criticité P × G)");
    out.push("| Rang | Risque | P | G | Score | Niveau | Responsable |\n|---|---|---|---|---|---|---|");
    risks.slice(0, 5).forEach((r, i) => out.push(`| ${i + 1} | **${r.id}** ${r.title} | ${r.probability} | ${r.gravity} | **${r.score}** | ${r.level} | ${r.owner} |`));
    const crit = risks.filter((r) => r.level === "Critique");
    out.push(`\n**Lecture** : ${k.total} risques au registre, dont ${k.critical} critique(s) (${crit.map((r) => r.id).join(", ") || "aucun"}) et ${k.high} élevé(s). Score moyen : ${k.avgScore.toFixed(1)}.`);
    const byCat: Record<string, number> = {};
    risks.forEach((r) => (byCat[r.category] = (byCat[r.category] || 0) + 1));
    out.push(`Répartition par catégorie : ${Object.entries(byCat).map(([c, n]) => `${c} ${n}`).join(" · ")}.`);
    const uncovered = risks.filter((r) => !(s.controls as any[]).some((c) => ids(c.risk_ids).includes(r.id)));
    out.push(uncovered.length ? `⚠️ Risques sans contrôle associé : ${uncovered.map((r) => r.id).join(", ")}.` : "Tous les risques sont couverts par au moins un contrôle.");
  }

  if (!mentioned.length && has("score", "p x g", "pxg", "p×g", "cotation", "explique")) {
    out.push("## Explication des scores P × G");
    out.push("Criticité = Probabilité (1–5) × Gravité (1–5). Seuils : 1–4 Faible · 5–9 Modéré · 10–15 Élevé · 16–25 Critique.");
    out.push("| Risque | P | G | Score | Niveau | Justification |\n|---|---|---|---|---|---|");
    risks.forEach((r) => out.push(`| ${r.id} | ${r.probability} | ${r.gravity} | ${r.score} | ${r.level} | ${r.justification || "non renseignée"} |`));
  }

  if (has("coso", "principe")) {
    out.push("## Rattachement des risques aux principes COSO 2013");
    out.push("| Risque | Principes COSO | Composantes | Appréciation |\n|---|---|---|---|");
    for (const r of mentioned.length ? risks.filter((x) => mentioned.includes(x.id)) : risks) {
      const pr = ids(r.coso_principles).map((p) => (s.principles as any[]).find((x) => x.id === p)).filter(Boolean);
      const comps = Array.from(new Set(pr.map((p: any) => (s.components as any[]).find((c) => c.id === p.component_id)?.name)));
      out.push(`| ${r.id} | ${pr.map((p: any) => `${p.id} ${p.title}`).join(" ; ") || "non renseigné"} | ${comps.join(" ; ") || "–"} | ${pr.map((p: any) => `${p.id} : ${p.assessment}`).join(" ; ") || "–"} |`);
    }
    const weakest = [...(s.components as any[])].sort((a, b) => a.maturity - b.maturity).slice(0, 2);
    out.push(`\nComposantes les plus exposées (maturité la plus faible) : ${weakest.map((c) => `${c.name} (${c.maturity}/5)`).join(" ; ")}. Principes déficients : ${k.deficientPrinciples}/17.`);
  }

  if (has("controle", "contrôle")) {
    out.push("## Contrôles internes proposés / existants");
    const target = mentioned.length ? risks.filter((r) => mentioned.includes(r.id)) : risks;
    out.push("| Risque | Contrôles couvrants | Nature | Statut | Indicateur |\n|---|---|---|---|---|");
    for (const r of target) {
      const cs = (s.controls as any[]).filter((c) => ids(c.risk_ids).includes(r.id));
      out.push(cs.length ? `| ${r.id} | ${cs.map((c) => `${c.id} ${c.name}`).join(" ; ")} | ${cs.map((c) => c.nature).join(" ; ")} | ${cs.map((c) => c.status).join(" ; ")} | ${cs.map((c) => c.indicator).join(" ; ")} |` : `| ${r.id} | **Aucun – à concevoir** | – | – | – |`);
    }
    const single = target.filter((r) => (s.controls as any[]).filter((c) => ids(c.risk_ids).includes(r.id)).length === 1);
    if (single.length) out.push(`\nPoint de dépendance : ${single.map((r) => r.id).join(", ")} ne repose(nt) que sur un seul contrôle – à surveiller en priorité.`);
    const toDesign = (s.controls as any[]).filter((c) => c.status === "À concevoir");
    if (toDesign.length) out.push(`Contrôles encore « à concevoir » : ${toDesign.map((c) => c.id).join(", ")}.`);
  }

  if (has("recommandation", "recommande", "lacune")) {
    out.push("## Recommandations (chaîne Risque → Lacune COSO → Action → Responsable → Indicateur)");
    out.push(chainTable(s, mentioned.length ? mentioned : undefined));
  }

  if (has("plan d'action", "plan d action", "plan", "action")) {
    out.push("## Plan d'action correctif");
    out.push(`Avancement moyen : **${k.actionProgress} %** · actions non terminées : ${k.pendingActions}/${s.actions.length}.`);
    out.push("| Priorité | Action | Responsable | Échéance | Statut | Avancement |\n|---|---|---|---|---|---|");
    (s.actions as any[]).forEach((a) => out.push(`| ${a.priority} | ${a.id} ${a.title} | ${a.owner} | ${a.due} | ${a.status} | ${a.progress} % |`));
    const blocked = (s.actions as any[]).filter((a) => a.priority === "P1" && a.status !== "Terminé");
    if (blocked.length) out.push(`\nActions P1 encore ouvertes : ${blocked.map((a) => a.id).join(", ")} – elles conditionnent le reste du dispositif.`);
  }

  if (has("anomal", "incident", "derogation")) {
    out.push("## Analyse des anomalies");
    out.push(`${s.anomalies.length} anomalie(s) enregistrée(s) : ${k.openAnomalies} non clôturée(s), dont ${k.overdueAnomalies} en retard ; ${k.closedAnomalies} clôturée(s).`);
    const byRisk: Record<string, number> = {};
    (s.anomalies as any[]).forEach((a) => (byRisk[a.risk_id || "non rattachée"] = (byRisk[a.risk_id || "non rattachée"] || 0) + 1));
    out.push(`Répartition par risque : ${Object.entries(byRisk).map(([r, n]) => `${r} : ${n}`).join(" · ")}.`);
    out.push("| Id | Nature | Gravité | Risque | Statut | Escalade | Échéance |\n|---|---|---|---|---|---|---|");
    (s.anomalies as any[]).forEach((a) => out.push(`| ${a.id} | ${a.nature} | ${a.severity} | ${a.risk_id || "–"} | ${a.status} | N${a.escalation} | ${a.due_on || "–"} |`));
    const n3 = (s.anomalies as any[]).filter((a) => a.escalation === 3 && a.status !== "Clôturée");
    if (n3.length) out.push(`\n⚠️ Anomalie(s) de niveau 3 (remontée immédiate à la direction générale, charte art. 11) : ${n3.map((a) => a.id).join(", ")}.`);
  }

  if (!out.length || has("synthese", "rapport", "executive", "resume", "bilan")) {
    out.push("## Synthèse exécutive de la gestion des risques");
    const top = risks.slice(0, 3);
    out.push(`- **Exposition** : ${k.total} risques (${k.critical} critiques, ${k.high} élevés). Priorités : ${top.map((r) => `${r.id} (${r.score})`).join(", ")}.`);
    out.push(`- **Dispositif de contrôle** : ${k.totalControls} contrôles, ${k.operationalControls} opérationnels ; ${k.coveredRisks}/${k.total} risques couverts.`);
    out.push(`- **COSO 2013** : ${k.deficientPrinciples} principes déficients ; maturité moyenne ${k.avgMaturity.toFixed(1)}/5.`);
    out.push(`- **Plan d'action** : avancement moyen ${k.actionProgress} %, ${k.pendingActions} action(s) ouverte(s).`);
    out.push(`- **Anomalies** : ${k.openAnomalies} ouverte(s), dont ${k.overdueAnomalies} en retard.`);
    out.push(`- **Dossiers TPE** : ${k.dossiers} analysé(s), ${k.dossiersBlocked} en présentation suspendue (règle de blocage C01).`);
    out.push("\n**Recommandations prioritaires**\n" + chainTable(s, top.map((r) => r.id)));
  }

  // Les lignes de tableau consécutives doivent rester contiguës en Markdown
  return out.join("\n\n").replace(/\|\n\n\|/g, "|\n|");
}
