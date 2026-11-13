"""Méthode de cotation du rapport EMSI (section 3.4) : criticité = P × G (1 à 25)."""

LEVELS = ["Faible", "Modéré", "Élevé", "Critique"]
LEVEL_COLORS = {"Faible": "#16a34a", "Modéré": "#eab308", "Élevé": "#f97316", "Critique": "#dc2626"}
LEVEL_TREATMENT = {
    "Faible": "Acceptable ; surveillance courante.",
    "Modéré": "Acceptable sous contrôle ; indicateur de suivi attribué.",
    "Élevé": "Mesure de maîtrise prioritaire ; revue trimestrielle par la direction des risques.",
    "Critique": "Renforcement immédiat ; plan d'action et suivi par la direction générale.",
}
PROBABILITY_SCALE = {
    1: ("Très improbable", "Aucun indice dans le cas ; événement exceptionnel."),
    2: ("Peu probable", "Situation possible mais non établie ; dépend d'une condition supplémentaire."),
    3: ("Possible", "Conditions partiellement réunies ; indices indirects."),
    4: ("Probable", "Dysfonctionnement établi ; les incitations jouent dans le sens du risque."),
    5: ("Quasi certain", "Défaut déjà observé ; aucune mesure n'en empêche la répétition."),
}
GRAVITY_SCALE = {
    1: ("Mineure", "Impact absorbable ; correction simple."),
    2: ("Limitée", "Impact local sur un dossier ou une équipe."),
    3: ("Significative", "Impact sur plusieurs dossiers ou la fiabilité du suivi."),
    4: ("Majeure", "Impact sur la qualité du portefeuille, la liquidité ou la conformité."),
    5: ("Critique", "Menace la stratégie, la liquidité ou la réputation de façon durable."),
}
CATEGORIES = ["Crédit", "Liquidité", "Opérationnel", "Conformité", "Stratégique"]
# Palette catégorielle validée (daltonisme / contraste), ordre fixe
CATEGORY_COLORS = {"Crédit": "#2a78d6", "Liquidité": "#eb6834", "Opérationnel": "#1baf7a", "Conformité": "#6250d6", "Stratégique": "#e87ba4"}


def clamp(v) -> int:
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        v = 1
    return max(1, min(5, v))


def score(p, g) -> int:
    return clamp(p) * clamp(g)


def level(s: int) -> str:
    if s >= 16:
        return "Critique"
    if s >= 10:
        return "Élevé"
    if s >= 5:
        return "Modéré"
    return "Faible"


def appetite_zone(lvl: str) -> str:
    return {"Critique": "inacceptable", "Élevé": "renforcee"}.get(lvl, "acceptable")
