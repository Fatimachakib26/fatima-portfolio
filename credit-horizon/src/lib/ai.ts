import "server-only";
import type { LanguageModel } from "ai";
import { createAnthropic } from "@ai-sdk/anthropic";

/**
 * Fournisseur d'IA générative – les clés restent EXCLUSIVEMENT côté serveur.
 * Priorité : 1) Vercel AI Gateway (AI_GATEWAY_API_KEY, ou OIDC automatique sur Vercel)
 *            2) Clé Anthropic directe (ANTHROPIC_API_KEY)
 *            3) Mode hors ligne : moteur d'analyse déterministe sur les données réelles.
 */
export type AiProvider = "gateway" | "anthropic" | "offline";

export function aiStatus(): { provider: AiProvider; model: string } {
  if (process.env.AI_GATEWAY_API_KEY || process.env.VERCEL_OIDC_TOKEN) {
    return { provider: "gateway", model: process.env.AI_MODEL || "anthropic/claude-sonnet-4.5" };
  }
  if (process.env.ANTHROPIC_API_KEY) {
    return { provider: "anthropic", model: process.env.ANTHROPIC_MODEL || "claude-sonnet-4-5" };
  }
  return { provider: "offline", model: "moteur-de-regles-local" };
}

export function getModel(): LanguageModel | null {
  const s = aiStatus();
  if (s.provider === "gateway") return s.model; // chaîne "fournisseur/modèle" → AI Gateway (fournisseur par défaut du SDK)
  if (s.provider === "anthropic") return createAnthropic({ apiKey: process.env.ANTHROPIC_API_KEY })(s.model);
  return null;
}
