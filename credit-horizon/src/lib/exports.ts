"use client";
import { levelFromScore, LEVEL_TREATMENT, LEVEL_STYLE } from "./scoring";
import { RACI_ACTIVITIES, RACI_ACTORS, APPETITE_LEVELS, CHARTER_PRINCIPLES } from "./reference";

/* ------------------------------------------------------------------ utilitaires */
const BRAND: [number, number, number] = [6, 59, 43];
const EMERALD: [number, number, number] = [16, 185, 129];

/** Les polices standard PDF ne couvrent que Latin-1 : on normalise les caractères typographiques. */
export function pdfText(s: unknown): string {
  return String(s ?? "")
    .replace(/[–—]/g, "-")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/→|⟶/g, "->")
    .replace(/≥/g, ">=")
    .replace(/≤/g, "<=")
    .replace(/…/g, "...")
    .replace(/œ/g, "oe")
    .replace(/Œ/g, "OE")
    .replace(/[   ]/g, " ")
    .replace(/•|●/g, "-")
    .replace(/[^\x00-\xFF]/g, "");
}

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

const stamp = () => new Date().toISOString().slice(0, 10);

async function newDoc(title: string, subtitle?: string, landscape = false) {
  const { jsPDF } = await import("jspdf");
  const autoTable = (await import("jspdf-autotable")).default;
  const doc = new jsPDF({ orientation: landscape ? "landscape" : "portrait", unit: "mm", format: "a4" });
  const W = doc.internal.pageSize.getWidth();
  doc.setFillColor(...BRAND);
  doc.rect(0, 0, W, 26, "F");
  doc.setFillColor(...EMERALD);
  doc.rect(0, 26, W, 1.2, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text("CREDIT HORIZON", 14, 12);
  doc.setFontSize(7.5);
  doc.setTextColor(110, 231, 183);
  doc.text("R I S K   I N T E L L I G E N C E", 14, 17.5);
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(8);
  doc.setFont("helvetica", "normal");
  doc.text(pdfText(`Édité le ${new Date().toLocaleString("fr-FR")}`), W - 14, 12, { align: "right" });
  doc.text("Projet EMSI - cas fictif - données de démonstration", W - 14, 17.5, { align: "right" });
  doc.setTextColor(...BRAND);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text(pdfText(title), 14, 38);
  let y = 44;
  if (subtitle) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
    doc.setTextColor(90, 100, 110);
    const lines = doc.splitTextToSize(pdfText(subtitle), W - 28);
    doc.text(lines, 14, y);
    y += lines.length * 4.5 + 2;
  }
  return { doc, autoTable, W, y };
}

function footer(doc: any) {
  const n = doc.getNumberOfPages();
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i);
    doc.setFontSize(7.5);
    doc.setTextColor(140, 150, 160);
    doc.text("CREDIT HORIZON RISK INTELLIGENCE - Document d'aide à la décision ; aucune décision d'octroi automatique.", 14, H - 8);
    doc.text(`Page ${i} / ${n}`, W - 14, H - 8, { align: "right" });
  }
}

function heading(doc: any, text: string, y: number) {
  const H = doc.internal.pageSize.getHeight();
  if (y > H - 30) {
    doc.addPage();
    y = 18;
  }
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(...BRAND);
  doc.text(pdfText(text), 14, y);
  doc.setDrawColor(...EMERALD);
  doc.setLineWidth(0.5);
  doc.line(14, y + 1.5, 40, y + 1.5);
  return y + 7;
}

function paragraph(doc: any, text: string, y: number, size = 9.5) {
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  doc.setFont("helvetica", "normal");
  doc.setFontSize(size);
  doc.setTextColor(40, 50, 60);
  const lines = doc.splitTextToSize(pdfText(text), W - 28);
  for (const l of lines) {
    if (y > H - 18) {
      doc.addPage();
      y = 18;
    }
    doc.text(l, 14, y);
    y += size * 0.45;
  }
  return y + 2;
}

const tableStyle: any = {
  styles: { font: "helvetica", fontSize: 8, cellPadding: 1.8, textColor: [30, 41, 59], lineColor: [226, 232, 240], lineWidth: 0.1 },
  headStyles: { fillColor: BRAND, textColor: 255, fontStyle: "bold" },
  alternateRowStyles: { fillColor: [244, 249, 247] },
  margin: { left: 14, right: 14 },
};

function table(doc: any, autoTable: any, y: number, head: string[], body: unknown[][], extra: any = {}) {
  autoTable(doc, { startY: y, head: [head.map(pdfText)], body: body.map((r) => r.map(pdfText)), ...tableStyle, ...extra });
  return doc.lastAutoTable.finalY + 6;
}

const hexToRgb = (h: string): [number, number, number] => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

function drawHeatmap(doc: any, risks: any[], x: number, y: number, cell = 22) {
  doc.setFontSize(8);
  for (let p = 5; p >= 1; p--) {
    for (let g = 1; g <= 5; g++) {
      const lvl = levelFromScore(p * g);
      const cx = x + 8 + (g - 1) * cell;
      const cy = y + (5 - p) * cell;
      const col = hexToRgb(LEVEL_STYLE[lvl].hex);
      doc.setFillColor(col[0] + (255 - col[0]) * 0.55, col[1] + (255 - col[1]) * 0.55, col[2] + (255 - col[2]) * 0.55);
      doc.setDrawColor(255, 255, 255);
      doc.rect(cx, cy, cell - 1, cell - 1, "FD");
      doc.setTextColor(100, 100, 100);
      doc.setFont("helvetica", "normal");
      doc.text(String(p * g), cx + cell - 3, cy + cell - 3, { align: "right" });
      const here = risks.filter((r) => Number(r.probability) === p && Number(r.gravity) === g);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(15, 23, 42);
      here.forEach((r, i) => doc.text(r.id, cx + 2, cy + 5 + i * 4));
    }
    doc.setTextColor(60, 60, 60);
    doc.setFont("helvetica", "bold");
    doc.text(String(p), x + 4, y + (5 - p) * cell + cell / 2 + 1, { align: "center" });
  }
  for (let g = 1; g <= 5; g++) doc.text(String(g), x + 8 + (g - 1) * cell + cell / 2, y + 5 * cell + 4, { align: "center" });
  doc.setFont("helvetica", "normal");
  doc.text("Gravité ->", x + 8 + 2.5 * cell, y + 5 * cell + 9, { align: "center" });
  doc.text("Probabilité", x - 1, y + 2.5 * cell, { angle: 90, align: "center" });
  return y + 5 * cell + 14;
}

/* ------------------------------------------------------------------ Markdown -> PDF */
export async function exportMarkdownPdf(title: string, md: string) {
  const { doc, autoTable } = await newDoc(title, "Réponse générée par Risk Advisor à partir des données enregistrées dans la plateforme.");
  let y = 52;
  const lines = md.replace(/\r/g, "").split("\n");
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    if (l.trim().startsWith("|") && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const cells = (s: string) => s.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim().replace(/\*\*/g, ""));
      const head = cells(l);
      i += 2;
      const body: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) body.push(cells(lines[i++]));
      y = table(doc, autoTable, y, head, body, { styles: { ...tableStyle.styles, fontSize: 7.5 } });
      continue;
    }
    const h = l.match(/^#{1,4}\s+(.*)$/);
    if (h) { y = heading(doc, h[1].replace(/\*\*/g, ""), y + 2); i++; continue; }
    const clean = l.replace(/\*\*/g, "").replace(/`/g, "").replace(/^\s*>\s?/, "").replace(/^\s*[-*•]\s+/, "  - ");
    y = paragraph(doc, clean, y, 9.5) - 1;
    i++;
  }
  footer(doc);
  doc.save(`risk-advisor-${stamp()}.pdf`);
}

/* ------------------------------------------------------------------ CSV */
export function exportCsv(filename: string, columns: { key: string; label: string }[], rows: any[]) {
  const esc = (v: unknown) => {
    const s = String(v ?? "").replace(/\r?\n/g, " ");
    return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [columns.map((c) => esc(c.label)).join(";"), ...rows.map((r) => columns.map((c) => esc(r[c.key])).join(";"))].join("\r\n");
  download(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }), filename);
}

export const RISK_COLUMNS = [
  { key: "id", label: "Identifiant" },
  { key: "title", label: "Risque" },
  { key: "event", label: "Description de l'événement" },
  { key: "causes", label: "Causes" },
  { key: "consequences", label: "Conséquences" },
  { key: "category", label: "Catégorie" },
  { key: "probability", label: "Probabilité (1-5)" },
  { key: "gravity", label: "Gravité (1-5)" },
  { key: "score", label: "Score P x G" },
  { key: "level", label: "Niveau de criticité" },
  { key: "owner", label: "Responsable" },
  { key: "control_ids", label: "Contrôles associés" },
  { key: "coso_principles", label: "Principes COSO" },
  { key: "recommendation", label: "Recommandation" },
  { key: "justification", label: "Justification" },
  { key: "basis", label: "Fondement" },
];

/* ------------------------------------------------------------------ Excel */
export async function exportExcel(s: any) {
  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  wb.creator = "CRÉDIT HORIZON RISK INTELLIGENCE";
  wb.created = new Date();
  const addSheet = (name: string, cols: { key: string; label: string; width?: number }[], rows: any[], colorize?: (row: any, r: any) => void) => {
    const ws = wb.addWorksheet(name, { views: [{ state: "frozen", ySplit: 1 }] });
    ws.columns = cols.map((c) => ({ header: c.label, key: c.key, width: c.width ?? Math.min(60, Math.max(12, c.label.length + 4)) }));
    rows.forEach((r) => {
      const row = ws.addRow(Object.fromEntries(cols.map((c) => [c.key, r[c.key]])));
      colorize?.(row, r);
    });
    const head = ws.getRow(1);
    head.font = { bold: true, color: { argb: "FFFFFFFF" } };
    head.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF063B2B" } };
    head.alignment = { vertical: "middle", wrapText: true };
    head.height = 28;
    ws.eachRow((row, i) => {
      if (i > 1) row.alignment = { vertical: "top", wrapText: true };
    });
    ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: cols.length } };
  };
  const wide = (k: string) => (["event", "causes", "consequences", "recommendation", "justification", "procedure", "objective", "coso_gap", "action", "indicator", "nature", "findings", "gaps", "recommendations", "diagnostic"].includes(k) ? 48 : undefined);
  const withW = (cols: { key: string; label: string }[]) => cols.map((c) => ({ ...c, width: wide(c.key) }));

  addSheet("Registre des risques", withW(RISK_COLUMNS), s.risks, (row, r) => {
    const hex = LEVEL_STYLE[levelFromScore(Number(r.score)) as keyof typeof LEVEL_STYLE].hex.slice(1).toUpperCase();
    const cell = row.getCell("level");
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF" + hex } };
    cell.font = { bold: true, color: { argb: "FFFFFFFF" } };
  });
  addSheet("Contrôles", withW([
    { key: "id", label: "Id" }, { key: "name", label: "Contrôle" }, { key: "nature", label: "Type" }, { key: "objective", label: "Objectif" },
    { key: "risk_ids", label: "Risques couverts" }, { key: "procedure", label: "Procédure" }, { key: "owner", label: "Responsable" },
    { key: "frequency", label: "Fréquence" }, { key: "evidence", label: "Preuve attendue" }, { key: "indicator", label: "Indicateur" },
    { key: "anomaly_treatment", label: "Traitement des anomalies" }, { key: "status", label: "Statut" },
  ]), s.controls);
  addSheet("COSO - composantes", withW([
    { key: "id", label: "N°" }, { key: "name", label: "Composante" }, { key: "principles", label: "Principes" }, { key: "findings", label: "Constats" },
    { key: "gaps", label: "Lacunes" }, { key: "risk_ids", label: "Risques" }, { key: "recommendations", label: "Recommandations" },
    { key: "owner", label: "Responsables" }, { key: "indicators", label: "Indicateurs" }, { key: "maturity", label: "Maturité (1-5)" },
  ]), s.components);
  addSheet("COSO - 17 principes", withW([
    { key: "id", label: "Principe" }, { key: "title", label: "Intitulé" }, { key: "nature", label: "Nature" }, { key: "diagnostic", label: "Diagnostic" },
    { key: "risk_ids", label: "Risques" }, { key: "assessment", label: "Appréciation" },
  ]), s.principles);
  addSheet("Recommandations", withW([
    { key: "id", label: "Id" }, { key: "risk_id", label: "RISQUE" }, { key: "coso_gap", label: "LACUNE COSO" }, { key: "action", label: "ACTION CORRECTIVE" },
    { key: "owner", label: "RESPONSABLE" }, { key: "indicator", label: "INDICATEUR DE SUIVI" }, { key: "basis", label: "Fondement" }, { key: "status", label: "Statut" },
  ]), s.recommendations);
  addSheet("Plan d'action", withW([
    { key: "id", label: "Id" }, { key: "priority", label: "Priorité" }, { key: "title", label: "Action" }, { key: "owner", label: "Responsable" },
    { key: "due", label: "Échéance" }, { key: "deliverable", label: "Livrable / preuve" }, { key: "risk_ids", label: "Risques" },
    { key: "control_ids", label: "Contrôles" }, { key: "status", label: "Statut" }, { key: "progress", label: "Avancement %" },
  ]), s.actions);
  addSheet("Anomalies", withW([
    { key: "id", label: "Id" }, { key: "detected_on", label: "Détectée le" }, { key: "dossier_ref", label: "Dossier" }, { key: "nature", label: "Nature" },
    { key: "severity", label: "Gravité" }, { key: "risk_id", label: "Risque" }, { key: "control_id", label: "Contrôle" }, { key: "owner", label: "Responsable" },
    { key: "due_on", label: "Échéance" }, { key: "status", label: "Statut" }, { key: "escalation", label: "Niveau d'escalade" }, { key: "resolution", label: "Résolution" },
  ]), s.anomalies);
  const raciRows = RACI_ACTIVITIES.map((a) => ({ activity: `${a.n}. ${a.activity}`, ...a.roles }));
  addSheet("Matrice RACI", [{ key: "activity", label: "Activité", width: 34 }, ...RACI_ACTORS.map((x) => ({ key: x.key, label: x.label, width: 18 }))], raciRows);
  const buf = await wb.xlsx.writeBuffer();
  download(new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `credit-horizon-registre-${stamp()}.xlsx`);
}

/* ------------------------------------------------------------------ Rapports PDF */
function riskRows(s: any) {
  return [...s.risks].sort((a: any, b: any) => b.score - a.score || a.id.localeCompare(b.id)).map((r: any) => [r.id, r.title, r.category, r.probability, r.gravity, r.score, r.level, r.owner]);
}
const levelCellColor = (data: any) => {
  if (data.section === "body" && data.column.index === 6) {
    const hex = LEVEL_STYLE[data.cell.raw as keyof typeof LEVEL_STYLE]?.hex;
    if (hex) {
      data.cell.styles.fillColor = hexToRgb(hex);
      data.cell.styles.textColor = 255;
      data.cell.styles.fontStyle = "bold";
    }
  }
};

export async function exportExecutivePdf(s: any) {
  const k = s.kpis;
  const { doc, autoTable, y: y0 } = await newDoc("Synthèse exécutive", "Situation consolidée des risques, du contrôle interne et du plan d'action.");
  let y = heading(doc, "1. Indicateurs clés", y0 + 4);
  y = table(doc, autoTable, y, ["Indicateur", "Valeur"], [
    ["Risques recensés", k.total], ["Risques critiques / élevés", `${k.critical} / ${k.high}`], ["Score moyen P x G", k.avgScore.toFixed(1)],
    ["Contrôles opérationnels", `${k.operationalControls} / ${k.totalControls}`], ["Risques couverts par un contrôle", `${k.coveredRisks} / ${k.total}`],
    ["Actions non terminées", k.pendingActions], ["Avancement moyen du plan d'action", `${k.actionProgress} %`],
    ["Anomalies ouvertes (dont en retard)", `${k.openAnomalies} (${k.overdueAnomalies})`], ["Principes COSO déficients", `${k.deficientPrinciples} / 17`],
    ["Maturité moyenne COSO", `${k.avgMaturity.toFixed(1)} / 5`], ["Dossiers TPE suspendus", `${k.dossiersBlocked} / ${k.dossiers}`],
  ], { columnStyles: { 0: { cellWidth: 100 } } });
  y = heading(doc, "2. Top 5 des risques prioritaires", y);
  y = table(doc, autoTable, y, ["Id", "Risque", "Catégorie", "P", "G", "Score", "Niveau", "Responsable"], riskRows(s).slice(0, 5), { didParseCell: levelCellColor });
  y = heading(doc, "3. Recommandations prioritaires", y);
  const top = [...s.risks].sort((a: any, b: any) => b.score - a.score).slice(0, 4).map((r: any) => r.id);
  y = table(doc, autoTable, y, ["Risque", "Lacune COSO", "Action corrective", "Responsable", "Indicateur"], s.recommendations.filter((r: any) => top.includes(r.risk_id)).map((r: any) => [r.risk_id, r.coso_gap, r.action, r.owner, r.indicator]), { styles: { ...tableStyle.styles, fontSize: 7.5 } });
  y = heading(doc, "4. Actions P1", y);
  table(doc, autoTable, y, ["Id", "Action", "Responsable", "Échéance", "Statut", "%"], s.actions.filter((a: any) => a.priority === "P1").map((a: any) => [a.id, a.title, a.owner, a.due, a.status, a.progress]));
  footer(doc);
  doc.save(`synthese-executive-${stamp()}.pdf`);
}

export async function exportHeatmapPdf(s: any) {
  const { doc, autoTable, y } = await newDoc("Cartographie des risques", "Matrice probabilité x gravité (5 x 5). Seuils : 1-4 Faible ; 5-9 Modéré ; 10-15 Élevé ; 16-25 Critique.", true);
  const end = drawHeatmap(doc, s.risks, 18, y + 4, 21);
  autoTable(doc, {
    startY: y + 4,
    margin: { left: 150, right: 14 },
    head: [["Id", "Risque", "Score", "Niveau"]],
    body: [...s.risks].sort((a: any, b: any) => b.score - a.score).map((r: any) => [r.id, pdfText(r.title), r.score, r.level]),
    ...{ styles: tableStyle.styles, headStyles: tableStyle.headStyles },
    didParseCell: (d: any) => {
      if (d.section === "body" && d.column.index === 3) {
        const hex = LEVEL_STYLE[d.cell.raw as keyof typeof LEVEL_STYLE]?.hex;
        if (hex) { d.cell.styles.fillColor = hexToRgb(hex); d.cell.styles.textColor = 255; }
      }
    },
  });
  void end;
  footer(doc);
  doc.save(`cartographie-risques-${stamp()}.pdf`);
}

export async function exportCosoPdf(s: any) {
  const { doc, autoTable, y: y0 } = await newDoc("Rapport COSO 2013", "Diagnostic du dispositif de contrôle interne par composante et par principe. Les appréciations sont provisoires et qualitatives.", true);
  let y = heading(doc, "1. Diagnostic par composante", y0 + 2);
  y = table(doc, autoTable, y, ["Composante", "Constats", "Lacunes", "Risques", "Recommandations", "Responsables", "Indicateurs", "Maturité"],
    s.components.map((c: any) => [`${c.id}. ${c.name} (${c.principles})`, c.findings, c.gaps, c.risk_ids, c.recommendations, c.owner, c.indicators, `${c.maturity}/5`]),
    { styles: { ...tableStyle.styles, fontSize: 7 } });
  y = heading(doc, "2. Diagnostic des 17 principes", y);
  table(doc, autoTable, y, ["Principe", "Intitulé", "Composante", "Nature", "Diagnostic", "Risques", "Appréciation"],
    s.principles.map((p: any) => [p.id, p.title, s.components.find((c: any) => c.id === p.component_id)?.name ?? "", p.nature, p.diagnostic, p.risk_ids, p.assessment]),
    { styles: { ...tableStyle.styles, fontSize: 7.5 } });
  footer(doc);
  doc.save(`rapport-coso-${stamp()}.pdf`);
}

export async function exportActionPlanPdf(s: any) {
  const { doc, autoTable, y: y0 } = await newDoc("Plan d'action correctif", "Actions priorisées (P1 à P3), chaînes de recommandations et suivi des anomalies.", true);
  let y = heading(doc, "1. Plan d'action", y0 + 2);
  y = table(doc, autoTable, y, ["Id", "Priorité", "Action", "Responsable", "Échéance", "Livrable / preuve", "Risques", "Contrôles", "Statut", "%"],
    s.actions.map((a: any) => [a.id, a.priority, a.title, a.owner, a.due, a.deliverable, a.risk_ids, a.control_ids, a.status, a.progress]));
  y = heading(doc, "2. Chaînes de recommandations", y);
  y = table(doc, autoTable, y, ["Id", "RISQUE", "LACUNE COSO", "ACTION CORRECTIVE", "RESPONSABLE", "INDICATEUR DE SUIVI", "Statut"],
    s.recommendations.map((r: any) => [r.id, r.risk_id, r.coso_gap, r.action, r.owner, r.indicator, r.status]), { styles: { ...tableStyle.styles, fontSize: 7.5 } });
  y = heading(doc, "3. Anomalies non clôturées", y);
  table(doc, autoTable, y, ["Id", "Détectée", "Dossier", "Nature", "Gravité", "Risque", "Responsable", "Échéance", "Statut", "Escalade"],
    s.anomalies.filter((a: any) => a.status !== "Clôturée").map((a: any) => [a.id, a.detected_on, a.dossier_ref, a.nature, a.severity, a.risk_id, a.owner, a.due_on, a.status, `N${a.escalation}`]));
  footer(doc);
  doc.save(`plan-action-${stamp()}.pdf`);
}

export async function exportFullReportPdf(s: any) {
  const k = s.kpis;
  const { doc, autoTable, y: y0 } = await newDoc("Rapport de gestion des risques", "Rapport complet : registre, cartographie, contrôle interne, diagnostic COSO, gouvernance, appétence au risque et plan d'action.");
  let y = heading(doc, "1. Synthèse", y0 + 2);
  y = paragraph(doc, `Le registre compte ${k.total} risques dont ${k.critical} critiques et ${k.high} élevés (score moyen ${k.avgScore.toFixed(1)}/25). ${k.coveredRisks} risques sur ${k.total} sont couverts par au moins un contrôle ; ${k.operationalControls} contrôles sur ${k.totalControls} sont opérationnels. Le diagnostic COSO identifie ${k.deficientPrinciples} principes déficients sur 17 (maturité moyenne ${k.avgMaturity.toFixed(1)}/5). Le plan d'action est avancé à ${k.actionProgress} % et ${k.openAnomalies} anomalie(s) restent ouvertes, dont ${k.overdueAnomalies} en retard.`, y);
  y = heading(doc, "2. Registre des risques", y);
  y = table(doc, autoTable, y, ["Id", "Risque", "Catégorie", "P", "G", "Score", "Niveau", "Responsable"], riskRows(s), { didParseCell: levelCellColor });
  for (const r of s.risks) {
    y = paragraph(doc, `${r.id} - Causes : ${r.causes} | Conséquences : ${r.consequences} | Traitement attendu : ${LEVEL_TREATMENT[r.level as keyof typeof LEVEL_TREATMENT]}`, y, 8);
  }
  doc.addPage();
  y = heading(doc, "3. Cartographie des risques", 18);
  y = drawHeatmap(doc, s.risks, 40, y + 2, 24);
  y = heading(doc, "4. Fiches de contrôle interne", y);
  y = table(doc, autoTable, y, ["Id", "Contrôle", "Type", "Risques", "Responsable", "Fréquence", "Preuve", "Indicateur", "Statut"],
    s.controls.map((c: any) => [c.id, c.name, c.nature, c.risk_ids, c.owner, c.frequency, c.evidence, c.indicator, c.status]), { styles: { ...tableStyle.styles, fontSize: 7 } });
  y = heading(doc, "5. Diagnostic COSO 2013", y);
  y = table(doc, autoTable, y, ["Composante", "Lacunes", "Risques", "Recommandations", "Maturité"], s.components.map((c: any) => [`${c.id}. ${c.name}`, c.gaps, c.risk_ids, c.recommendations, `${c.maturity}/5`]), { styles: { ...tableStyle.styles, fontSize: 7.5 } });
  y = heading(doc, "6. Gouvernance - matrice RACI", y);
  y = table(doc, autoTable, y, ["Activité", ...RACI_ACTORS.map((a) => a.label)], RACI_ACTIVITIES.map((a) => [`${a.n}. ${a.activity}`, ...RACI_ACTORS.map((x) => a.roles[x.key])]), { styles: { ...tableStyle.styles, fontSize: 7, halign: "center" }, columnStyles: { 0: { halign: "left", cellWidth: 48 } } });
  y = heading(doc, "7. Appétence au risque", y);
  y = paragraph(doc, "Principes : " + CHARTER_PRINCIPLES.join(" ; "), y, 8.5);
  y = table(doc, autoTable, y, ["Niveau", "Description"], APPETITE_LEVELS.map((l) => [l.title, l.description + " Exemples : " + l.examples.join(" ; ")]));
  y = heading(doc, "8. Recommandations (Risque -> Lacune COSO -> Action -> Responsable -> Indicateur)", y);
  y = table(doc, autoTable, y, ["Risque", "Lacune COSO", "Action corrective", "Responsable", "Indicateur"], s.recommendations.map((r: any) => [r.risk_id, r.coso_gap, r.action, r.owner, r.indicator]), { styles: { ...tableStyle.styles, fontSize: 7 } });
  y = heading(doc, "9. Plan d'action", y);
  table(doc, autoTable, y, ["Id", "Prio.", "Action", "Responsable", "Échéance", "Statut", "%"], s.actions.map((a: any) => [a.id, a.priority, a.title, a.owner, a.due, a.status, a.progress]));
  footer(doc);
  doc.save(`rapport-gestion-risques-${stamp()}.pdf`);
}
