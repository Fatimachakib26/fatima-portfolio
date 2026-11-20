"""
Exports des résultats.

Format « long » (une observation par ligne) : directement exploitable dans
Power BI ou Excel (tableaux croisés), sans retraitement.
"""
from __future__ import annotations

import io

import pandas as pd


def summary_long(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """tables : {période ou contexte : tableau (stratégies × indicateurs)}."""
    frames = []
    for context, tab in tables.items():
        long = tab.rename_axis("strategie").reset_index().melt(
            id_vars="strategie", var_name="indicateur", value_name="valeur")
        long.insert(0, "contexte", context)
        frames.append(long)
    return pd.concat(frames, ignore_index=True)


def returns_long(returns: pd.DataFrame, context: str) -> pd.DataFrame:
    out = returns.rename_axis("date").reset_index().melt(id_vars="date", var_name="strategie",
                                                          value_name="rendement")
    out.insert(0, "contexte", context)
    return out


def weights_long(weights: dict[str, pd.DataFrame], context: str) -> pd.DataFrame:
    frames = []
    for strat, w in weights.items():
        f = w.rename_axis("date").reset_index().melt(id_vars="date", var_name="actif", value_name="poids")
        f.insert(0, "strategie", strat)
        frames.append(f)
    out = pd.concat(frames, ignore_index=True)
    out.insert(0, "contexte", context)
    return out


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """CSV UTF-8 avec BOM (accents corrects dans Excel), séparateur « ; »,
    virgule décimale : conventions françaises."""
    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=";", decimal=",", date_format="%Y-%m-%d")
    return buf.getvalue().encode("utf-8-sig")


def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        for name, df in sheets.items():
            df.to_excel(xl, sheet_name=name[:31])
    return buf.getvalue()
