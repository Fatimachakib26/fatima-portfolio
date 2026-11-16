import { NextResponse } from "next/server";
import { z } from "zod";
import { q, audit } from "@/lib/db";
import { requireUser, errorResponse, HttpError } from "@/lib/auth";

export const dynamic = "force-dynamic";
const t = z.string().trim().max(4000);

const componentSchema = z
  .object({
    findings: t,
    gaps: t,
    risk_ids: t,
    recommendations: t,
    owner: t,
    indicators: t,
    maturity: z.coerce.number().int().min(1).max(5),
  })
  .partial();

const principleSchema = z
  .object({
    nature: z.enum(["Constat", "Hypothèse à vérifier", "Constat et hypothèse"]),
    diagnostic: t,
    risk_ids: t,
    assessment: z.enum(["Non évalué", "Déficient", "Partiel", "Satisfaisant"]),
  })
  .partial();

export async function PUT(req: Request, ctx: { params: Promise<{ kind: string; id: string }> }) {
  try {
    const user = await requireUser("coso.write");
    const { kind, id } = await ctx.params;
    const isComp = kind === "components";
    if (!isComp && kind !== "principles") throw new HttpError(404, "Ressource inconnue.");
    const data = (isComp ? componentSchema : principleSchema).parse(await req.json()) as Record<string, unknown>;
    const keys = Object.keys(data).filter((k) => data[k] !== undefined);
    if (!keys.length) throw new HttpError(400, "Aucune donnée.");
    const table = isComp ? "coso_components" : "coso_principles";
    const rows = await q(
      `update ${table} set ${keys.map((k, i) => `${k} = $${i + 2}`).join(", ")}, updated_at = now() where id = $1 returning *`,
      [isComp ? Number(id) : id, ...keys.map((k) => data[k])],
    );
    if (!rows.length) throw new HttpError(404, "Élément COSO introuvable.");
    await audit(user, "Modification", isComp ? "Composante COSO" : "Principe COSO", id, `Champs : ${keys.join(", ")}`);
    return NextResponse.json(rows[0]);
  } catch (e) {
    return errorResponse(e);
  }
}
