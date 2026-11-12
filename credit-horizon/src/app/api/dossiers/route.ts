import { NextResponse } from "next/server";
import { q, audit } from "@/lib/db";
import { requireUser, errorResponse } from "@/lib/auth";
import { analyzeDossier } from "@/lib/dossier-analysis";
import { dossierSchema } from "@/lib/dossier-schema";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    await requireUser();
    const rows = await q("select * from dossiers order by created_at desc, id desc");
    return NextResponse.json(rows);
  } catch (e) {
    return errorResponse(e);
  }
}

export async function POST(req: Request) {
  try {
    const user = await requireUser("dossiers.write");
    const d = dossierSchema.parse(await req.json());
    const year = new Date().getFullYear();
    const existing = await q<{ id: string }>("select id from dossiers where id like $1", [`TPE-${year}-%`]);
    const max = existing.reduce((m, r) => Math.max(m, parseInt(r.id.split("-")[2], 10) || 0), 0);
    const id = `TPE-${year}-${String(max + 1).padStart(3, "0")}`;
    const analysis = analyzeDossier(d as any);
    const [row] = await q(
      `insert into dossiers (id,company,request,financials,documents,guarantees,observations,analysis,status,created_by)
       values ($1,$2::jsonb,$3::jsonb,$4::jsonb,$5::jsonb,$6::jsonb,$7,$8::jsonb,$9,$10) returning *`,
      [id, JSON.stringify(d.company), JSON.stringify(d.request), JSON.stringify(d.financials), JSON.stringify(d.documents), JSON.stringify(d.guarantees), d.observations, JSON.stringify(analysis), analysis.status, user.name],
    );
    await audit(user, "Création + analyse", "Dossier TPE", id, analysis.status);
    return NextResponse.json(row, { status: 201 });
  } catch (e) {
    return errorResponse(e);
  }
}
