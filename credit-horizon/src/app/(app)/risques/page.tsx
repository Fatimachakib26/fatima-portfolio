"use client";
import { Fragment, useMemo, useState } from "react";
import { ListChecks, Plus, Search, Pencil, Trash2, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import Link from "next/link";
import { api, useApi, useUser, fmtDateTime } from "@/lib/client";
import { can } from "@/lib/permissions";
import { PageHeader, Card, LevelBadge, Spinner, ErrorBox, Modal, Field, Badge, DemoBadge, Toast, ReadOnlyNotice, Empty } from "@/components/ui";
import { computeScore, levelFromScore, LEVEL_TREATMENT, PROBABILITY_SCALE, GRAVITY_SCALE, LEVELS } from "@/lib/scoring";
import { CATEGORY_COLORS } from "@/lib/chart-colors";

const EMPTY = {
  title: "", category: "Crédit", event: "", causes: "", consequences: "", probability: 3, gravity: 3,
  justification: "", owner: "", control_ids: "", coso_principles: "", basis: "Constat", recommendation: "",
};

export default function RisksPage() {
  const user = useUser();
  const canWrite = can(user.role, "risks.write");
  const { data, error, loading, reload } = useApi<any[]>("/api/data/risks");
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("");
  const [lvl, setLvl] = useState("");
  const [sort, setSort] = useState<"score" | "id">("score");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [edit, setEdit] = useState<any | null>(null);
  const [toast, setToast] = useState<{ m: string; t?: "red" } | null>(null);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || [])
      .map((r) => ({ ...r, score: Number(r.score), level: levelFromScore(Number(r.score)) }))
      .filter((r) => (!cat || r.category === cat) && (!lvl || r.level === lvl))
      .filter((r) => !s || [r.id, r.title, r.event, r.causes, r.consequences, r.owner, r.control_ids, r.recommendation].join(" ").toLowerCase().includes(s))
      .sort((a, b) => (sort === "score" ? b.score - a.score || a.id.localeCompare(b.id) : a.id.localeCompare(b.id)));
  }, [data, search, cat, lvl, sort]);

  async function remove(r: any) {
    if (!confirm(`Supprimer définitivement le risque ${r.id} – ${r.title} ?`)) return;
    try {
      await api(`/api/data/risks/${r.id}`, { method: "DELETE" });
      setToast({ m: `Risque ${r.id} supprimé.` });
      reload();
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    }
  }

  return (
    <div>
      <PageHeader
        title="Registre des risques"
        subtitle="Registre dynamique : identification, cotation P × G automatique, criticité, responsables, contrôles et recommandations. Les risques R01 à R08 proviennent du projet EMSI."
        icon={<ListChecks className="h-5 w-5" />}
        actions={
          canWrite && (
            <button className="btn-primary" onClick={() => setEdit({ ...EMPTY })}>
              <Plus className="h-4 w-4" /> Nouveau risque
            </button>
          )
        }
      />
      {!canWrite && <ReadOnlyNotice text="Consultation seule : la modification du registre est réservée à la fonction risques et à l'administrateur (séparation des tâches)." />}

      <Card>
        <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-[1fr_180px_160px_160px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input className="input pl-9" placeholder="Rechercher (identifiant, événement, cause, responsable…)" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="input" value={cat} onChange={(e) => setCat(e.target.value)}>
            <option value="">Toutes catégories</option>
            {Object.keys(CATEGORY_COLORS).map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select className="input" value={lvl} onChange={(e) => setLvl(e.target.value)}>
            <option value="">Tous niveaux</option>
            {LEVELS.map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
          <select className="input" value={sort} onChange={(e) => setSort(e.target.value as any)}>
            <option value="score">Tri : criticité</option>
            <option value="id">Tri : identifiant</option>
          </select>
        </div>

        {loading && !data ? (
          <Spinner />
        ) : error ? (
          <ErrorBox message={error} onRetry={reload} />
        ) : !rows.length ? (
          <Empty text="Aucun risque ne correspond aux critères." />
        ) : (
          <div className="-mx-4 overflow-x-auto sm:-mx-5">
            <table className="table-pro min-w-[960px]">
              <thead>
                <tr>
                  <th></th>
                  <th>ID</th>
                  <th>Risque / événement</th>
                  <th>Catégorie</th>
                  <th className="text-center">P</th>
                  <th className="text-center">G</th>
                  <th className="text-center">P × G</th>
                  <th>Criticité</th>
                  <th>Responsable</th>
                  <th>Contrôles</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <Fragment key={r.id}>
                    <tr className="cursor-pointer" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>
                      <td className="text-slate-400">{expanded === r.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}</td>
                      <td className="font-bold text-brand-800">
                        {r.id}
                        <div className="mt-1">{r.is_demo && <DemoBadge />}</div>
                      </td>
                      <td className="max-w-[340px]">
                        <div className="font-semibold text-slate-900">{r.title}</div>
                        <div className="line-clamp-2 text-xs text-slate-500">{r.event}</div>
                      </td>
                      <td>
                        <span className="inline-flex items-center gap-1.5 text-xs">
                          <span className="h-2 w-2 rounded-full" style={{ background: CATEGORY_COLORS[r.category] }} />
                          {r.category}
                        </span>
                      </td>
                      <td className="text-center font-semibold">{r.probability}</td>
                      <td className="text-center font-semibold">{r.gravity}</td>
                      <td className="text-center text-base font-bold text-brand-950">{r.score}</td>
                      <td>
                        <LevelBadge level={r.level} />
                      </td>
                      <td className="max-w-[200px] text-xs text-slate-600">{r.owner}</td>
                      <td className="text-xs">
                        <div className="flex flex-wrap gap-1">
                          {String(r.control_ids || "").split(/[,;\s]+/).filter(Boolean).map((c: string) => (
                            <Badge key={c} tone="brand">
                              {c}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        {canWrite && (
                          <div className="flex gap-1">
                            <button className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-brand-700" title="Modifier" onClick={() => setEdit(r)}>
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button className="rounded-lg p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600" title="Supprimer" onClick={() => remove(r)}>
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                    {expanded === r.id && (
                      <tr className="!bg-brand-50/30">
                        <td colSpan={11}>
                          <div className="grid gap-4 py-2 text-sm md:grid-cols-2 xl:grid-cols-3">
                            <Detail label="Événement redouté" text={r.event} />
                            <Detail label="Causes" text={r.causes} />
                            <Detail label="Conséquences" text={r.consequences} />
                            <Detail label="Justification de la cotation" text={r.justification} />
                            <Detail label="Recommandation" text={r.recommendation} />
                            <div>
                              <div className="label">Traitement attendu</div>
                              <p className="text-slate-700">{LEVEL_TREATMENT[r.level as keyof typeof LEVEL_TREATMENT]}</p>
                              <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                                <Badge tone={r.basis === "Constat" ? "brand" : "amber"}>{r.basis}</Badge>
                                {r.coso_principles && <Badge tone="violet">COSO : {r.coso_principles}</Badge>}
                              </div>
                              <p className="mt-2 text-[11px] text-slate-400">Mis à jour le {fmtDateTime(r.updated_at)}{r.updated_by ? ` par ${r.updated_by}` : ""}</p>
                              <Link href={`/assistant?q=${encodeURIComponent(`Analyse le risque ${r.id} : explique son score P × G, relie-le aux principes COSO et propose une recommandation complète.`)}`} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:underline">
                                <Sparkles className="h-3.5 w-3.5" /> Analyser avec Risk Advisor
                              </Link>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-xs text-slate-400">{rows.length} risque(s) affiché(s) · cliquez sur une ligne pour le détail.</p>
      </Card>

      {edit && (
        <RiskForm
          initial={edit}
          onClose={() => setEdit(null)}
          onSaved={(m) => {
            setEdit(null);
            setToast({ m });
            reload();
          }}
        />
      )}
      <Toast message={toast?.m ?? null} tone={toast?.t} onDone={() => setToast(null)} />
    </div>
  );
}

function Detail({ label, text }: { label: string; text?: string }) {
  return (
    <div>
      <div className="label">{label}</div>
      <p className="whitespace-pre-line text-slate-700">{text || "–"}</p>
    </div>
  );
}

function RiskForm({ initial, onClose, onSaved }: { initial: any; onClose: () => void; onSaved: (m: string) => void }) {
  const [f, setF] = useState<any>({ ...EMPTY, ...initial });
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const isNew = !initial.id;
  const score = computeScore(f.probability, f.gravity);
  const level = levelFromScore(score);
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr(null);
    const payload = Object.fromEntries(Object.keys(EMPTY).map((k) => [k, f[k] ?? ""]));
    try {
      const r = await api(isNew ? "/api/data/risks" : `/api/data/risks/${initial.id}`, { method: isNew ? "POST" : "PUT", json: payload });
      onSaved(isNew ? `Risque ${r.id} créé (score ${r.score}).` : `Risque ${initial.id} mis à jour.`);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={isNew ? "Nouveau risque" : `Modifier ${initial.id}`} wide>
      <form onSubmit={save} className="grid gap-4 md:grid-cols-2">
        <Field label="Intitulé du risque *" className="md:col-span-2">
          <input className="input" required value={f.title} onChange={set("title")} />
        </Field>
        <Field label="Catégorie">
          <select className="input" value={f.category} onChange={set("category")}>
            {Object.keys(CATEGORY_COLORS).map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </Field>
        <Field label="Fondement">
          <select className="input" value={f.basis} onChange={set("basis")}>
            <option>Constat</option>
            <option>Hypothèse</option>
          </select>
        </Field>
        <Field label="Description de l'événement *" className="md:col-span-2">
          <textarea className="input min-h-[70px]" required value={f.event} onChange={set("event")} />
        </Field>
        <Field label="Causes">
          <textarea className="input min-h-[70px]" value={f.causes} onChange={set("causes")} />
        </Field>
        <Field label="Conséquences">
          <textarea className="input min-h-[70px]" value={f.consequences} onChange={set("consequences")} />
        </Field>
        <Field label={`Probabilité : ${f.probability} – ${PROBABILITY_SCALE[f.probability - 1]?.label}`} hint={PROBABILITY_SCALE[f.probability - 1]?.desc}>
          <input type="range" min={1} max={5} className="w-full accent-brand-700" value={f.probability} onChange={(e) => setF({ ...f, probability: Number(e.target.value) })} />
        </Field>
        <Field label={`Gravité : ${f.gravity} – ${GRAVITY_SCALE[f.gravity - 1]?.label}`} hint={GRAVITY_SCALE[f.gravity - 1]?.desc}>
          <input type="range" min={1} max={5} className="w-full accent-brand-700" value={f.gravity} onChange={(e) => setF({ ...f, gravity: Number(e.target.value) })} />
        </Field>
        <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3 md:col-span-2">
          <span className="text-sm text-slate-600">Score calculé automatiquement :</span>
          <span className="text-2xl font-bold text-brand-950">{score}</span>
          <LevelBadge level={level} />
          <span className="hidden text-xs text-slate-500 md:inline">{LEVEL_TREATMENT[level]}</span>
        </div>
        <Field label="Justification de la cotation" className="md:col-span-2">
          <textarea className="input min-h-[60px]" value={f.justification} onChange={set("justification")} />
        </Field>
        <Field label="Responsable *">
          <input className="input" required value={f.owner} onChange={set("owner")} />
        </Field>
        <Field label="Contrôles associés" hint="Ex. : C01, C04">
          <input className="input" value={f.control_ids} onChange={set("control_ids")} />
        </Field>
        <Field label="Principes COSO" hint="Ex. : P10, P12">
          <input className="input" value={f.coso_principles} onChange={set("coso_principles")} />
        </Field>
        <Field label="Recommandation" className="md:col-span-2">
          <textarea className="input min-h-[60px]" value={f.recommendation} onChange={set("recommendation")} />
        </Field>
        {err && <div className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 md:col-span-2">{err}</div>}
        <div className="flex justify-end gap-2 md:col-span-2">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Annuler
          </button>
          <button className="btn-primary" disabled={saving}>
            {saving ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
