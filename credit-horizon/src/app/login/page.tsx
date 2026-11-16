"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Lock, ShieldCheck, Sparkles, Grid3x3, FlaskConical } from "lucide-react";
import { Logo } from "@/components/Shell";

const DEMO = [
  { email: "admin@credithorizon.ma", role: "Administrateur" },
  { email: "directeur@credithorizon.ma", role: "Directeur" },
  { email: "analyste@credithorizon.ma", role: "Analyste risques" },
  { email: "commercial@credithorizon.ma", role: "Commercial" },
  { email: "controleur@credithorizon.ma", role: "Contrôleur interne" },
];
const DEMO_PASSWORD = "Horizon2026!";

function LoginForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(sp.get("expired") ? "Votre session a expiré. Veuillez vous reconnecter." : null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Connexion impossible.");
      const next = sp.get("next");
      router.push(next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard");
      router.refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-brand-950 via-brand-900 to-brand-700 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <Logo />
        <div className="relative z-10 max-w-lg">
          <h1 className="text-4xl font-extrabold leading-tight">Maîtriser le risque, accompagner la croissance des TPE.</h1>
          <p className="mt-4 text-brand-100/80">
            Plateforme intégrée de gestion des risques financiers : registre P × G, cartographie, diagnostic COSO 2013, contrôle interne, gouvernance RACI et assistant IA « Risk Advisor ».
          </p>
          <div className="mt-8 grid grid-cols-3 gap-3 text-xs">
            {[
              { i: Grid3x3, t: "Cartographie 5 × 5" },
              { i: ShieldCheck, t: "COSO 2013 – 17 principes" },
              { i: Sparkles, t: "IA générative" },
            ].map(({ i: I, t }) => (
              <div key={t} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <I className="mb-2 h-5 w-5 text-brand-400" />
                {t}
              </div>
            ))}
          </div>
        </div>
        <div className="text-xs text-brand-200/60">Projet EMSI · Génie Financier – Contrôle interne & gestion des risques financiers</div>
        <svg className="absolute -bottom-24 -right-24 h-[28rem] w-[28rem] opacity-10" viewBox="0 0 200 200">
          <circle cx="100" cy="100" r="90" fill="none" stroke="#10b981" strokeWidth="2" />
          <circle cx="100" cy="100" r="60" fill="none" stroke="#10b981" strokeWidth="2" />
          <circle cx="100" cy="100" r="30" fill="none" stroke="#10b981" strokeWidth="2" />
        </svg>
      </div>

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 inline-block rounded-xl bg-brand-900 px-3 py-2 lg:hidden">
            <Logo />
          </div>
          <h2 className="text-2xl font-bold text-brand-950">Connexion</h2>
          <p className="mt-1 text-sm text-slate-500">Accédez à votre espace de gestion des risques.</p>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="label">Adresse e-mail</span>
              <input className="input" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="prenom.nom@credithorizon.ma" />
            </label>
            <label className="block">
              <span className="label">Mot de passe</span>
              <input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            {error && <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <button className="btn-primary w-full !py-2.5" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />} Se connecter
            </button>
          </form>

          <div className="mt-8 rounded-2xl border border-violet-200 bg-violet-50 p-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-violet-800">
              <FlaskConical className="h-4 w-4" /> Comptes de démonstration
            </div>
            <p className="mb-3 text-xs text-violet-700">
              Mot de passe commun : <code className="rounded bg-white px-1.5 py-0.5 font-semibold">{DEMO_PASSWORD}</code> — cliquez sur un rôle pour pré-remplir.
            </p>
            <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {DEMO.map((d) => (
                <button
                  key={d.email}
                  type="button"
                  onClick={() => {
                    setEmail(d.email);
                    setPassword(DEMO_PASSWORD);
                  }}
                  className="rounded-lg border border-violet-200 bg-white px-2.5 py-1.5 text-left text-xs hover:border-violet-400"
                >
                  <div className="font-semibold text-violet-900">{d.role}</div>
                  <div className="truncate text-[10px] text-violet-600">{d.email}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
