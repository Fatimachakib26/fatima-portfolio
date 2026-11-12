import "server-only";
import bcrypt from "bcryptjs";
import path from "node:path";
import { SCHEMA_SQL } from "./schema";
import {
  SEED_RISKS,
  SEED_CONTROLS,
  SEED_COSO_COMPONENTS,
  SEED_COSO_PRINCIPLES,
  SEED_RECOMMENDATIONS,
  SEED_ACTIONS,
  SEED_ANOMALIES,
  SEED_HISTORY,
  SEED_HISTORY_MONTHS,
  DEMO_USERS,
  DEMO_PASSWORD,
} from "./seed-data";
import { SEED_DOSSIERS } from "./seed-dossiers";
import { analyzeDossier } from "./dossier-analysis";

/**
 * Couche d'accès PostgreSQL.
 *  - Production : DATABASE_URL (Supabase / tout PostgreSQL) via postgres.js
 *  - Démo locale : PostgreSQL embarqué (PGlite, WASM) persistant dans ./.data
 * Le même SQL paramétré ($1, $2…) est utilisé dans les deux cas.
 */

type Row = Record<string, any>;
interface Driver {
  kind: "postgres" | "pglite";
  query<T = Row>(sql: string, params?: unknown[]): Promise<T[]>;
  exec(sql: string): Promise<void>;
}

const g = globalThis as unknown as { __chDb?: Promise<Driver> };

async function createDriver(): Promise<Driver> {
  const url = process.env.DATABASE_URL;
  if (url) {
    const postgres = (await import("postgres")).default;
    const sql = postgres(url, { max: 5, prepare: false, idle_timeout: 20, ssl: url.includes("localhost") ? false : "require" });
    return {
      kind: "postgres",
      async query(text, params = []) {
        return (await sql.unsafe(text, params as any[])) as any;
      },
      async exec(text) {
        await sql.unsafe(text);
      },
    };
  }
  const { PGlite } = await import("@electric-sql/pglite");
  const dir = process.env.PGLITE_DIR || (process.env.VERCEL ? "/tmp/ch-pglite" : path.join(process.cwd(), ".data", "pglite"));
  (await import("node:fs")).mkdirSync(path.dirname(dir), { recursive: true });
  const db = new PGlite(dir);
  await db.waitReady;
  return {
    kind: "pglite",
    async query(text, params = []) {
      const r = await db.query(text, params as any[]);
      return r.rows as any;
    },
    async exec(text) {
      await db.exec(text);
    },
  };
}

async function init(): Promise<Driver> {
  const d = await createDriver();
  await d.exec(SCHEMA_SQL);
  const [{ n }] = await d.query<{ n: number }>("select count(*)::int as n from users");
  if (n === 0) await seed(d);
  return d;
}

export function getDb(): Promise<Driver> {
  if (!g.__chDb) {
    g.__chDb = init().catch((e) => {
      g.__chDb = undefined;
      throw e;
    });
  }
  return g.__chDb;
}

export async function q<T = Row>(sql: string, params: unknown[] = []): Promise<T[]> {
  const d = await getDb();
  return d.query<T>(sql, params);
}

export async function dbKind() {
  return (await getDb()).kind;
}

// ------------------------------------------------------------------ seed
export async function seed(d: Driver, opts: { keepUsers?: boolean } = {}) {
  if (!opts.keepUsers) {
    const hash = await bcrypt.hash(DEMO_PASSWORD, 10);
    for (const u of DEMO_USERS) {
      await d.query(
        "insert into users (email, name, role, password_hash, is_demo) values ($1,$2,$3,$4,true) on conflict (email) do nothing",
        [u.email, u.name, u.role, hash],
      );
    }
  }
  for (const r of SEED_RISKS) {
    await d.query(
      `insert into risks (id,title,category,event,causes,consequences,probability,gravity,justification,owner,control_ids,coso_principles,basis,recommendation,is_demo)
       values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,true)`,
      [r.id, r.title, r.category, r.event, r.causes, r.consequences, r.probability, r.gravity, r.justification, r.owner, r.control_ids, r.coso_principles, r.basis, r.recommendation],
    );
    const hist = SEED_HISTORY[r.id] || [];
    for (let i = 0; i < hist.length; i++) {
      const [p, gr] = hist[i];
      await d.query(
        "insert into risk_history (risk_id, probability, gravity, score, recorded_at, is_demo) values ($1,$2,$3,$4,$5,true)",
        [r.id, p, gr, p * gr, `${SEED_HISTORY_MONTHS[i]}-01T09:00:00Z`],
      );
    }
  }
  for (const c of SEED_CONTROLS) {
    await d.query(
      `insert into controls (id,name,nature,objective,risk_ids,procedure,owner,supervision,frequency,evidence,indicator,anomaly_treatment,status,is_demo)
       values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,true)`,
      [c.id, c.name, c.nature, c.objective, c.risk_ids, c.procedure, c.owner, c.supervision, c.frequency, c.evidence, c.indicator, c.anomaly_treatment, c.status],
    );
  }
  for (const c of SEED_COSO_COMPONENTS) {
    await d.query(
      `insert into coso_components (id,name,principles,question,findings,gaps,risk_ids,recommendations,owner,indicators,maturity,is_demo)
       values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,true)`,
      [c.id, c.name, c.principles, c.question, c.findings, c.gaps, c.risk_ids, c.recommendations, c.owner, c.indicators, c.maturity],
    );
  }
  for (const p of SEED_COSO_PRINCIPLES) {
    await d.query(
      `insert into coso_principles (id,component_id,title,nature,diagnostic,risk_ids,assessment,is_demo) values ($1,$2,$3,$4,$5,$6,$7,true)`,
      [p.id, p.component_id, p.title, p.nature, p.diagnostic, p.risk_ids, p.assessment],
    );
  }
  for (const r of SEED_RECOMMENDATIONS) {
    await d.query(
      `insert into recommendations (id,risk_id,coso_gap,action,owner,indicator,basis,status,is_demo) values ($1,$2,$3,$4,$5,$6,$7,$8,true)`,
      [r.id, r.risk_id, r.coso_gap, r.action, r.owner, r.indicator, r.basis, r.status],
    );
  }
  for (const a of SEED_ACTIONS) {
    await d.query(
      `insert into actions (id,priority,title,owner,due,deliverable,risk_ids,control_ids,status,progress,is_demo) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,true)`,
      [a.id, a.priority, a.title, a.owner, a.due, a.deliverable, a.risk_ids, a.control_ids, a.status, a.progress],
    );
  }
  for (const a of SEED_ANOMALIES) {
    await d.query(
      `insert into anomalies (id,detected_on,dossier_ref,nature,severity,risk_id,control_id,owner,due_on,status,escalation,resolution,declared_by,is_demo)
       values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,'Données de démonstration',true)`,
      [a.id, a.detected_on, a.dossier_ref, a.nature, a.severity, a.risk_id, a.control_id, a.owner, a.due_on, a.status, a.escalation, a.resolution],
    );
  }
  for (const ds of SEED_DOSSIERS) {
    const analysis = analyzeDossier(ds as any);
    await d.query(
      `insert into dossiers (id,company,request,financials,documents,guarantees,observations,analysis,status,created_by,is_demo)
       values ($1,$2::jsonb,$3::jsonb,$4::jsonb,$5::jsonb,$6::jsonb,$7,$8::jsonb,$9,'Données de démonstration',true)`,
      [ds.id, JSON.stringify(ds.company), JSON.stringify(ds.request), JSON.stringify(ds.financials), JSON.stringify(ds.documents), JSON.stringify(ds.guarantees), ds.observations, JSON.stringify(analysis), analysis.status],
    );
  }
}

/** Réinitialise toutes les données métier (les comptes utilisateurs sont conservés). */
export async function resetDemoData() {
  const d = await getDb();
  await d.exec(
    "delete from risk_history; delete from risks; delete from controls; delete from coso_principles; delete from coso_components; delete from recommendations; delete from actions; delete from anomalies; delete from dossiers;",
  );
  await seed(d, { keepUsers: true });
}

export async function audit(user: { email: string } | null, action: string, entity: string, entityId: string, details = "") {
  try {
    await q("insert into audit_log (user_email, action, entity, entity_id, details) values ($1,$2,$3,$4,$5)", [
      user?.email ?? "système",
      action,
      entity,
      entityId,
      details.slice(0, 2000),
    ]);
  } catch {
    /* l'audit ne doit jamais bloquer une opération métier */
  }
}

export async function nextId(table: string, prefix: string, pad: number, sep = "") {
  const rows = await q<{ id: string }>(`select id from ${table} where id like $1`, [`${prefix}${sep}%`]);
  let max = 0;
  for (const r of rows) {
    const n = parseInt(r.id.slice(prefix.length + sep.length), 10);
    if (!Number.isNaN(n) && n > max) max = n;
  }
  return `${prefix}${sep}${String(max + 1).padStart(pad, "0")}`;
}
