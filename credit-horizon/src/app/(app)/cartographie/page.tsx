"use client";
import { useMemo, useState } from "react";
import { Grid3x3 } from "lucide-react";
import { useApi } from "@/lib/client";
import { PageHeader, Card, LevelBadge, Spinner, ErrorBox, Badge } from "@/components/ui";
import HeatMap from "@/components/HeatMap";
import { levelFromScore, LEVEL_TREATMENT, LEVELS } from "@/lib/scoring";
import { CATEGORY_COLORS } from "@/lib/chart-colors";

export default function CartographiePage() {
  const { data, error, loading, reload } = useApi<any[]>("/api/data/risks");
  const [cat, setCat] = useState("");
  const [sel, setSel] = useState<any | null>(null);
  const risks = useMemo(
    () => (data || []).map((r) => ({ ...r, score: Number(r.score), level: levelFromScore(Number(r.score)) })).filter((r) => !cat || r.category === cat),
    [data, cat],
  );

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div>
      <PageHeader
        title="Cartographie des risques"
        subtitle="Matrice thermique interactive 5 × 5 (probabilité × gravité). Chaque risque est positionné dans sa cellule ; cliquez pour afficher sa fiche."
        icon={<Grid3x3 className="h-5 w-5" />}
        actions={
          <select className="input !w-auto" value={cat} onChange={(e) => setCat(e.target.value)}>
            <option value="">Toutes catégories</option>
            {Object.keys(CATEGORY_COLORS).map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        }
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Card>
          <HeatMap risks={risks} onSelect={setSel} selected={sel?.id} />
        </Card>
        <div className="space-y-4">
          <Card title={sel ? `${sel.id} – ${sel.title}` : "Fiche du risque"}>
            {sel ? (
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <LevelBadge level={sel.level} score={sel.score} />
                  <Badge>{sel.category}</Badge>
                </div>
                <p className="text-slate-700">{sel.event}</p>
                <div className="rounded-xl bg-slate-50 p-3 text-xs">
                  <b>P = {sel.probability}</b> × <b>G = {sel.gravity}</b> = <b>{sel.score}</b>
                  <p className="mt-1 text-slate-600">{sel.justification}</p>
                </div>
                <p className="text-xs text-slate-600">
                  <b>Traitement attendu :</b> {LEVEL_TREATMENT[sel.level as keyof typeof LEVEL_TREATMENT]}
                </p>
                <p className="text-xs text-slate-600">
                  <b>Responsable :</b> {sel.owner}
                </p>
                <p className="text-xs text-slate-600">
                  <b>Contrôles :</b> {sel.control_ids || "aucun"}
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Sélectionnez un risque dans la matrice.</p>
            )}
          </Card>
          <Card title="Synthèse par zone">
            <ul className="space-y-2 text-sm">
              {[...LEVELS].reverse().map((l) => {
                const rs = risks.filter((r) => r.level === l);
                return (
                  <li key={l} className="flex items-start gap-2">
                    <LevelBadge level={l} />
                    <span className="flex-1 text-xs text-slate-600">{rs.length ? rs.sort((a, b) => b.score - a.score).map((r) => `${r.id} (${r.score})`).join(", ") : "aucun risque"}</span>
                  </li>
                );
              })}
            </ul>
          </Card>
        </div>
      </div>
      <Card className="mt-4" title="Classement des risques par criticité">
        <div className="-mx-4 overflow-x-auto sm:-mx-5">
          <table className="table-pro">
            <thead>
              <tr>
                <th>Rang</th>
                <th>Risque</th>
                <th className="text-center">P</th>
                <th className="text-center">G</th>
                <th>Criticité</th>
                <th>Traitement attendu</th>
              </tr>
            </thead>
            <tbody>
              {[...risks].sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).map((r, i) => (
                <tr key={r.id} className="cursor-pointer" onClick={() => setSel(r)}>
                  <td className="font-bold text-slate-400">{i + 1}</td>
                  <td className="font-medium">
                    {r.id} · {r.title}
                  </td>
                  <td className="text-center">{r.probability}</td>
                  <td className="text-center">{r.gravity}</td>
                  <td>
                    <LevelBadge level={r.level} score={r.score} />
                  </td>
                  <td className="text-xs text-slate-500">{LEVEL_TREATMENT[r.level as keyof typeof LEVEL_TREATMENT]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
