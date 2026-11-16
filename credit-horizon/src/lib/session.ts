// Jetons de session (JWT HS256) – compatible Edge (middleware) et Node.
import { SignJWT, jwtVerify } from "jose";
import type { Role } from "./permissions";

export const SESSION_COOKIE = "ch_session";
export const SESSION_TTL_SECONDS = 60 * 60 * 8; // 8 heures

export interface SessionUser {
  id: number;
  email: string;
  name: string;
  role: Role;
}

const DEV_FALLBACK = "credit-horizon-dev-secret-change-me-0123456789";

export function authSecretConfigured() {
  return Boolean(process.env.AUTH_SECRET && process.env.AUTH_SECRET.length >= 16);
}

function key() {
  return new TextEncoder().encode(authSecretConfigured() ? process.env.AUTH_SECRET! : DEV_FALLBACK);
}

export async function signSession(u: SessionUser) {
  return new SignJWT({ email: u.email, name: u.name, role: u.role })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(String(u.id))
    .setIssuedAt()
    .setExpirationTime(`${SESSION_TTL_SECONDS}s`)
    .sign(key());
}

export async function verifySession(token?: string | null): Promise<SessionUser | null> {
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, key(), { algorithms: ["HS256"] });
    return { id: Number(payload.sub), email: String(payload.email), name: String(payload.name), role: payload.role as Role };
  } catch {
    return null;
  }
}
