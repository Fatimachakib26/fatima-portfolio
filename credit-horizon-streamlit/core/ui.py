"""Éléments d'interface partagés : identité visuelle, en-têtes, badges, garde de connexion."""
from __future__ import annotations

import streamlit as st

from . import auth, db
from .scoring import LEVEL_COLORS

CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
[data-testid="stSidebar"] {background: linear-gradient(180deg, #04261c 0%, #063b2b 100%);}
[data-testid="stSidebar"] * {color: #e6f4ee;}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {background: rgba(16,185,129,.18); border: 1px solid rgba(16,185,129,.4);}
[data-testid="stSidebar"] .stButton button {background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.15); color: #e6f4ee;}
.block-container {padding-top: 3.4rem; max-width: 1400px;}
[data-testid="stSidebarHeader"] img, [data-testid="stLogo"] {height: 2.6rem !important; max-width: 100%;}
h1, h2, h3 {color: #04261c; letter-spacing: -0.01em;}
div[data-testid="stMetric"] {background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(6,59,43,.06), 0 4px 16px rgba(6,59,43,.06);}
div[data-testid="stMetric"] label p {text-transform: uppercase; font-size: .72rem; letter-spacing: .04em; color: #64748b;}
.ch-brand {display:flex; gap:10px; align-items:center; padding: 4px 0 14px 0; border-bottom: 1px solid rgba(255,255,255,.12); margin-bottom: 8px;}
.ch-brand b {font-size: 1.02rem; letter-spacing: .03em; color: #fff;}
.ch-brand small {display:block; font-size: .62rem; letter-spacing: .3em; color: #34d399; font-weight: 700;}
.ch-header {display:flex; gap:14px; align-items:flex-start; margin-bottom: 6px;}
.ch-icon {background:#063b2b; color:#6ee7b7; border-radius: 12px; padding: 8px 11px; font-size: 1.25rem;}
.ch-sub {color:#64748b; font-size: .92rem; margin-top: -6px;}
.ch-demo {background:#f5f3ff; border:1px solid #ddd6fe; color:#5b21b6; border-radius:10px; padding:6px 12px; font-size:.78rem; margin-bottom: 12px;}
.ch-pill {display:inline-block; padding: 2px 9px; border-radius: 999px; font-size: .75rem; font-weight: 700; color: #fff;}
.ch-badge {display:inline-block; padding: 1px 7px; border-radius: 6px; font-size: .72rem; font-weight: 700; background:#d1fae5; color:#0a4d38; margin: 0 3px 3px 0;}
.ch-card {background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:14px 16px; margin-bottom: 10px;}
.ch-chain {display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 8px;}
.ch-chain div {background:#f8fafc; border-radius:10px; padding:8px; font-size:.82rem;}
.ch-chain b {display:block; font-size:.66rem; color:#0f7a58; letter-spacing:.05em;}
.ch-kpis {display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 14px;}
.ch-kpi {background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:14px 16px; box-shadow: 0 1px 2px rgba(6,59,43,.06), 0 4px 16px rgba(6,59,43,.06);}
.ch-kpi .l {font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; color:#64748b; font-weight:600;}
.ch-kpi .v {font-size:1.8rem; font-weight:800; color:#04261c; line-height:1.25; font-variant-numeric: tabular-nums;}
.ch-kpi .h {font-size:.78rem; color:#64748b;}
.ch-kpi.red {border-left:4px solid #dc2626;} .ch-kpi.amber {border-left:4px solid #f59e0b;} .ch-kpi.green {border-left:4px solid #10b981;} .ch-kpi.brand {border-left:4px solid #0f7a58;}
.ch-warn {background:#fffbeb; border:1px solid #fde68a; color:#92400e; border-radius:10px; padding:8px 12px; font-size:.82rem;}
@media (max-width: 800px) {.ch-chain {grid-template-columns: 1fr;}}
</style>
"""

BRAND = """<div class="ch-brand"><svg viewBox="0 0 64 64" width="34" height="34"><rect width="64" height="64" rx="14" fill="#0a4d38"/>
<path d="M12 42 Q32 14 52 42" fill="none" stroke="#10b981" stroke-width="5" stroke-linecap="round"/><path d="M8 46h48" stroke="#d1fae5" stroke-width="4" stroke-linecap="round"/>
<circle cx="32" cy="24" r="5" fill="#34d399"/></svg><div><b>CRÉDIT HORIZON</b><small>RISK INTELLIGENCE</small></div></div>"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f'<div class="ch-header"><div class="ch-icon">{icon}</div><div><h1 style="margin:0;font-size:1.7rem">{title}</h1></div></div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="ch-sub">{subtitle}</p>', unsafe_allow_html=True)


def kpis(items: list[tuple]):
    """items : (libellé, valeur, aide, ton) avec ton dans brand | red | amber | green."""
    html = "".join(f'<div class="ch-kpi {t}"><div class="l">{l}</div><div class="v">{v}</div><div class="h">{h}</div></div>' for l, v, h, t in items)
    st.markdown(f'<div class="ch-kpis">{html}</div>', unsafe_allow_html=True)


def demo_banner():
    st.markdown('<div class="ch-demo">🧪 <b>Environnement de démonstration</b> – cas académique fictif EMSI. '
                'Les lignes marquées « Démo » sont des données de démonstration.</div>', unsafe_allow_html=True)


def level_pill(level: str, score: int | None = None) -> str:
    return f'<span class="ch-pill" style="background:{LEVEL_COLORS.get(level, "#94a3b8")}">{level}{f" · {score}" if score is not None else ""}</span>'


def user() -> dict | None:
    return st.session_state.get("user")


def can(perm: str) -> bool:
    u = user()
    return bool(u) and auth.can(u["role"], perm)


def readonly(text: str):
    st.info("🔒 " + text)


def audit(action: str, entity: str, entity_id: str = "", details: str = ""):
    db.audit(user(), action, entity, entity_id, details)


def toast_ok(msg: str):
    st.session_state["_toast"] = msg


def flush_toast():
    m = st.session_state.pop("_toast", None)
    if m:
        st.toast(m, icon="✅")
