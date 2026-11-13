// Palette catégorielle validée (contrôle daltonisme / contraste) – ordre fixe, jamais cyclé.
export const CATEGORY_COLORS: Record<string, string> = {
  Crédit: "#2a78d6",
  Liquidité: "#eb6834",
  Opérationnel: "#1baf7a",
  Conformité: "#6250d6",
  Stratégique: "#e87ba4",
};
export const CATEGORIES = Object.keys(CATEGORY_COLORS);
export const SERIES = { primary: "#0f7a58", secondary: "#2a78d6" };
