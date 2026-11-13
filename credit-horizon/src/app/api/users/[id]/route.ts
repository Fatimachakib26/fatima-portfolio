import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { q, audit } from "@/lib/db";
import { requireUser, errorResponse, HttpError } from "@/lib/auth";

export const dynamic = "force-dynamic";
type Ctx = { params: Promise<{ id: string }> };

export async function PUT(req: Request, ctx: Ctx) {
  try {
    const admin = await requireUser("users.manage");
    const id = Number((await ctx.params).id);
    const body = z
      .object({
        name: z.string().trim().min(2).max(120),
        role: z.enum(["admin", "directeur", "analyste", "commercial", "controleur"]),
        active: z.boolean(),
        password: z.string().min(8).max(200),
      })
      .partial()
      .parse(await req.json());
    if (id === admin.id && (body.active === false || (body.role && body.role !== "admin")))
      throw new HttpError(400, "Vous ne pouvez pas désactiver ou rétrograder votre propre compte administrateur.");
    const sets: string[] = [];
    const params: unknown[] = [id];
    for (const k of ["name", "role", "active"] as const) {
      if (body[k] !== undefined) {
        params.push(body[k]);
        sets.push(`${k} = $${params.length}`);
      }
    }
    if (body.password) {
      params.push(await bcrypt.hash(body.password, 10));
      sets.push(`password_hash = $${params.length}`);
    }
    if (!sets.length) throw new HttpError(400, "Aucune donnée.");
    const rows = await q(`update users set ${sets.join(", ")} where id = $1 returning id, email, name, role, active, is_demo, created_at`, params);
    if (!rows.length) throw new HttpError(404, "Utilisateur introuvable.");
    await audit(admin, "Modification", "Utilisateur", String(id), Object.keys(body).filter((k) => k !== "password").join(", ") + (body.password ? ", mot de passe" : ""));
    return NextResponse.json(rows[0]);
  } catch (e) {
    return errorResponse(e);
  }
}

export async function DELETE(_req: Request, ctx: Ctx) {
  try {
    const admin = await requireUser("users.manage");
    const id = Number((await ctx.params).id);
    if (id === admin.id) throw new HttpError(400, "Impossible de supprimer votre propre compte.");
    const rows = await q("delete from users where id = $1 returning email", [id]);
    if (!rows.length) throw new HttpError(404, "Utilisateur introuvable.");
    await audit(admin, "Suppression", "Utilisateur", rows[0].email);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return errorResponse(e);
  }
}
