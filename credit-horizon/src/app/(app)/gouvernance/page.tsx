"use client";
import { Network, CheckCircle2, XCircle, KeyRound } from "lucide-react";
import { PageHeader, Card, Badge } from "@/components/ui";
import { RACI_ACTORS, RACI_ACTIVITIES, DELEGATION_MATRIX, segregationCheck, type RaciCode } from "@/lib/reference";
import { ROLES, permissionMatrix } from "@/lib/permissions";

const CODE_STYLE: Record<RaciCode, string> = {
  R: "bg-brand-600 text-white",
  A: "bg-brand-950 text-white",
  "A/R": "bg-gradient-to-br from-brand-950 to-brand-600 text-white",
  C: "bg-sky-100 text-sky-800",
  I: "bg-slate-100 text-slate-600",
  "–": "text-slate-300",
};
const BLOCK_TONE: Record<string, string> = {
  Constitution: "bg-sky-50 text-sky-800",
  "Analyse / contrôle": "bg-violet-50 text-violet-800",
  Autorisation: "bg-amber-50 text-amber-800",
  Exécution: "bg-emerald-50 text-emerald-800",
  Suivi: "bg-slate-100 text-slate-700",
  Pilotage: "bg-brand-50 text-brand-800",
};
const PERM_LABEL: Record<string, string> = {
  "risks.write": "Modifier le registre des risques",
  "risks.delete": "Supprimer un risque",
  "controls.write": "Gérer les fiches de contrôle",
  "coso.write": "Mettre à jour le diagnostic COSO",
  "actions.write": "Piloter le plan d'action",
  "recommendations.write": "Gérer les recommandations",
  "anomalies.create": "Déclarer une anomalie",
  "anomalies.write": "Traiter / clôturer une anomalie",
  "dossiers.write": "Saisir les dossiers TPE",
  "appetite.write": "Approuver la charte d'appétence",
  "users.manage": "Gérer les utilisateurs",
  "audit.view": "Consulter le journal d'audit",
  "demo.reset": "Réinitialiser les données",
};

export default function GouvernancePage() {
  const check = segregationCheck();
  const groups = Array.from(new Set(RACI_ACTORS.map((a) => a.group)));
  const matrix = permissionMatrix();
  return (
    <div>
      <PageHeader
        title="Gouvernance et matrice RACI"
        subtitle="Responsabilités des acteurs sur les 14 activités du processus d'octroi et de suivi : R = Responsible (réalise), A = Accountable (valide, responsabilité finale), C = Consulted, I = Informed."
        icon={<Network className="h-5 w-5" />}
      />
      <Card title="Matrice RACI des décisions">
        <div className="-mx-4 overflow-x-auto sm:-mx-5">
          <table className="table-pro min-w-[860px]">
            <thead>
              <tr>
                <th rowSpan={2}>Activité</th>
                <th rowSpan={2}>Bloc</th>
                {groups.map((g) => (
                  <th key={g} colSpan={RACI_ACTORS.filter((a) => a.group === g).length} className="!border-b-0 text-center !text-brand-800">
                    {g}
                  </th>
                ))}
              </tr>
              <tr>
                {RACI_ACTORS.map((a) => (
                  <th key={a.key} className="!top-[37px] whitespace-normal text-center !normal-case !tracking-normal">
                    {a.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {RACI_ACTIVITIES.map((a) => (
                <tr key={a.n}>
                  <td className="font-medium">
                    {a.n}. {a.activity}
                  </td>
                  <td>
                    <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${BLOCK_TONE[a.block]}`}>{a.block}</span>
                  </td>
                  {RACI_ACTORS.map((x) => (
                    <td key={x.key} className="text-center">
                      <span className={`inline-flex min-w-[34px] justify-center rounded-md px-1.5 py-1 text-xs font-bold ${CODE_STYLE[a.roles[x.key]]}`}>{a.roles[x.key]}</span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-600">
          {(["R", "A", "A/R", "C", "I"] as RaciCode[]).map((c) => (
            <span key={c} className="inline-flex items-center gap-1.5">
              <span className={`rounded px-1.5 py-0.5 font-bold ${CODE_STYLE[c]}`}>{c}</span>
              {c === "R" ? "Responsible – réalise" : c === "A" ? "Accountable – valide" : c === "A/R" ? "Réalise et valide" : c === "C" ? "Consulted – consulté" : "Informed – informé"}
            </span>
          ))}
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Contrôle automatique de la séparation des tâches" subtitle="Vérifié par la plateforme à partir de la matrice">
          <div className={`mb-3 flex items-center gap-2 rounded-xl p-3 text-sm font-semibold ${check.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`}>
            {check.ok ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
            {check.ok ? "Séparation des tâches respectée : aucun acteur ne cumule constitution, analyse et autorisation." : "Conflit de séparation des tâches détecté."}
          </div>
          <ul className="space-y-1.5 text-sm">
            <li className="flex items-center gap-2">
              {check.singleA.every((s) => s.count === 1) ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-red-600" />}
              Une seule responsabilité finale (A) par activité : {check.singleA.filter((s) => s.count === 1).length}/14
            </li>
            {check.actors.map((a) => (
              <li key={a.actor} className="flex items-center gap-2 text-xs">
                {a.conflict ? <XCircle className="h-4 w-4 text-red-600" /> : <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
                <span className="w-56 font-medium">{a.actor}</span>
                <span className="text-slate-500">R/A sur : {a.blocks.join(", ") || "aucun bloc critique"}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">
            L'avis de la fonction risques (activité 6) et l'autorisation (activité 7) sont distincts ; le décaissement (8) relève de la finance, la direction étant seulement informée, ce qui évite de cumuler autorisation et exécution.
          </p>
        </Card>
        <Card title="Délégations d'autorisation" subtitle="Format Réalise / Valide / Est informé (rapport, tableau 4.6)">
          <div className="space-y-2">
            {DELEGATION_MATRIX.map((d) => (
              <div key={d.decision} className="rounded-xl border border-slate-100 p-3 text-xs">
                <div className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-brand-900">
                  <KeyRound className="h-4 w-4 text-brand-500" /> {d.decision}
                </div>
                <div className="grid gap-1 sm:grid-cols-3">
                  <div><Badge tone="brand">Réalise</Badge> <span className="text-slate-600">{d.realise}</span></div>
                  <div><Badge tone="amber">Valide</Badge> <span className="text-slate-600">{d.valide}</span></div>
                  <div><Badge>Informé</Badge> <span className="text-slate-600">{d.informe}</span></div>
                </div>
              </div>
            ))}
            <p className="text-[11px] text-slate-400">Les plafonds chiffrés de délégation ne sont pas fournis par le cas ; ils doivent être fixés par la direction générale (matrice des pouvoirs – action A01).</p>
          </div>
        </Card>
      </div>

      <Card className="mt-4" title="Traduction applicative : droits par rôle" subtitle="Les permissions de la plateforme appliquent la séparation des tâches (contrôle C03 – droits d'accès définis par rôle)">
        <div className="-mx-4 overflow-x-auto sm:-mx-5">
          <table className="table-pro min-w-[720px]">
            <thead>
              <tr>
                <th>Droit</th>
                {ROLES.map((r) => <th key={r.id} className="text-center">{r.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {Object.entries(matrix).map(([perm, roles]) => (
                <tr key={perm}>
                  <td className="text-sm">{PERM_LABEL[perm] ?? perm}</td>
                  {ROLES.map((r) => (
                    <td key={r.id} className="text-center">
                      {roles.includes(r.id) ? <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-600" /> : <span className="text-slate-300">–</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
