"""
Graphiques Plotly de l'application.

Chaque fonction reçoit des données réellement téléchargées / calculées et
retourne une figure ; aucune donnée n'est générée ici.
"""
from __future__ import annotations

import numpy as np
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
                  height: int = 360, title: str = "", log_y: bool = False) -> go.Figure:
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
            x=b.index, y=b, name=f"{benchmark.name} (référence)", mode="lines",
            line=dict(width=3.4, color="#F1F5F9", dash="dot"),  # trait épais et clair : bien visible
            hovertemplate=f"<b>{benchmark.name}</b><br>%{{x|%d/%m/%Y}}<br>Base 100 : %{{y:.1f}}<extra></extra>",
        ))
    if log_y:  # échelle logarithmique : des performances très différentes restent lisibles
        lo = min(norm.min().min(), b.min() if benchmark is not None else norm.min().min())
        hi = max(norm.max().max(), b.max() if benchmark is not None else norm.max().max())
        ticks = [v for v in (50, 100, 200, 500, 1000, 2000, 5000) if lo * 0.9 <= v <= hi * 1.1]
        fig.update_yaxes(type="log", title="Base 100 (échelle log.)", tickvals=ticks,
                         ticktext=[f"{v:,}".replace(",", "\u202f") for v in ticks],
                         minor=dict(ticks="", showgrid=False), tickmode="array")
    fig.update_layout(hovermode="x unified", yaxis_title="Base 100 (échelle log.)" if log_y else "Base 100",
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


# =========================================================================== #
# Optimisation
# =========================================================================== #
PORTFOLIO_COLORS = {
    "Variance minimale": COLORS["cyan"],
    "Sharpe maximal": COLORS["violet2"],
    "Équipondéré (1/N)": COLORS["amber"],
}
PORTFOLIO_SYMBOLS = {"Variance minimale": "diamond", "Sharpe maximal": "star", "Équipondéré (1/N)": "square"}


def _pct_axes(fig: go.Figure, x: str = "Volatilité annualisée", y: str = "Rendement espéré annualisé") -> None:
    fig.update_xaxes(title=x, tickformat=".0%")
    fig.update_yaxes(title=y, tickformat=".0%")


def _weights_hover(weights: pd.Series) -> str:
    return "<br>".join(f"{k} : {v:.1%}".replace(".", ",") for k, v in weights.items() if v > 0.0005)


DISPLAY_NAMES = {"Équipondéré (1/N)": "Équipondéré 1/N"}


def frontier_chart(cloud: pd.DataFrame | None, frontier: pd.DataFrame, portfolios: dict, rf: float,
                   height: int = 480, show_cml: bool = True, assets: pd.DataFrame | None = None,
                   annotate: bool = True) -> go.Figure:
    """Frontière efficiente : nuage Monte-Carlo, frontière exacte, droite de marché des capitaux
    (depuis (0, r_f)), actifs individuels et les 3 portefeuilles remarquables.

    assets : DataFrame indexé par ticker avec les colonnes « rendement » et « volatilite ».
    """
    fig = base_figure("", height)
    if cloud is not None and len(cloud):
        fig.add_trace(go.Scatter(  # SVG (et non WebGL) : les marqueurs restent visibles au-dessus
            x=cloud["volatilite"], y=cloud["rendement"], mode="markers", name="Portefeuilles aléatoires",
            marker=dict(size=4, color=cloud["sharpe"], colorscale=[[0, "#1E1B4B"], [0.5, "#7C3AED"], [1, "#22D3EE"]],
                        opacity=0.5, colorbar=dict(title="Sharpe", thickness=10, len=0.55, x=1.02)),
            hovertemplate="Portefeuille aléatoire<br>Volatilité : %{x:.1%}<br>Rendement : %{y:.1%}"
                          "<br>Sharpe : %{marker.color:.2f}<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=frontier["volatilite"], y=frontier["rendement"], mode="lines", name="Frontière efficiente",
        line=dict(color="#fff", width=3),
        customdata=frontier["sharpe"],
        hovertemplate="<b>Frontière efficiente</b><br>Rendement : %{y:.2%}<br>Volatilité : %{x:.2%}"
                      "<br>Sharpe : %{customdata:.2f}<extra></extra>",
    ))
    if assets is not None and len(assets):
        sr = (assets["rendement"] - rf) / assets["volatilite"]
        fig.add_trace(go.Scatter(
            x=assets["volatilite"], y=assets["rendement"], mode="markers+text", name="Actifs individuels",
            text=list(assets.index), textposition="top center", textfont=dict(size=10, color=COLORS["muted"]),
            marker=dict(size=7, color=COLORS["muted"], line=dict(color="#07071A", width=1)),
            customdata=sr.to_numpy(),
            hovertemplate="<b>%{text}</b><br>Rendement : %{y:.2%}<br>Volatilité : %{x:.2%}"
                          "<br>Sharpe : %{customdata:.2f}<extra></extra>",
        ))
    pts_x = [frontier["volatilite"]] + ([assets["volatilite"]] if assets is not None and len(assets) else [])
    pts_y = [frontier["rendement"]] + ([assets["rendement"]] if assets is not None and len(assets) else [])
    if cloud is not None and len(cloud):
        pts_x.append(cloud["volatilite"])
        pts_y.append(cloud["rendement"])
    x_hi = max(float(v.max()) for v in pts_x) * 1.08
    y_lo = min(min(float(v.min()) for v in pts_y), rf) - 0.02
    y_hi = max(float(v.max()) for v in pts_y) * 1.08
    ms = portfolios.get("Sharpe maximal")
    if show_cml and ms is not None and ms.volatility > 0:
        fig.add_trace(go.Scatter(  # droite de marché des capitaux : de (0, r_f) à travers le Sharpe maximal
            x=[0, x_hi], y=[rf, rf + ms.sharpe * x_hi], mode="lines", name="Droite de marché des capitaux",
            line=dict(color=COLORS["violet2"], width=1.6, dash="dash"),
            hovertemplate=f"Droite de marché des capitaux<br>pente = Sharpe maximal ({ms.sharpe:.2f})<extra></extra>"
                          .replace(f"{ms.sharpe:.2f}", f"{ms.sharpe:.2f}".replace(".", ",")),
        ))
        fig.add_trace(go.Scatter(x=[0], y=[rf], mode="markers", name=f"Taux sans risque ({rf:.1%})".replace(".", ","),
                                 marker=dict(size=8, color=COLORS["violet2"]), showlegend=False,
                                 hovertemplate="Taux sans risque : %{y:.2%}<extra></extra>"))
    for name, p in portfolios.items():
        label = DISPLAY_NAMES.get(name, name)
        fig.add_trace(go.Scatter(
            x=[p.volatility], y=[p.expected_return], mode="markers", name=label,
            marker=dict(size=19 if name == "Sharpe maximal" else 15, color=PORTFOLIO_COLORS.get(name, "#fff"),
                        symbol=PORTFOLIO_SYMBOLS.get(name, "circle"), line=dict(color="#07071A", width=2)),
            hovertemplate=(f"<b>{label}</b><br>Rendement : %{{y:.2%}}<br>Volatilité : %{{x:.2%}}<br>Sharpe : "
                           + f"{p.sharpe:.2f}".replace(".", ",") + "<br>" + _weights_hover(p.weights)
                           + "<extra></extra>"),
        ))
        if annotate:
            fig.add_annotation(x=p.volatility, y=p.expected_return, text=label, showarrow=True, arrowhead=0,
                               ax=-60 if name == "Équipondéré (1/N)" else 50, ay=-28 if name != "Variance minimale" else 28,
                               font=dict(size=11, color=PORTFOLIO_COLORS.get(name, "#fff")),
                               arrowcolor=PORTFOLIO_COLORS.get(name, "#fff"), bgcolor="rgba(7,7,26,0.75)")
    _pct_axes(fig)
    fig.update_xaxes(range=[0, x_hi])
    fig.update_yaxes(range=[y_lo, y_hi])
    fig.update_layout(legend=dict(orientation="h", y=-0.14, yanchor="top", xanchor="left", x=0, font=dict(size=11)))
    return fig


def donut_chart(weights: pd.Series, height: int = 320) -> go.Figure:
    w = weights[weights > 0.0005]
    colors = asset_colors(list(weights.index))
    fig = go.Figure(go.Pie(
        labels=w.index, values=w.values, hole=0.62, sort=False,
        marker=dict(colors=[colors[a] for a in w.index], line=dict(color="#07071A", width=2)),
        textinfo="label+percent", textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>Poids : %{percent}<extra></extra>",
    ))
    fig.update_layout(height=height, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def corr_heatmap(corr: pd.DataFrame, height: int = 380) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index, zmin=0, zmax=1,  # actions : corrélations positives
        colorscale=[[0, "#0B0B24"], [0.4, "#1E1B4B"], [0.55, "#33207A"], [0.65, "#5B21B6"], [0.75, "#7C3AED"],
                    [0.9, "#A21CAF"], [1, "#C026D3"]],
        text=[[f"{v:.2f}".replace(".", ",") for v in row] for row in corr.values], texttemplate="%{text}",
        textfont=dict(color="#FFFFFF", size=11),
        hovertemplate="%{y} / %{x}<br>Corrélation : %{z:.2f}<extra></extra>",
        colorbar=dict(thickness=10, tickvals=[0, 0.25, 0.5, 0.75, 1], ticktext=["0", "0,25", "0,5", "0,75", "1"]),
    ))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(autorange="reversed"))
    return fig


def grouped_bars(df: pd.DataFrame, height: int = 360, pct_axis: bool = True, colors: list[str] | None = None,
                 y_title: str = "", hline: float | None = None, hline_label: str = "") -> go.Figure:
    """Barres groupées : une série par colonne, une catégorie par ligne."""
    fig = base_figure("", height)
    palette = colors or [COLORS["violet2"], COLORS["cyan"], COLORS["amber"], COLORS["pink"]]
    for i, col in enumerate(df.columns):
        fig.add_trace(go.Bar(
            x=df.index, y=df[col], name=col, marker=dict(color=palette[i % len(palette)], line=dict(width=0)),
            hovertemplate=f"<b>%{{x}}</b><br>{col} : %{{y:.1%}}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.25, yaxis_title=y_title)
    if hline is not None:
        fig.add_hline(y=hline, line=dict(color=COLORS["down"], dash="dash", width=1.5), annotation_text=hline_label,
                      annotation_position="top right", annotation_font=dict(size=10, color=COLORS["down"]))
    if pct_axis:
        fig.update_yaxes(tickformat=".0%")
    return fig


# =========================================================================== #
# Risque
# =========================================================================== #
def add_crisis_bands(fig: go.Figure, crises: list[tuple[str, str, str]], index: pd.Index) -> None:
    for label, a, b in crises:
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        if b < index[0] or a > index[-1]:
            continue
        fig.add_vrect(x0=max(a, index[0]), x1=min(b, index[-1]), fillcolor="rgba(142,143,181,0.18)",
                      line_width=0, layer="below", annotation_text=label, annotation_position="top left",
                      annotation_font=dict(size=10, color=COLORS["muted"]))


def rolling_corr_chart(rc: pd.Series, crises, height: int = 380) -> go.Figure:
    fig = base_figure("", height)
    fig.add_trace(go.Scatter(
        x=rc.index, y=rc, mode="lines", name=rc.name, line=dict(color=COLORS["violet2"], width=2),
        fill="tozeroy", fillcolor=_hex_to_rgba(COLORS["violet2"], 0.10),
        hovertemplate="%{x|%d/%m/%Y}<br>Corrélation moyenne : %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(y=float(rc.mean()), line=dict(color=COLORS["cyan"], dash="dot", width=1.2),
                  annotation_text="moyenne", annotation_font=dict(size=10, color=COLORS["cyan"]))
    add_crisis_bands(fig, crises, rc.index)
    fig.update_layout(showlegend=False, yaxis_title="Corrélation moyenne des paires")
    return fig


def distribution_chart(r: pd.Series, var_hist: float, var_param: float, height: int = 380) -> go.Figure:
    """Histogramme des rendements, densité normale ajustée et VaR (NormalReturns.py / VaR.py du cours)."""
    import numpy as np
    from scipy.stats import norm

    fig = base_figure("", height)
    fig.add_trace(go.Histogram(
        x=r, nbinsx=120, histnorm="probability density", name="Rendements observés",
        marker=dict(color=_hex_to_rgba(COLORS["violet2"], 0.55), line=dict(width=0)),
        hovertemplate="Rendement : %{x:.2%}<extra></extra>",
    ))
    x = np.linspace(r.min(), r.max(), 400)
    fig.add_trace(go.Scatter(x=x, y=norm.pdf(x, r.mean(), r.std()), mode="lines", name="Loi normale ajustée",
                             line=dict(color=COLORS["cyan"], width=2), hoverinfo="skip"))
    # étiquettes de part et d'autre de chaque ligne pour éviter qu'elles se chevauchent
    left_first = var_hist >= var_param
    for v, label, color, pos in ((var_hist, "VaR historique", COLORS["down"], "top left" if left_first else "top right"),
                                 (var_param, "VaR normale", COLORS["amber"], "top right" if left_first else "top left")):
        fig.add_vline(x=-v, line=dict(color=color, dash="dash", width=1.5), annotation_text=label,
                      annotation_position=pos, annotation_font=dict(size=10, color=color))
    fig.update_xaxes(tickformat=".1%", title="Rendement journalier")
    fig.update_yaxes(title="Densité")
    return fig


# =========================================================================== #
# Backtests
# =========================================================================== #
STRAT_COLORS = [COLORS["amber"], COLORS["cyan"], COLORS["violet2"], COLORS["pink"], COLORS["up"]]


def strategy_colors(names: list[str]) -> dict[str, str]:
    known = {k: v for k, v in PORTFOLIO_COLORS.items()}
    out, i = {}, 0
    for n in names:
        if n in known:
            out[n] = known[n]
        elif n.startswith("Équipondéré"):
            out[n] = COLORS["amber"]
        else:
            out[n] = [COLORS["cyan"], COLORS["violet2"], COLORS["pink"], COLORS["up"]][i % 4]
            i += 1
    return out


def wealth_chart(returns: pd.DataFrame, benchmark: pd.Series | None = None, height: int = 420,
                 crises=None, start_value: float = 100.0, baseline: bool = False) -> go.Figure:
    """Valeur de 100 investis (rendements nets)."""
    fig = base_figure("", height)
    colors = strategy_colors(list(returns.columns))
    for col in returns.columns:
        v = start_value * (1 + returns[col]).cumprod()
        fig.add_trace(go.Scatter(x=v.index, y=v, mode="lines", name=col, line=dict(width=2.2, color=colors[col]),
                                 hovertemplate=f"<b>{col}</b><br>%{{x|%d/%m/%Y}}<br>Valeur : %{{y:.1f}}<extra></extra>"))
    if benchmark is not None:
        v = start_value * (1 + benchmark).cumprod()
        fig.add_trace(go.Scatter(x=v.index, y=v, mode="lines", name=f"{benchmark.name} (référence)",
                                 line=dict(width=1.6, color="#94A3B8", dash="dot"),
                                 hovertemplate=f"<b>{benchmark.name}</b><br>%{{x|%d/%m/%Y}}<br>Valeur : %{{y:.1f}}<extra></extra>"))
    if crises:
        add_crisis_bands(fig, crises, returns.index)
    if baseline:
        fig.add_hline(y=start_value, line=dict(color=COLORS["muted"], dash="dot", width=1.2))
    fig.update_layout(hovermode="x unified", yaxis_title=f"Valeur de {start_value:.0f} investis",
                      legend=dict(orientation="h", y=-0.12, yanchor="top", xanchor="left", x=0, font=dict(size=11)))
    return fig


def drawdown_chart(returns: pd.DataFrame, height: int = 300) -> go.Figure:
    fig = base_figure("", height)
    colors = strategy_colors(list(returns.columns))
    for col in returns.columns:
        w = (1 + returns[col]).cumprod()
        dd = w / w.cummax().clip(lower=1.0) - 1
        fig.add_trace(go.Scatter(x=dd.index, y=dd, mode="lines", name=col, line=dict(width=1.6, color=colors[col]),
                                 hovertemplate=f"<b>{col}</b><br>%{{x|%d/%m/%Y}}<br>Drawdown : %{{y:.1%}}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", title="Baisse depuis le plus haut")
    fig.update_layout(hovermode="x unified", showlegend=False)
    return fig


def stacked_weights_chart(weights: pd.DataFrame, height: int = 340) -> go.Figure:
    fig = base_figure("", height)
    colors = asset_colors(list(weights.columns))
    w = weights.iloc[::5]  # une séance sur 5 suffit à l'affichage
    for col in w.columns:
        fig.add_trace(go.Scatter(x=w.index, y=w[col], mode="lines", name=col, stackgroup="w",
                                 line=dict(width=0.5, color=colors[col]),
                                 hovertemplate=f"<b>{col}</b> : %{{y:.1%}}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", range=[0, 1], title="Poids")
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.12, yanchor="top", xanchor="left", x=0))
    return fig


def announced_vs_realized_chart(announced: pd.Series, realized: pd.Series, height: int = 340) -> go.Figure:
    fig = base_figure("", height)
    fig.add_trace(go.Scatter(x=announced.index, y=announced, mode="lines+markers", name="Sharpe annoncé (ex ante)",
                             line=dict(color=COLORS["violet2"], width=2), marker=dict(size=5),
                             hovertemplate="%{x|%d/%m/%Y}<br>Annoncé : %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=realized.index, y=realized, mode="lines+markers", name="Sharpe réalisé (12 mois suivants)",
                             line=dict(color=COLORS["cyan"], width=2), marker=dict(size=5),
                             hovertemplate="%{x|%d/%m/%Y}<br>Réalisé : %{y:.2f}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=COLORS["muted"], width=1))
    fig.update_layout(hovermode="x unified", yaxis_title="Ratio de Sharpe",
                      legend=dict(orientation="h", y=-0.12, yanchor="top", xanchor="left", x=0))
    return fig


def realized_frontier_chart(fr: pd.DataFrame, points: pd.DataFrame, height: int = 500) -> go.Figure:
    """Frontière estimée (période d'estimation) et position réalisée (test) des mêmes
    portefeuilles ; flèches reliant l'annoncé au réalisé pour les portefeuilles clés."""
    fig = base_figure("", height)
    fig.add_trace(go.Scatter(x=fr["volatilite"], y=fr["rendement"], mode="lines+markers", name="Frontière estimée",
                             line=dict(color=COLORS["violet2"], width=3), marker=dict(size=4),
                             hovertemplate="Frontière estimée<br>Volatilité : %{x:.1%}<br>Rendement : %{y:.1%}<extra></extra>"))
    fig.add_trace(go.Scatter(x=fr["volatilite_realisee"], y=fr["rendement_realise"], mode="lines+markers",
                             name="Frontière réalisée (mêmes poids)", line=dict(color=COLORS["cyan"], width=2, dash="dot"),
                             marker=dict(size=4),
                             hovertemplate="Réalisé en test<br>Volatilité : %{x:.1%}<br>Rendement : %{y:.1%}<extra></extra>"))
    for name, row in points.iterrows():
        color = PORTFOLIO_COLORS.get(name, "#fff")
        label = DISPLAY_NAMES.get(name, name)
        sym = PORTFOLIO_SYMBOLS.get(name, "circle")
        fig.add_trace(go.Scatter(
            x=[row["volatilite"]], y=[row["rendement"]], mode="markers", name=f"{label} · annoncé",
            marker=dict(size=14, symbol=sym + "-open", color=color, line=dict(width=2)),
            hovertemplate=f"<b>{label} — annoncé</b><br>Rendement : %{{y:.2%}}<br>Volatilité : %{{x:.2%}}"
                          f"<br>Sharpe : {row['sharpe']:.2f}<extra></extra>".replace(f"{row['sharpe']:.2f}", f"{row['sharpe']:.2f}".replace(".", ","))))
        fig.add_trace(go.Scatter(
            x=[row["volatilite_realisee"]], y=[row["rendement_realise"]], mode="markers", name=f"{label} · réalisé",
            marker=dict(size=14, symbol=sym, color=color, line=dict(color="#07071A", width=1.5)),
            hovertemplate=f"<b>{label} — réalisé</b><br>Rendement : %{{y:.2%}}<br>Volatilité : %{{x:.2%}}"
                          f"<br>Sharpe : {row['sharpe_realise']:.2f}<extra></extra>".replace(f"{row['sharpe_realise']:.2f}", f"{row['sharpe_realise']:.2f}".replace(".", ","))))
        fig.add_annotation(x=row["volatilite_realisee"], y=row["rendement_realise"], ax=row["volatilite"],
                           ay=row["rendement"], xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                           arrowhead=3, arrowsize=1.2, arrowwidth=2, arrowcolor=color, standoff=6, startstandoff=6)
    _pct_axes(fig, y="Rendement annualisé (moyenne × 252)")
    fig.update_layout(legend=dict(orientation="h", y=-0.14, yanchor="top", xanchor="left", x=0, font=dict(size=11)))
    return fig


def two_frontiers_chart(a, b, label_a: str, label_b: str, height: int = 480) -> go.Figure:
    """Deux univers (UniverseResult) : frontières et Sharpe maximal de chacun."""
    fig = base_figure("", height)
    for u, label, color in ((a, label_a, COLORS["violet2"]), (b, label_b, COLORS["cyan"])):
        fig.add_trace(go.Scatter(x=u.frontier["volatilite"], y=u.frontier["rendement"], mode="lines", name=label,
                                 line=dict(color=color, width=3),
                                 hovertemplate=f"{label}<br>Volatilité : %{{x:.1%}}<br>Rendement : %{{y:.1%}}<extra></extra>"))
        ms_ret = float(u.max_sharpe_weights @ u.est.mu)
        ms_vol = float(np.sqrt(u.max_sharpe_weights @ u.est.cov @ u.max_sharpe_weights))
        fig.add_trace(go.Scatter(x=[ms_vol], y=[ms_ret], mode="markers", name=f"Sharpe maximal · {label}",
                                 marker=dict(size=16, symbol="star", color=color, line=dict(color="#07071A", width=1.5)),
                                 hovertemplate=f"<b>Sharpe maximal · {label}</b><br>Rendement : %{{y:.2%}}<br>"
                                               f"Volatilité : %{{x:.2%}}<br>Sharpe : " + f"{u.sharpe_announced:.2f}".replace(".", ",")
                                               + "<extra></extra>"))
        extra = [t for t in u.assets if t not in a.assets] if u is b else []
        if extra:
            fig.add_trace(go.Scatter(x=u.est.vol[extra], y=u.est.mu[extra], mode="markers+text", text=extra,
                                     textposition="top center", name="Actifs ajoutés",
                                     marker=dict(size=8, color=COLORS["amber"]),
                                     hovertemplate="<b>%{text}</b><br>Rendement : %{y:.2%}<br>Volatilité : %{x:.2%}<extra></extra>"))
    _pct_axes(fig)
    fig.update_layout(legend=dict(orientation="h", y=-0.14, yanchor="top", xanchor="left", x=0, font=dict(size=11)))
    return fig


def sensitivity_heatmap(grid: pd.DataFrame, ref: float, height: int = 380) -> go.Figure:
    z = grid.astype(float).values
    text = [[("—" if pd.isna(v) else f"{v:.2f}".replace(".", ",")) for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{round(c * 100)} %" for c in grid.columns],
        y=[f"{w} séances" for w in grid.index], text=text, texttemplate="%{text}", textfont=dict(size=14),
        zmid=ref, colorscale=[[0, "#F43F5E"], [0.5, "#161743"], [1, "#22D3EE"]],
        colorbar=dict(title="Sharpe", thickness=10),
        hovertemplate="Fenêtre : %{y}<br>Plafond : %{x}<br>Sharpe hors échantillon : %{text}<extra></extra>",
    ))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(title="Plafond de poids par actif", type="category"),
                      yaxis=dict(title="Fenêtre d'estimation", type="category"),
                      title=dict(text=f"Référence 1/N : Sharpe {ref:.2f}".replace(".", ","), font=dict(size=13)))
    return fig


def capm_chart(cp: dict, asset: str, market: str, height: int = 300) -> go.Figure:
    import numpy as np

    fig = base_figure("", height)
    fig.add_trace(go.Scatter(x=cp["x"], y=cp["y"], mode="markers", name="Séances",
                             marker=dict(size=4, color=_hex_to_rgba(COLORS["violet2"], 0.45)),
                             hovertemplate=f"{market} : %{{x:.2%}}<br>{asset} : %{{y:.2%}}<extra></extra>"))
    xs = np.linspace(cp["x"].min(), cp["x"].max(), 50)
    fig.add_trace(go.Scatter(x=xs, y=cp["intercept"] + cp["beta"] * xs, mode="lines", name="Droite du CAPM",
                             line=dict(color=COLORS["cyan"], width=2.5), hoverinfo="skip"))
    fig.update_xaxes(tickformat=".0%", title=f"Excès de rendement {market}")
    fig.update_yaxes(tickformat=".0%", title=f"Excès de rendement {asset}")
    fig.update_layout(showlegend=False)
    return fig
