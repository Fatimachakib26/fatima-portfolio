import { NextResponse } from "next/server";
import { resetDemoData, audit } from "@/lib/db";
import { requireUser, errorResponse } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST() {
  try {
    const user = await requireUser("demo.reset");
    await resetDemoData();
    await audit(user, "Réinitialisation", "Données de démonstration", "*");
    return NextResponse.json({ ok: true });
  } catch (e) {
    return errorResponse(e);
  }
}
