export type Role = "admin" | "directeur" | "analyste" | "commercial" | "controleur";

export const ROLES: { id: Role; label: string; description: string }[] = [
  { id: "admin", label: "Administrateur", description: "Gestion complète de la plateforme et des utilisateurs." },
  { id: "directeur", label: "Directeur", description: "Pilotage, arbitrages, validation du plan d'action." },
  { id: "analyste", label: "Analyste risques", description: "Registre, cartographie, analyse des dossiers, anomalies." },
  { id: "commercial", label: "Commercial", description: "Constitution des dossiers TPE, déclaration d'anomalies." },
  { id: "controleur", label: "Contrôleur interne", description: "Contrôles, diagnostic COSO, revue indépendante." },
];

export const ROLE_LABEL: Record<Role, string> = Object.fromEntries(ROLES.map((r) => [r.id, r.label])) as Record<Role, string>;

export type Permission =
  | "risks.write"
  | "risks.delete"
  | "controls.write"
  | "coso.write"
  | "actions.write"
  | "recommendations.write"
  | "anomalies.create"
  | "anomalies.write"
  | "dossiers.write"
  | "appetite.write"
  | "users.manage"
  | "audit.view"
  | "demo.reset";

// Matrice des permissions : traduit la séparation des tâches du RACI (section 4.4).
// Ex. : le commercial constitue les dossiers mais ne modifie ni le registre ni les contrôles.
const MATRIX: Record<Permission, Role[]> = {
  "risks.write": ["admin", "analyste"],
  "risks.delete": ["admin", "analyste"],
  "controls.write": ["admin", "controleur"],
  "coso.write": ["admin", "controleur"],
  "actions.write": ["admin", "directeur", "analyste", "controleur"],
  "recommendations.write": ["admin", "analyste", "controleur"],
  "anomalies.create": ["admin", "directeur", "analyste", "commercial", "controleur"],
  "anomalies.write": ["admin", "directeur", "analyste", "controleur"],
  "dossiers.write": ["admin", "analyste", "commercial"],
  "appetite.write": ["admin", "directeur"],
  "users.manage": ["admin"],
  "audit.view": ["admin", "directeur", "controleur"],
  "demo.reset": ["admin"],
};

export function can(role: Role | undefined | null, perm: Permission): boolean {
  if (!role) return false;
  return MATRIX[perm].includes(role);
}

export function permissionMatrix() {
  return MATRIX;
}
