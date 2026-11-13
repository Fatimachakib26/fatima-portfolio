"""Étape 5 – Tables d'analyse (« marts ») : petites, agrégées, prêtes pour le tableau de bord et Power BI.

Définitions (identiques partout) :
- Prêts dénoués      = prêts remboursés (PIF) + prêts passés en perte (CHGOFF)
- Taux de défaut     = prêts passés en perte / prêts dénoués
- Taux de perte      = montant passé en perte / montant approuvé des prêts dénoués
"""
from __future__ import annotations

import json

import pandas as pd

from .config import MARTS, RAW, SIZE_BANDS, TERM_BANDS


def agg(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    funded = df[df["Population"] != "Non décaissé"]
    res = funded[funded["Population"] == "Dénoué"]
    g_all = funded.groupby(by).agg(loans=("GrossApproval", "size"), approved_usd=("GrossApproval", "sum"))
    g_res = res.groupby(by).agg(resolved=("Defaulted", "size"), defaults=("Defaulted", "sum"),
                                resolved_usd=("GrossApproval", "sum"), chargeoff_usd=("GrossChargeOffAmount", "sum"),
                                median_months_to_default=("MonthsToChargeOff", "median"))
    out = g_all.join(g_res, how="left").fillna({"resolved": 0, "defaults": 0, "resolved_usd": 0, "chargeoff_usd": 0})
    out["default_rate"] = (out["defaults"] / out["resolved"]).where(out["resolved"] > 0)
    out["loss_rate"] = (out["chargeoff_usd"] / out["resolved_usd"]).where(out["resolved_usd"] > 0)
    out = out.reset_index()
    for c in ["loans", "resolved", "defaults"]:
        out[c] = out[c].astype(int)
    return out


def run(df: pd.DataFrame) -> dict:
    MARTS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RAW / "MANIFEST.json").read_text(encoding="utf-8"))
    funded = df[df["Population"] != "Non décaissé"]
    res = funded[funded["Population"] == "Dénoué"]
    co = res[res["Defaulted"] == 1]

    overview = {
        "as_of": str(df["AsOfDate"].max().date()),
        "cohorts": f"FY{int(df['ApprovalFY'].min())}–FY{int(df['ApprovalFY'].max())}",
        "loans_funded": int(len(funded)), "loans_resolved": int(len(res)), "loans_active_undisclosed": int((funded["Population"] == "En cours (non publié)").sum()),
        "defaults": int(len(co)), "default_rate": float(len(co) / len(res)),
        "approved_usd": float(funded["GrossApproval"].sum()), "chargeoff_usd": float(co["GrossChargeOffAmount"].sum()),
        "loss_rate": float(co["GrossChargeOffAmount"].sum() / res["GrossApproval"].sum()),
        "median_loan_usd": float(funded["GrossApproval"].median()), "median_term_months": float(funded["TermInMonths"].median()),
        "median_months_to_default": float(co["MonthsToChargeOff"].median()),
        "share_defaults_within_24m": float((co["MonthsToChargeOff"] <= 24).mean()),
        "lenders": int(funded["LocationID"].nunique()), "states": int(funded["BorrState"].nunique()),
    }

    tables = {
        "by_cohort": agg(df, "ApprovalFY").rename(columns={"ApprovalFY": "cohort_fy"}),
        "by_sector": agg(df, "Sector").rename(columns={"Sector": "sector"}).sort_values("approved_usd", ascending=False),
        "by_state": agg(df, "BorrState").rename(columns={"BorrState": "state"}).sort_values("approved_usd", ascending=False),
        "by_size": agg(df, "SizeBand").rename(columns={"SizeBand": "size_band"}),
        "by_term": agg(df, "TermBand").rename(columns={"TermBand": "term_band"}),
        "by_business_age": agg(df[df["BusinessAge"] != ""], "BusinessAge").rename(columns={"BusinessAge": "business_age"}),
        "by_collateral": agg(df, "CollateralInd").rename(columns={"CollateralInd": "collateral"}),
        "by_rate_type": agg(df, "FixedorVariableInterestInd").rename(columns={"FixedorVariableInterestInd": "rate_type"}),
        "by_processing": agg(df, "ProcessingMethod").rename(columns={"ProcessingMethod": "processing_method"}).sort_values("loans", ascending=False).head(8),
    }
    order = {"by_size": [b[2] for b in SIZE_BANDS], "by_term": [b[2] for b in TERM_BANDS]}
    for k, labels in order.items():
        col = tables[k].columns[0]
        tables[k] = tables[k].set_index(col).reindex(labels).reset_index()

    # Délai avant passage en perte (signal d'alerte précoce – lien avec le risque R04)
    bins = [0, 12, 24, 36, 48, 60, 1e9]
    labels = ["0–12 mois", "12–24 mois", "24–36 mois", "36–48 mois", "48–60 mois", "> 60 mois"]
    ttd = pd.cut(co["MonthsToChargeOff"], bins=bins, labels=labels, include_lowest=True).value_counts().reindex(labels)
    tables["time_to_default"] = pd.DataFrame({"bucket": labels, "defaults": ttd.values.astype(int), "share": (ttd / ttd.sum()).values})

    # Concentration sectorielle (lien avec le contrôle C07)
    sec = tables["by_sector"]
    shares = sec["approved_usd"] / sec["approved_usd"].sum()
    overview["top3_sector_share"] = float(shares.head(3).sum())
    overview["hhi_sector"] = float((shares ** 2).sum())

    for name, t in tables.items():
        t.to_csv(MARTS / f"{name}.csv", index=False)
    payload = {"source": manifest["source"], "files": manifest["files"], "overview": overview,
               "tables": {k: json.loads(v.to_json(orient="records", double_precision=6)) for k, v in tables.items()}}
    (MARTS / "sba_marts.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload
