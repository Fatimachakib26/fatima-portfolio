import "server-only";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE, verifySession, type SessionUser } from "./session";
import { can, type Permission } from "./permissions";
import { q } from "./db";

export async function getSessionUser(): Promise<SessionUser | null> {
  const jar = await cookies();
  const s = await verifySession(jar.get(SESSION_COOKIE)?.value);
  if (!s) return null;
  // Vérifie que le compte existe toujours et est actif ; le rôle fait foi en base.
  const rows = await q<{ id: number; email: string; name: string; role: any; active: boolean }>(
    "select id, email, name, role, active from users where id = $1",
    [s.id],
  );
  const u = rows[0];
  if (!u || !u.active) return null;
  return { id: u.id, email: u.email, name: u.name, role: u.role };
}

export class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function requireUser(perm?: Permission): Promise<SessionUser> {
  const u = await getSessionUser();
  if (!u) throw new HttpError(401, "Session expirée ou absente. Veuillez vous reconnecter.");
  if (perm && !can(u.role, perm)) throw new HttpError(403, "Action non autorisée pour votre rôle (séparation des tâches).");
  return u;
}

export function errorResponse(e: unknown) {
  if (e instanceof HttpError) return NextResponse.json({ error: e.message }, { status: e.status });
  if (e && typeof e === "object" && "issues" in (e as any)) {
    const issues = (e as any).issues as { path: (string | number)[]; message: string }[];
    return NextResponse.json({ error: "Données invalides : " + issues.map((i) => `${i.path.join(".")} – ${i.message}`).join(" ; ") }, { status: 400 });
  }
  console.error(e);
  return NextResponse.json({ error: "Erreur interne du serveur. Veuillez réessayer." }, { status: 500 });
}
