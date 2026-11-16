import { NextResponse } from "next/server";
import { getSessionUser, errorResponse } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const u = await getSessionUser();
    if (!u) return NextResponse.json({ error: "Non authentifié." }, { status: 401 });
    return NextResponse.json(u);
  } catch (e) {
    return errorResponse(e);
  }
}
