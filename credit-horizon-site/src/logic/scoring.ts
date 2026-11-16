// Méthode de cotation du rapport EMSI (section 3.4) : Criticité = P × G (1 à 25)
// Seuils (tableau 3.3) : 1-4 Faible · 5-9 Modéré · 10-15 Élevé · 16-25 Critique

export type Level = "Faible" | "Modéré" | "Élevé" | "Critique";

export const LEVELS: Level[] = ["Faible", "Modéré", "Élevé", "Critique"];

export function computeScore(p: number, g: number): number {
  return clamp(p) * clamp(g);
}

function clamp(n: number) {
  const v = Math.round(Number(n) || 0);
  return Math.min(5, Math.max(1, v));
}

export function levelFromScore(score: number): Level {
  if (score >= 16) return "Critique";
  if (score >= 10) return "Élevé";
  if (score >= 5) return "Modéré";
  return "Faible";
}

export const LEVEL_STYLE: Record<Level, { bg: string; text: string; ring: string; hex: string; soft: string }> = {
  Faible: { bg: "bg-emerald-500", text: "text-emerald-700", ring: "ring-emerald-200", hex: "#16a34a", soft: "bg-emerald-50" },
  Modéré: { bg: "bg-yellow-400", text: "text-yellow-700", ring: "ring-yellow-200", hex: "#eab308", soft: "bg-yellow-50" },
  Élevé: { bg: "bg-orange-500", text: "text-orange-700", ring: "ring-orange-200", hex: "#f97316", soft: "bg-orange-50" },
  Critique: { bg: "bg-red-600", text: "text-red-700", ring: "ring-red-200", hex: "#dc2626", soft: "bg-red-50" },
};

export const LEVEL_TREATMENT: Record<Level, string> = {
  Faible: "Acceptable ; surveillance courante.",
  Modéré: "Acceptable sous contrôle ; indicateur de suivi attribué.",
  Élevé: "Mesure de maîtrise prioritaire ; revue trimestrielle par la direction des risques.",
  Critique: "Renforcement immédiat ; plan d'action et suivi par la direction générale.",
};

export const PROBABILITY_SCALE = [
  { v: 1, label: "Très improbable", desc: "Aucun indice dans le cas ; événement exceptionnel." },
  { v: 2, label: "Peu probable", desc: "Situation possible mais non établie ; dépend d'une condition supplémentaire." },
  { v: 3, label: "Possible", desc: "Conditions partiellement réunies ; indices indirects." },
  { v: 4, label: "Probable", desc: "Dysfonctionnement établi ; les incitations jouent dans le sens du risque." },
  { v: 5, label: "Quasi certain", desc: "Défaut déjà observé ; aucune mesure n'en empêche la répétition." },
];

export const GRAVITY_SCALE = [
  { v: 1, label: "Mineure", desc: "Impact absorbable dans le fonctionnement courant ; correction simple." },
  { v: 2, label: "Limitée", desc: "Impact local sur un dossier ou une équipe ; correction rapide." },
  { v: 3, label: "Significative", desc: "Impact sur plusieurs dossiers ou la fiabilité du suivi ; effet financier modéré." },
  { v: 4, label: "Majeure", desc: "Impact sur la qualité du portefeuille, la liquidité ou la conformité." },
  { v: 5, label: "Critique", desc: "Menace la stratégie, la liquidité ou la réputation de façon durable." },
];

/** Appétence (lecture applicative de la charte, art. 5 et tableau 3.3). */
export type AppetiteZone = "acceptable" | "renforcee" | "inacceptable";
export function appetiteFromLevel(level: Level): AppetiteZone {
  if (level === "Critique") return "inacceptable";
  if (level === "Élevé") return "renforcee";
  return "acceptable";
}
