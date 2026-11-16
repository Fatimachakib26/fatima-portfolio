import { NextResponse } from "next/server";
import { q } from "@/lib/db";
import { requireUser, errorResponse } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    await requireUser("audit.view");
    return NextResponse.json(await q("select * from audit_log order by at desc, id desc limit 200"));
  } catch (e) {
    return errorResponse(e);
  }
}
