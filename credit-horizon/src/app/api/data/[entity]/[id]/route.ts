import { NextResponse } from "next/server";
import { q, audit } from "@/lib/db";
import { requireUser, errorResponse, HttpError } from "@/lib/auth";
import { getEntity } from "@/lib/entities";

export const dynamic = "force-dynamic";
type Ctx = { params: Promise<{ entity: string; id: string }> };

export async function PUT(req: Request, ctx: Ctx) {
  try {
    const { entity, id } = await ctx.params;
    const cfg = getEntity(entity);
    if (!cfg) throw new HttpError(404, "Entité inconnue.");
    const user = await requireUser(cfg.writePerm);
    const parsed = cfg.schema.partial().parse(await req.json()) as Record<string, unknown>;
    const keys = Object.keys(parsed).filter((k) => parsed[k] !== undefined);
    if (!keys.length) throw new HttpError(400, "Aucune donnée à mettre à jour.");
    const [before] = await q(`select * from ${cfg.table} where id = $1`, [id]);
    if (!before) throw new HttpError(404, `${cfg.label} introuvable.`);
    const sets = keys.map((k, i) => `${k} = $${i + 2}`);
    if ("updated_at" in before) sets.push("updated_at = now()");
    const params: unknown[] = [id, ...keys.map((k) => parsed[k])];
    if (entity === "risks") {
      params.push(user.email);
      sets.push(`updated_by = $${params.length}`);
    }
    const [row] = await q(`update ${cfg.table} set ${sets.join(", ")} where id = $1 returning ${cfg.select ?? "*"}`, params);
    if (
      entity === "risks" &&
      (Number(before.probability) !== Number(row.probability) || Number(before.gravity) !== Number(row.gravity))
    ) {
      await q("insert into risk_history (risk_id, probability, gravity, score) values ($1,$2,$3,$4)", [
        id,
        row.probability,
        row.gravity,
        Number(row.probability) * Number(row.gravity),
      ]);
    }
    const changed = keys.filter((k) => String(before[k] ?? "") !== String(parsed[k] ?? "")).join(", ");
    await audit(user, "Modification", cfg.label, id, changed ? `Champs modifiés : ${changed}` : "Aucun changement");
    return NextResponse.json(row);
  } catch (e) {
    return errorResponse(e);
  }
}

export async function DELETE(_req: Request, ctx: Ctx) {
  try {
    const { entity, id } = await ctx.params;
    const cfg = getEntity(entity);
    if (!cfg) throw new HttpError(404, "Entité inconnue.");
    const user = await requireUser(cfg.deletePerm);
    const rows = await q(`delete from ${cfg.table} where id = $1 returning id`, [id]);
    if (!rows.length) throw new HttpError(404, `${cfg.label} introuvable.`);
    if (entity === "risks") await q("delete from risk_history where risk_id = $1", [id]);
    await audit(user, "Suppression", cfg.label, id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return errorResponse(e);
  }
}
