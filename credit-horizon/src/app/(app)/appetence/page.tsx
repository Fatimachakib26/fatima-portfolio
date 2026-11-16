"use client";
import { Gauge, CheckCircle2, AlertTriangle, Ban, ArrowUpRight } from "lucide-react";
import { useApi } from "@/lib/client";
import { PageHeader, Card, Spinner, ErrorBox, LevelBadge } from "@/components/ui";
import { APPETITE_LEVELS, APPETITE_BY_CATEGORY, CHARTER_PRINCIPLES, ESCALATION } from "@/lib/reference";
import { appetiteFromLevel, levelFromScore, LEVEL_TREATMENT } from "@/lib/scoring";

const STYLE = {
  acceptable: { box: "border-emerald-200 bg-emerald-50", icon: CheckCircle2, ic: "text-emerald-600", title: "text-emerald-900" },
  renforcee: { box: "border-amber-200 bg-amber-50", icon: AlertTriangle, ic: "text-amber-600", title: "text-amber-900" },
  inacceptable: { box: "border-red-200 bg-red-50", icon: Ban, ic: "text-red-600", title: "text-red-900" },
} as const;

export default function AppetencePage() {
  const { data, error, loading, reload } = useApi<any[]>("/api/data/risks");
  const risks = (data || []).map((r) => ({ ...r, score: Number(r.score), level: levelFromScore(Number(r.score)) }));
  return (
    <div>
      <PageHeader
        title="Charte d'appétence au risque"
        subtitle="Charte qualitative : elle fixe ce que Crédit Horizon accepte, accepte sous conditions ou refuse. Elle ne repose sur aucun modèle PD/LGD ; les seuils chiffrés éventuels seront fixés par la direction à partir de données réelles."
        icon={<Gauge className="h-5 w-5" />}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        {APPETITE_LEVELS.map((l) => {
          const st = STYLE[l.key];
          const I = st.icon;
          return (
            <div key={l.key} className={`rounded-2xl border p-5 ${st.box}`}>
              <div className={`mb-2 flex items-center gap-2 font-bold ${st.title}`}>
                <I className={`h-5 w-5 ${st.ic}`} /> {l.title}
              </div>
              <p className="mb-3 text-sm text-slate-700">{l.description}</p>
              <ul className="space-y-1 text-xs text-slate-700">
                {l.examples.map((e) => (
                  <li key={e} className="flex gap-1.5">
                    <span className={st.ic}>•</span> {e}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      <Card className="mt-4" title="Positionnement des risques du registre" subtitle="Lecture applicative : Faible/Modéré → acceptable sous contrôle ; Élevé → autorisation renforcée et mesure prioritaire ; Critique → hors appétence en l'état, renforcement immédiat">
        {loading && !data ? (
          <Spinner />
        ) : error ? (
          <ErrorBox message={error} onRetry={reload} />
        ) : (
          <div className="grid gap-3 md:grid-cols-3">
            {APPETITE_LEVELS.map((l) => {
              const st = STYLE[l.key];
              const rs = risks.filter((r) => appetiteFromLevel(r.level) === l.key).sort((a, b) => b.score - a.score);
              return (
                <div key={l.key} className={`rounded-xl border p-3 ${st.box}`}>
                  <div className={`mb-2 text-xs font-bold uppercase tracking-wide ${st.title}`}>{l.title}</div>
                  {rs.length ? (
                    <ul className="space-y-1.5">
                      {rs.map((r) => (
                        <li key={r.id} className="flex items-center gap-2 rounded-lg bg-white/80 px-2 py-1.5 text-xs">
                          <b>{r.id}</b>
                          <span className="flex-1 truncate" title={r.title}>{r.title}</span>
                          <LevelBadge level={r.level} score={r.score} />
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500">Aucun risque dans cette zone.</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
        <p className="mt-3 text-[11px] text-slate-500">Traitement attendu par niveau : {Object.entries(LEVEL_TREATMENT).map(([k, v]) => `${k} – ${v}`).join(" · ")}</p>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Principes généraux (article 3)">
          <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-700">
            {CHARTER_PRINCIPLES.map((p) => <li key={p}>{p}</li>)}
          </ol>
        </Card>
        <Card title="Mécanismes d'escalade (article 11)">
          <div className="space-y-2">
            {ESCALATION.map((e) => (
              <div key={e.level} className="flex gap-3 rounded-xl border border-slate-100 p-3">
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white ${e.level === 3 ? "bg-red-600" : e.level === 2 ? "bg-amber-500" : "bg-brand-600"}`}>N{e.level}</div>
                <div>
                  <div className="flex items-center gap-1 text-sm font-semibold text-slate-800">{e.title} <ArrowUpRight className="h-3.5 w-3.5 text-slate-400" /></div>
                  <p className="text-xs text-slate-600">{e.text}</p>
                </div>
              </div>
            ))}
            <p className="text-[11px] text-slate-400">Le délai de chaque niveau est fixé par la direction (non défini dans le cas).</p>
          </div>
        </Card>
      </div>

      <Card className="mt-4" title="Appétence par catégorie de risque (tableau 5.1)">
        <div className="-mx-4 overflow-x-auto sm:-mx-5">
          <table className="table-pro">
            <thead><tr><th>Catégorie</th><th>Appétence qualitative</th><th>Limites et situations inacceptables</th></tr></thead>
            <tbody>
              {APPETITE_BY_CATEGORY.map((c) => (
                <tr key={c.category}>
                  <td className="font-semibold">{c.category}</td>
                  <td className="text-sm text-slate-700">{c.appetite}</td>
                  <td className="text-sm text-red-800">{c.limits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
