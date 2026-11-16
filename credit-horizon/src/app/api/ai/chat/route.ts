import { z } from "zod";
import { streamText } from "ai";
import { requireUser, errorResponse, HttpError } from "@/lib/auth";
import { getSnapshot } from "@/lib/snapshot";
import { buildContext, ADVISOR_RULES } from "@/lib/ai-context";
import { offlineAnswer } from "@/lib/offline-advisor";
import { aiStatus, getModel } from "@/lib/ai";
import { audit } from "@/lib/db";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const bodySchema = z.object({
  messages: z
    .array(z.object({ role: z.enum(["user", "assistant"]), content: z.string().max(20000) }))
    .min(1)
    .max(30),
  focus: z.string().max(40).optional(),
});

const usage = new Map<string, number[]>();
function rateLimit(key: string, max = 20, windowMs = 60_000) {
  const now = Date.now();
  const arr = (usage.get(key) || []).filter((t) => now - t < windowMs);
  if (arr.length >= max) throw new HttpError(429, "Trop de requêtes vers l'assistant. Patientez une minute.");
  arr.push(now);
  usage.set(key, arr);
}

export async function POST(req: Request) {
  try {
    const user = await requireUser();
    rateLimit(user.email);
    const { messages, focus } = bodySchema.parse(await req.json());
    const last = messages[messages.length - 1];
    if (last.role !== "user") throw new HttpError(400, "Le dernier message doit provenir de l'utilisateur.");

    const snapshot = await getSnapshot();
    const status = aiStatus();
    const model = getModel();
    await audit(user, "Requête IA", "Risk Advisor", status.provider, last.content.slice(0, 300));

    const encoder = new TextEncoder();
    const headers = {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-AI-Provider": status.provider,
      "X-AI-Model": encodeURIComponent(status.model),
    };

    if (!model) {
      const text = offlineAnswer(snapshot, last.content, focus);
      return new Response(encoder.encode(text), { headers });
    }

    const system = `${ADVISOR_RULES}\n\nUtilisateur connecté : ${user.name} (rôle : ${user.role}).\n\n${buildContext(snapshot, focus)}`;

    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        let sent = false;
        try {
          const result = streamText({
            model,
            system,
            messages: messages.map((m) => ({ role: m.role, content: m.content })),
            temperature: 0.2,
            maxOutputTokens: 3000,
          });
          for await (const part of result.fullStream) {
            if (part.type === "text-delta") {
              const t = (part as any).text ?? (part as any).delta ?? "";
              if (t) {
                controller.enqueue(encoder.encode(t));
                sent = true;
              }
            } else if (part.type === "error") {
              throw (part as any).error;
            }
          }
        } catch (err) {
          console.error("[Risk Advisor] erreur du modèle :", err);
          const notice = sent
            ? "\n\n> ⚠️ La génération a été interrompue (erreur du service d'IA)."
            : "> ⚠️ Le service d'IA générative est momentanément indisponible. Réponse produite par le moteur d'analyse local, à partir des données réelles de la plateforme.\n\n" +
              offlineAnswer(snapshot, last.content, focus);
          controller.enqueue(encoder.encode(notice));
        } finally {
          controller.close();
        }
      },
    });
    return new Response(stream, { headers });
  } catch (e) {
    return errorResponse(e);
  }
}

export async function GET() {
  try {
    await requireUser();
    return Response.json(aiStatus());
  } catch (e) {
    return errorResponse(e);
  }
}
