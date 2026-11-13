import { NextResponse } from "next/server";
import { q } from "@/lib/db";
import { requireUser, errorResponse } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    await requireUser();
    const [components, principles] = await Promise.all([
      q("select * from coso_components order by id"),
      q("select * from coso_principles order by component_id, cast(substring(id from 2) as int)"),
    ]);
    return NextResponse.json({ components, principles });
  } catch (e) {
    return errorResponse(e);
  }
}
