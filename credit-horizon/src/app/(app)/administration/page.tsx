"use client";
import { useEffect, useState } from "react";
import { Settings, UserPlus, Pencil, Trash2, RefreshCw, Database, Cpu, KeyRound, History } from "lucide-react";
import { api, useApi, useUser, fmtDateTime } from "@/lib/client";
import { can, ROLES, ROLE_LABEL } from "@/lib/permissions";
import { PageHeader, Card, Spinner, ErrorBox, Badge, DemoBadge, Toast, Modal, Field, ReadOnlyNotice } from "@/components/ui";

export default function AdminPage() {
  const user = useUser();
  const isAdmin = can(user.role, "users.manage");
  const users = useApi<any[]>(isAdmin ? "/api/users" : null);
  const audit = useApi<any[]>(can(user.role, "audit.view") ? "/api/audit" : null);
  const [health, setHealth] = useState<any>(null);
  const [edit, setEdit] = useState<any | null>(null);
  const [toast, setToast] = useState<{ m: string; t?: "red" } | null>(null);

  useEffect(() => {
    fetch("/api/health").then((r) => r.json()).then(setHealth).catch(() => {});
  }, []);

  async function reset() {
    if (!confirm("Réinitialiser toutes les données métier (risques, contrôles, COSO, actions, anomalies, dossiers) avec les données de démonstration ? Les comptes utilisateurs sont conservés.")) return;
    try {
      await api("/api/admin/reset", { method: "POST" });
      setToast({ m: "Données de démonstration restaurées." });
      audit.reload();
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    }
  }
  async function removeUser(u: any) {
    if (!confirm(`Supprimer le compte ${u.email} ?`)) return;
    try {
      await api(`/api/users/${u.id}`, { method: "DELETE" });
      users.reload();
    } catch (e: any) {
      setToast({ m: e.message, t: "red" });
    }
  }

  return (
    <div>
      <PageHeader title="Administration" subtitle="Utilisateurs, rôles, état technique de la plateforme et journal d'audit." icon={<Settings className="h-5 w-5" />} />
      {!isAdmin && <ReadOnlyNotice text="La gestion des utilisateurs est réservée à l'administrateur. Vous avez accès au journal d'audit." />}

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Status icon={<Database className="h-5 w-5" />} label="Base de données" value={health ? (health.database === "postgres" ? "PostgreSQL / Supabase" : "PostgreSQL embarqué (PGlite)") : "…"} ok={health?.ok} />
        <Status icon={<Cpu className="h-5 w-5" />} label="IA générative" value={health ? (health.ai.provider === "offline" ? "Non configurée – mode hors ligne" : `${health.ai.provider === "gateway" ? "AI Gateway" : "Anthropic"} · ${health.ai.model}`) : "…"} ok={health?.ai?.provider !== "offline"} />
        <Status icon={<KeyRound className="h-5 w-5" />} label="Secret de session" value={health ? (health.authSecret ? "AUTH_SECRET configuré" : "Secret de développement (à configurer)") : "…"} ok={health?.authSecret} />
      </div>

      {isAdmin && (
        <Card
          title="Utilisateurs et rôles"
          actions={
            <div className="flex gap-2">
              <button className="btn-ghost" onClick={reset}><RefreshCw className="h-4 w-4" /> Réinitialiser la démo</button>
              <button className="btn-primary" onClick={() => setEdit({ email: "", name: "", role: "analyste", password: "" })}><UserPlus className="h-4 w-4" /> Nouvel utilisateur</button>
            </div>
          }
        >
          {users.loading && !users.data ? <Spinner /> : users.error ? <ErrorBox message={users.error} /> : (
            <div className="-mx-4 overflow-x-auto sm:-mx-5">
              <table className="table-pro min-w-[700px]">
                <thead><tr><th>Nom</th><th>E-mail</th><th>Rôle</th><th>Statut</th><th>Créé le</th><th /></tr></thead>
                <tbody>
                  {users.data!.map((u) => (
                    <tr key={u.id}>
                      <td className="font-medium">{u.name} {u.is_demo && <DemoBadge />}</td>
                      <td className="text-xs">{u.email}</td>
                      <td><Badge tone="brand">{ROLE_LABEL[u.role as keyof typeof ROLE_LABEL]}</Badge></td>
                      <td><Badge tone={u.active ? "emerald" : "red"}>{u.active ? "Actif" : "Désactivé"}</Badge></td>
                      <td className="text-xs">{fmtDateTime(u.created_at)}</td>
                      <td>
                        <div className="flex gap-1">
                          <button className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100" onClick={() => setEdit({ ...u, password: "" })}><Pencil className="h-4 w-4" /></button>
                          {u.id !== user.id && <button className="rounded-lg p-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600" onClick={() => removeUser(u)}><Trash2 className="h-4 w-4" /></button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {can(user.role, "audit.view") && (
        <Card className="mt-4" title={<span className="inline-flex items-center gap-2"><History className="h-4 w-4" /> Journal d'audit (200 dernières opérations)</span>} subtitle="Traçabilité des décisions et modifications (charte, article 7)">
          {audit.loading && !audit.data ? <Spinner /> : audit.error ? <ErrorBox message={audit.error} /> : (
            <div className="-mx-4 max-h-[480px] overflow-auto sm:-mx-5">
              <table className="table-pro min-w-[700px]">
                <thead><tr><th>Date</th><th>Utilisateur</th><th>Action</th><th>Objet</th><th>Détail</th></tr></thead>
                <tbody>
                  {audit.data!.map((a) => (
                    <tr key={a.id}>
                      <td className="whitespace-nowrap text-xs">{fmtDateTime(a.at)}</td>
                      <td className="text-xs">{a.user_email}</td>
                      <td><Badge tone={a.action === "Suppression" ? "red" : a.action.startsWith("Création") ? "emerald" : "slate"}>{a.action}</Badge></td>
                      <td className="text-xs">{a.entity} <b>{a.entity_id}</b></td>
                      <td className="max-w-[360px] truncate text-xs text-slate-500" title={a.details}>{a.details}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {edit && <UserForm u={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); setToast({ m: "Utilisateur enregistré." }); users.reload(); }} />}
      <Toast message={toast?.m ?? null} tone={toast?.t} onDone={() => setToast(null)} />
    </div>
  );
}

function Status({ icon, label, value, ok }: { icon: React.ReactNode; label: string; value: string; ok?: boolean }) {
  return (
    <div className="card flex items-center gap-3 p-4">
      <div className={`rounded-xl p-2.5 ${ok ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"}`}>{icon}</div>
      <div><div className="text-xs font-semibold uppercase text-slate-500">{label}</div><div className="text-sm font-medium text-slate-800">{value}</div></div>
    </div>
  );
}

function UserForm({ u, onClose, onSaved }: { u: any; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState(u);
  const [err, setErr] = useState<string | null>(null);
  const isNew = !u.id;
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      if (isNew) await api("/api/users", { method: "POST", json: { email: f.email, name: f.name, role: f.role, password: f.password } });
      else await api(`/api/users/${u.id}`, { method: "PUT", json: { name: f.name, role: f.role, active: f.active, ...(f.password ? { password: f.password } : {}) } });
      onSaved();
    } catch (e: any) {
      setErr(e.message);
    }
  }
  return (
    <Modal open onClose={onClose} title={isNew ? "Nouvel utilisateur" : `Modifier ${u.email}`}>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Field label="Nom complet"><input className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="E-mail"><input className="input" type="email" required disabled={!isNew} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Rôle">
          <select className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
            {ROLES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
          </select>
        </Field>
        <Field label={isNew ? "Mot de passe (8 caractères min.)" : "Nouveau mot de passe (facultatif)"}>
          <input className="input" type="password" minLength={8} required={isNew} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
        </Field>
        {!isNew && (
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} /> Compte actif
          </label>
        )}
        <p className="text-xs text-slate-500 sm:col-span-2">{ROLES.find((r) => r.id === f.role)?.description}</p>
        {err && <div className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-2">{err}</div>}
        <div className="flex justify-end gap-2 sm:col-span-2">
          <button type="button" className="btn-ghost" onClick={onClose}>Annuler</button>
          <button className="btn-primary">Enregistrer</button>
        </div>
      </form>
    </Modal>
  );
}
