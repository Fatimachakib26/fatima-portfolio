"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  LayoutDashboard,
  ListChecks,
  Grid3x3,
  FileSearch,
  Landmark,
  ShieldCheck,
  Network,
  Gauge,
  Sparkles,
  FileDown,
  Settings,
  LogOut,
  Menu,
  X,
  ClipboardList,
  FlaskConical,
} from "lucide-react";
import { UserContext, type ClientUser } from "@/lib/client";
import { ROLE_LABEL } from "@/lib/permissions";

const NAV = [
  { href: "/dashboard", label: "Dashboard exécutif", icon: LayoutDashboard },
  { href: "/risques", label: "Registre des risques", icon: ListChecks },
  { href: "/cartographie", label: "Cartographie", icon: Grid3x3 },
  { href: "/dossiers", label: "Dossiers TPE", icon: FileSearch },
  { href: "/coso", label: "Diagnostic COSO", icon: Landmark },
  { href: "/controles", label: "Contrôle interne", icon: ShieldCheck },
  { href: "/suivi", label: "Suivi & anomalies", icon: ClipboardList },
  { href: "/gouvernance", label: "Gouvernance RACI", icon: Network },
  { href: "/appetence", label: "Appétence au risque", icon: Gauge },
  { href: "/assistant", label: "Risk Advisor IA", icon: Sparkles, highlight: true },
  { href: "/rapports", label: "Rapports & exports", icon: FileDown },
];

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 64 64" className="h-9 w-9 shrink-0" aria-hidden>
        <rect width="64" height="64" rx="14" fill="#0a4d38" />
        <path d="M12 42 Q32 14 52 42" fill="none" stroke="#10b981" strokeWidth="5" strokeLinecap="round" />
        <path d="M8 46h48" stroke="#d1fae5" strokeWidth="4" strokeLinecap="round" />
        <circle cx="32" cy="24" r="5" fill="#34d399" />
      </svg>
      {!compact && (
        <div className="leading-tight">
          <div className="text-[15px] font-extrabold tracking-wide text-white">CRÉDIT HORIZON</div>
          <div className="text-[10px] font-semibold tracking-[0.3em] text-brand-400">RISK INTELLIGENCE</div>
        </div>
      )}
    </div>
  );
}

export default function Shell({ user, children, warnings }: { user: ClientUser; children: ReactNode; warnings: string[] }) {
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  const nav = (
    <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3 py-4">
      {NAV.map((n) => {
        const active = path === n.href || path.startsWith(n.href + "/");
        const Icon = n.icon;
        return (
          <Link
            key={n.href}
            href={n.href}
            onClick={() => setOpen(false)}
            className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
              active ? "bg-brand-500/15 text-white ring-1 ring-brand-500/40" : "text-brand-100/80 hover:bg-white/5 hover:text-white"
            }`}
          >
            <Icon className={`h-[18px] w-[18px] ${active ? "text-brand-400" : n.highlight ? "text-brand-400" : "text-brand-300/70"}`} />
            <span className="flex-1">{n.label}</span>
            {n.highlight && <span className="rounded bg-brand-500 px-1.5 py-0.5 text-[9px] font-bold uppercase text-white">IA</span>}
          </Link>
        );
      })}
      {user.role === "admin" || user.role === "directeur" || user.role === "controleur" ? (
        <Link
          href="/administration"
          onClick={() => setOpen(false)}
          className={`mt-2 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
            path.startsWith("/administration") ? "bg-brand-500/15 text-white ring-1 ring-brand-500/40" : "text-brand-100/80 hover:bg-white/5 hover:text-white"
          }`}
        >
          <Settings className="h-[18px] w-[18px] text-brand-300/70" /> Administration
        </Link>
      ) : null}
    </nav>
  );

  const userBox = (
    <div className="border-t border-white/10 p-3">
      <div className="flex items-center gap-3 rounded-xl bg-white/5 p-2.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-500 text-sm font-bold text-white">
          {user.name.split(" ").map((x) => x[0]).slice(0, 2).join("")}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-white">{user.name}</div>
          <div className="truncate text-[11px] text-brand-300">{ROLE_LABEL[user.role]}</div>
        </div>
        <button onClick={logout} title="Se déconnecter" className="rounded-lg p-1.5 text-brand-200 hover:bg-white/10 hover:text-white">
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </div>
  );

  return (
    <UserContext.Provider value={user}>
      <div className="flex min-h-screen">
        {/* Sidebar desktop */}
        <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-gradient-to-b from-brand-950 to-brand-900 lg:flex">
          <div className="border-b border-white/10 px-5 py-5">
            <Logo />
          </div>
          {nav}
          {userBox}
        </aside>

        {/* Drawer mobile/tablette */}
        {open && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
            <aside className="absolute inset-y-0 left-0 flex w-72 flex-col bg-gradient-to-b from-brand-950 to-brand-900">
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                <Logo />
                <button onClick={() => setOpen(false)} className="text-brand-200" aria-label="Fermer le menu">
                  <X className="h-5 w-5" />
                </button>
              </div>
              {nav}
              {userBox}
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
          <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
            <button onClick={() => setOpen(true)} className="rounded-lg p-1.5 text-brand-900 hover:bg-slate-100" aria-label="Ouvrir le menu">
              <Menu className="h-5 w-5" />
            </button>
            <div className="rounded-lg bg-brand-900 px-2 py-1">
              <Logo />
            </div>
          </header>
          <div className="no-print flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-violet-200 bg-violet-50 px-4 py-1.5 text-[11px] text-violet-800 sm:px-8">
            <FlaskConical className="h-3.5 w-3.5" />
            <span>
              <b>Environnement de démonstration</b> – cas académique fictif EMSI. Les éléments marqués « Démo » sont des données de démonstration.
            </span>
            {warnings.map((w) => (
              <span key={w} className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-800">
                {w}
              </span>
            ))}
          </div>
          <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-8">{children}</main>
          <footer className="no-print border-t border-slate-200 px-8 py-4 text-center text-[11px] text-slate-400">
            CRÉDIT HORIZON RISK INTELLIGENCE · Projet EMSI – Contrôle interne & gestion des risques financiers · Aide à la décision : aucune décision d'octroi automatique
          </footer>
        </div>
      </div>
    </UserContext.Provider>
  );
}
