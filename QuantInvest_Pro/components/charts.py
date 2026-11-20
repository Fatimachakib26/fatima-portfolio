"""
Graphiques Plotly de l'application.

Chaque fonction reçoit des données réellement téléchargées / calculées et
retourne une figure ; aucune donnée n'est générée ici.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from config import COLORS, SERIES_COLORS

PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}
BENCH_COLOR = COLORS["cyan"]


def base_figure(title: str = "", height: int = 360) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title, height=height)
    return fig


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def asset_colors(assets: list[str]) -> dict[str, str]:
    """Couleur stable par actif (même couleur sur toutes les pages)."""
    palette = [c for c in SERIES_COLORS if c.upper() != BENCH_COLOR.upper()]
    return {a: palette[i % len(palette)] for i, a in enumerate(assets)}


def base100_chart(prices: pd.DataFrame, benchmark: pd.Series | None = None,
                  height: int = 360, title: str = "") -> go.Figure:
    """Performance comparée, toutes les séries ramenées à 100 au départ."""
    fig = base_figure(title, height)
    norm = prices / prices.iloc[0] * 100
    colors = asset_colors(list(prices.columns))
    for col in norm.columns:
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm[col], name=col, mode="lines",
            line=dict(width=1.8, color=colors[col]),
            hovertemplate=f"<b>{col}</b><br>%{{x|%d/%m/%Y}}<br>Base 100 : %{{y:.1f}}<extra></extra>",
        ))
    if benchmark is not None:
        b = benchmark / benchmark.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=b.index, y=b, name=f"{benchmark.name} (benchmark)", mode="lines",
            line=dict(width=2.6, color=BENCH_COLOR, dash="dot"),
            hovertemplate=f"<b>{benchmark.name}</b><br>%{{x|%d/%m/%Y}}<br>Base 100 : %{{y:.1f}}<extra></extra>",
        ))
    fig.update_layout(hovermode="x unified", yaxis_title="Base 100",
                      margin=dict(l=10, r=10, t=40 if title else 10, b=10),
                      legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0,
                                  font=dict(size=10)))
    return fig


def price_chart(prices: pd.Series, currency: str | None = None, height: int = 360) -> go.Figure:
    """Prix ajusté d'un actif, avec remplissage dégradé."""
    color = COLORS["violet2"]
    fig = base_figure("", height)
    fig.add_trace(go.Scatter(
        x=prices.index, y=prices, mode="lines", name=prices.name,
        line=dict(width=2, color=color), fill="tozeroy", fillcolor=_hex_to_rgba(color, 0.12),
        hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.2f} " + (currency or "") + "<extra></extra>",
    ))
    lo, hi = float(prices.min()), float(prices.max())
    pad = (hi - lo) * 0.08 or 1.0
    fig.update_layout(showlegend=False, yaxis=dict(range=[lo - pad, hi + pad],
                      title=f"Prix ajusté ({currency})" if currency else "Prix ajusté"))
    return fig


def sparkline(series: pd.Series, up: bool, height: int = 60) -> go.Figure:
    """Mini-courbe sans axes pour les cartes d'actifs."""
    color = COLORS["up"] if up else COLORS["down"]
    fig = go.Figure(go.Scatter(
        x=series.index, y=series, mode="lines", line=dict(width=1.8, color=color),
        fill="tozeroy", fillcolor=_hex_to_rgba(color, 0.10), hoverinfo="skip",
    ))
    lo, hi = float(series.min()), float(series.max())
    pad = (hi - lo) * 0.1 or 1.0
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      xaxis=dict(visible=False), yaxis=dict(visible=False, range=[lo - pad, hi + pad]))
    return fig
