"use client";
import Link from "next/link";
import { useMemo } from "react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line, Legend, LabelList,
} from "recharts";
import { LayoutDashboard, AlertOctagon, ShieldCheck, ListTodo, Bug, Landmark, ArrowRight, FileSearch } from "lucide-react";
import { useApi } from "@/lib/client";
import { PageHeader, Card, Kpi, LevelBadge, Spinner, ErrorBox, Badge, statusTone, Progress, DemoBadge } from "@/components/ui";
import { LEVELS, LEVEL_STYLE, levelFromScore } from "@/lib/scoring";
import { CATEGORY_COLORS, SERIES } from "@/lib/chart-colors";
import HeatMap from "@/components/HeatMap";

const MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

export default function Dashboard() {
  const { data, error, loading, reload } = useApi<any>("/api/snapshot");

  const derived = useMemo(() => {
    if (!data) return null;
    const risks = data.risks as any[];
    const byCat: Record<string, number> = {};
    risks.forEach((r) => (byCat[r.category] = (byCat[r.category] || 0) + 1));
    const catData = Object.entries(byCat).map(([name, value]) => ({ name, value }));
    const levelData = LEVELS.map((l) => ({ name: l, value: risks.filter((r) => r.level === l).length, fill: LEVEL_STYLE[l].hex }));
    // Évolution : dernière cotation connue de chaque risque à la fin de chaque mois
    const hist = data.history as any[];
    const months = Array.from(new Set(hist.map((h) => String(h.recorded_at).slice(0, 7)))).sort();
    const evo = months.map((m) => {
      const latest: Record<string, number> = {};
      hist.filter((h) => String(h.recorded_at).slice(0, 7) <= m).forEach((h) => (latest[h.risk_id] = h.score));
      const scores = Object.entries(latest).filter(([id]) => risks.some((r) => r.id === id)).map(([, s]) => s);
      const [y, mo] = m.split("-");
      return {
        month: `${MONTHS_FR[Number(mo) - 1]} ${y.slice(2)}`,
        "Score moyen": scores.length ? Number((scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)) : 0,
        "Score maximal": scores.length ? Math.max(...scores) : 0,
        critiques: scores.filter((s) => levelFromScore(s) === "Critique").length,
      };
    });
    const top5 = [...risks].sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).slice(0, 5);
    const pending = (data.actions as any[]).filter((a) => a.status !== "Terminé").sort((a, b) => a.priority.localeCompare(b.priority)).slice(0, 6);
    const ctrlStatus: Record<string, number> = {};
    (data.controls as any[]).forEach((c) => (ctrlStatus[c.status] = (ctrlStatus[c.status] || 0) + 1));
    return { catData, levelData, evo, top5, pending, ctrlStatus };
  }, [data]);

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data || !derived) return null;
  const k = data.kpis;
  const closureRate = data.anomalies.length ? Math.round((k.closedAnomalies / data.anomalies.length) * 100) : 0;

  return (
    <div>
      <PageHeader
        title="Dashboard exécutif"
        subtitle="Vue consolidée de l'exposition aux risques, du dispositif de contrôle interne et de l'avancement des actions correctives."
        icon={<LayoutDashboard className="h-5 w-5" />}
        actions={
          <Link href="/assistant" className="btn-emerald">
            Analyse IA de la situation <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Risques recensés" value={k.total} hint={`Score moyen ${k.avgScore.toFixed(1)} / 25`} icon={<LayoutDashboard className="h-5 w-5" />} />
        <Kpi label="Risques critiques" value={k.critical} hint={`${k.high} risques élevés`} icon={<AlertOctagon className="h-5 w-5" />} tone="red" />
        <Kpi label="Contrôles opérationnels" value={`${k.operationalControls}/${k.totalControls}`} hint={`${k.coveredRisks}/${k.total} risques couverts`} icon={<ShieldCheck className="h-5 w-5" />} tone="emerald" />
        <Kpi label="Actions en attente" value={k.pendingActions} hint={`Avancement moyen ${k.actionProgress} %`} icon={<ListTodo className="h-5 w-5" />} tone="amber" />
        <Kpi label="Anomalies ouvertes" value={k.openAnomalies} hint={`${k.overdueAnomalies} en retard`} icon={<Bug className="h-5 w-5" />} tone={k.overdueAnomalies ? "red" : "slate"} />
        <Kpi label="Maturité COSO" value={`${k.avgMaturity.toFixed(1)}/5`} hint={`${k.deficientPrinciples}/17 principes déficients`} icon={<Landmark className="h-5 w-5" />} tone="slate" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Répartition des risques par catégorie" subtitle="Nombre de risques au registre">
          <div className="h-56">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={derived.catData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2} stroke="#fff" strokeWidth={2} label={({ value }) => value}>
                  {derived.catData.map((d) => (
                    <Cell key={d.name} fill={CATEGORY_COLORS[d.name] || "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: any, n: any) => [`${v} risque(s)`, n]} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Répartition par niveau de criticité" subtitle="Seuils : 1–4 Faible · 5–9 Modéré · 10–15 Élevé · 16–25 Critique">
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={derived.levelData} margin={{ top: 18, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "#f1f5f9" }} formatter={(v: any) => [`${v} risque(s)`, "Nombre"]} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {derived.levelData.map((d) => (
                    <Cell key={d.name} fill={d.fill} />
                  ))}
                  <LabelList dataKey="value" position="top" style={{ fontSize: 12, fill: "#334155", fontWeight: 600 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Évolution des risques" subtitle="Dernière cotation P × G connue en fin de mois (historique de démonstration + modifications réelles)">
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={derived.evo} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#475569" }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 25]} ticks={[0, 5, 10, 15, 20, 25]} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: any, n: any) => [v, n]} labelFormatter={(l, p: any) => `${l} · ${p?.[0]?.payload?.critiques ?? 0} risque(s) critique(s)`} />
                <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="Score maximal" stroke={SERIES.secondary} strokeWidth={2} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="Score moyen" stroke={SERIES.primary} strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-3" title="Top 5 des risques prioritaires" actions={<Link href="/risques" className="text-xs font-semibold text-brand-700 hover:underline">Registre complet →</Link>}>
          <div className="-mx-4 overflow-x-auto sm:-mx-5">
            <table className="table-pro">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Risque</th>
                  <th>Catégorie</th>
                  <th className="text-center">P</th>
                  <th className="text-center">G</th>
                  <th>Criticité</th>
                  <th>Responsable</th>
                </tr>
              </thead>
              <tbody>
                {derived.top5.map((r: any, i: number) => (
                  <tr key={r.id}>
                    <td className="font-bold text-slate-400">{i + 1}</td>
                    <td>
                      <div className="font-semibold text-brand-900">
                        {r.id} · {r.title}
                      </div>
                    </td>
                    <td>
                      <span className="inline-flex items-center gap-1.5 text-xs">
                        <span className="h-2 w-2 rounded-full" style={{ background: CATEGORY_COLORS[r.category] }} />
                        {r.category}
                      </span>
                    </td>
                    <td className="text-center">{r.probability}</td>
                    <td className="text-center">{r.gravity}</td>
                    <td>
                      <LevelBadge level={r.level} score={r.score} />
                    </td>
                    <td className="max-w-[220px] text-xs text-slate-600">{r.owner}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card className="xl:col-span-2" title="Cartographie synthétique" actions={<Link href="/cartographie" className="text-xs font-semibold text-brand-700 hover:underline">Ouvrir →</Link>}>
          <HeatMap risks={data.risks} compact />
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Indicateurs de contrôle interne" subtitle="Calculés à partir des fiches de contrôle, du registre des anomalies et du diagnostic COSO">
          <div className="space-y-3 text-sm">
            <Indicator label="Couverture des risques par au moins un contrôle" value={Math.round((k.coveredRisks / Math.max(1, k.total)) * 100)} />
            <Indicator label="Contrôles opérationnels ou efficaces" value={Math.round((k.operationalControls / Math.max(1, k.totalControls)) * 100)} />
            <Indicator label="Taux de clôture des anomalies" value={closureRate} />
            <Indicator label="Avancement du plan d'action" value={k.actionProgress} />
            <Indicator label="Principes COSO non déficients" value={Math.round(((17 - k.deficientPrinciples) / 17) * 100)} />
          </div>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {Object.entries(derived.ctrlStatus).map(([s, n]) => (
              <Badge key={s} tone={statusTone(s)}>
                {s} : {n as number}
              </Badge>
            ))}
            <Link href="/dossiers" className="ml-auto inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:underline">
              <FileSearch className="h-3.5 w-3.5" /> {k.dossiersBlocked}/{k.dossiers} dossiers TPE suspendus
            </Link>
          </div>
        </Card>
        <Card title="Actions correctives en attente" actions={<Link href="/suivi" className="text-xs font-semibold text-brand-700 hover:underline">Plan d'action →</Link>}>
          <ul className="divide-y divide-slate-100">
            {derived.pending.map((a: any) => (
              <li key={a.id} className="flex items-center gap-3 py-2.5">
                <Badge tone={a.priority === "P1" ? "red" : a.priority === "P2" ? "amber" : "slate"}>{a.priority}</Badge>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-slate-800">
                    {a.id} · {a.title}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    {a.owner} · {a.due} {a.is_demo && <DemoBadge />}
                  </div>
                </div>
                <div className="w-28">
                  <Progress value={a.progress} />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function Indicator({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-slate-600">{label}</span>
      </div>
      <Progress value={value} />
    </div>
  );
}
