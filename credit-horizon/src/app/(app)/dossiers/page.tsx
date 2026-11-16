"use client";
import Link from "next/link";
import { FileSearch, Plus } from "lucide-react";
import { useApi, useUser, fmtMAD, fmtDate } from "@/lib/client";
import { can } from "@/lib/permissions";
import { PageHeader, Card, Spinner, ErrorBox, Badge, statusTone, DemoBadge, Empty, Progress } from "@/components/ui";

export default function DossiersPage() {
  const user = useUser();
  const { data, error, loading, reload } = useApi<any[]>("/api/dossiers");
  return (
    <div>
      <PageHeader
        title="Analyse intelligente des dossiers TPE"
        subtitle="Vérification de la complétude documentaire (contrôle C01), détection des informations manquantes et des incohérences, points de vigilance et synthèse d'analyse. Aucune décision d'octroi n'est produite par la plateforme."
        icon={<FileSearch className="h-5 w-5" />}
        actions={
          can(user.role, "dossiers.write") && (
            <Link href="/dossiers/nouveau" className="btn-primary">
              <Plus className="h-4 w-4" /> Nouveau dossier
            </Link>
          )
        }
      />
      <Card>
        {loading && !data ? (
          <Spinner />
        ) : error ? (
          <ErrorBox message={error} onRetry={reload} />
        ) : !data?.length ? (
          <Empty text="Aucun dossier enregistré." />
        ) : (
          <div className="-mx-4 overflow-x-auto sm:-mx-5">
            <table className="table-pro min-w-[880px]">
              <thead>
                <tr>
                  <th>Référence</th>
                  <th>Entreprise</th>
                  <th>Financement</th>
                  <th>Complétude</th>
                  <th>Constats</th>
                  <th>Statut de l'analyse</th>
                  <th>Saisi par</th>
                </tr>
              </thead>
              <tbody>
                {data.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <Link href={`/dossiers/${d.id}`} className="font-bold text-brand-800 hover:underline">
                        {d.id}
                      </Link>
                      <div className="mt-1">{d.is_demo && <DemoBadge />}</div>
                    </td>
                    <td>
                      <div className="font-semibold">{d.company?.name}</div>
                      <div className="text-xs text-slate-500">
                        {d.company?.sector} · {d.company?.city}
                      </div>
                    </td>
                    <td className="text-xs">
                      <div className="font-semibold text-slate-800">{fmtMAD(d.request?.amount)}</div>
                      {d.request?.product} · {d.request?.duration_months} mois
                    </td>
                    <td className="w-40">
                      <Progress value={d.analysis?.completeness?.rate ?? 0} />
                    </td>
                    <td className="text-xs">
                      <div className="flex flex-wrap gap-1">
                        <Badge tone={d.analysis?.inconsistencies?.length ? "red" : "slate"}>{d.analysis?.inconsistencies?.length ?? 0} incohérence(s)</Badge>
                        <Badge tone={d.analysis?.vigilance?.length ? "amber" : "slate"}>{d.analysis?.vigilance?.length ?? 0} vigilance</Badge>
                      </div>
                    </td>
                    <td>
                      <Badge tone={statusTone(d.status)}>{d.status}</Badge>
                    </td>
                    <td className="text-xs text-slate-500">
                      {d.created_by}
                      <br />
                      {fmtDate(d.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
