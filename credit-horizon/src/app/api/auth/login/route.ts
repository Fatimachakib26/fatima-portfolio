import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { q, audit } from "@/lib/db";
import { errorResponse, HttpError } from "@/lib/auth";
import { signSession, SESSION_COOKIE, SESSION_TTL_SECONDS } from "@/lib/session";

export const dynamic = "force-dynamic";

// Limitation simple des tentatives (mémoire du processus) contre le brute force.
const attempts = new Map<string, { n: number; until: number }>();

export async function POST(req: Request) {
  try {
    const { email, password } = z
      .object({ email: z.string().trim().toLowerCase().email("e-mail invalide"), password: z.string().min(1).max(200) })
      .parse(await req.json());
    const a = attempts.get(email);
    if (a && a.until > Date.now()) throw new HttpError(429, "Trop de tentatives. Réessayez dans quelques minutes.");
    const [u] = await q<{ id: number; email: string; name: string; role: any; password_hash: string; active: boolean }>(
      "select * from users where email = $1",
      [email],
    );
    const ok = u && u.active && (await bcrypt.compare(password, u.password_hash));
    if (!ok) {
      const n = (a?.n ?? 0) + 1;
      attempts.set(email, { n, until: n >= 5 ? Date.now() + 5 * 60_000 : 0 });
      throw new HttpError(401, "Identifiants incorrects ou compte désactivé.");
    }
    attempts.delete(email);
    const token = await signSession({ id: u.id, email: u.email, name: u.name, role: u.role });
    await audit(u, "Connexion", "Session", String(u.id));
    const res = NextResponse.json({ ok: true, user: { id: u.id, email: u.email, name: u.name, role: u.role } });
    res.cookies.set(SESSION_COOKIE, token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: SESSION_TTL_SECONDS,
    });
    return res;
  } catch (e) {
    return errorResponse(e);
  }
}
