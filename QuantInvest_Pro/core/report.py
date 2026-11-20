"""Rapport HTML autonome (tableaux, graphiques Plotly interactifs, verdict, hypothèses, sources)."""
from __future__ import annotations

import html
from datetime import datetime

import pandas as pd

CSS = """body{font-family:Inter,Arial,sans-serif;background:#07071A;color:#E6E6F5;max-width:1100px;margin:auto;padding:24px}
h1,h2{font-family:'Space Grotesk',Arial,sans-serif}h1{color:#C4B5FD}h2{border-bottom:1px solid #3b2a7a;padding-bottom:6px;margin-top:36px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #2a2b55;padding:6px 8px;text-align:right}
th{background:#161743}td:first-child,th:first-child{text-align:left}.box{background:#121335;border:1px solid #3b2a7a;
border-radius:12px;padding:14px 18px;line-height:1.6}small{color:#8E8FB5}"""


def build_html(title: str, verdict: str, tables: dict[str, pd.DataFrame], figures: dict[str, object],
               hypotheses: list[str], sources: list[str]) -> str:
    parts = [f"<html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{CSS}</style></head><body>",
             f"<h1>{html.escape(title)}</h1><small>Rapport généré le {datetime.now():%d/%m/%Y à %H:%M} par QuantInvest Pro</small>",
             f"<h2>Verdict</h2><div class='box'>{verdict}</div>"]
    for name, df in tables.items():
        parts.append(f"<h2>{html.escape(name)}</h2>{df.to_html(escape=True, border=0)}")
    first = True
    for name, fig in figures.items():
        parts.append(f"<h2>{html.escape(name)}</h2>")
        parts.append(fig.to_html(full_html=False, include_plotlyjs="cdn" if first else False))
        first = False
    parts.append("<h2>Hypothèses et limites</h2><ul>" + "".join(f"<li>{html.escape(h)}</li>" for h in hypotheses) + "</ul>")
    parts.append("<h2>Sources</h2><ul>" + "".join(f"<li>{html.escape(s)}</li>" for s in sources) + "</ul></body></html>")
    return "\n".join(parts)
