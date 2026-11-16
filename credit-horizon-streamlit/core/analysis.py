"""Analyse des dossiers TPE (module 4) – outille le contrôle C01 et la grille de vérification (tableau 5.5).

IMPORTANT : ce moteur NE PREND AUCUNE DÉCISION D'OCTROI. Il produit une aide à l'analyse, transmise à la
fonction risques pour avis, puis à l'instance délégataire (contrôle C02).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

PRODUCTS = ["Crédit d'investissement", "Crédit d'équipement", "Crédit de fonctionnement", "Microcrédit"]
GUARANTEE_TYPES = ["Aucune", "Caution personnelle du dirigeant", "Nantissement de fonds de commerce", "Nantissement de matériel",
                   "Hypothèque", "Garantie d'un fonds de garantie public"]
LEGAL_FORMS = ["SARL", "SARLAU", "SA", "SNC", "Entreprise individuelle", "Auto-entrepreneur", "Coopérative"]

CHECKLIST = [
    ("doc_form", "Formulaire de demande signé", "Tous", "avant_avis"),
    ("doc_id", "Pièce d'identité du dirigeant / représentant", "Tous", "avant_avis"),
    ("doc_company", "Documents d'identification de l'entreprise (RC, ICE, statuts)", "Tous", "avant_avis"),
    ("doc_activity", "Justificatifs d'activité et de revenus", "Tous", "avant_avis"),
    ("doc_financial", "Relevés ou justificatifs financiers disponibles", "Selon le produit", "avant_avis"),
    ("doc_schedule", "Échéancier et objet du financement", "Tous", "avant_avis"),
    ("doc_guarantee", "Justificatifs des garanties, si applicables", "Crédits garantis", "avant_avis"),
    ("doc_contact", "Coordonnées et informations de contact", "Tous", "avant_avis"),
    ("check_concordance", "Concordance des noms, montants, dates et données", "Tous", "avant_avis"),
    ("check_mandatory", "Vérification des pièces obligatoires selon le type de crédit", "Tous", "avant_avis"),
    ("risk_opinion", "Avis de la fonction risques joint au dossier", "Tous", "avant_decision"),
    ("decision_delegation", "Décision et délégation d'autorisation conformes", "Tous", "avant_decision"),
]

# Seuils INDICATIFS de démonstration (le cas n'en fixe aucun) – à valider par la direction.
THRESHOLDS = {
    "amount_to_revenue": 0.5, "debt_service_to_revenue": 0.3, "revenue_gap_bank": 0.2, "revenue_drop": 0.2,
    "leverage": 3.0, "young_company_years": 2, "short_term_max_months": 24, "indicative_rate": 0.08,
}

DISCLAIMER = ("Aide à l'analyse uniquement. Cette synthèse ne constitue en aucun cas une décision d'octroi : la décision relève "
              "de l'instance délégataire, après avis indépendant de la fonction risques (contrôle C02). Les seuils utilisés sont "
              "indicatifs et doivent être validés par la direction.")


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ") + " MAD"


def pct(n: float) -> str:
    return f"{n * 100:.1f} %".replace(".", ",")


def _norm(s: str | None) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\b(sarl|sarlau|sa|sas|snc|au|ste|societe)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def monthly_installment(amount: float, months: float, rate: float = THRESHOLDS["indicative_rate"]) -> float:
    if months <= 0:
        return 0.0
    r = rate / 12
    return amount / months if r == 0 else amount * r / (1 - (1 + r) ** -months)


def is_required(key: str, d: dict) -> bool:
    if key == "doc_guarantee":
        return (d.get("guarantees") or {}).get("type") not in (None, "", "Aucune")
    if key == "doc_financial":
        return (d.get("request") or {}).get("product") != "Microcrédit"
    return True


def analyze_dossier(d: dict, today: date | None = None) -> dict:
    today = today or date.today()
    c, rq, f, g = d.get("company", {}), d.get("request", {}), d.get("financials", {}), d.get("guarantees", {}) or {}
    docs = d.get("documents", {}) or {}
    missing_info, incoh, vigil, ratios, risks = [], [], [], [], set()

    def add(lst, code, msg, sev, risk):
        lst.append({"code": code, "message": msg, "severity": sev, "risk": risk})

    # 1. Complétude documentaire (C01)
    required = [x for x in CHECKLIST if x[3] == "avant_avis" and is_required(x[0], d)]
    missing_docs = [x[1] for x in required if docs.get(x[0]) != "oui"]
    present = len(required) - len(missing_docs)
    rate = round(present / len(required) * 100) if required else 0
    pending = [x[1] for x in CHECKLIST if x[3] == "avant_decision" and docs.get(x[0]) != "oui"]
    if missing_docs:
        risks.add("R01")

    # 2. Informations manquantes
    for v, label in [
        (c.get("name"), "Raison sociale"), (c.get("legal_form"), "Forme juridique"), (c.get("rc_number"), "Numéro de registre de commerce"),
        (c.get("ice"), "Identifiant commun de l'entreprise (ICE)"), (c.get("creation_date"), "Date de création"), (c.get("sector"), "Secteur d'activité"),
        (c.get("activity"), "Description de l'activité"), (c.get("manager_name"), "Nom du dirigeant"), (rq.get("product"), "Type de financement"),
        (num(rq.get("amount")), "Montant demandé"), (num(rq.get("duration_months")), "Durée du financement"), (rq.get("purpose"), "Objet du financement"),
        (num(f.get("revenue_n")), "Chiffre d'affaires du dernier exercice"), (num(f.get("net_result")), "Résultat net du dernier exercice"),
        (num(f.get("equity")), "Fonds propres"),
    ]:
        if v is None or v == "":
            add(missing_info, "MISSING", f"{label} non renseigné(e).", "attention", "R01")
    if not g.get("type"):
        add(missing_info, "MISSING_GUAR", "Nature de la garantie non précisée (indiquer « Aucune » le cas échéant).", "attention", "R01")
    if len((d.get("observations") or "").strip()) < 20:
        add(missing_info, "MISSING_OBS", "Observations de l'analyste absentes ou trop succinctes : l'analyse doit être motivée et traçable.", "info", "R02")
    if missing_info:
        risks.add("R01")

    amount, months = num(rq.get("amount")), num(rq.get("duration_months"))
    ca, ca1, ca_bank = num(f.get("revenue_n")), num(f.get("revenue_n1")), num(f.get("revenue_bank"))
    result, equity = num(f.get("net_result")), num(f.get("equity"))
    debt = num(f.get("existing_debt")) or 0.0
    existing_monthly = num(f.get("existing_monthly_installments")) or 0.0
    g_value, g_type = num(g.get("value")), g.get("type") or ""

    # 3. Incohérences
    if amount is not None and amount <= 0:
        add(incoh, "AMOUNT", "Le montant demandé doit être strictement positif.", "alerte", "R01")
    if months is not None and (months <= 0 or months > 240):
        add(incoh, "DURATION", "Durée de financement hors bornes plausibles (1 à 240 mois).", "alerte", "R01")
    creation = None
    if c.get("creation_date"):
        try:
            creation = datetime.strptime(str(c["creation_date"])[:10], "%Y-%m-%d").date()
            if creation > today:
                add(incoh, "CREATION_FUTURE", "La date de création de l'entreprise est postérieure à la date du jour.", "alerte", "R01")
        except ValueError:
            add(incoh, "CREATION_FORMAT", "Date de création illisible (format attendu AAAA-MM-JJ).", "attention", "R01")
    if c.get("name_on_documents") and c.get("name") and _norm(c["name_on_documents"]) != _norm(c["name"]):
        add(incoh, "NAME_MISMATCH", f"La raison sociale figurant sur les pièces (« {c['name_on_documents']} ») diffère de celle du formulaire (« {c['name']} »).", "alerte", "R01")
    if ca and ca_bank is not None and ca > 0:
        gap = abs(ca - ca_bank) / ca
        ratios.append(("Écart CA déclaré / CA relevés bancaires", pct(gap)))
        if gap > THRESHOLDS["revenue_gap_bank"]:
            add(incoh, "REVENUE_GAP", f"Le chiffre d'affaires déclaré ({fmt(ca)}) s'écarte de {pct(gap)} du chiffre d'affaires reconstitué à partir des relevés bancaires ({fmt(ca_bank)}).", "alerte", "R01")
    if ca is not None and result is not None and result > ca:
        add(incoh, "RESULT_GT_CA", "Le résultat net déclaré est supérieur au chiffre d'affaires : donnée incohérente.", "alerte", "R08")
    if existing_monthly > 0 and debt == 0:
        add(incoh, "DEBT_INCOH", "Des mensualités existantes sont déclarées alors que l'endettement existant est nul.", "attention", "R08")
    if g_type and g_type != "Aucune" and (g_value is None or g_value <= 0):
        add(incoh, "GUAR_VALUE", f"Une garantie (« {g_type} ») est déclarée sans valeur estimée.", "attention", "R01")
    if g_type in ("", "Aucune") and docs.get("doc_guarantee") == "oui":
        add(incoh, "GUAR_DOC", "Un justificatif de garantie est coché alors qu'aucune garantie n'est déclarée.", "attention", "R01")
    if rq.get("product") == "Crédit de fonctionnement" and months and months > THRESHOLDS["short_term_max_months"]:
        add(incoh, "PRODUCT_DURATION", f"Durée de {months:.0f} mois peu cohérente avec un crédit de fonctionnement (besoin à court terme) : vérifier l'objet du financement.", "attention", "R06")
    if docs.get("check_concordance") == "non":
        add(incoh, "CONCORDANCE", "La vérification de concordance des noms, montants et dates est déclarée non satisfaisante.", "alerte", "R01")

    # 4. Points de vigilance (seuils indicatifs)
    if amount and ca and ca > 0:
        r = amount / ca
        ratios.append(("Montant demandé / CA", pct(r)))
        if r > THRESHOLDS["amount_to_revenue"]:
            add(vigil, "AMOUNT_CA", f"Le montant demandé représente {pct(r)} du chiffre d'affaires annuel.", "attention", "R03")
    if amount and months and months > 0:
        m = monthly_installment(amount, months)
        ratios.append(("Échéance mensuelle estimée (taux indicatif 8 %)", fmt(m)))
        if ca and ca > 0:
            ds = (m + existing_monthly) * 12 / ca
            ratios.append(("Charges de remboursement annuelles / CA", pct(ds)))
            if ds > THRESHOLDS["debt_service_to_revenue"]:
                add(vigil, "DEBT_SERVICE", f"Les remboursements annuels (existants + nouveau crédit) représenteraient {pct(ds)} du chiffre d'affaires.", "alerte", "R03")
        if result is not None and result > 0 and m * 12 > result:
            add(vigil, "RESULT_COVER", f"Le résultat net annuel ({fmt(result)}) ne couvre pas les échéances annuelles estimées du nouveau crédit ({fmt(m * 12)}).", "attention", "R04")
    if result is not None and result < 0:
        add(vigil, "LOSS", "Résultat net déficitaire sur le dernier exercice.", "alerte", "R03")
    if equity is not None and equity <= 0:
        add(vigil, "EQUITY", "Fonds propres nuls ou négatifs.", "alerte", "R03")
    if equity and equity > 0 and amount:
        lev = (debt + amount) / equity
        ratios.append(("(Dettes existantes + montant) / fonds propres", f"{lev:.2f}".replace(".", ",")))
        if lev > THRESHOLDS["leverage"]:
            add(vigil, "LEVERAGE", f"Endettement post-financement élevé : {lev:.1f} fois les fonds propres.".replace(".", ",", 1), "attention", "R03")
    if ca and ca1 and ca1 > 0 and (ca1 - ca) / ca1 > THRESHOLDS["revenue_drop"]:
        add(vigil, "CA_DROP", f"Baisse du chiffre d'affaires de {pct((ca1 - ca) / ca1)} par rapport à l'exercice précédent.", "attention", "R03")
    if creation and 0 <= (today - creation).days / 365.25 < THRESHOLDS["young_company_years"]:
        add(vigil, "YOUNG", f"Entreprise créée depuis moins de {THRESHOLDS['young_company_years']} ans : historique financier limité.", "info", "R03")
    if g_type in ("", "Aucune") and amount:
        add(vigil, "NO_GUAR", "Aucune garantie proposée : point à apprécier par la fonction risques au regard de la charte.", "info", "R01")
    if g_value and amount and g_type not in ("", "Aucune") and g_value < amount * 0.5:
        add(vigil, "GUAR_LOW", f"La valeur estimée de la garantie ({fmt(g_value)}) couvre moins de la moitié du montant demandé.", "info", "R01")
    for x in incoh + vigil:
        risks.add(x["risk"])

    blocking = bool(missing_docs) or any(i["severity"] == "alerte" for i in incoh)
    status = "Incomplet – présentation suspendue" if blocking else "Complet – transmissible pour avis risques"
    linked = sorted(risks)

    name = c.get("name") or "L'entreprise"
    sector = f" (secteur : {c['sector']})" if c.get("sector") else ""
    amt = fmt(amount) if amount else "un montant non précisé"
    dur = f" sur {months:.0f} mois" if months else ""
    prod = f" au titre d'un {rq['product'].lower()}" if rq.get("product") else ""
    purp = f" pour : {rq['purpose']}" if rq.get("purpose") else ""
    parts = [
        f"{name}{sector} sollicite {amt}{dur}{prod}{purp}.",
        f"Complétude documentaire : {rate} % ({present}/{len(required)} pièces requises avant avis).",
    ]
    if missing_docs:
        parts.append(f"Pièces manquantes : {' ; '.join(missing_docs)}.")
    if missing_info:
        parts.append(f"{len(missing_info)} information(s) à compléter.")
    if incoh:
        parts.append(f"{len(incoh)} incohérence(s) relevée(s), dont {sum(i['severity'] == 'alerte' for i in incoh)} significative(s).")
    if vigil:
        parts.append(f"{len(vigil)} point(s) de vigilance à examiner par la fonction risques.")
    parts.append(
        "Conformément à la règle de blocage de la grille de vérification (C01), la présentation du dossier est suspendue jusqu'à "
        "régularisation ; l'anomalie doit être inscrite au registre (C04)." if blocking else
        "Le dossier peut être transmis à la fonction risques pour avis indépendant, préalable à la décision de l'instance délégataire (C02)."
    )
    if linked:
        parts.append(f"Risques du registre concernés : {', '.join(linked)}.")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "completeness": {"rate": rate, "required": len(required), "present": present, "missing_docs": missing_docs, "pending_before_decision": pending},
        "missing_info": missing_info, "inconsistencies": incoh, "vigilance": vigil,
        "ratios": ratios, "linked_risks": linked, "blocking": blocking, "status": status,
        "synthesis": " ".join(parts), "disclaimer": DISCLAIMER,
    }
