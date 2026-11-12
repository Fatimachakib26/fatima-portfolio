"""Lecture consolidée des données et calcul des indicateurs."""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from . import db
from .scoring import level, score


def split_ids(v) -> list[str]:
    return [x for x in str(v or "").replace(";", ",").replace(" ", ",").split(",") if x]


def risks_df() -> pd.DataFrame:
    df = pd.DataFrame(db.query("select * from risks order by id"))
    if df.empty:
        return df
    df["score"] = [score(p, g) for p, g in zip(df.probability, df.gravity)]
    df["level"] = df.score.map(level)
    return df


def table_df(table: str, order: str = "id") -> pd.DataFrame:
    return pd.DataFrame(db.query(f"select * from {table} order by {order}"))


def dossiers() -> list[dict]:
    out = []
    for r in db.query("select * from dossiers order by created_at desc, id desc"):
        d = json.loads(r["payload"])
        d.update(id=r["id"], analysis=json.loads(r["analysis"] or "{}"), status=r["status"], created_by=r["created_by"],
                 is_demo=r["is_demo"], created_at=r["created_at"])
        out.append(d)
    return out


def snapshot() -> dict:
    return {
        "risks": risks_df(),
        "controls": table_df("controls"),
        "components": table_df("coso_components"),
        "principles": pd.DataFrame(db.query("select * from coso_principles order by component_id, cast(substr(id,2) as integer)")),
        "recommendations": table_df("recommendations"),
        "actions": table_df("actions", "priority, id"),
        "anomalies": table_df("anomalies", "detected_on desc, id desc"),
        "dossiers": dossiers(),
        "history": table_df("risk_history", "recorded_at"),
    }


def kpis(s: dict) -> dict:
    r, c, a, an, p, comp = s["risks"], s["controls"], s["actions"], s["anomalies"], s["principles"], s["components"]
    today = date.today().isoformat()
    total = len(r)
    covered = sum(any(rid in split_ids(x) for x in c.risk_ids) for rid in r.id) if total and not c.empty else 0
    open_an = an[an.status != "Clôturée"] if not an.empty else an
    return {
        "total": total,
        "critical": int((r.level == "Critique").sum()) if total else 0,
        "high": int((r.level == "Élevé").sum()) if total else 0,
        "avg_score": float(r.score.mean()) if total else 0.0,
        "pending_actions": int((a.status != "Terminé").sum()) if not a.empty else 0,
        "action_progress": round(float(a.progress.mean())) if not a.empty else 0,
        "open_anomalies": len(open_an),
        "overdue_anomalies": int(((open_an.due_on != "") & (open_an.due_on < today)).sum()) if len(open_an) else 0,
        "closed_anomalies": int((an.status == "Clôturée").sum()) if not an.empty else 0,
        "operational_controls": int(c.status.isin(["Opérationnel", "Efficace"]).sum()) if not c.empty else 0,
        "total_controls": len(c),
        "covered_risks": covered,
        "deficient_principles": int((p.assessment == "Déficient").sum()) if not p.empty else 0,
        "avg_maturity": float(comp.maturity.mean()) if not comp.empty else 0.0,
        "dossiers": len(s["dossiers"]),
        "dossiers_blocked": sum(1 for d in s["dossiers"] if d["analysis"].get("blocking")),
    }
