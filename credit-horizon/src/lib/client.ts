"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { Role } from "./permissions";

export interface ClientUser {
  id: number;
  email: string;
  name: string;
  role: Role;
}

export const UserContext = createContext<ClientUser | null>(null);
export function useUser() {
  const u = useContext(UserContext);
  if (!u) throw new Error("UserContext manquant");
  return u;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T = any>(url: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init || {};
  let res: Response;
  try {
    res = await fetch(url, {
      ...rest,
      headers: { ...(json !== undefined ? { "Content-Type": "application/json" } : {}), ...(rest.headers || {}) },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Connexion au serveur impossible. Vérifiez votre réseau.");
  }
  if (res.status === 401 && typeof window !== "undefined" && !url.includes("/api/auth/login")) {
    window.location.href = "/login?expired=1";
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, (data as any)?.error || `Erreur ${res.status}`);
  return data as T;
}

export function useApi<T = any>(url: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!url) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api<T>(url));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [url]);
  useEffect(() => {
    reload();
  }, [reload]);
  return { data, error, loading, reload, setData };
}

export const fmtMAD = (n: unknown) => {
  const v = Number(n);
  return Number.isFinite(v) && String(n) !== "" ? new Intl.NumberFormat("fr-MA", { maximumFractionDigits: 0 }).format(v) + " MAD" : "–";
};
export const fmtDate = (s?: string | null) => (s ? new Date(s).toLocaleDateString("fr-FR") : "–");
export const fmtDateTime = (s?: string | null) => (s ? new Date(s).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "–");
export const splitIds = (v: unknown) => String(v ?? "").split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);
