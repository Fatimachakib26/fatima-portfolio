import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { q, audit } from "@/lib/db";
import { requireUser, errorResponse, HttpError } from "@/lib/auth";

export const dynamic = "force-dynamic";

const roleEnum = z.enum(["admin", "directeur", "analyste", "commercial", "controleur"]);

export async function GET() {
  try {
    await requireUser("users.manage");
    return NextResponse.json(await q("select id, email, name, role, active, is_demo, created_at from users order by id"));
  } catch (e) {
    return errorResponse(e);
  }
}

export async function POST(req: Request) {
  try {
    const admin = await requireUser("users.manage");
    const body = z
      .object({
        email: z.string().trim().toLowerCase().email("e-mail invalide"),
        name: z.string().trim().min(2).max(120),
        role: roleEnum,
        password: z.string().min(8, "mot de passe : 8 caractères minimum").max(200),
      })
      .parse(await req.json());
    const exists = await q("select 1 from users where email = $1", [body.email]);
    if (exists.length) throw new HttpError(409, "Un compte existe déjà avec cet e-mail.");
    const hash = await bcrypt.hash(body.password, 10);
    const [row] = await q(
      "insert into users (email, name, role, password_hash) values ($1,$2,$3,$4) returning id, email, name, role, active, is_demo, created_at",
      [body.email, body.name, body.role, hash],
    );
    await audit(admin, "Création", "Utilisateur", body.email, `Rôle : ${body.role}`);
    return NextResponse.json(row, { status: 201 });
  } catch (e) {
    return errorResponse(e);
  }
}
