"use client";

export type ChatMsg = { role: "user" | "assistant"; content: string };

/** Appelle l'API Risk Advisor et diffuse la réponse au fil de l'eau. Retourne le fournisseur utilisé. */
export async function streamAdvisor(messages: ChatMsg[], onText: (full: string) => void, focus?: string, signal?: AbortSignal) {
  const res = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, focus }),
    signal,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `Erreur ${res.status} de l'assistant.`);
  }
  const provider = res.headers.get("X-AI-Provider") || "offline";
  const model = decodeURIComponent(res.headers.get("X-AI-Model") || "");
  const reader = res.body?.getReader();
  if (!reader) throw new Error("Flux de réponse indisponible.");
  const dec = new TextDecoder();
  let full = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    full += dec.decode(value, { stream: true });
    onText(full);
  }
  return { provider, model, text: full };
}
