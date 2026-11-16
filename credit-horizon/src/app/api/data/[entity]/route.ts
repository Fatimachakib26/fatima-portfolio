import { NextResponse } from "next/server";
import { q, audit, nextId } from "@/lib/db";
import { requireUser, errorResponse, HttpError } from "@/lib/auth";
import { getEntity } from "@/lib/entities";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, ctx: { params: Promise<{ entity: string }> }) {
  try {
    await requireUser();
    const { entity } = await ctx.params;
    const cfg = getEntity(entity);
    if (!cfg) throw new HttpError(404, "Entité inconnue.");
    const rows = await q(`select ${cfg.select ?? "*"} from ${cfg.table} order by ${cfg.orderBy}`);
    return NextResponse.json(rows);
  } catch (e) {
    return errorResponse(e);
  }
}

export async function POST(req: Request, ctx: { params: Promise<{ entity: string }> }) {
  try {
    const { entity } = await ctx.params;
    const cfg = getEntity(entity);
    if (!cfg) throw new HttpError(404, "Entité inconnue.");
    const user = await requireUser(cfg.createPerm ?? cfg.writePerm);
    const data = cfg.schema.parse(await req.json()) as Record<string, unknown>;
    for (const [k, fn] of Object.entries(cfg.extraCreate ?? {})) data[k] = fn(user);
    const id = await nextId(cfg.table, cfg.idPrefix, cfg.idPad, cfg.idSep);
    const cols = ["id", ...Object.keys(data)];
    const vals = [id, ...Object.values(data)];
    const ph = cols.map((_, i) => `$${i + 1}`).join(",");
    const [row] = await q(`insert into ${cfg.table} (${cols.join(",")}) values (${ph}) returning ${cfg.select ?? "*"}`, vals);
    if (entity === "risks") {
      await q("insert into risk_history (risk_id, probability, gravity, score) values ($1,$2,$3,$4)", [
        id,
        data.probability,
        data.gravity,
        Number(data.probability) * Number(data.gravity),
      ]);
    }
    await audit(user, "Création", cfg.label, id, JSON.stringify(data).slice(0, 500));
    return NextResponse.json(row, { status: 201 });
  } catch (e) {
    return errorResponse(e);
  }
}
