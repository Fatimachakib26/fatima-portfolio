import { NextResponse } from "next/server";
import { q, audit } from "@/lib/db";
import { requireUser, errorResponse, HttpError } from "@/lib/auth";
import { analyzeDossier } from "@/lib/dossier-analysis";
import { dossierSchema } from "@/lib/dossier-schema";

export const dynamic = "force-dynamic";
type Ctx = { params: Promise<{ id: string }> };

export async function GET(_req: Request, ctx: Ctx) {
  try {
    await requireUser();
    const { id } = await ctx.params;
    const [row] = await q("select * from dossiers where id = $1", [id]);
    if (!row) throw new HttpError(404, "Dossier introuvable.");
    return NextResponse.json(row);
  } catch (e) {
    return errorResponse(e);
  }
}

export async function PUT(req: Request, ctx: Ctx) {
  try {
    const user = await requireUser("dossiers.write");
    const { id } = await ctx.params;
    const d = dossierSchema.parse(await req.json());
    const analysis = analyzeDossier(d as any);
    const rows = await q(
      `update dossiers set company=$2::text::jsonb, request=$3::text::jsonb, financials=$4::text::jsonb, documents=$5::text::jsonb, guarantees=$6::text::jsonb,
       observations=$7, analysis=$8::text::jsonb, status=$9, updated_at=now() where id=$1 returning *`,
      [id, JSON.stringify(d.company), JSON.stringify(d.request), JSON.stringify(d.financials), JSON.stringify(d.documents), JSON.stringify(d.guarantees), d.observations, JSON.stringify(analysis), analysis.status],
    );
    if (!rows.length) throw new HttpError(404, "Dossier introuvable.");
    await audit(user, "Modification + réanalyse", "Dossier TPE", id, analysis.status);
    return NextResponse.json(rows[0]);
  } catch (e) {
    return errorResponse(e);
  }
}

export async function DELETE(_req: Request, ctx: Ctx) {
  try {
    const user = await requireUser("dossiers.write");
    const { id } = await ctx.params;
    const rows = await q("delete from dossiers where id = $1 returning id", [id]);
    if (!rows.length) throw new HttpError(404, "Dossier introuvable.");
    await audit(user, "Suppression", "Dossier TPE", id);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return errorResponse(e);
  }
}
