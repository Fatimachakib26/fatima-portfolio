"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Sparkles, Send, Loader2, RotateCcw, FileDown, Copy, Bot, User as UserIcon, Square, Cpu, ShieldAlert,
  ListOrdered, Calculator, Target, Landmark, FileWarning, ShieldCheck, Lightbulb, ClipboardList, Bug, FileText, BookOpen, MessageSquare,
} from "lucide-react";
import { useApi } from "@/lib/client";
import { streamAdvisor, type ChatMsg } from "@/lib/advisor-client";
import Markdown from "@/components/Markdown";
import { PageHeader, Badge } from "@/components/ui";
import { exportMarkdownPdf } from "@/lib/exports";

const CAPABILITIES = [
  { icon: ListOrdered, label: "Analyser le registre", prompt: "Analyse l'ensemble du registre des risques : exposition globale, répartition par catégorie, risques critiques et couverture par les contrôles." },
  { icon: Calculator, label: "Expliquer les scores P × G", prompt: "Explique les scores P × G de chaque risque du registre, en t'appuyant sur les échelles et les justifications enregistrées." },
  { icon: Target, label: "Risques prioritaires", prompt: "Identifie les risques prioritaires et justifie l'ordre de traitement, en tenant compte de la chaîne causale entre les risques." },
  { icon: Landmark, label: "Relier aux principes COSO", prompt: "Relie chaque risque du registre aux composantes et principes COSO 2013 concernés, avec l'appréciation actuelle de chaque principe." },
  { icon: FileWarning, label: "Incohérences documentaires", prompt: "Détecte les incohérences documentaires et les pièces manquantes dans les dossiers TPE enregistrés, et indique les risques concernés." },
  { icon: ShieldCheck, label: "Proposer des contrôles", prompt: "Propose des contrôles internes pour renforcer la couverture des risques, en identifiant les risques insuffisamment couverts et les points de dépendance." },
  { icon: Lightbulb, label: "Recommandations", prompt: "Génère des recommandations personnalisées pour les risques critiques et élevés, au format RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI." },
  { icon: ClipboardList, label: "Construire un plan d'action", prompt: "Construis un plan d'action priorisé (P1, P2, P3) à partir des risques, des recommandations et de l'avancement actuel des actions." },
  { icon: Bug, label: "Analyser les anomalies", prompt: "Analyse le registre des anomalies : tendances, risques et contrôles concernés, anomalies en retard ou à escalader selon la charte." },
  { icon: FileText, label: "Synthèse exécutive", prompt: "Rédige une synthèse exécutive professionnelle de la situation des risques et du contrôle interne, destinée à la direction générale." },
  { icon: BookOpen, label: "Rapport de gestion des risques", prompt: "Prépare un rapport de gestion des risques structuré : contexte, cartographie, diagnostic COSO, dispositif de contrôle, anomalies, plan d'action et recommandations." },
  { icon: MessageSquare, label: "Question libre", prompt: "" },
];

const STORAGE_KEY = "ch-advisor-conversation";

function AssistantInner() {
  const sp = useSearchParams();
  const status = useApi<{ provider: string; model: string }>("/api/ai/chat");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const autoSent = useRef(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) setMessages(JSON.parse(saved));
    } catch {}
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-30)));
    } catch {}
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);
  useEffect(() => {
    const q = sp.get("q");
    if (q && !autoSent.current) {
      autoSent.current = true;
      send(q, []);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp]);

  async function send(text: string, base = messages) {
    const content = text.trim();
    if (!content || busy) return;
    setError(null);
    const next: ChatMsg[] = [...base, { role: "user", content }];
    setMessages([...next, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await streamAdvisor(next.slice(-20), (t) => setMessages([...next, { role: "assistant", content: t }]), undefined, ctrl.signal);
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setError(e.message);
        setMessages(next);
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  const provider = status.data?.provider;
  const lastAnswer = [...messages].reverse().find((m) => m.role === "assistant" && m.content);

  return (
    <div className="flex h-[calc(100vh-150px)] min-h-[560px] flex-col">
      <PageHeader
        title="Risk Advisor – Assistant IA"
        subtitle="Consultant senior virtuel en gestion des risques financiers et COSO 2013. Il raisonne uniquement sur les données enregistrées dans la plateforme et ne prend aucune décision d'octroi."
        icon={<Sparkles className="h-5 w-5" />}
        actions={
          <>
            <span className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs">
              <Cpu className="h-4 w-4 text-brand-600" />
              {provider === "gateway" ? "Vercel AI Gateway" : provider === "anthropic" ? "API Anthropic" : provider === "offline" ? "Mode hors ligne" : "…"}
              {status.data?.model && <Badge tone={provider === "offline" ? "amber" : "brand"}>{status.data.model}</Badge>}
            </span>
            {lastAnswer && (
              <button className="btn-ghost" onClick={() => exportMarkdownPdf("Risk Advisor – Analyse", messages.map((m) => (m.role === "user" ? `### Question\n${m.content}` : m.content)).join("\n\n"))}>
                <FileDown className="h-4 w-4" /> PDF
              </button>
            )}
            <button className="btn-ghost" onClick={() => { abortRef.current?.abort(); setMessages([]); }}>
              <RotateCcw className="h-4 w-4" /> Nouvelle conversation
            </button>
          </>
        }
      />
      {provider === "offline" && (
        <div className="mb-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          Aucune clé de modèle génératif n'est configurée sur le serveur (AI_GATEWAY_API_KEY ou ANTHROPIC_API_KEY). Les réponses sont produites par le moteur d'analyse local, à partir des données réelles de la plateforme.
        </div>
      )}

      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {!messages.length ? (
            <div>
              <div className="mb-5 text-center">
                <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-800 to-brand-500 text-white shadow-lg">
                  <Sparkles className="h-7 w-7" />
                </div>
                <h2 className="text-lg font-bold text-brand-950">Que souhaitez-vous analyser ?</h2>
                <p className="text-sm text-slate-500">Choisissez une analyse ou posez votre question en langage naturel.</p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {CAPABILITIES.map((c) => (
                  <button
                    key={c.label}
                    onClick={() => (c.prompt ? send(c.prompt) : inputRef.current?.focus())}
                    className="group flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left transition hover:border-brand-400 hover:bg-brand-50/50"
                  >
                    <c.icon className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
                    <div>
                      <div className="text-sm font-semibold text-slate-800">{c.label}</div>
                      {c.prompt && <div className="line-clamp-2 text-[11px] text-slate-500">{c.prompt}</div>}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-4xl space-y-5">
              {messages.map((m, i) => (
                <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                  {m.role === "assistant" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-800 text-brand-300">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}
                  <div className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm ${m.role === "user" ? "bg-brand-800 text-white" : "border border-slate-200 bg-white"}`}>
                    {m.role === "user" ? (
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    ) : m.content ? (
                      <div className="prose-ai">
                        <Markdown text={m.content} />
                        {!busy && (
                          <div className="mt-2 flex gap-2 border-t border-slate-100 pt-2">
                            <button className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-brand-700" onClick={() => navigator.clipboard?.writeText(m.content)}>
                              <Copy className="h-3 w-3" /> Copier
                            </button>
                            <button className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-brand-700" onClick={() => exportMarkdownPdf("Risk Advisor – Analyse", m.content)}>
                              <FileDown className="h-3 w-3" /> Exporter en PDF
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="inline-flex items-center gap-2 text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" /> Analyse des données de la plateforme…
                      </span>
                    )}
                  </div>
                  {m.role === "user" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-200 text-slate-600">
                      <UserIcon className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}
              <div ref={endRef} />
            </div>
          )}
        </div>
        {error && <div className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}
        {messages.length > 0 && (
          <div className="flex gap-1.5 overflow-x-auto border-t border-slate-100 px-4 py-2">
            {CAPABILITIES.filter((c) => c.prompt).map((c) => (
              <button key={c.label} disabled={busy} onClick={() => send(c.prompt)} className="whitespace-nowrap rounded-full border border-slate-200 px-2.5 py-1 text-[11px] text-slate-600 hover:border-brand-400 hover:text-brand-800 disabled:opacity-40">
                {c.label}
              </button>
            ))}
          </div>
        )}
        <form
          className="flex items-end gap-2 border-t border-slate-200 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <textarea
            ref={inputRef}
            className="input max-h-40 min-h-[44px] flex-1 resize-none"
            rows={1}
            placeholder="Ex. : Pourquoi R03 est-il le risque le plus critique ? Quels contrôles renforcer pour R07 ?"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
          />
          {busy ? (
            <button type="button" className="btn-ghost !py-2.5" onClick={() => abortRef.current?.abort()} title="Arrêter">
              <Square className="h-4 w-4" />
            </button>
          ) : (
            <button className="btn-primary !py-2.5" disabled={!input.trim()}>
              <Send className="h-4 w-4" />
            </button>
          )}
        </form>
      </div>
    </div>
  );
}

export default function AssistantPage() {
  return (
    <Suspense>
      <AssistantInner />
    </Suspense>
  );
}
