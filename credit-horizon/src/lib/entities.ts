import "server-only";
import { z } from "zod";
import type { Permission } from "./permissions";

// Configuration déclarative des entités exposées par l'API CRUD générique.
const txt = (max = 4000) => z.string().trim().max(max).default("");
const req = (label: string, max = 500) => z.string().trim().min(1, `${label} obligatoire`).max(max);

export interface EntityConfig {
  table: string;
  label: string;
  schema: z.ZodObject<any>;
  writePerm: Permission;
  createPerm?: Permission;
  deletePerm: Permission;
  idPrefix: string;
  idPad: number;
  idSep?: string;
  orderBy: string;
  select?: string;
  extraCreate?: Record<string, (user: { name: string; email: string }) => unknown>;
}

export const ENTITIES: Record<string, EntityConfig> = {
  risks: {
    table: "risks",
    label: "Risque",
    idPrefix: "R",
    idPad: 2,
    orderBy: "id",
    select: "*, probability*gravity as score",
    writePerm: "risks.write",
    deletePerm: "risks.delete",
    schema: z.object({
      title: req("Intitulé du risque"),
      category: z.enum(["Crédit", "Liquidité", "Opérationnel", "Conformité", "Stratégique"]),
      event: req("Description de l'événement", 4000),
      causes: txt(),
      consequences: txt(),
      probability: z.coerce.number().int().min(1).max(5),
      gravity: z.coerce.number().int().min(1).max(5),
      justification: txt(),
      owner: req("Responsable"),
      control_ids: txt(200),
      coso_principles: txt(200),
      basis: z.enum(["Constat", "Hypothèse"]).default("Constat"),
      recommendation: txt(),
    }),
  },
  controls: {
    table: "controls",
    label: "Contrôle",
    idPrefix: "C",
    idPad: 2,
    orderBy: "id",
    writePerm: "controls.write",
    deletePerm: "controls.write",
    schema: z.object({
      name: req("Intitulé du contrôle"),
      nature: z.enum(["Préventif", "Détectif", "Correctif", "Détectif et correctif"]),
      objective: req("Objectif", 2000),
      risk_ids: txt(200),
      procedure: txt(),
      owner: req("Responsable"),
      supervision: txt(300),
      frequency: req("Fréquence"),
      evidence: txt(),
      indicator: txt(),
      anomaly_treatment: txt(),
      status: z.enum(["À concevoir", "En déploiement", "Opérationnel", "Efficace", "Déficient"]),
      last_review: z.string().trim().max(20).optional().nullable(),
    }),
  },
  recommendations: {
    table: "recommendations",
    label: "Recommandation",
    idPrefix: "REC",
    idPad: 2,
    orderBy: "id",
    writePerm: "recommendations.write",
    deletePerm: "recommendations.write",
    schema: z.object({
      risk_id: req("Risque"),
      coso_gap: req("Lacune COSO", 2000),
      action: req("Action corrective", 3000),
      owner: req("Responsable"),
      indicator: req("Indicateur de suivi", 1000),
      basis: z.enum(["Constat", "Hypothèse"]).default("Constat"),
      status: z.enum(["À lancer", "En cours", "Mise en œuvre", "Abandonnée"]),
    }),
  },
  actions: {
    table: "actions",
    label: "Action",
    idPrefix: "A",
    idPad: 2,
    orderBy: "priority, id",
    writePerm: "actions.write",
    deletePerm: "actions.write",
    schema: z.object({
      priority: z.enum(["P1", "P2", "P3"]),
      title: req("Intitulé"),
      owner: req("Responsable"),
      due: txt(100),
      deliverable: txt(500),
      risk_ids: txt(200),
      control_ids: txt(200),
      status: z.enum(["À faire", "En cours", "Terminé", "Bloqué"]),
      progress: z.coerce.number().int().min(0).max(100),
    }),
  },
  anomalies: {
    table: "anomalies",
    label: "Anomalie",
    idPrefix: "AN",
    idSep: "-",
    idPad: 3,
    orderBy: "detected_on desc, id desc",
    writePerm: "anomalies.write",
    createPerm: "anomalies.create",
    deletePerm: "anomalies.write",
    extraCreate: { declared_by: (u) => u.name },
    schema: z.object({
      detected_on: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "date au format AAAA-MM-JJ"),
      dossier_ref: txt(100),
      nature: req("Nature de l'anomalie", 2000),
      severity: z.enum(["Mineure", "Significative", "Majeure", "Critique"]),
      risk_id: txt(20),
      control_id: txt(20),
      owner: req("Responsable"),
      due_on: z.string().trim().max(10).default(""),
      status: z.enum(["Ouverte", "En cours", "Clôturée"]),
      escalation: z.coerce.number().int().min(1).max(3),
      resolution: txt(),
    }),
  },
};

export function getEntity(name: string): EntityConfig | null {
  return Object.prototype.hasOwnProperty.call(ENTITIES, name) ? ENTITIES[name] : null;
}
