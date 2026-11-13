"""Étapes 2 à 4 – Profilage, validation et nettoyage.

Principe : chaque transformation est une règle numérotée, appliquée dans l'ordre et comptée.
Une ligne n'est jamais supprimée en silence : soit elle passe en « clean », soit elle part dans
le journal des rejets avec le code de la règle qui l'a écartée.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import CLEAN, NAICS_SECTORS, PII_COLUMNS, RAW, REPORTS, SIZE_BANDS, SOURCE, TERM_BANDS

DATE_COLS = ["AsOfDate", "ApprovalDate", "FirstDisbursementDate", "PaidInFullDate", "ChargeOffDate"]
NUM_COLS = ["GrossApproval", "SBAGuaranteedApproval", "InitialInterestRate", "TermInMonths", "GrossChargeOffAmount", "JobsSupported"]
STATUS_MAP = {"PIF": "PIF", "CHGOFF": "CHGOFF", "CANCLD": "CANCLD", "EXEMPT": "EXEMPT", "COMMIT": "COMMIT"}


def read_raw() -> pd.DataFrame:
    # Lecture « tout en texte » : aucune conversion implicite, rien n'est masqué à ce stade.
    f = RAW / SOURCE["files"]["loans"]["name"]
    return pd.read_csv(f, dtype=str, keep_default_na=False, encoding="utf-8", low_memory=False)


def profile(df: pd.DataFrame) -> list[dict]:
    rows = []
    for c in df.columns:
        s = df[c]
        empty = int((s.str.strip() == "").sum())
        rows.append({"column": c, "empty": empty, "empty_pct": round(empty / len(df) * 100, 2), "distinct": int(s.nunique()),
                     "examples": " | ".join(s[s.str.strip() != ""].drop_duplicates().head(3).str.slice(0, 40))})
    return rows


def band(v: float, bands) -> str:
    for lo, hi, label in bands:
        if lo < v <= hi or (lo == 0 and v == 0):
            return label
    return bands[-1][2]


def run() -> dict:
    log: list[dict] = []
    rejects: list[pd.DataFrame] = []

    def step(rule: str, desc: str, before: int, after: int, note: str = ""):
        log.append({"rule": rule, "description": desc, "rows_before": before, "rows_after": after, "affected": before - after if before != after else None, "note": note})

    raw = read_raw()
    n_raw = len(raw)
    prof = profile(raw)
    df = raw.copy()

    # R01 – espaces parasites (ex. Program = " 7A")
    changed = int(sum((df[c] != df[c].str.strip()).sum() for c in df.columns))
    for c in df.columns:
        df[c] = df[c].str.strip()
    step("R01", "Suppression des espaces en début/fin de texte", n_raw, len(df), f"{changed} cellules corrigées")

    # R02 – doublons exacts
    dup = df.duplicated(keep="first")
    rejects.append(df[dup].assign(reject_rule="R02", reject_reason="Doublon exact d'une ligne précédente"))
    n = len(df)
    df = df[~dup].copy()
    step("R02", "Suppression des doublons exacts (première occurrence conservée)", n, len(df))

    # R03 – normalisation des codes (écarts entre fichier et dictionnaire officiel)
    df["LoanStatus"] = df["LoanStatus"].str.replace(" ", "", regex=False).str.upper()
    unknown = ~df["LoanStatus"].isin(STATUS_MAP)
    rejects.append(df[unknown].assign(reject_rule="R03", reject_reason="Statut de prêt inconnu du dictionnaire"))
    n = len(df)
    df = df[~unknown].copy()
    df["RevolverStatus"] = df["RevolverStatus"].map({"Y": 1, "N": 0, "1": 1, "0": 0})
    for c in ["CollateralInd", "SoldSecMrktInd"]:
        df[c] = df[c].map({"Y": True, "N": False}).astype("boolean")
    step("R03", "Normalisation des codes : « P I F » → PIF, Y/N → 1/0 ou booléen", n, len(df))

    # R04 – typage numérique
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c].replace("", np.nan), errors="coerce")
    bad = df["GrossApproval"].isna() | (df["GrossApproval"] <= 0) | df["TermInMonths"].isna()
    rejects.append(df[bad].assign(reject_rule="R04", reject_reason="Montant approuvé ou durée absent(e) ou non positif(ve)"))
    n = len(df)
    df = df[~bad].copy()
    step("R04", "Conversion des montants, taux et durées en nombres ; montant > 0 obligatoire", n, len(df))

    # R05 – typage des dates (format ISO AAAA-MM-JJ attendu)
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c].replace("", pd.NaT), format="%Y-%m-%d", errors="coerce")
    bad = df["ApprovalDate"].isna()
    rejects.append(df[bad].assign(reject_rule="R05", reject_reason="Date d'approbation absente ou invalide"))
    n = len(df)
    df = df[~bad].copy()
    step("R05", "Conversion des dates ; date d'approbation obligatoire", n, len(df))

    # R06 – cohérence des montants : garantie SBA ≤ montant du prêt
    bad = df["SBAGuaranteedApproval"] > df["GrossApproval"]
    rejects.append(df[bad].assign(reject_rule="R06", reject_reason="Garantie SBA supérieure au montant du prêt"))
    n = len(df)
    df = df[~bad].copy()
    step("R06", "Contrôle : garantie SBA ≤ montant approuvé", n, len(df))

    # R07 – cohérence statut / dates / montants
    co, pif = df["LoanStatus"] == "CHGOFF", df["LoanStatus"] == "PIF"
    bad = (co & df["ChargeOffDate"].isna()) | (pif & df["PaidInFullDate"].isna())
    # Les dates de remboursement sont publiées au mois près (souvent le 1er ou le dernier jour du mois) :
    # la comparaison se fait donc au niveau du mois, sinon un prêt remboursé dans son premier mois serait rejeté à tort.
    appr_m = df["ApprovalDate"].dt.to_period("M")
    bad |= (df["ChargeOffDate"].dt.to_period("M") < appr_m) | (df["PaidInFullDate"].dt.to_period("M") < appr_m)
    rejects.append(df[bad].assign(reject_rule="R07", reject_reason="Statut incohérent avec les dates (date manquante ou antérieure à l'approbation)"))
    n = len(df)
    df = df[~bad].copy()
    step("R07", "Contrôle : un prêt soldé/passé en perte a une date cohérente, postérieure à l'approbation", n, len(df))

    # R08 – minimisation : suppression des données personnelles
    df = df.drop(columns=PII_COLUMNS)
    step("R08", "Suppression des données personnelles (nom, adresse, code postal de l'emprunteur)", len(df), len(df), ", ".join(PII_COLUMNS))

    # R09 – variables dérivées pour l'analyse
    df["Sector"] = df["NaicsCode"].str.slice(0, 2).map(NAICS_SECTORS).fillna("Non classé")
    df["SizeBand"] = df["GrossApproval"].map(lambda v: band(v, SIZE_BANDS))
    df["TermBand"] = df["TermInMonths"].map(lambda v: band(v, TERM_BANDS))
    df["Population"] = np.select(
        [df["LoanStatus"].isin(["PIF", "CHGOFF"]), df["LoanStatus"].eq("EXEMPT"), df["LoanStatus"].isin(["CANCLD", "COMMIT"])],
        ["Dénoué", "En cours (non publié)", "Non décaissé"], default="Autre")
    df["Defaulted"] = np.where(df["Population"] == "Dénoué", (df["LoanStatus"] == "CHGOFF").astype(int), np.nan)
    df["MonthsToChargeOff"] = ((df["ChargeOffDate"] - df["ApprovalDate"]).dt.days / 30.4375).round(1)
    df["LossRate"] = np.where(co.loc[df.index], df["GrossChargeOffAmount"] / df["GrossApproval"], np.nan)
    step("R09", "Variables dérivées : secteur NAICS, tranches de montant et de durée, population d'analyse, défaut, délai et taux de perte", len(df), len(df))

    rej = pd.concat(rejects, ignore_index=True)
    n_rej = len(rej)
    assert n_raw == len(df) + n_rej, "Réconciliation impossible : lignes brutes ≠ lignes propres + rejets"

    CLEAN.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN / "loans_clean.csv.gz", index=False, compression="gzip", date_format="%Y-%m-%d")
    rej.drop(columns=[c for c in PII_COLUMNS if c in rej.columns]).to_csv(CLEAN / "rejected_rows.csv.gz", index=False, compression="gzip")

    summary = {
        "raw_rows": n_raw, "clean_rows": len(df), "rejected_rows": n_rej,
        "rejects_by_rule": rej["reject_rule"].value_counts().to_dict(),
        "status_counts": df["LoanStatus"].value_counts().to_dict(),
        "population_counts": df["Population"].value_counts().to_dict(),
        "gross_approval_total": float(df["GrossApproval"].sum()),
        "rules": log, "profile": prof,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "cleaning_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_quality_report(summary)
    return {"df": df, "summary": summary}


def write_quality_report(s: dict) -> None:
    L = ["# Rapport de qualité des données – SBA 7(a) FY2010–FY2019", "",
         f"Source : {SOURCE['landing_page']} · licence : {SOURCE['license']}", "",
         "## Réconciliation", "",
         "| Lignes brutes | Lignes propres | Lignes rejetées | Contrôle |", "|---:|---:|---:|---|",
         f"| {s['raw_rows']:,} | {s['clean_rows']:,} | {s['rejected_rows']:,} | {'OK' if s['raw_rows'] == s['clean_rows'] + s['rejected_rows'] else 'ÉCART'} |", "",
         "## Règles appliquées", "", "| Règle | Description | Lignes avant | Lignes après | Remarque |", "|---|---|---:|---:|---|"]
    for r in s["rules"]:
        L.append(f"| {r['rule']} | {r['description']} | {r['rows_before']:,} | {r['rows_after']:,} | {r['note']} |")
    L += ["", "## Rejets par règle", "", "| Règle | Lignes |", "|---|---:|"] + [f"| {k} | {v:,} |" for k, v in s["rejects_by_rule"].items()]
    L += ["", "## Populations d'analyse", "", "| Population | Prêts |", "|---|---:|"] + [f"| {k} | {v:,} |" for k, v in s["population_counts"].items()]
    L += ["", "Le taux de défaut est calculé uniquement sur les prêts **dénoués** (remboursés ou passés en perte) : "
          "les prêts non décaissés n'ont jamais porté de risque et l'issue des prêts « EXEMPT » n'est pas publiée.", "",
          "## Profil du fichier brut (avant toute correction)", "", "| Colonne | Vides | % vides | Valeurs distinctes | Exemples |", "|---|---:|---:|---:|---|"]
    for p in s["profile"]:
        L.append(f"| {p['column']} | {p['empty']:,} | {p['empty_pct']} | {p['distinct']:,} | {p['examples'].replace('|', '/')} |")
    (REPORTS / "data_quality_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
