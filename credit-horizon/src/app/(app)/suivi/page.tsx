"use client";
import { useMemo, useState } from "react";
import { ClipboardList, Plus, Pencil, Trash2, Bug, Lightbulb, ListTodo, ArrowRight } from "lucide-react";
import { api, useApi, useUser } from "@/lib/client";
import { can, type Permission } from "@/lib/permissions";
import { PageHeader, Card, Spinner, ErrorBox, Badge, statusTone, DemoBadge, Toast, Progress, Empty } from "@/components/ui";
import EntityForm, { type FieldDef } from "@/components/EntityForm";

const ACTION_FIELDS: FieldDef[] = [
  { key: "title", label: "Intitulé de l'action", required: true, full: true },
  { key: "priority", label: "Priorité", type: "select", options: ["P1", "P2", "P3"] },
  { key: "status", label: "Statut", type: "select", options: ["À faire", "En cours", "Terminé", "Bloqué"] },
  { key: "owner", label: "Responsable", required: true },
  { key: "due", label: "Échéance", hint: "Ex. : Semaines 1 à 2, ou une date" },
  { key: "deliverable", label: "Livrable / preuve", full: true },
  { key: "risk_ids", label: "Risques traités" },
  { key: "control_ids", label: "Contrôles concernés" },
  { key: "progress", label: "Avancement (%)", type: "range", min: 0, max: 100 },
];
const RECO_FIELDS: FieldDef[] = [
  { key: "risk_id", label: "RISQUE", required: true, hint: "Ex. : R03" },
  { key: "status", label: "Statut", type: "select", options: ["À lancer", "En cours", "Mise en œuvre", "Abandonnée"] },
  { key: "coso_gap", label: "LACUNE COSO", type: "textarea", required: true },
  { key: "action", label: "ACTION CORRECTIVE", type: "textarea", required: true },
  { key: "owner", label: "RESPONSABLE", required: true },
  { key: "basis", label: "Fondement", type: "select", options: ["Constat", "Hypothèse"] },
  { key: "indicator", label: "INDICATEUR DE SUIVI", type: "textarea", required: true },
];
const ANOM_FIELDS: FieldDef[] = [
  { key: "detected_on", label: "Date de détection", type: "date", required: true },
  { key: "dossier_ref", label: "Dossier / référence" },
  { key: "nature", label: "Nature de l'anomalie", type: "textarea", required: true },
  { key: "severity", label: "Gravité", type: "select", options: ["Mineure", "Significative", "Majeure", "Critique"] },
  { key: "status", label: "Statut", type: "select", options: ["Ouverte", "En cours", "Clôturée"] },
  { key: "risk_id", label: "Risque lié", hint: "Ex. : R01" },
  { key: "control_id", label: "Contrôle lié", hint: "Ex. : C04" },
  { key: "owner", label: "Responsable du traitement", required: true },
  { key: "due_on", label: "Échéance de régularisation", type: "date" },
  { key: "escalation", label: "Niveau d'escalade (charte art. 11)", type: "select", options: ["1", "2", "3"] },
  { key: "resolution", label: "Résolution / preuve de clôture", type: "textarea" },
];

type Tab = "actions" | "recommendations" | "anomalies";

export default function SuiviPage() {
  const user = useUser();
  const [tab, setTab] = useState<Tab>("actions");
  const actions = useApi<any[]>("/api/data/actions");
  const recos = useApi<any[]>("/api/data/recommendations");
  const anomalies = useApi<any[]>("/api/data/anomalies");
  const [edit, setEdit] = useState<{ kind: Tab; row: any } | null>(null);
  const [toast, setToast] = useState<{ m: string; t?: "red" } | null>(null);
  const [filter, setFilter] = useState("");

  const perms: Record<Tab, { write: Permission; create: Permission }> = {
    actions: { write: "actions.write", create: "actions.write" },
    recommendations: { write: "recommendations.write", create: "recommendations.write" },
    anomalies: { write: "anomalies.write", create: "anomalies.create" },
  };
  const src = { actions, recommendations: recos, anomalies }[tab];
  const today = new Date().toISOString().slice(0, 10);

  const rows = useMemo(() => (src.data || []).filter((r) => !filter || r.status === filter), [src.data, filter]);

  async function remove(kind: Tab, id: string) {
    if (!confirm(`Supprimer ${id} ?`)) return;
    try {
      await api(`/api/data/${kind}/${id}`, { method: "DELETE" });
      setToast({ m: `${id} supprimé.` });
      src.reload();
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    }
  }

  const statuses = tab === "actions" ? ["À faire", "En cours", "Terminé", "Bloqué"] : tab === "recommendations" ? ["À lancer", "En cours", "Mise en œuvre", "Abandonnée"] : ["Ouverte", "En cours", "Clôturée"];
  const newRow =
    tab === "actions"
      ? { priority: "P2", status: "À faire", progress: 0 }
      : tab === "recommendations"
        ? { status: "À lancer", basis: "Constat" }
        : { detected_on: today, severity: "Significative", status: "Ouverte", escalation: "1" };

  return (
    <div>
      <PageHeader
        title="Suivi des recommandations et des anomalies"
        subtitle="Plan d'action correctif priorisé, chaînes de recommandations (Risque → Lacune COSO → Action → Responsable → Indicateur) et registre unique des anomalies et dérogations (contrôle C04)."
        icon={<ClipboardList className="h-5 w-5" />}
        actions={
          can(user.role, perms[tab].create) && (
            <button className="btn-primary" onClick={() => setEdit({ kind: tab, row: newRow })}>
              <Plus className="h-4 w-4" /> {tab === "actions" ? "Nouvelle action" : tab === "recommendations" ? "Nouvelle recommandation" : "Déclarer une anomalie"}
            </button>
          )
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {([
          ["actions", "Plan d'action", ListTodo, actions.data?.filter((a) => a.status !== "Terminé").length],
          ["recommendations", "Recommandations", Lightbulb, recos.data?.length],
          ["anomalies", "Anomalies", Bug, anomalies.data?.filter((a) => a.status !== "Clôturée").length],
        ] as const).map(([k, l, I, n]) => (
          <button key={k} onClick={() => { setTab(k); setFilter(""); }} className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold ${tab === k ? "bg-brand-800 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}>
            <I className="h-4 w-4" /> {l} {n !== undefined && <span className={`rounded-full px-1.5 text-[11px] ${tab === k ? "bg-white/20" : "bg-slate-100"}`}>{n}</span>}
          </button>
        ))}
        <select className="input ml-auto !w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">Tous statuts</option>
          {statuses.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      <Card>
        {src.loading && !src.data ? (
          <Spinner />
        ) : src.error ? (
          <ErrorBox message={src.error} onRetry={src.reload} />
        ) : !rows.length ? (
          <Empty text="Aucun élément." />
        ) : tab === "actions" ? (
          <div className="-mx-4 overflow-x-auto sm:-mx-5">
            <table className="table-pro min-w-[900px]">
              <thead><tr><th>Prio.</th><th>Action</th><th>Responsable</th><th>Échéance</th><th>Livrable</th><th>Liens</th><th>Statut</th><th className="w-36">Avancement</th><th /></tr></thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.id}>
                    <td><Badge tone={a.priority === "P1" ? "red" : a.priority === "P2" ? "amber" : "slate"}>{a.priority}</Badge></td>
                    <td className="max-w-[300px]"><b className="text-brand-800">{a.id}</b> {a.title} <div className="mt-1">{a.is_demo && <DemoBadge />}</div></td>
                    <td className="text-xs">{a.owner}</td>
                    <td className="whitespace-nowrap text-xs">{a.due}</td>
                    <td className="max-w-[200px] text-xs text-slate-500">{a.deliverable}</td>
                    <td className="text-xs">{a.risk_ids}<br /><span className="text-slate-400">{a.control_ids}</span></td>
                    <td><Badge tone={statusTone(a.status)}>{a.status}</Badge></td>
                    <td><Progress value={a.progress} /></td>
                    <td><RowActions kind="actions" row={a} perm={perms.actions.write} onEdit={() => setEdit({ kind: "actions", row: a })} onDelete={() => remove("actions", a.id)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : tab === "recommendations" ? (
          <div className="space-y-3">
            {rows.map((r) => (
              <div key={r.id} className="rounded-xl border border-slate-200 p-3">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <b className="text-brand-800">{r.id}</b>
                  <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                  <Badge tone={r.basis === "Constat" ? "brand" : "amber"}>{r.basis}</Badge>
                  {r.is_demo && <DemoBadge />}
                  <div className="ml-auto"><RowActions kind="recommendations" row={r} perm={perms.recommendations.write} onEdit={() => setEdit({ kind: "recommendations", row: r })} onDelete={() => remove("recommendations", r.id)} /></div>
                </div>
                <div className="grid gap-2 text-xs md:grid-cols-[110px_1fr_auto_1fr_auto_1fr_auto_1fr_auto_1fr] md:items-start">
                  {[["RISQUE", r.risk_id], ["LACUNE COSO", r.coso_gap], ["ACTION CORRECTIVE", r.action], ["RESPONSABLE", r.owner], ["INDICATEUR", r.indicator]].map(([k, v], i) => (
                    <div key={k} className="contents">
                      {i > 0 && <ArrowRight className="mx-auto hidden h-4 w-4 text-brand-500 md:block" />}
                      <div className="rounded-lg bg-slate-50 p-2">
                        <div className="text-[10px] font-bold tracking-wide text-brand-700">{k}</div>
                        <div className="text-slate-700">{v}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="-mx-4 overflow-x-auto sm:-mx-5">
            <table className="table-pro min-w-[980px]">
              <thead><tr><th>Id</th><th>Détectée</th><th>Dossier</th><th>Nature</th><th>Gravité</th><th>Risque / contrôle</th><th>Responsable</th><th>Échéance</th><th>Escalade</th><th>Statut</th><th /></tr></thead>
              <tbody>
                {rows.map((a) => {
                  const late = a.status !== "Clôturée" && a.due_on && a.due_on < today;
                  return (
                    <tr key={a.id}>
                      <td className="font-bold text-brand-800">{a.id}<div className="mt-1">{a.is_demo && <DemoBadge />}</div></td>
                      <td className="whitespace-nowrap text-xs">{a.detected_on}</td>
                      <td className="text-xs">{a.dossier_ref}</td>
                      <td className="max-w-[280px] text-xs">{a.nature}{a.resolution && <div className="mt-1 text-emerald-700">✓ {a.resolution}</div>}<div className="text-[10px] text-slate-400">Déclarée par {a.declared_by || "–"}</div></td>
                      <td><Badge tone={a.severity === "Critique" ? "red" : a.severity === "Majeure" ? "amber" : "slate"}>{a.severity}</Badge></td>
                      <td className="text-xs">{a.risk_id} {a.control_id && <span className="text-slate-400">/ {a.control_id}</span>}</td>
                      <td className="text-xs">{a.owner}</td>
                      <td className={`whitespace-nowrap text-xs ${late ? "font-bold text-red-600" : ""}`}>{a.due_on || "–"}{late && " (retard)"}</td>
                      <td><Badge tone={a.escalation === 3 ? "red" : a.escalation === 2 ? "amber" : "slate"}>N{a.escalation}</Badge></td>
                      <td><Badge tone={statusTone(a.status)}>{a.status}</Badge></td>
                      <td><RowActions kind="anomalies" row={a} perm={perms.anomalies.write} onEdit={() => setEdit({ kind: "anomalies", row: { ...a, escalation: String(a.escalation) } })} onDelete={() => remove("anomalies", a.id)} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {edit && (
        <EntityForm
          title={edit.row.id ? `Modifier ${edit.row.id}` : edit.kind === "anomalies" ? "Déclarer une anomalie" : "Nouvel élément"}
          fields={edit.kind === "actions" ? ACTION_FIELDS : edit.kind === "recommendations" ? RECO_FIELDS : ANOM_FIELDS}
          initial={edit.row}
          endpoint={`/api/data/${edit.kind}`}
          id={edit.row.id}
          onClose={() => setEdit(null)}
          onSaved={(r) => {
            setEdit(null);
            setToast({ m: `${r.id} enregistré.` });
            ({ actions, recommendations: recos, anomalies })[edit.kind].reload();
          }}
        />
      )}
      <Toast message={toast?.m ?? null} tone={toast?.t} onDone={() => setToast(null)} />
    </div>
  );

  function RowActions({ perm, onEdit, onDelete }: { kind: Tab; row: any; perm: Permission; onEdit: () => void; onDelete: () => void }) {
    if (!can(user.role, perm)) return null;
    return (
      <div className="flex gap-1">
        <button className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100" onClick={onEdit} title="Modifier"><Pencil className="h-4 w-4" /></button>
        <button className="rounded-lg p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600" onClick={onDelete} title="Supprimer"><Trash2 className="h-4 w-4" /></button>
      </div>
    );
  }
}
