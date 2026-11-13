"use client";
import { useState } from "react";
import { FileDown, FileText, FileSpreadsheet, Table2, Grid3x3, Landmark, ClipboardList, BookOpen, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/client";
import { PageHeader, Card, Toast } from "@/components/ui";
import {
  exportFullReportPdf, exportExecutivePdf, exportCosoPdf, exportHeatmapPdf, exportActionPlanPdf, exportExcel, exportCsv, RISK_COLUMNS, exportMarkdownPdf,
} from "@/lib/exports";
import { streamAdvisor } from "@/lib/advisor-client";

export default function RapportsPage() {
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<{ m: string; t?: "red" } | null>(null);

  async function run(key: string, fn: (s: any) => Promise<void> | void) {
    setBusy(key);
    try {
      const s = await api("/api/snapshot");
      await fn(s);
      setToast({ m: "Export généré." });
    } catch (e: any) {
      setToast({ m: e.message || "Échec de l'export.", t: "red" });
    } finally {
      setBusy(null);
    }
  }

  async function aiReport() {
    setBusy("ai");
    try {
      const { text } = await streamAdvisor(
        [{ role: "user", content: "Prépare un rapport de gestion des risques complet et professionnel destiné à la direction générale : synthèse, cartographie et risques prioritaires, diagnostic COSO, dispositif de contrôle, anomalies, plan d'action, recommandations au format RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI, et prochaines étapes." }],
        () => {},
      );
      await exportMarkdownPdf("Rapport de gestion des risques – rédigé par Risk Advisor", text);
      setToast({ m: "Rapport IA généré." });
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    } finally {
      setBusy(null);
    }
  }

  const items = [
    { key: "full", icon: BookOpen, title: "Rapport complet de gestion des risques", desc: "PDF : synthèse, registre, cartographie, contrôles, COSO, RACI, appétence, recommandations, plan d'action.", fmt: "PDF", fn: exportFullReportPdf },
    { key: "exec", icon: FileText, title: "Synthèse exécutive", desc: "PDF : indicateurs clés, top 5 des risques, recommandations prioritaires, actions P1.", fmt: "PDF", fn: exportExecutivePdf },
    { key: "coso", icon: Landmark, title: "Rapport COSO 2013", desc: "PDF : diagnostic des 5 composantes et des 17 principes.", fmt: "PDF", fn: exportCosoPdf },
    { key: "map", icon: Grid3x3, title: "Cartographie des risques", desc: "PDF paysage : matrice 5 × 5 et classement par criticité.", fmt: "PDF", fn: exportHeatmapPdf },
    { key: "plan", icon: ClipboardList, title: "Plan d'action correctif", desc: "PDF : actions priorisées, chaînes de recommandations, anomalies ouvertes.", fmt: "PDF", fn: exportActionPlanPdf },
    { key: "xlsx", icon: FileSpreadsheet, title: "Registre Excel complet", desc: "XLSX multi-onglets : registre, contrôles, COSO, recommandations, plan d'action, anomalies, RACI.", fmt: "XLSX", fn: exportExcel },
    { key: "csv-risks", icon: Table2, title: "Registre des risques (CSV)", desc: "CSV séparateur « ; », encodage UTF-8, compatible Excel.", fmt: "CSV", fn: (s: any) => exportCsv(`registre-risques-${new Date().toISOString().slice(0, 10)}.csv`, RISK_COLUMNS, s.risks) },
    {
      key: "csv-anom", icon: Table2, title: "Registre des anomalies (CSV)", desc: "Export du registre unique des anomalies et dérogations (C04).", fmt: "CSV",
      fn: (s: any) => exportCsv(`anomalies-${new Date().toISOString().slice(0, 10)}.csv`, [
        { key: "id", label: "Id" }, { key: "detected_on", label: "Détectée le" }, { key: "dossier_ref", label: "Dossier" }, { key: "nature", label: "Nature" },
        { key: "severity", label: "Gravité" }, { key: "risk_id", label: "Risque" }, { key: "control_id", label: "Contrôle" }, { key: "owner", label: "Responsable" },
        { key: "due_on", label: "Échéance" }, { key: "status", label: "Statut" }, { key: "escalation", label: "Escalade" }, { key: "resolution", label: "Résolution" },
      ], s.anomalies),
    },
    {
      key: "csv-actions", icon: Table2, title: "Plan d'action (CSV)", desc: "Export du plan d'action correctif.", fmt: "CSV",
      fn: (s: any) => exportCsv(`plan-action-${new Date().toISOString().slice(0, 10)}.csv`, [
        { key: "id", label: "Id" }, { key: "priority", label: "Priorité" }, { key: "title", label: "Action" }, { key: "owner", label: "Responsable" },
        { key: "due", label: "Échéance" }, { key: "deliverable", label: "Livrable" }, { key: "risk_ids", label: "Risques" }, { key: "control_ids", label: "Contrôles" },
        { key: "status", label: "Statut" }, { key: "progress", label: "Avancement %" },
      ], s.actions),
    },
  ];

  return (
    <div>
      <PageHeader title="Rapports et exportations" subtitle="Tous les documents sont générés à partir des données enregistrées au moment de l'export." icon={<FileDown className="h-5 w-5" />} />
      <Card className="mb-4 !border-brand-200 !bg-gradient-to-r from-brand-50 to-white">
        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
          <div className="rounded-xl bg-brand-800 p-2.5 text-brand-300"><Sparkles className="h-5 w-5" /></div>
          <div className="flex-1">
            <div className="font-bold text-brand-950">Rapport rédigé par Risk Advisor (IA)</div>
            <p className="text-sm text-slate-600">L'assistant rédige un rapport narratif de gestion des risques à partir des données réelles, puis l'exporte en PDF.</p>
          </div>
          <button className="btn-emerald" onClick={aiReport} disabled={!!busy}>
            {busy === "ai" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Générer le rapport IA
          </button>
        </div>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((it) => (
          <button key={it.key} onClick={() => run(it.key, it.fn)} disabled={!!busy} className="card group flex items-start gap-3 p-4 text-left transition hover:border-brand-400 disabled:opacity-60">
            <div className="rounded-xl bg-brand-50 p-2.5 text-brand-700 group-hover:bg-brand-800 group-hover:text-white">
              {busy === it.key ? <Loader2 className="h-5 w-5 animate-spin" /> : <it.icon className="h-5 w-5" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 font-semibold text-slate-900">
                {it.title}
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">{it.fmt}</span>
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{it.desc}</p>
            </div>
          </button>
        ))}
      </div>
      <Toast message={toast?.m ?? null} tone={toast?.t} onDone={() => setToast(null)} />
    </div>
  );
}
