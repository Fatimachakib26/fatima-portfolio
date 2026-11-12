import "server-only";
import type { Snapshot } from "./snapshot";
import { computeKpis } from "./snapshot";
import { LEVEL_TREATMENT, levelFromScore, PROBABILITY_SCALE, GRAVITY_SCALE } from "./scoring";
import {
  RACI_ACTORS,
  RACI_ACTIVITIES,
  APPETITE_LEVELS,
  APPETITE_BY_CATEGORY,
  CHARTER_PRINCIPLES,
  ESCALATION,
  HYPOTHESES,
  DYSFUNCTIONS,
  DELEGATION_MATRIX,
} from "./reference";

export const ADVISOR_RULES = `Tu es « Risk Advisor », l'assistant IA de la plateforme CRÉDIT HORIZON RISK INTELLIGENCE.
Tu te comportes comme un consultant senior en gestion des risques financiers et en contrôle interne (COSO 2013), au service d'un organisme de financement des TPE.

RÈGLES IMPÉRATIVES
1. Réponds toujours en français professionnel, clair et structuré (titres Markdown, listes, tableaux si utile).
2. Utilise EXCLUSIVEMENT les données de la plateforme fournies ci-dessous (registre, contrôles, COSO, recommandations, plan d'action, anomalies, dossiers, RACI, charte). Cite les identifiants (R01, C02, P10, REC03, A04, AN-002, TPE-2026-001…).
3. N'invente JAMAIS de chiffres, de seuils, de montants, de noms ou de faits. Si une information manque, dis-le explicitement (« information non disponible dans la plateforme ») et indique comment l'obtenir. Distingue « constat » (fait du cas) et « hypothèse à vérifier ».
4. Ne prends JAMAIS de décision d'octroi ou de refus de crédit et ne formule pas de recommandation d'accorder/refuser. Tu fournis une aide à l'analyse ; la décision relève de l'instance délégataire après avis indépendant de la fonction risques (contrôle C02).
5. Toute recommandation suit OBLIGATOIREMENT la chaîne :
   **RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI**
   (présente-la sous forme de tableau Markdown à 5 colonnes ou de liste numérotée avec ces 5 libellés).
6. La criticité = Probabilité × Gravité (1 à 25). Seuils : 1–4 Faible ; 5–9 Modéré ; 10–15 Élevé ; 16–25 Critique.
7. Reste concis : privilégie l'essentiel, puis propose des prochaines étapes concrètes.
8. Les données sont celles d'un cas académique fictif (projet EMSI) ; les éléments marqués « démo » sont des données de démonstration.`;

const join = (v: unknown) => String(v ?? "").trim();

export function buildContext(s: Snapshot, focus?: string) {
  const k = computeKpis(s);
  const lines: string[] = [];
  lines.push(`# DONNÉES DE LA PLATEFORME (extraites le ${new Date(s.generatedAt).toLocaleString("fr-FR")})`);
  lines.push(
    `## Indicateurs\n- Risques : ${k.total} (critiques : ${k.critical}, élevés : ${k.high}) ; score moyen ${k.avgScore.toFixed(1)}\n- Contrôles : ${k.totalControls} (opérationnels/efficaces : ${k.operationalControls}) ; risques couverts par au moins un contrôle : ${k.coveredRisks}/${k.total}\n- Plan d'action : ${s.actions.length} actions, ${k.pendingActions} non terminées, avancement moyen ${k.actionProgress} %\n- Anomalies : ${s.anomalies.length} (ouvertes : ${k.openAnomalies}, en retard : ${k.overdueAnomalies}, clôturées : ${k.closedAnomalies})\n- Principes COSO jugés déficients : ${k.deficientPrinciples}/17 ; maturité moyenne des composantes ${k.avgMaturity.toFixed(1)}/5\n- Dossiers TPE : ${k.dossiers} (présentation suspendue : ${k.dossiersBlocked})`,
  );

  lines.push(`## Échelles\nProbabilité : ${PROBABILITY_SCALE.map((p) => `${p.v}=${p.label} (${p.desc})`).join(" | ")}\nGravité : ${GRAVITY_SCALE.map((p) => `${p.v}=${p.label} (${p.desc})`).join(" | ")}\nTraitement : ${Object.entries(LEVEL_TREATMENT).map(([l, t]) => `${l} → ${t}`).join(" | ")}`);

  lines.push("## Registre des risques");
  for (const r of s.risks as any[]) {
    lines.push(
      `### ${r.id} – ${r.title}${r.is_demo ? " [démo]" : ""}\n- Catégorie : ${r.category} | P=${r.probability} G=${r.gravity} → score ${r.score} (${levelFromScore(r.score)}) | Fondement : ${r.basis}\n- Événement : ${join(r.event)}\n- Causes : ${join(r.causes)}\n- Conséquences : ${join(r.consequences)}\n- Justification : ${join(r.justification)}\n- Responsable : ${join(r.owner)} | Contrôles : ${join(r.control_ids) || "aucun"} | Principes COSO : ${join(r.coso_principles) || "non renseigné"}\n- Recommandation : ${join(r.recommendation)}`,
    );
  }

  lines.push("## Fiches de contrôle");
  for (const c of s.controls as any[]) {
    lines.push(
      `- ${c.id} ${c.name} (${c.nature}, statut : ${c.status}) — risques : ${c.risk_ids} ; objectif : ${c.objective} ; procédure : ${c.procedure} ; responsable : ${c.owner} ; supervision : ${c.supervision} ; fréquence : ${c.frequency} ; preuve : ${c.evidence} ; indicateur : ${c.indicator} ; anomalie : ${c.anomaly_treatment}`,
    );
  }

  lines.push("## Diagnostic COSO 2013 – composantes");
  for (const c of s.components as any[]) {
    lines.push(`- ${c.id}. ${c.name} (${c.principles}, maturité ${c.maturity}/5) — constats : ${c.findings} ; lacunes : ${c.gaps} ; risques : ${c.risk_ids} ; recommandations : ${c.recommendations} ; responsable : ${c.owner} ; indicateurs : ${c.indicators}`);
  }
  lines.push("## Diagnostic COSO – 17 principes");
  for (const p of s.principles as any[]) {
    lines.push(`- ${p.id} ${p.title} [${p.nature} ; appréciation : ${p.assessment}] — ${p.diagnostic} ; risques : ${p.risk_ids || "–"}`);
  }

  lines.push("## Chaînes de recommandations");
  for (const r of s.recommendations as any[]) {
    lines.push(`- ${r.id} (${r.status}, ${r.basis}) : ${r.risk_id} → ${r.coso_gap} → ${r.action} → ${r.owner} → ${r.indicator}`);
  }

  lines.push("## Plan d'action");
  for (const a of s.actions as any[]) {
    lines.push(`- ${a.id} [${a.priority}] ${a.title} — ${a.owner} ; échéance : ${a.due} ; livrable : ${a.deliverable} ; risques : ${a.risk_ids || "–"} ; contrôles : ${a.control_ids || "–"} ; statut : ${a.status} (${a.progress} %)`);
  }

  lines.push("## Registre des anomalies");
  for (const a of s.anomalies as any[]) {
    lines.push(`- ${a.id} du ${a.detected_on} (${a.dossier_ref}) : ${a.nature} — gravité ${a.severity} ; risque ${a.risk_id || "–"} ; contrôle ${a.control_id || "–"} ; responsable ${a.owner} ; échéance ${a.due_on || "–"} ; statut ${a.status} ; escalade niveau ${a.escalation}${a.resolution ? ` ; résolution : ${a.resolution}` : ""}${a.is_demo ? " [démo]" : ""}`);
  }

  lines.push("## Dossiers TPE analysés");
  for (const d of s.dossiers as any[]) {
    const an = d.analysis || {};
    const highlight = focus && focus === d.id;
    lines.push(
      `- ${d.id}${highlight ? " (DOSSIER EN COURS D'EXAMEN)" : ""} – ${d.company?.name} (${d.company?.sector || "secteur non renseigné"}) : ${d.request?.product || "produit ?"} de ${d.request?.amount || "?"} MAD sur ${d.request?.duration_months || "?"} mois ; statut : ${d.status}${d.is_demo ? " [démo]" : ""}\n  Complétude ${an.completeness?.rate ?? "?"} % ; pièces manquantes : ${(an.completeness?.missingDocs || []).join(" ; ") || "aucune"}\n  Incohérences : ${(an.inconsistencies || []).map((i: any) => i.message).join(" | ") || "aucune"}\n  Vigilance : ${(an.vigilance || []).map((i: any) => i.message).join(" | ") || "aucun point"}\n  Informations manquantes : ${(an.missingInfo || []).map((i: any) => i.message).join(" | ") || "aucune"}\n  Observations analyste : ${d.observations || "–"}`,
    );
    if (highlight) {
      lines.push(`  Données détaillées : ${JSON.stringify({ company: d.company, request: d.request, financials: d.financials, guarantees: d.guarantees, ratios: an.ratios })}`);
    }
  }

  lines.push("## Gouvernance – matrice RACI (R réalise, A valide/responsable final, C consulté, I informé)");
  lines.push(`Acteurs : ${RACI_ACTORS.map((a) => a.label).join(" | ")}`);
  for (const a of RACI_ACTIVITIES) lines.push(`- ${a.n}. ${a.activity} : ${RACI_ACTORS.map((x) => `${x.label}=${a.roles[x.key]}`).join(", ")}`);
  lines.push("Délégations (réalise / valide / informé) : " + DELEGATION_MATRIX.map((d) => `${d.decision} → ${d.realise} / ${d.valide} / ${d.informe}`).join(" ; "));

  lines.push("## Charte d'appétence au risque");
  lines.push("Principes : " + CHARTER_PRINCIPLES.join(" ; "));
  for (const l of APPETITE_LEVELS) lines.push(`- ${l.title} : ${l.description} Exemples : ${l.examples.join(" ; ")}`);
  for (const c of APPETITE_BY_CATEGORY) lines.push(`- ${c.category} : appétence – ${c.appetite} ; limites – ${c.limits}`);
  lines.push("Escalade : " + ESCALATION.map((e) => `${e.title} : ${e.text}`).join(" ; "));
  lines.push("## Faits du cas (dysfonctionnements) : " + DYSFUNCTIONS.map((d) => `${d.id} ${d.text}`).join(" ; "));
  lines.push("## Hypothèses de travail : " + HYPOTHESES.map((h) => `${h.id} ${h.text}`).join(" ; "));
  return lines.join("\n");
}
