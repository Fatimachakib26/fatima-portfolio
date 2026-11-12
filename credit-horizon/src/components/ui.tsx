"use client";
import { useEffect, type ReactNode } from "react";
import { AlertTriangle, Loader2, X, FlaskConical, Inbox } from "lucide-react";
import { LEVEL_STYLE, levelFromScore, type Level } from "@/lib/scoring";

export function PageHeader({ title, subtitle, icon, actions }: { title: string; subtitle?: string; icon?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex items-start gap-3">
        {icon && <div className="mt-0.5 hidden rounded-xl bg-brand-800 p-2.5 text-brand-300 sm:block">{icon}</div>}
        <div>
          <h1 className="text-xl font-bold tracking-tight text-brand-950 sm:text-2xl">{title}</h1>
          {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-500">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="no-print flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, subtitle, children, className = "", actions }: { title?: ReactNode; subtitle?: string; children: ReactNode; className?: string; actions?: ReactNode }) {
  return (
    <section className={`card p-4 sm:p-5 ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-sm font-bold text-brand-950">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Kpi({ label, value, hint, icon, tone = "brand" }: { label: string; value: ReactNode; hint?: string; icon?: ReactNode; tone?: "brand" | "red" | "amber" | "emerald" | "slate" }) {
  const tones = {
    brand: "bg-brand-50 text-brand-700",
    red: "bg-red-50 text-red-600",
    amber: "bg-amber-50 text-amber-600",
    emerald: "bg-emerald-50 text-emerald-600",
    slate: "bg-slate-100 text-slate-600",
  };
  return (
    <div className="card flex items-start gap-3 p-4">
      {icon && <div className={`rounded-xl p-2.5 ${tones[tone]}`}>{icon}</div>}
      <div className="min-w-0">
        <div className="break-words text-[11px] font-medium uppercase tracking-wide text-slate-500 [hyphens:auto] sm:text-xs" lang="fr">{label}</div>
        <div className="mt-0.5 text-2xl font-bold text-brand-950">{value}</div>
        {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
      </div>
    </div>
  );
}

export function LevelBadge({ level, score }: { level?: Level; score?: number }) {
  const l = level ?? levelFromScore(score ?? 0);
  const st = LEVEL_STYLE[l];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold ${st.soft} ${st.text} ring-1 ${st.ring}`}>
      <span className={`h-2 w-2 rounded-full ${st.bg}`} />
      {l}
      {score !== undefined && <span className="opacity-70">· {score}</span>}
    </span>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "brand" | "red" | "amber" | "emerald" | "blue" | "violet" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    brand: "bg-brand-100 text-brand-800",
    red: "bg-red-100 text-red-700",
    amber: "bg-amber-100 text-amber-800",
    emerald: "bg-emerald-100 text-emerald-700",
    blue: "bg-sky-100 text-sky-700",
    violet: "bg-violet-100 text-violet-700",
  };
  return <span className={`inline-flex items-center whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${tones[tone]}`}>{children}</span>;
}

export function DemoBadge() {
  return (
    <span title="Donnée de démonstration issue du cas académique EMSI (fictif)" className="inline-flex items-center gap-1 rounded-md bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-700">
      <FlaskConical className="h-3 w-3" /> Démo
    </span>
  );
}

export function statusTone(s: string): "slate" | "brand" | "red" | "amber" | "emerald" | "blue" {
  if (["Terminé", "Clôturée", "Efficace", "Opérationnel", "Mise en œuvre", "Satisfaisant", "Complet – transmissible pour avis risques"].includes(s)) return "emerald";
  if (["En cours", "En déploiement", "Partiel"].includes(s)) return "blue";
  if (["Ouverte", "Bloqué", "Déficient", "Critique", "Incomplet – présentation suspendue"].includes(s)) return "red";
  if (["À faire", "À lancer", "À concevoir"].includes(s)) return "amber";
  return "slate";
}

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
      <Loader2 className="h-5 w-5 animate-spin text-brand-600" /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost !py-1 text-xs">
          Réessayer
        </button>
      )}
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-sm text-slate-400">
      <Inbox className="h-8 w-8" /> {text}
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-brand-950/50 p-0 backdrop-blur-sm sm:items-center sm:p-4" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl ${wide ? "sm:max-w-4xl" : "sm:max-w-2xl"}`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-100 bg-white px-5 py-3.5">
          <h3 className="font-bold text-brand-950">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100" aria-label="Fermer">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function Field({ label, children, hint, className = "" }: { label: string; children: ReactNode; hint?: string; className?: string }) {
  return (
    <label className={`block ${className}`}>
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

export function ReadOnlyNotice({ text }: { text: string }) {
  return <div className="no-print mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800">🔒 {text}</div>;
}

export function Toast({ message, tone = "emerald", onDone }: { message: string | null; tone?: "emerald" | "red"; onDone: () => void }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDone, 3500);
    return () => clearTimeout(t);
  }, [message, onDone]);
  if (!message) return null;
  return (
    <div className={`fixed bottom-4 right-4 z-[60] max-w-sm rounded-xl px-4 py-3 text-sm font-medium text-white shadow-xl ${tone === "red" ? "bg-red-600" : "bg-brand-800"}`}>
      {message}
    </div>
  );
}

export function Progress({ value }: { value: number }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-full min-w-[60px] overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${v === 100 ? "bg-emerald-500" : "bg-brand-600"}`} style={{ width: `${v}%` }} />
      </div>
      <span className="w-9 text-right text-xs font-semibold text-slate-600">{v}%</span>
    </div>
  );
}
