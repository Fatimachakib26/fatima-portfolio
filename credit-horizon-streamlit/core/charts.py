"""Graphiques Plotly partagés (palette validée daltonisme ; niveaux en couleurs de statut avec libellés)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .scoring import CATEGORY_COLORS, GRAVITY_SCALE, LEVEL_COLORS, LEVELS, PROBABILITY_SCALE, level

LAYOUT = dict(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
              font=dict(family="Inter, system-ui, sans-serif", color="#334155", size=12))
CELL_BG = {"Faible": "#bbf7d0", "Modéré": "#fef08a", "Élevé": "#fed7aa", "Critique": "#fca5a5"}
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def donut_categories(risks: pd.DataFrame) -> go.Figure:
    c = risks.category.value_counts()
    fig = go.Figure(go.Pie(labels=c.index, values=c.values, hole=0.58, sort=False, textinfo="value",
                           marker=dict(colors=[CATEGORY_COLORS.get(x, "#94a3b8") for x in c.index], line=dict(color="#fff", width=2)),
                           hovertemplate="%{label} : %{value} risque(s)<extra></extra>"))
    fig.update_layout(**LAYOUT, height=260, legend=dict(orientation="h", y=-0.05))
    return fig


def bar_levels(risks: pd.DataFrame) -> go.Figure:
    counts = [int((risks.level == lv).sum()) for lv in LEVELS]
    fig = go.Figure(go.Bar(x=LEVELS, y=counts, marker_color=[LEVEL_COLORS[lv] for lv in LEVELS], text=counts, textposition="outside",
                           hovertemplate="%{x} : %{y} risque(s)<extra></extra>"))
    fig.update_layout(**LAYOUT, height=260, yaxis=dict(gridcolor="#e2e8f0", rangemode="tozero", dtick=1), bargap=0.45)
    return fig


def evolution(history: pd.DataFrame, risk_ids: list[str]) -> go.Figure:
    h = history.copy()
    h["month"] = h.recorded_at.str.slice(0, 7)
    rows = []
    for m in sorted(h.month.unique()):
        latest = h[h.month <= m].sort_values("recorded_at").groupby("risk_id").score.last()
        latest = latest[latest.index.isin(risk_ids)]
        y, mo = m.split("-")
        rows.append({"mois": f"{MONTHS[int(mo) - 1]} {y[2:]}", "moyen": round(latest.mean(), 1), "max": latest.max(),
                     "critiques": int(sum(level(v) == "Critique" for v in latest))})
    d = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_scatter(x=d.mois, y=d["max"], name="Score maximal", mode="lines+markers", line=dict(color="#2a78d6", width=2), marker=dict(size=8))
    fig.add_scatter(x=d.mois, y=d.moyen, name="Score moyen", mode="lines+markers", line=dict(color="#0f7a58", width=2), marker=dict(size=8),
                    customdata=d.critiques, hovertemplate="%{x} : %{y}<br>%{customdata} risque(s) critique(s)<extra></extra>")
    fig.update_layout(**LAYOUT, height=260, hovermode="x unified", yaxis=dict(range=[0, 25], tickvals=[0, 5, 10, 15, 20, 25], gridcolor="#e2e8f0"),
                      legend=dict(orientation="h", y=-0.2))
    return fig


def heatmap(risks: pd.DataFrame, compact: bool = False) -> go.Figure:
    z, text, hover = [], [], []
    for p in range(5, 0, -1):
        zr, tr, hr = [], [], []
        for g in range(1, 6):
            s = p * g
            ids = list(risks[(risks.probability == p) & (risks.gravity == g)].id)
            zr.append(LEVELS.index(level(s)))
            tr.append(("<b>" + "<br>".join(ids) + "</b>") if ids else f"<span style='color:#94a3b8'>{s}</span>")
            titles = [f"{r.id} – {r.title}" for r in risks[risks.id.isin(ids)].itertuples()]
            hr.append(f"P={p} × G={g} = {s} ({level(s)})" + ("<br>" + "<br>".join(titles) if titles else ""))
        z.append(zr), text.append(tr), hover.append(hr)
    scale = [[0, CELL_BG["Faible"]], [0.25, CELL_BG["Faible"]], [0.25, CELL_BG["Modéré"]], [0.5, CELL_BG["Modéré"]],
             [0.5, CELL_BG["Élevé"]], [0.75, CELL_BG["Élevé"]], [0.75, CELL_BG["Critique"]], [1, CELL_BG["Critique"]]]
    xl = [f"{g}<br><sub>{GRAVITY_SCALE[g][0]}</sub>" if not compact else str(g) for g in range(1, 6)]
    yl = [f"{p} · {PROBABILITY_SCALE[p][0]}" if not compact else str(p) for p in range(5, 0, -1)]
    fig = go.Figure(go.Heatmap(z=z, x=xl, y=yl, text=text, texttemplate="%{text}", textfont=dict(size=12 if compact else 14, color="#0f172a"),
                               colorscale=scale, zmin=0, zmax=3, showscale=False, xgap=4, ygap=4, hovertext=hover, hoverinfo="text"))
    fig.update_layout(**LAYOUT, height=320 if compact else 520, xaxis=dict(title="Gravité", side="bottom"), yaxis=dict(title="Probabilité"))
    return fig
