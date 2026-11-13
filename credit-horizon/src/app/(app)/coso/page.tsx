"use client";
import { useState } from "react";
import { Landmark, Pencil } from "lucide-react";
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip } from "recharts";
import { useApi, useUser, splitIds } from "@/lib/client";
import { can } from "@/lib/permissions";
import { PageHeader, Card, Spinner, ErrorBox, Badge, Toast, ReadOnlyNotice, DemoBadge } from "@/components/ui";
import EntityForm, { type FieldDef } from "@/components/EntityForm";

const COMP_FIELDS: FieldDef[] = [
  { key: "findings", label: "Constats", type: "textarea" },
  { key: "gaps", label: "Lacunes", type: "textarea" },
  { key: "risk_ids", label: "Risques associés", hint: "Ex. : R03, R07" },
  { key: "owner", label: "Responsables" },
  { key: "recommendations", label: "Recommandations", type: "textarea" },
  { key: "indicators", label: "Indicateurs de suivi", type: "textarea" },
  { key: "maturity", label: "Maturité (1 = initiale, 5 = optimisée)", type: "range", min: 1, max: 5 },
];
const PRIN_FIELDS: FieldDef[] = [
  { key: "nature", label: "Nature", type: "select", options: ["Constat", "Hypothèse à vérifier", "Constat et hypothèse"] },
  { key: "assessment", label: "Appréciation", type: "select", options: ["Non évalué", "Déficient", "Partiel", "Satisfaisant"] },
  { key: "diagnostic", label: "Diagnostic", type: "textarea" },
  { key: "risk_ids", label: "Risques associés" },
];
const ASSESS_TONE: Record<string, "red" | "amber" | "emerald" | "slate"> = { Déficient: "red", Partiel: "amber", Satisfaisant: "emerald", "Non évalué": "slate" };
const COMP_COLORS = ["#0a4d38", "#0f7a58", "#10b981", "#2a78d6", "#6250d6"];

export default function CosoPage() {
  const user = useUser();
  const canWrite = can(user.role, "coso.write");
  const { data, error, loading, reload } = useApi<{ components: any[]; principles: any[] }>("/api/coso");
  const [active, setActive] = useState(1);
  const [editComp, setEditComp] = useState<any | null>(null);
  const [editPrin, setEditPrin] = useState<any | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;
  const comp = data.components.find((c) => c.id === active)!;
  const principles = data.principles.filter((p) => p.component_id === active);
  const counts = ["Déficient", "Partiel", "Satisfaisant", "Non évalué"].map((a) => ({ a, n: data.principles.filter((p) => p.assessment === a).length }));
  const radar = data.components.map((c) => ({ comp: c.name.replace("Information et communication", "Information & comm."), Maturité: c.maturity }));

  return (
    <div>
      <PageHeader
        title="Diagnostic COSO 2013"
        subtitle="Cinq composantes et dix-sept principes. Les appréciations sont provisoires et distinguent les constats (faits du cas) des hypothèses à vérifier."
        icon={<Landmark className="h-5 w-5" />}
      />
      {!canWrite && <ReadOnlyNotice text="Consultation seule : le diagnostic COSO est mis à jour par le contrôle interne et l'administrateur." />}

      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <Card title="Maturité par composante" subtitle="Échelle 1 (initiale) à 5 (optimisée)" className="lg:col-span-1">
          <div className="h-60">
            <ResponsiveContainer>
              <RadarChart data={radar} outerRadius="70%">
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="comp" tick={{ fontSize: 10, fill: "#475569" }} />
                <PolarRadiusAxis domain={[0, 5]} tickCount={6} tick={{ fontSize: 9, fill: "#94a3b8" }} />
                <Radar dataKey="Maturité" stroke="#0f7a58" fill="#10b981" fillOpacity={0.25} strokeWidth={2} dot={{ r: 4 }} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Appréciation des 17 principes" className="lg:col-span-2">
          <div className="mb-4 flex flex-wrap gap-2">
            {counts.map(({ a, n }) => (
              <Badge key={a} tone={ASSESS_TONE[a]}>
                {a} : {n}
              </Badge>
            ))}
            <Badge tone="brand">Constats : {data.principles.filter((p) => p.nature.startsWith("Constat")).length}</Badge>
            <Badge tone="slate">Hypothèses à vérifier : {data.principles.filter((p) => p.nature === "Hypothèse à vérifier").length}</Badge>
          </div>
          <div className="grid grid-cols-6 gap-1.5 sm:grid-cols-9 lg:grid-cols-[repeat(17,minmax(0,1fr))]">
            {data.principles.map((p) => (
              <button
                key={p.id}
                onClick={() => setActive(p.component_id)}
                title={`${p.id} – ${p.title} : ${p.assessment}`}
                className={`rounded-lg py-2 text-center text-[11px] font-bold ${
                  p.assessment === "Déficient" ? "bg-red-100 text-red-700" : p.assessment === "Partiel" ? "bg-amber-100 text-amber-800" : p.assessment === "Satisfaisant" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                } ${p.component_id === active ? "ring-2 ring-brand-700" : ""}`}
              >
                {p.id}
              </button>
            ))}
          </div>
          <div className="mt-2 flex">
            {data.components.map((c, i) => (
              <div key={c.id} className="h-1.5 rounded-full" style={{ flex: data.principles.filter((p) => p.component_id === c.id).length, background: COMP_COLORS[i], marginRight: 3 }} title={c.name} />
            ))}
          </div>
        </Card>
      </div>

      <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
        {data.components.map((c) => (
          <button
            key={c.id}
            onClick={() => setActive(c.id)}
            className={`whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-semibold transition ${active === c.id ? "bg-brand-800 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"}`}
          >
            {c.id}. {c.name}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
        <Card
          title={`${comp.id}. ${comp.name} (${comp.principles})`}
          subtitle={comp.question}
          actions={canWrite && <button className="btn-ghost !py-1.5 text-xs" onClick={() => setEditComp(comp)}><Pencil className="h-3.5 w-3.5" /> Modifier</button>}
        >
          <div className="mb-3 flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Maturité</span>
            {[1, 2, 3, 4, 5].map((n) => (
              <span key={n} className={`h-2.5 w-8 rounded-full ${n <= comp.maturity ? "bg-brand-600" : "bg-slate-200"}`} />
            ))}
            <span className="text-sm font-bold">{comp.maturity}/5</span>
            {comp.is_demo && <DemoBadge />}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Block label="Constats" text={comp.findings} />
            <Block label="Lacunes identifiées" text={comp.gaps} tone="red" />
            <div>
              <div className="label">Risques associés</div>
              <div className="flex flex-wrap gap-1">{splitIds(comp.risk_ids).map((r) => <Badge key={r} tone="brand">{r}</Badge>)}</div>
            </div>
            <Block label="Responsables" text={comp.owner} />
            <Block label="Recommandations" text={comp.recommendations} tone="emerald" />
            <Block label="Indicateurs de suivi" text={comp.indicators} />
          </div>
        </Card>
        <Card title="Principes de la composante">
          <ul className="space-y-3">
            {principles.map((p) => (
              <li key={p.id} className="rounded-xl border border-slate-100 p-3">
                <div className="flex items-start gap-2">
                  <span className="rounded-md bg-brand-800 px-1.5 py-0.5 text-[11px] font-bold text-white">{p.id}</span>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-slate-800">{p.title}</div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <Badge tone={ASSESS_TONE[p.assessment]}>{p.assessment}</Badge>
                      <Badge tone={p.nature === "Hypothèse à vérifier" ? "slate" : "violet"}>{p.nature}</Badge>
                      {splitIds(p.risk_ids).map((r) => <Badge key={r} tone="brand">{r}</Badge>)}
                    </div>
                    <p className="mt-1.5 text-xs text-slate-600">{p.diagnostic}</p>
                  </div>
                  {canWrite && (
                    <button className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-brand-700" onClick={() => setEditPrin(p)} title="Modifier">
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {editComp && (
        <EntityForm title={`Modifier – ${editComp.name}`} fields={COMP_FIELDS} initial={editComp} endpoint="/api/coso/components" id={editComp.id}
          onClose={() => setEditComp(null)} onSaved={() => { setEditComp(null); setToast("Composante mise à jour."); reload(); }} />
      )}
      {editPrin && (
        <EntityForm title={`Modifier ${editPrin.id} – ${editPrin.title}`} fields={PRIN_FIELDS} initial={editPrin} endpoint="/api/coso/principles" id={editPrin.id}
          onClose={() => setEditPrin(null)} onSaved={() => { setEditPrin(null); setToast("Principe mis à jour."); reload(); }} />
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}

function Block({ label, text, tone }: { label: string; text: string; tone?: "red" | "emerald" }) {
  return (
    <div className={tone === "red" ? "rounded-xl bg-red-50/60 p-3" : tone === "emerald" ? "rounded-xl bg-emerald-50/60 p-3" : ""}>
      <div className="label">{label}</div>
      <p className="whitespace-pre-line text-sm text-slate-700">{text || "–"}</p>
    </div>
  );
}
