import { NextResponse } from "next/server";
import { requireUser, errorResponse } from "@/lib/auth";
import { getSnapshot, computeKpis } from "@/lib/snapshot";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    await requireUser();
    const s = await getSnapshot();
    return NextResponse.json({ ...s, kpis: computeKpis(s) });
  } catch (e) {
    return errorResponse(e);
  }
}
