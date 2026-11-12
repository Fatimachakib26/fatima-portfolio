"use client";
import { useMemo, useState } from "react";
import { ShieldCheck, Plus, Pencil, Trash2, Search } from "lucide-react";
import { api, useApi, useUser, splitIds } from "@/lib/client";
import { can } from "@/lib/permissions";
import { PageHeader, Card, Spinner, ErrorBox, Badge, statusTone, DemoBadge, Toast, ReadOnlyNotice, LevelBadge } from "@/components/ui";
import EntityForm, { type FieldDef } from "@/components/EntityForm";
import { levelFromScore } from "@/lib/scoring";

const FIELDS: FieldDef[] = [
  { key: "name", label: "Intitulé du contrôle", required: true, full: true },
  { key: "nature", label: "Type de contrôle", type: "select", options: ["Préventif", "Détectif", "Correctif", "Détectif et correctif"] },
  { key: "status", label: "Statut", type: "select", options: ["À concevoir", "En déploiement", "Opérationnel", "Efficace", "Déficient"] },
  { key: "objective", label: "Objectif du contrôle", type: "textarea", required: true },
  { key: "risk_ids", label: "Risques couverts", hint: "Ex. : R01, R08" },
  { key: "owner", label: "Responsable", required: true },
  { key: "procedure", label: "Description de la procédure", type: "textarea" },
  { key: "supervision", label: "Supervision" },
  { key: "frequency", label: "Fréquence", required: true },
  { key: "evidence", label: "Preuve attendue", type: "textarea" },
  { key: "indicator", label: "Indicateur de performance", type: "textarea" },
  { key: "anomaly_treatment", label: "Traitement des anomalies", type: "textarea" },
  { key: "last_review", label: "Dernière revue", type: "date" },
];
const EMPTY = Object.fromEntries(FIELDS.map((f) => [f.key, f.options ? f.options[0] : ""]));

export default function ControlsPage() {
  const user = useUser();
  const canWrite = can(user.role, "controls.write");
  const { data, error, loading, reload } = useApi<any[]>("/api/data/controls");
  const risks = useApi<any[]>("/api/data/risks");
  const [edit, setEdit] = useState<any | null>(null);
  const [toast, setToast] = useState<{ m: string; t?: "red" } | null>(null);
  const [search, setSearch] = useState("");

  const list = useMemo(() => (data || []).filter((c) => !search || JSON.stringify(c).toLowerCase().includes(search.toLowerCase())), [data, search]);

  async function remove(c: any) {
    if (!confirm(`Supprimer la fiche ${c.id} ?`)) return;
    try {
      await api(`/api/data/controls/${c.id}`, { method: "DELETE" });
      setToast({ m: `Contrôle ${c.id} supprimé.` });
      reload();
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    }
  }

  return (
    <div>
      <PageHeader
        title="Contrôle interne – fiches de contrôle"
        subtitle="Huit contrôles organisationnels (C01 à C08) : objectif, risque couvert, type, procédure, responsable, fréquence, preuve, indicateur et traitement des anomalies."
        icon={<ShieldCheck className="h-5 w-5" />}
        actions={canWrite && <button className="btn-primary" onClick={() => setEdit({ ...EMPTY })}><Plus className="h-4 w-4" /> Nouvelle fiche</button>}
      />
      {!canWrite && <ReadOnlyNotice text="Consultation seule : les fiches de contrôle sont gérées par le contrôle interne et l'administrateur." />}

      {risks.data && data && (
        <Card className="mb-4" title="Matrice de couverture risques × contrôles" subtitle="● = le contrôle couvre le risque. Un risque couvert par un seul contrôle constitue un point de dépendance.">
          <div className="-mx-4 overflow-x-auto sm:-mx-5">
            <table className="table-pro">
              <thead>
                <tr>
                  <th>Risque</th>
                  {data.map((c) => <th key={c.id} className="text-center">{c.id}</th>)}
                  <th className="text-center">Couverture</th>
                </tr>
              </thead>
              <tbody>
                {risks.data.map((r) => {
                  const n = data.filter((c) => splitIds(c.risk_ids).includes(r.id)).length;
                  return (
                    <tr key={r.id}>
                      <td className="whitespace-nowrap"><b>{r.id}</b> <span className="text-xs text-slate-500">{r.title.slice(0, 48)}{r.title.length > 48 ? "…" : ""}</span> <LevelBadge level={levelFromScore(Number(r.score))} /></td>
                      {data.map((c) => <td key={c.id} className="text-center text-brand-700">{splitIds(c.risk_ids).includes(r.id) ? "●" : ""}</td>)}
                      <td className="text-center">
                        <Badge tone={n === 0 ? "red" : n === 1 ? "amber" : "emerald"}>{n === 0 ? "Non couvert" : n === 1 ? "1 – dépendance" : `${n} contrôles`}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <div className="mb-3 relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input className="input pl-9" placeholder="Rechercher une fiche…" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      {loading && !data ? (
        <Spinner />
      ) : error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {list.map((c) => (
            <Card
              key={c.id}
              title={<span><span className="text-brand-600">{c.id}</span> · {c.name}</span>}
              actions={
                canWrite && (
                  <div className="flex gap-1">
                    <button className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100" onClick={() => setEdit(c)} title="Modifier"><Pencil className="h-4 w-4" /></button>
                    <button className="rounded-lg p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600" onClick={() => remove(c)} title="Supprimer"><Trash2 className="h-4 w-4" /></button>
                  </div>
                )
              }
            >
              <div className="mb-3 flex flex-wrap gap-1.5">
                <Badge tone="violet">{c.nature}</Badge>
                <Badge tone={statusTone(c.status)}>{c.status}</Badge>
                {splitIds(c.risk_ids).map((r) => <Badge key={r} tone="brand">{r}</Badge>)}
                {c.is_demo && <DemoBadge />}
              </div>
              <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-[150px_1fr]">
                {[
                  ["Objectif", c.objective],
                  ["Procédure", c.procedure],
                  ["Responsable", c.owner],
                  ["Supervision", c.supervision],
                  ["Fréquence", c.frequency],
                  ["Preuve attendue", c.evidence],
                  ["Indicateur", c.indicator],
                  ["Traitement des anomalies", c.anomaly_treatment],
                  ["Dernière revue", c.last_review || "–"],
                ].map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">{k}</dt>
                    <dd className="text-slate-700">{v || "–"}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          ))}
        </div>
      )}
      {edit && (
        <EntityForm
          title={edit.id ? `Modifier ${edit.id}` : "Nouvelle fiche de contrôle"}
          fields={FIELDS}
          initial={{ ...EMPTY, ...edit, last_review: edit.last_review || "" }}
          endpoint="/api/data/controls"
          id={edit.id}
          onClose={() => setEdit(null)}
          onSaved={(r) => {
            setEdit(null);
            setToast({ m: `Fiche ${r.id} enregistrée.` });
            reload();
          }}
        />
      )}
      <Toast message={toast?.m ?? null} tone={toast?.t} onDone={() => setToast(null)} />
    </div>
  );
}
