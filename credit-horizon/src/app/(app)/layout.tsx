import { redirect } from "next/navigation";
import Shell from "@/components/Shell";
import { getSessionUser } from "@/lib/auth";
import { dbKind } from "@/lib/db";
import { aiStatus } from "@/lib/ai";
import { authSecretConfigured } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  const warnings: string[] = [];
  const kind = await dbKind();
  if (kind === "pglite") warnings.push("Base embarquée (PGlite)");
  if (aiStatus().provider === "offline") warnings.push("IA : mode hors ligne");
  if (!authSecretConfigured() && process.env.NODE_ENV === "production") warnings.push("AUTH_SECRET non configuré");
  return (
    <Shell user={user} warnings={warnings}>
      {children}
    </Shell>
  );
}
