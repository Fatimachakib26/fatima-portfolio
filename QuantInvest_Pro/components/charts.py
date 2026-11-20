"""
Graphiques Plotly. Les fonctions de tracé (frontière efficiente, heatmap,
courbes de performance…) seront ajoutées aux étapes 5 et 6 ; elles ne
recevront que des données réellement calculées par core/.
"""
from __future__ import annotations

import plotly.graph_objects as go

PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def base_figure(title: str = "", height: int = 360) -> go.Figure:
    """Figure vide portant le template de l'application."""
    fig = go.Figure()
    fig.update_layout(title=title, height=height)
    return fig
