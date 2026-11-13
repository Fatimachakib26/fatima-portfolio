import { NextResponse } from "next/server";
import { dbKind } from "@/lib/db";
import { aiStatus } from "@/lib/ai";
import { authSecretConfigured } from "@/lib/session";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const db = await dbKind();
    return NextResponse.json({ ok: true, database: db, ai: aiStatus(), authSecret: authSecretConfigured() });
  } catch (e) {
    console.error("[health] base de données indisponible :", e);
    return NextResponse.json({ ok: false, error: "Base de données indisponible." }, { status: 503 });
  }
}
