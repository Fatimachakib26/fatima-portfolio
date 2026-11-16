"use client";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdownLite from "./Markdown";
import { FileSearch, Save, Trash2, Sparkles, AlertTriangle, CheckCircle2, Info, ShieldAlert, ArrowLeft, Loader2, Bug } from "lucide-react";
import { api, useUser } from "@/lib/client";
import { can } from "@/lib/permissions";
import { analyzeDossier, CHECKLIST, PRODUCTS, GUARANTEE_TYPES, isRequired, type DossierInput, type Finding } from "@/lib/dossier-analysis";
import { PageHeader, Card, Field, Badge, statusTone, Toast, DemoBadge, ReadOnlyNotice, Progress } from "./ui";
import { streamAdvisor } from "@/lib/advisor-client";

const EMPTY: DossierInput = {
  company: { name: "", legal_form: "SARL", rc_number: "", ice: "", creation_date: "", sector: "", activity: "", city: "", manager_name: "", employees: "", name_on_documents: "" },
  request: { product: "Crédit d'investissement", amount: "", duration_months: "", purpose: "" },
  financials: { fiscal_year: "", revenue_n: "", revenue_n1: "", revenue_bank: "", net_result: "", equity: "", existing_debt: "", existing_monthly_installments: "" },
  documents: Object.fromEntries(CHECKLIST.map((c) => [c.key, ""])),
  guarantees: { type: "Aucune", value: "", description: "" },
  observations: "",
};

export default function DossierEditor({ existing }: { existing?: any }) {
  const user = useUser();
  const router = useRouter();
  const editable = can(user.role, "dossiers.write");
  const [d, setD] = useState<DossierInput>(() =>
    existing
      ? {
          company: { ...EMPTY.company, ...existing.company },
          request: { ...EMPTY.request, ...existing.request },
          financials: { ...EMPTY.financials, ...existing.financials },
          documents: { ...EMPTY.documents, ...existing.documents },
          guarantees: { ...EMPTY.guarantees, ...existing.guarantees },
          observations: existing.observations || "",
        }
      : EMPTY,
  );
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ m: string; t?: "red" } | null>(null);
  const [ai, setAi] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const analysis = useMemo(() => analyzeDossier(d), [d]);

  const setC = (k: string) => (e: any) => setD({ ...d, company: { ...d.company, [k]: e.target.value } });
  const setR = (k: string) => (e: any) => setD({ ...d, request: { ...d.request, [k]: e.target.value } });
  const setF = (k: string) => (e: any) => setD({ ...d, financials: { ...d.financials, [k]: e.target.value } });
  const setG = (k: string) => (e: any) => setD({ ...d, guarantees: { ...d.guarantees, [k]: e.target.value } });
  const setDoc = (k: string, v: string) => setD({ ...d, documents: { ...d.documents, [k]: v as any } });

  async function save() {
    setSaving(true);
    try {
      const r = await api(existing ? `/api/dossiers/${existing.id}` : "/api/dossiers", { method: existing ? "PUT" : "POST", json: d });
      setToast({ m: `Dossier ${r.id} enregistré et analysé : ${r.status}.` });
      if (!existing) router.push(`/dossiers/${r.id}`);
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!existing || !confirm(`Supprimer le dossier ${existing.id} ?`)) return;
    try {
      await api(`/api/dossiers/${existing.id}`, { method: "DELETE" });
      router.push("/dossiers");
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    }
  }

  async function declareAnomaly() {
    if (!existing) return setToast({ m: "Enregistrez d'abord le dossier.", t: "red" });
    const first = analysis.inconsistencies[0] || null;
    const nature = analysis.completeness.missingDocs.length
      ? `Dossier incomplet – pièces manquantes : ${analysis.completeness.missingDocs.join(" ; ")}`
      : first
        ? `Incohérence : ${first.message}`
        : "Anomalie relevée lors de l'analyse du dossier";
    try {
      const today = new Date().toISOString().slice(0, 10);
      const r = await api("/api/data/anomalies", {
        method: "POST",
        json: { detected_on: today, dossier_ref: existing.id, nature: nature.slice(0, 1900), severity: analysis.inconsistencies.some((i) => i.severity === "alerte") ? "Majeure" : "Significative", risk_id: "R01", control_id: "C01", owner: "Fonction risques", due_on: "", status: "Ouverte", escalation: 1, resolution: "" },
      });
      setToast({ m: `Anomalie ${r.id} inscrite au registre (C04).` });
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    }
  }

  async function aiSynthesis() {
    if (!existing) return setToast({ m: "Enregistrez d'abord le dossier pour que l'IA travaille sur les données enregistrées.", t: "red" });
    setAi("");
    setAiLoading(true);
    try {
      await streamAdvisor(
        [{ role: "user", content: `Rédige une synthèse d'analyse professionnelle du dossier ${existing.id} : complétude documentaire, informations manquantes, incohérences, points de vigilance, risques du registre concernés et contrôles applicables, puis les diligences à mener avant l'avis de la fonction risques. Rappelle qu'aucune décision d'octroi ne peut être prise par l'outil.` }],
        (t) => setAi(t),
        existing.id,
      );
    } catch (e: any) {
      setAi(`> ⚠️ ${e.message}`);
    } finally {
      setAiLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title={existing ? `Dossier ${existing.id}` : "Nouveau dossier de financement TPE"}
        subtitle="L'analyse se met à jour en temps réel pendant la saisie et est enregistrée avec le dossier."
        icon={<FileSearch className="h-5 w-5" />}
        actions={
          <>
            <Link href="/dossiers" className="btn-ghost">
              <ArrowLeft className="h-4 w-4" /> Retour
            </Link>
            {existing && <button className="btn-ghost" onClick={declareAnomaly}><Bug className="h-4 w-4" /> Déclarer une anomalie</button>}
            {editable && existing && (
              <button className="btn-ghost !text-red-600" onClick={remove}>
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            {editable && (
              <button className="btn-primary" onClick={save} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Enregistrer et analyser
              </button>
            )}
          </>
        }
      />
      {!editable && <ReadOnlyNotice text="Consultation seule : la saisie des dossiers est réservée aux commerciaux, analystes risques et administrateurs." />}
      {existing?.is_demo && <div className="mb-3"><DemoBadge /> <span className="text-xs text-slate-500">Dossier fictif de démonstration</span></div>}

      <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
        <fieldset disabled={!editable} className="space-y-4">
          <Card title="1. Informations de l'entreprise">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Raison sociale *"><input className="input" value={d.company.name} onChange={setC("name")} /></Field>
              <Field label="Forme juridique">
                <select className="input" value={d.company.legal_form} onChange={setC("legal_form")}>
                  {["SARL", "SARLAU", "SA", "SNC", "Entreprise individuelle", "Auto-entrepreneur", "Coopérative"].map((x) => <option key={x}>{x}</option>)}
                </select>
              </Field>
              <Field label="Date de création"><input type="date" className="input" value={d.company.creation_date} onChange={setC("creation_date")} /></Field>
              <Field label="N° registre de commerce"><input className="input" value={d.company.rc_number} onChange={setC("rc_number")} /></Field>
              <Field label="ICE"><input className="input" value={d.company.ice} onChange={setC("ice")} /></Field>
              <Field label="Ville"><input className="input" value={d.company.city} onChange={setC("city")} /></Field>
              <Field label="Dirigeant"><input className="input" value={d.company.manager_name} onChange={setC("manager_name")} /></Field>
              <Field label="Effectif"><input type="number" min={0} className="input" value={d.company.employees as any} onChange={setC("employees")} /></Field>
              <Field label="Raison sociale figurant sur les pièces" hint="Sert au contrôle de concordance"><input className="input" value={d.company.name_on_documents} onChange={setC("name_on_documents")} /></Field>
            </div>
          </Card>

          <Card title="2. Activité et financement demandé">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Secteur d'activité"><input className="input" value={d.company.sector} onChange={setC("sector")} /></Field>
              <Field label="Description de l'activité" className="sm:col-span-2"><input className="input" value={d.company.activity} onChange={setC("activity")} /></Field>
              <Field label="Type de financement">
                <select className="input" value={d.request.product} onChange={setR("product")}>
                  {PRODUCTS.map((x) => <option key={x}>{x}</option>)}
                </select>
              </Field>
              <Field label="Montant demandé (MAD) *"><input type="number" min={0} className="input" value={d.request.amount as any} onChange={setR("amount")} /></Field>
              <Field label="Durée (mois) *"><input type="number" min={1} className="input" value={d.request.duration_months as any} onChange={setR("duration_months")} /></Field>
              <Field label="Objet du financement" className="sm:col-span-2 lg:col-span-3"><input className="input" value={d.request.purpose} onChange={setR("purpose")} /></Field>
            </div>
          </Card>

          <Card title="3. Informations financières (MAD)">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Field label="Exercice"><input className="input" value={d.financials.fiscal_year} onChange={setF("fiscal_year")} placeholder="2025" /></Field>
              <Field label="CA exercice N"><input type="number" className="input" value={d.financials.revenue_n as any} onChange={setF("revenue_n")} /></Field>
              <Field label="CA exercice N-1"><input type="number" className="input" value={d.financials.revenue_n1 as any} onChange={setF("revenue_n1")} /></Field>
              <Field label="CA selon relevés bancaires" hint="Contrôle de cohérence"><input type="number" className="input" value={d.financials.revenue_bank as any} onChange={setF("revenue_bank")} /></Field>
              <Field label="Résultat net"><input type="number" className="input" value={d.financials.net_result as any} onChange={setF("net_result")} /></Field>
              <Field label="Fonds propres"><input type="number" className="input" value={d.financials.equity as any} onChange={setF("equity")} /></Field>
              <Field label="Dettes financières existantes"><input type="number" className="input" value={d.financials.existing_debt as any} onChange={setF("existing_debt")} /></Field>
              <Field label="Mensualités existantes"><input type="number" className="input" value={d.financials.existing_monthly_installments as any} onChange={setF("existing_monthly_installments")} /></Field>
            </div>
          </Card>

          <Card title="4. Pièces justificatives – grille de vérification (C01)" subtitle="Grille simple de vérification des dossiers (rapport, tableau 5.5)">
            <div className="divide-y divide-slate-100">
              {CHECKLIST.map((c) => {
                const req = c.stage === "avant_avis" && isRequired(c.key, d);
                return (
                  <div key={c.key} className="flex flex-col gap-2 py-2 sm:flex-row sm:items-center">
                    <div className="flex-1 text-sm">
                      {c.label}
                      <div className="text-[11px] text-slate-400">
                        {c.scope} · {c.stage === "avant_decision" ? "exigé avant la décision" : req ? "obligatoire avant avis" : "non requis pour ce dossier"}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {[
                        ["oui", "Oui", "bg-emerald-600"],
                        ["non", "Non", "bg-red-600"],
                        ["na", "N/A", "bg-slate-500"],
                      ].map(([v, l, bg]) => (
                        <button
                          type="button"
                          key={v}
                          onClick={() => setDoc(c.key, v)}
                          className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${d.documents[c.key] === v ? `${bg} text-white` : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                        >
                          {l}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card title="5. Garanties">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Nature de la garantie">
                <select className="input" value={d.guarantees.type} onChange={setG("type")}>
                  {GUARANTEE_TYPES.map((x) => <option key={x}>{x}</option>)}
                </select>
              </Field>
              <Field label="Valeur estimée (MAD)"><input type="number" className="input" value={d.guarantees.value as any} onChange={setG("value")} /></Field>
              <Field label="Description"><input className="input" value={d.guarantees.description} onChange={setG("description")} /></Field>
            </div>
          </Card>

          <Card title="6. Observations de l'analyste">
            <textarea className="input min-h-[100px]" value={d.observations} onChange={(e) => setD({ ...d, observations: e.target.value })} placeholder="Appréciation motivée, éléments vérifiés, points restant à confirmer…" />
          </Card>
        </fieldset>

        <div className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <Card title="Résultat de l'analyse" subtitle="Aide à l'analyse – aucune décision d'octroi">
            <div className={`mb-3 flex items-start gap-2 rounded-xl p-3 text-sm font-semibold ${analysis.blocking ? "bg-red-50 text-red-800" : "bg-emerald-50 text-emerald-800"}`}>
              {analysis.blocking ? <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" /> : <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />}
              {analysis.status}
            </div>
            <div className="mb-1 text-xs font-semibold text-slate-500">Complétude documentaire ({analysis.completeness.present}/{analysis.completeness.required})</div>
            <Progress value={analysis.completeness.rate} />
            <Section title="Pièces manquantes" items={analysis.completeness.missingDocs.map((m) => ({ code: m, message: m, severity: "alerte" as const }))} />
            <Section title="Incohérences" items={analysis.inconsistencies} />
            <Section title="Informations manquantes" items={analysis.missingInfo} />
            <Section title="Points de vigilance" items={analysis.vigilance} />
            {analysis.completeness.pendingBeforeDecision.length > 0 && (
              <p className="mt-3 text-[11px] text-slate-500">À produire avant décision : {analysis.completeness.pendingBeforeDecision.join(" ; ")}.</p>
            )}
            {analysis.ratios.length > 0 && (
              <div className="mt-3 rounded-xl bg-slate-50 p-3">
                <div className="mb-1 text-xs font-semibold text-slate-500">Ratios calculés (seuils indicatifs)</div>
                {analysis.ratios.map((r) => (
                  <div key={r.label} className="flex justify-between gap-2 text-xs">
                    <span className="text-slate-600">{r.label}</span>
                    <b>{r.value}</b>
                  </div>
                ))}
              </div>
            )}
            {analysis.linkedRisks.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-1 text-xs">
                Risques concernés : {analysis.linkedRisks.map((r) => <Badge key={r} tone="brand">{r}</Badge>)}
              </div>
            )}
          </Card>
          <Card title="Synthèse d'analyse">
            <p className="text-sm leading-relaxed text-slate-700">{analysis.synthesis}</p>
            <p className="mt-3 rounded-lg bg-amber-50 p-2.5 text-[11px] text-amber-800">{analysis.disclaimer}</p>
            <button className="btn-emerald mt-3 w-full" onClick={aiSynthesis} disabled={aiLoading}>
              {aiLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Synthèse rédigée par Risk Advisor (IA)
            </button>
            {ai && (
              <div className="prose-ai mt-3 max-h-[480px] overflow-y-auto rounded-xl border border-brand-100 bg-brand-50/40 p-3 text-sm">
                <ReactMarkdownLite text={ai} />
              </div>
            )}
          </Card>
          {existing && <Badge tone={statusTone(existing.status)}>Statut enregistré : {existing.status}</Badge>}
        </div>
      </div>
      <Toast message={toast?.m ?? null} tone={toast?.t} onDone={() => setToast(null)} />
    </div>
  );
}

function Section({ title, items }: { title: string; items: Finding[] }) {
  if (!items.length) return null;
  return (
    <div className="mt-3">
      <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-500">
        {title} ({items.length})
      </div>
      <ul className="space-y-1">
        {items.map((i, k) => (
          <li key={k} className="flex gap-1.5 text-xs text-slate-700">
            {i.severity === "alerte" ? <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-600" /> : i.severity === "attention" ? <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" /> : <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-500" />}
            <span>
              {i.message} {i.risk && <span className="text-slate-400">({i.risk})</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
