import { z } from "zod";

const s = (max = 300) => z.string().trim().max(max).optional().default("");
const n = z.union([z.number(), z.string().trim().max(30)]).optional().default("");
const doc = z.enum(["oui", "non", "na", ""]).default("");

export const dossierSchema = z.object({
  company: z.object({
    name: z.string().trim().min(1, "raison sociale obligatoire").max(200),
    legal_form: s(50),
    rc_number: s(50),
    ice: s(30),
    creation_date: s(10),
    sector: s(120),
    activity: s(1000),
    city: s(80),
    manager_name: s(120),
    employees: n,
    name_on_documents: s(200),
  }),
  request: z.object({
    product: s(60),
    amount: n,
    duration_months: n,
    purpose: s(1000),
  }),
  financials: z.object({
    fiscal_year: s(10),
    revenue_n: n,
    revenue_n1: n,
    revenue_bank: n,
    net_result: n,
    equity: n,
    existing_debt: n,
    existing_monthly_installments: n,
  }),
  documents: z.record(z.string().max(40), doc),
  guarantees: z.object({ type: s(80), value: n, description: s(500) }),
  observations: z.string().trim().max(5000).default(""),
});

export type DossierPayload = z.infer<typeof dossierSchema>;
