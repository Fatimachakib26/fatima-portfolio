"""
Tanger II — Application interactive de démonstration du montage financier.

Lancement :  streamlit run app.py
"""
from __future__ import annotations

import io
import time
import zipfile
from dataclasses import asdict, replace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import auth
import model as M

st.set_page_config(page_title="Tanger II · Simulateur financier", page_icon="🏭", layout="wide")

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
COL = {"A": "#2a6f97", "B": "#c8553d", "C": "#6a994e", "X": "#8e6c8a", "grid": "rgba(128,128,128,.18)"}
st.markdown(
    """
<style>
.block-container{padding-top:1.4rem;max-width:1400px}
.login-head{text-align:center;margin:3rem 0 1rem}
.login-head .logo{width:64px;height:64px;border-radius:16px;margin:0 auto .8rem;display:flex;
 align-items:center;justify-content:center;font-weight:800;font-size:1.5rem;color:#fff;
 background:linear-gradient(135deg,#2a6f97,#c8553d)}
.login-head h2{margin:.2rem 0}.login-head p{opacity:.7;margin:0}
div[data-testid="stMetric"]{background:rgba(127,127,127,.06);border:1px solid rgba(127,127,127,.15);
 border-radius:12px;padding:.7rem .9rem}
.verdict{border-radius:10px;padding:.6rem .9rem;margin:.2rem 0;font-weight:600}
.ok{background:rgba(106,153,78,.15);border-left:5px solid #6a994e}
.ko{background:rgba(200,85,61,.15);border-left:5px solid #c8553d}
.warn{background:rgba(233,168,58,.18);border-left:5px solid #e9a83a}
</style>
""",
    unsafe_allow_html=True,
)


def fig_layout(fig, h=380, title=None):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40 if title else 15, b=10), title=title,
                      legend=dict(orientation="h", y=-0.15), hovermode="x unified",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor=COL["grid"])
    fig.update_yaxes(gridcolor=COL["grid"])
    return fig


def pct(x, d=2):
    return "n.d." if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x*100:,.{d}f} %".replace(",", " ")


def mdh(x, d=1):
    return f"{x:,.{d}f} MDH".replace(",", " ")


def xx(x):
    return "n.d." if x is None or np.isnan(x) else f"{x:.2f}x"


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=2000)
def run_cached(fin_d: dict, sh_d: dict, mk_d: dict):
    return M.run(M.Financing(**fin_d), M.Shocks(**sh_d), M.Market(**mk_d))


def run(fin, sh=None, mk=None):
    return run_cached(asdict(fin), asdict(sh or M.Shocks()), asdict(mk or M.Market()))


@st.cache_data(show_spinner=False)
def mc_cached(fin_d, sh_d, mk_d, n, vol, seed):
    draws = M.draw_mc(n, vol, seed=seed)
    return pd.DataFrame(M.monte_carlo(M.Financing(**fin_d), M.Shocks(**sh_d), M.Market(**mk_d), draws))


@st.cache_data(show_spinner=False)
def opt_cached(sh_d, mk_d, need, eq_grid, l_grid):
    return pd.DataFrame(M.optimize(M.Shocks(**sh_d), M.Market(**mk_d), eq_grid, l_grid, need))


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------
if not auth.login_form():
    st.stop()

user = st.session_state.user
ss = st.session_state
ss.setdefault("custom", [])
ss.setdefault("market", asdict(M.Market()))

PAGES = ["🏠 Tableau de bord", "🎛️ Simulateur (curseurs)", "📝 Formulaire scénario",
         "🌪️ Sensibilités & stress tests", "🎲 Monte-Carlo", "⚙️ Optimiseur de structure",
         "▶️ Simulation en direct", "📤 Export Power BI"]
ADMIN_ONLY = {"⚙️ Optimiseur de structure", "📤 Export Power BI"}

with st.sidebar:
    st.markdown(f"### 🏭 Tanger II\nConnecté : **{user['name']}** · _{user['role']}_")
    allowed = [p for p in PAGES if user["role"] == "admin" or p not in ADMIN_ONLY]
    page = st.radio("Navigation", allowed, label_visibility="collapsed")
    st.divider()
    with st.expander("Coût du capital (global)"):
        mk = ss.market
        mk["rf"] = st.slider("Taux sans risque", 0.02, 0.06, mk["rf"], 0.0005, format="%.4f")
        mk["beta_u"] = st.slider("Bêta désendetté", 0.6, 1.8, mk["beta_u"], 0.05)
        mk["mrp"] = st.slider("Prime de risque marché", 0.04, 0.10, mk["mrp"], 0.001, format="%.3f")
        mk["specific_premium"] = st.slider("Prime spécifique", 0.0, 0.05, mk["specific_premium"], 0.005,
                                           format="%.3f")
        mk["tv_method"] = st.selectbox("Valeur terminale", [1, 2, 3], index=mk["tv_method"] - 1,
                                       format_func={1: "VNC + BFR (prudent)", 2: "Gordon-Shapiro",
                                                    3: "Multiple d'EBITDA"}.get)
        if mk["tv_method"] == 2:
            mk["growth"] = st.slider("Croissance à l'infini", 0.0, 0.04, mk["growth"], 0.0025)
        if mk["tv_method"] == 3:
            mk["exit_multiple"] = st.slider("Multiple de sortie", 3.0, 9.0, mk["exit_multiple"], 0.5)
    st.caption("Cas pédagogique fictif. Modèle Python recalculé à partir des hypothèses de "
               "l'onglet 02 du modèle Excel ; de légers écarts avec l'Excel sont possibles.")
    if st.button("Se déconnecter", width="stretch"):
        auth.logout()

MK = M.Market(**ss.market)


def kpi_frame(results: dict) -> pd.DataFrame:
    rows = []
    for name, r in results.items():
        k = r["kpi"]
        rows.append({"Scénario": name, "WACC": k["WACC"], "VAN projet (MDH)": k["VAN projet"],
                     "TRI projet": k["TRI projet"], "TRI FP": k["TRI FP"], "Coût FP": k["Coût FP (Ke)"],
                     "DSCR min": k["DSCR min"], "Levier max": k["Levier max"],
                     "Trésorerie min (MDH)": k["Trésorerie min"], "Besoin non financé (MDH)": k["Besoin non financé"],
                     "Dilution": k["Dilution"], "Covenants": "✅" if k["Covenants OK"] else "❌"})
    return pd.DataFrame(rows).set_index("Scénario")


def style_kpi(df):
    return df.style.format({"WACC": "{:.2%}", "TRI projet": "{:.2%}", "TRI FP": "{:.2%}", "Coût FP": "{:.2%}",
                            "VAN projet (MDH)": "{:,.1f}", "DSCR min": "{:.2f}x", "Levier max": "{:.2f}x",
                            "Trésorerie min (MDH)": "{:,.1f}", "Besoin non financé (MDH)": "{:,.1f}",
                            "Dilution": "{:.1%}"}, na_rep="n.d.")


# ===========================================================================
# 1. Tableau de bord
# ===========================================================================
if page == PAGES[0]:
    st.title("Tableau de bord — Financement de l'unité « Tanger II »")
    st.caption("Usine de pièces plastiques injectées et peintes · 500 000 kits/an · mise en service le 01/07/2028 · "
               "besoin ≈ 960 MDH · capacité d'apport de la maison mère : 350 MDH")
    case = st.selectbox("Cas d'hypothèses", list(M.CASES), index=0)
    sh = M.CASES[case]
    res = {k: run(f, sh, MK) for k, f in M.SCENARIOS.items()}
    b = res["B"]["kpi"]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("CA 2032 (MDH)", f"{b['CA 2032']:,.0f}".replace(",", " "))
    c2.metric("EBITDA 2032 (MDH)", f"{b['EBITDA 2032']:,.0f}", pct(b["EBITDA 2032"] / b["CA 2032"], 1) + " marge")
    c3.metric("VAN projet B (MDH)", f"{b['VAN projet']:,.1f}", f"WACC {pct(b['WACC'])}")
    c4.metric("TRI projet", pct(b["TRI projet"]))
    c5.metric("TRI fonds propres (B)", pct(b["TRI FP"]), f"Ke {pct(b['Coût FP (Ke)'])}")
    c6.metric("DSCR min (B)", xx(b["DSCR min"]), "≥ 1,20x requis",
              delta_color="normal" if b["DSCR min"] >= 1.2 else "inverse")

    st.subheader("Comparaison des trois montages")
    st.dataframe(style_kpi(kpi_frame({M.SCENARIOS[k].name: v for k, v in res.items()})), width="stretch")

    t = {k: pd.DataFrame(v["table"]).set_index("Année") for k, v in res.items()}
    g1, g2 = st.columns(2)
    with g1:
        tb = t["B"]
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=tb.index, y=tb["Chiffre d'affaires"], name="Chiffre d'affaires", marker_color="#9fb7c9")
        fig.add_bar(x=tb.index, y=tb["EBITDA économique"], name="EBITDA", marker_color=COL["A"])
        fig.add_scatter(x=tb.index, y=tb["Marge EBITDA"] * 100, name="Marge EBITDA (%)", secondary_y=True,
                        line=dict(color=COL["B"], width=3))
        fig.update_layout(barmode="overlay")
        st.plotly_chart(fig_layout(fig, title="Activité et rentabilité (MDH)"), width="stretch")
    with g2:
        fig = go.Figure()
        for k in "ABC":
            fig.add_scatter(x=t[k].index, y=t[k]["DSCR"], name=f"DSCR {k}", line=dict(color=COL[k], width=3),
                            mode="lines+markers")
        fig.add_hline(y=1.2, line_dash="dash", line_color="red", annotation_text="Covenant 1,20x")
        st.plotly_chart(fig_layout(fig, title="DSCR par scénario"), width="stretch")
    g3, g4 = st.columns(2)
    with g3:
        fig = go.Figure()
        for k in "ABC":
            fig.add_scatter(x=t[k].index, y=t[k]["Trésorerie (fin)"], name=f"Trésorerie {k}",
                            line=dict(color=COL[k], width=3))
        fig.add_hline(y=40, line_dash="dot", annotation_text="Minimum cible 40 MDH")
        fig.add_hline(y=0, line_color="red")
        st.plotly_chart(fig_layout(fig, title="Trésorerie de clôture (MDH)"), width="stretch")
    with g4:
        f = M.SCENARIOS["B"]
        labels = ["CAPEX", "BFR initial", "Réserve trésorerie", "Frais", "Fonds propres", "Dette bancaire",
                  "Crédit-bail"]
        fig = go.Figure(go.Sankey(
            node=dict(label=["Fonds propres", "Dette bancaire", "Crédit-bail", "Besoin total",
                             "CAPEX", "BFR initial", "Réserve + frais"],
                      color=[COL["A"], COL["B"], COL["C"], "#888", "#9fb7c9", "#e9a83a", "#bbb"], pad=18),
            link=dict(source=[0, 1, 2, 3, 3, 3], target=[3, 3, 3, 4, 5, 6],
                      value=[f.equity, f.debt, f.lease, 791, 107, 62])))
        st.plotly_chart(fig_layout(fig, title="Ressources → emplois, scénario B (MDH)"), width="stretch")

    best = "B"
    st.markdown(f"<div class='verdict ok'>Recommandation : scénario <b>B sécurisé</b> — seul montage admissible "
                f"sans condition préalable (apport 350 MDH, aucune dilution, covenants respectés). "
                f"A dilue la maison mère de {pct(res['A']['kpi']['Dilution'],1)} ; C dépend d'aides non acquises.</div>",
                unsafe_allow_html=True)
    with st.expander("Tableau financier détaillé — scénario B"):
        st.dataframe(t[best].T.style.format("{:,.1f}", na_rep="—"), width="stretch")

# ===========================================================================
# 2. Simulateur
# ===========================================================================
elif page == PAGES[1]:
    st.title("Simulateur — chocs et mesures correctrices")
    st.caption("Déplacez les curseurs : tout le modèle (BP, BFR, dette, crédit-bail, IS, trésorerie, valorisation) "
               "se recalcule instantanément pour les trois scénarios.")
    left, right = st.columns([1, 2.6])
    with left:
        preset = st.selectbox("Partir du cas", list(M.CASES))
        p = M.CASES[preset]
        st.markdown("**Chocs d'exploitation**")
        price = st.slider("Prix de vente (%)", -10.0, 10.0, p.price * 100, 0.5, format="%+.1f %%") / 100
        volume = st.slider("Volumes (%)", -20.0, 10.0, p.volume * 100, 1.0, format="%+.0f %%") / 100
        mat = st.slider("Coût matières (%)", -10.0, 15.0, p.materials * 100, 0.5, format="%+.1f %%") / 100
        ene = st.slider("Coût énergie (%)", -20.0, 50.0, p.energy * 100, 5.0, format="%+.0f %%") / 100
        dso = st.slider("Allongement délai clients (jours)", 0, 60, int(p.dso_days), 5)
        st.markdown("**Chocs de projet**")
        capex = st.slider("Dépassement du CAPEX (%)", -10.0, 40.0, p.capex_overrun * 100, 1.0, format="%+.0f %%") / 100
        delay = st.slider("Retard de mise en production (mois)", 0, 18, int(p.delay_months), 1)
        rate = st.slider("Variation du taux d'intérêt (pts)", -1.0, 3.0, p.rate * 100, 0.25, format="%+.2f") / 100
        prime = st.toggle("Prime à l'investissement obtenue (C)", value=p.prime_obtained >= 0.5)
        st.markdown("**Mesures correctrices**")
        eq_x = st.slider("Apport complémentaire FP (MDH)", 0, 150, int(p.extra_equity), 5)
        sb = st.slider("Dette de réserve (MDH)", 0, 150, int(p.standby_debt), 5)
        gr = st.slider("Différé supplémentaire (semestres)", 0, 4, int(p.extra_grace))
        tn = st.slider("Allongement de la dette (semestres)", 0, 6, int(p.extra_tenor))
        dc = st.slider("Investissements reportés (MDH)", 0, 60, int(p.deferred_capex), 5)
    sh = M.Shocks(capex, delay, price, volume, mat, ene, 0.0, rate, dso, 1.0 if prime else 0.0, eq_x, sb, gr, tn, dc)
    res = {k: run(f, sh, MK) for k, f in M.SCENARIOS.items()}
    base = {k: run(f, M.Shocks(), MK) for k, f in M.SCENARIOS.items()}
    with right:
        cols = st.columns(3)
        for col, k in zip(cols, "ABC"):
            r, b0 = res[k]["kpi"], base[k]["kpi"]
            with col:
                st.markdown(f"#### <span style='color:{COL[k]}'>●</span> Scénario {k}", unsafe_allow_html=True)
                st.caption(M.SCENARIOS[k].name.split("—")[1].strip())
                st.metric("VAN projet (MDH)", f"{r['VAN projet']:,.1f}", f"{r['VAN projet'] - b0['VAN projet']:+.1f} vs central")
                st.metric("TRI FP", pct(r["TRI FP"]), f"{(r['TRI FP'] - b0['TRI FP'])*100:+.2f} pts")
                st.metric("DSCR min", xx(r["DSCR min"]), f"{r['DSCR min'] - b0['DSCR min']:+.2f}")
                st.metric("Trésorerie min (MDH)", f"{r['Trésorerie min']:,.1f}")
                ok = r["Covenants OK"]
                gap = r["Besoin non financé"]
                msg = ("✅ Soutenable" if ok else
                       f"❌ {'Besoin non financé ' + mdh(gap, 0) if gap > 0 else ''}"
                       f"{' · DSCR < 1,20x' if r['DSCR min'] < 1.2 else ''}"
                       f"{' · Levier > 3,5x' if r['Levier max'] > 3.5 else ''}")
                st.markdown(f"<div class='verdict {'ok' if ok else 'ko'}'>{msg}</div>", unsafe_allow_html=True)
        sel = st.radio("Graphiques du scénario", list("ABC"), index=1, horizontal=True)
        tb = pd.DataFrame(res[sel]["table"]).set_index("Année")
        t0 = pd.DataFrame(base[sel]["table"]).set_index("Année")
        g1, g2 = st.columns(2)
        with g1:
            fig = go.Figure()
            fig.add_scatter(x=t0.index, y=t0["Trésorerie (fin)"], name="Central", line=dict(dash="dot", color="#999"))
            fig.add_scatter(x=tb.index, y=tb["Trésorerie (fin)"], name="Simulé", fill="tozeroy",
                            line=dict(color=COL[sel], width=3))
            fig.add_hline(y=0, line_color="red")
            st.plotly_chart(fig_layout(fig, 330, "Trésorerie (MDH)"), width="stretch")
        with g2:
            fig = go.Figure()
            fig.add_scatter(x=t0.index, y=t0["DSCR"], name="Central", line=dict(dash="dot", color="#999"))
            fig.add_scatter(x=tb.index, y=tb["DSCR"], name="Simulé", line=dict(color=COL[sel], width=3),
                            mode="lines+markers")
            fig.add_hline(y=1.2, line_dash="dash", line_color="red")
            st.plotly_chart(fig_layout(fig, 330, "DSCR"), width="stretch")
        fig = go.Figure()
        fig.add_bar(x=tb.index, y=tb["FCFF projet"], name="FCFF projet", marker_color=COL[sel])
        fig.add_bar(x=tb.index, y=tb["Dividendes"], name="Dividendes", marker_color="#e9a83a")
        fig.add_scatter(x=tb.index, y=tb["Dette bancaire (fin)"] + tb["Crédit-bail (encours)"], name="Dette + crédit-bail",
                        line=dict(color="#555", width=2))
        st.plotly_chart(fig_layout(fig, 330, "Flux et endettement (MDH)"), width="stretch")

# ===========================================================================
# 3. Formulaire
# ===========================================================================
elif page == PAGES[2]:
    st.title("Formulaire — construire un scénario de financement")
    st.caption("Renseignez une structure personnalisée ; elle est évaluée et comparée aux scénarios A, B et C.")
    with st.form("scenario"):
        a, b, c = st.columns(3)
        with a:
            st.markdown("**Ressources (MDH)**")
            name = st.text_input("Nom du scénario", f"Perso {len(ss.custom) + 1}")
            eq = st.number_input("Fonds propres", 100.0, 700.0, 350.0, 10.0)
            debt = st.number_input("Dette bancaire LT", 0.0, 800.0, 450.0, 10.0)
            lease = st.number_input("Crédit-bail (valeur du matériel)", 0.0, 355.0, 180.0, 10.0)
        with b:
            st.markdown("**Conditions de la dette**")
            r = st.number_input("Taux de la dette (%)", 2.0, 12.0, 5.25, 0.05) / 100
            grace = st.select_slider("Différé (semestres)", list(range(0, 11)), 6)
            nrep = st.select_slider("Échéances semestrielles", list(range(6, 25)), 14)
            prof = st.radio("Profil", ["Annuités constantes", "Capital constant"], horizontal=True)
            lr = st.number_input("Taux du crédit-bail (%)", 3.0, 12.0, 6.5, 0.05) / 100
        with c:
            st.markdown("**Aides publiques (conditionnelles)**")
            prime = st.slider("Prime à l'investissement (% assiette)", 0.0, 0.30, 0.0, 0.01)
            bridge = st.slider("Part préfinancée par crédit relais", 0.0, 1.0, 0.0, 0.1)
            hol = st.checkbox("Exonération d'IS de 5 ans (sociétés industrielles nouvelles)")
            case = st.selectbox("Évaluer dans le cas", list(M.CASES))
        sub = st.form_submit_button("Évaluer le scénario", type="primary", width="stretch")
    if sub:
        f = M.Financing(name, eq, debt, lease, r, grace, nrep, prof.startswith("Ann"), 0.01, lr if lease else 0.0,
                        14, 0.01, prime, bridge, -0.0025, hol)
        ss.custom.append({"fin": asdict(f), "case": case})
        st.success(f"Scénario « {name} » enregistré.")
    if ss.custom:
        last = ss.custom[-1]
        f = M.Financing(**last["fin"])
        sh = M.CASES[last["case"]]
        need = 960
        total = f.equity + f.debt + f.lease
        res = {M.SCENARIOS[k].name: run(v, sh, MK) for k, v in M.SCENARIOS.items()}
        for item in ss.custom:
            res[item["fin"]["name"]] = run(M.Financing(**item["fin"]), M.CASES[item["case"]], MK)
        k = res[f.name]["kpi"]
        st.subheader(f"Résultat : {f.name} ({last['case']})")
        cc = st.columns(5)
        cc[0].metric("Ressources", mdh(total, 0), f"{total - need:+.0f} vs besoin 960")
        cc[1].metric("VAN projet", mdh(k["VAN projet"]))
        cc[2].metric("TRI FP", pct(k["TRI FP"]), f"Ke {pct(k['Coût FP (Ke)'])}")
        cc[3].metric("DSCR min", xx(k["DSCR min"]))
        cc[4].metric("Levier max", xx(k["Levier max"]))
        checks = [
            ("Apport ≤ capacité de la maison mère (350 MDH)", f.equity <= 350),
            ("Dette bancaire ≤ plafond présumé des banques (540 MDH)", f.debt <= 540),
            ("DSCR minimum ≥ 1,20x", k["DSCR min"] >= 1.2),
            ("Dette nette / EBITDA ≤ 3,5x", k["Levier max"] <= 3.5),
            ("Trésorerie jamais négative", k["Trésorerie min"] >= 0),
            ("TRI FP > coût des fonds propres", k["TRI FP"] > k["Coût FP (Ke)"]),
            ("Aucune aide non acquise dans le montage", prime == 0 and not hol),
        ]
        cl = st.columns(2)
        for i, (lbl, okk) in enumerate(checks):
            cl[i % 2].markdown(f"<div class='verdict {'ok' if okk else 'ko'}'>{'✅' if okk else '❌'} {lbl}</div>",
                               unsafe_allow_html=True)
        st.dataframe(style_kpi(kpi_frame(res)), width="stretch")
        # radar
        cats = ["VAN", "TRI FP", "DSCR min", "Liquidité", "Faible levier", "Contrôle"]

        def score(kp):
            return [np.clip(kp["VAN projet"] / 300, 0, 1), np.clip(kp["TRI FP"] / 0.25, 0, 1),
                    np.clip((kp["DSCR min"] - 1) / 1, 0, 1), np.clip(kp["Trésorerie min"] / 100, 0, 1),
                    np.clip(1 - kp["Levier max"] / 4, 0, 1), 1 - kp["Dilution"]]
        fig = go.Figure()
        palette = [COL["A"], COL["B"], COL["C"], COL["X"], "#e9a83a", "#3a9e9e", "#777"]
        for i, (nm, rr) in enumerate(res.items()):
            s = score(rr["kpi"])
            fig.add_scatterpolar(r=s + [s[0]], theta=cats + [cats[0]], name=nm, fill="toself", opacity=.55,
                                 line=dict(color=palette[i % len(palette)]))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
        st.plotly_chart(fig_layout(fig, 460, "Profil multicritère (normalisé 0-1)"), width="stretch")
        if st.button("Effacer les scénarios personnalisés"):
            ss.custom = []
            st.rerun()

# ===========================================================================
# 4. Sensibilités & stress
# ===========================================================================
elif page == PAGES[3]:
    st.title("Sensibilités et stress tests")
    sc = st.radio("Scénario", list("ABC"), index=1, horizontal=True, format_func=lambda k: M.SCENARIOS[k].name)
    fin = M.SCENARIOS[sc]
    tab1, tab2, tab3 = st.tabs(["Diagramme tornade", "Carte de chaleur 2D", "Table des cas (stress)"])
    with tab1:
        metric = st.selectbox("Indicateur", ["VAN projet", "TRI FP", "DSCR min", "Trésorerie min"])
        ref, rows = M.tornado(fin, M.Shocks(), MK, metric)
        fig = go.Figure()
        lbl = [r[0] for r in rows]
        fig.add_bar(y=lbl, x=[r[1] for r in rows], orientation="h", name="Variable à la baisse", marker_color=COL["A"])
        fig.add_bar(y=lbl, x=[r[2] for r in rows], orientation="h", name="Variable à la hausse", marker_color=COL["B"])
        fig.update_layout(barmode="overlay")
        st.plotly_chart(fig_layout(fig, 430, f"Écart de « {metric} » autour du cas central ({ref:,.3f})"),
                        width="stretch")
    with tab2:
        c1, c2 = st.columns(2)
        metric2 = c1.selectbox("Indicateur ", ["VAN projet", "DSCR min", "TRI FP"])
        pair = c2.selectbox("Couple de variables", ["Prix × Volumes", "CAPEX × Retard", "Matières × Prix"])
        if pair == "Prix × Volumes":
            xs, ys, xa, ya = np.linspace(-0.06, 0.06, 9), np.linspace(-0.15, 0.06, 8), "price", "volume"
        elif pair == "CAPEX × Retard":
            xs, ys, xa, ya = np.linspace(0, 0.30, 7), np.arange(0, 13, 2), "capex_overrun", "delay_months"
        else:
            xs, ys, xa, ya = np.linspace(-0.06, 0.06, 9), np.linspace(-0.06, 0.06, 9), "materials", "price"
        z = [[run(fin, replace(M.Shocks(), **{xa: float(x), ya: float(y)}), MK)["kpi"][metric2] for x in xs] for y in ys]
        fig = go.Figure(go.Heatmap(z=z, x=[f"{x:+.0%}" if xa != "delay_months" else f"{x:.0f}" for x in xs],
                                   y=[f"{y:+.0%}" if ya != "delay_months" else f"{y:.0f} mois" for y in ys],
                                   colorscale="RdYlGn", zmid=0 if metric2 == "VAN projet" else (1.2 if metric2 == "DSCR min" else 0.157),
                                   text=np.round(z, 2), texttemplate="%{text}"))
        fig.update_xaxes(title=xa); fig.update_yaxes(title=ya)
        st.plotly_chart(fig_layout(fig, 480, f"{metric2} — {pair}"), width="stretch")
    with tab3:
        rows = []
        for cname, sh in M.CASES.items():
            for k, f in M.SCENARIOS.items():
                kp = run(f, sh, MK)["kpi"]
                rows.append({"Cas": cname, "Scénario": k, "VAN": kp["VAN projet"], "TRI FP": kp["TRI FP"],
                             "DSCR min": kp["DSCR min"], "Levier max": kp["Levier max"],
                             "Besoin non financé": kp["Besoin non financé"],
                             "Verdict": "✅ soutenable" if kp["Covenants OK"] else "❌ non soutenable"})
        df = pd.DataFrame(rows)
        st.dataframe(df.style.format({"VAN": "{:,.1f}", "TRI FP": "{:.2%}", "DSCR min": "{:.2f}x",
                                      "Levier max": "{:.2f}x", "Besoin non financé": "{:,.1f}"}),
                     width="stretch", height=520)
        fig = go.Figure()
        for k in "ABC":
            d = df[df.Scénario == k]
            fig.add_bar(x=d["Cas"], y=d["VAN"], name=k, marker_color=COL[k])
        st.plotly_chart(fig_layout(fig, 380, "VAN projet par cas (MDH)"), width="stretch")

# ===========================================================================
# 5. Monte-Carlo
# ===========================================================================
elif page == PAGES[4]:
    st.title("Simulation de Monte-Carlo (copule gaussienne corrélée)")
    st.caption("Sept facteurs de risque tirés conjointement : prix, volumes, matières, énergie (lois normales), "
               "dépassement du CAPEX (loi triangulaire), retard (loi exponentielle tronquée à 18 mois), taux. "
               "Les corrélations (ex. CAPEX ↔ retard = 0,6 ; matières ↔ énergie = 0,5) passent par une décomposition de Cholesky.")
    c = st.columns(4)
    sc = c[0].selectbox("Scénario", list("ABC"), index=1, format_func=lambda k: M.SCENARIOS[k].name)
    n = c[1].select_slider("Nombre de tirages", [250, 500, 1000, 2000, 5000], 1000)
    seed = c[2].number_input("Graine aléatoire", 0, 9999, 42)
    c[3].markdown(" ")
    with st.expander("Paramètres des lois", expanded=False):
        p = st.columns(4)
        vol = {"price": p[0].slider("σ prix", 0.0, 0.08, 0.02, 0.005),
               "volume": p[1].slider("σ volumes", 0.0, 0.20, 0.06, 0.01),
               "materials": p[2].slider("σ matières", 0.0, 0.10, 0.03, 0.005),
               "energy": p[3].slider("σ énergie", 0.0, 0.40, 0.10, 0.02),
               "rate": p[0].slider("σ taux", 0.0, 0.02, 0.005, 0.001, format="%.3f"),
               "delay_mean": p[1].slider("Retard moyen (mois)", 0.0, 8.0, 2.0, 0.5)}
        tri_lo = p[2].slider("CAPEX min", -0.10, 0.0, -0.03, 0.01)
        tri_hi = p[3].slider("CAPEX max", 0.05, 0.50, 0.25, 0.01)
        vol["capex_tri"] = (tri_lo, 0.0, tri_hi)
    with st.spinner(f"{n} simulations du modèle complet…"):
        df = mc_cached(asdict(M.SCENARIOS[sc]), asdict(M.Shocks()), asdict(MK), n,
                       {k: (tuple(v) if isinstance(v, tuple) else v) for k, v in vol.items()}, int(seed))
    m = st.columns(5)
    m[0].metric("VAN moyenne (MDH)", f"{df['VAN projet'].mean():,.1f}")
    m[1].metric("P(VAN < 0)", pct((df["VAN projet"] < 0).mean(), 1))
    m[2].metric("VaR 5 % VAN (MDH)", f"{df['VAN projet'].quantile(0.05):,.0f}")
    m[3].metric("P(DSCR < 1,20x)", pct((df["DSCR min"] < 1.2).mean(), 1))
    m[4].metric("P(trésorerie < 0)", pct((df["Trésorerie min"] < 0).mean(), 1))
    g1, g2 = st.columns(2)
    with g1:
        fig = go.Figure(go.Histogram(x=df["VAN projet"], nbinsx=60, marker_color=COL[sc]))
        fig.add_vline(x=0, line_color="red")
        fig.add_vline(x=df["VAN projet"].quantile(0.05), line_dash="dash", annotation_text="VaR 5 %")
        st.plotly_chart(fig_layout(fig, 360, "Distribution de la VAN projet (MDH)"), width="stretch")
    with g2:
        fig = go.Figure(go.Histogram(x=df["DSCR min"], nbinsx=60, marker_color=COL["X"]))
        fig.add_vline(x=1.2, line_color="red", annotation_text="Covenant")
        st.plotly_chart(fig_layout(fig, 360, "Distribution du DSCR minimum"), width="stretch")
    g3, g4 = st.columns(2)
    with g3:
        corr = df[M.MC_VARS + ["VAN projet"]].corr(method="spearman")["VAN projet"].drop("VAN projet").sort_values()
        fig = go.Figure(go.Bar(x=corr.values, y=corr.index, orientation="h",
                               marker_color=[COL["B"] if v < 0 else COL["C"] for v in corr.values]))
        st.plotly_chart(fig_layout(fig, 360, "Contribution au risque (corrélation de rang avec la VAN)"),
                        width="stretch")
    with g4:
        fig = go.Figure(go.Scatter(x=df["capex_overrun"] * 100, y=df["delay_months"], mode="markers",
                                   marker=dict(color=df["VAN projet"], colorscale="RdYlGn", cmid=0, size=6,
                                               colorbar=dict(title="VAN")), opacity=.7))
        fig.update_xaxes(title="Dépassement CAPEX (%)"); fig.update_yaxes(title="Retard (mois)")
        st.plotly_chart(fig_layout(fig, 360, "Nuage CAPEX × retard coloré par la VAN"), width="stretch")
    st.download_button("Télécharger les tirages (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       f"monte_carlo_{sc}.csv", "text/csv")

# ===========================================================================
# 6. Optimiseur
# ===========================================================================
elif page == PAGES[5]:
    st.title("Optimiseur de structure financière")
    st.caption("Recherche exhaustive sur grille : maximiser le TRI des fonds propres sous contraintes "
               "(apport ≤ capacité, dette ≤ plafond bancaire, DSCR ≥ 1,20x, levier ≤ 3,5x, trésorerie ≥ 0).")
    c = st.columns(4)
    case = c[0].selectbox("Cas", list(M.CASES))
    need = c[1].number_input("Ressources à lever (MDH)", 900, 1200, 980, 10)
    eq_cap = c[2].number_input("Capacité d'apport (MDH)", 200, 600, 350, 10)
    bank_cap = c[3].number_input("Plafond dette bancaire (MDH)", 300, 800, 540, 10)
    eq_grid = tuple(range(250, 501, 25))
    l_grid = tuple(range(0, 301, 30))
    with st.spinner("Évaluation de la grille…"):
        df = opt_cached(asdict(M.CASES[case]), asdict(MK), float(need), eq_grid, l_grid)
    df["Admissible"] = (df["Dette"] <= bank_cap) & (df["Fonds propres"] <= eq_cap) & \
                       (df["DSCR min"] >= 1.2) & (df["Levier max"] <= 3.5) & (df["Trésorerie min"] >= 0)
    feas = df[df.Admissible]
    if feas.empty:
        st.error("Aucune structure admissible : il faut des mesures correctrices ou des fonds propres supplémentaires.")
    else:
        best = feas.sort_values("TRI FP", ascending=False).iloc[0]
        robust = feas.sort_values("DSCR min", ascending=False).iloc[0]
        a, b = st.columns(2)
        a.markdown(f"<div class='verdict ok'>🎯 Rendement max : FP {best['Fonds propres']:.0f} · dette {best['Dette']:.0f} · "
                   f"crédit-bail {best['Crédit-bail']:.0f} MDH → TRI FP {pct(best['TRI FP'])}, DSCR {best['DSCR min']:.2f}x</div>",
                   unsafe_allow_html=True)
        b.markdown(f"<div class='verdict warn'>🛡️ Robustesse max : FP {robust['Fonds propres']:.0f} · dette {robust['Dette']:.0f} · "
                   f"crédit-bail {robust['Crédit-bail']:.0f} MDH → DSCR {robust['DSCR min']:.2f}x, TRI FP {pct(robust['TRI FP'])}</div>",
                   unsafe_allow_html=True)
    metric = st.radio("Carte", ["TRI FP", "DSCR min", "VAN projet", "Levier max"], horizontal=True)
    piv = df.pivot(index="Crédit-bail", columns="Fonds propres", values=metric)
    adm = df.pivot(index="Crédit-bail", columns="Fonds propres", values="Admissible")
    text = [[("✓ " if adm.iloc[i, j] else "") + (f"{piv.iloc[i, j]:.1%}" if metric == "TRI FP" else f"{piv.iloc[i, j]:.2f}")
             for j in range(piv.shape[1])] for i in range(piv.shape[0])]
    fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, colorscale="Viridis",
                               text=text, texttemplate="%{text}"))
    fig.update_xaxes(title="Fonds propres (MDH)"); fig.update_yaxes(title="Crédit-bail (MDH)")
    st.plotly_chart(fig_layout(fig, 520, f"{metric} (✓ = structure admissible ; dette = solde)"), width="stretch")
    fig = go.Figure()
    fig.add_scatter(x=df["DSCR min"], y=df["TRI FP"], mode="markers", name="Toutes",
                    marker=dict(color=np.where(df.Admissible, COL["C"], "#bbb"), size=9),
                    text=[f"FP {a:.0f} / D {b:.0f} / CB {c:.0f}" for a, b, c in zip(df["Fonds propres"], df["Dette"], df["Crédit-bail"])])
    fig.add_vline(x=1.2, line_dash="dash", line_color="red")
    fig.update_xaxes(title="DSCR minimum (risque)"); fig.update_yaxes(title="TRI des fonds propres (rendement)", tickformat=".0%")
    st.plotly_chart(fig_layout(fig, 420, "Frontière rendement / risque des structures"), width="stretch")

# ===========================================================================
# 7. Simulation en direct
# ===========================================================================
elif page == PAGES[6]:
    st.title("Simulation en direct")
    mode = st.radio("Mode", ["🎬 Film du projet 2027 → 2038", "🎲 Monte-Carlo en temps réel",
                             "🎯 Épreuve finale : choc tiré au sort"], horizontal=True)

    if mode.startswith("🎬"):
        c = st.columns(4)
        sc = c[0].selectbox("Scénario", list("ABC"), index=1, format_func=lambda k: M.SCENARIOS[k].name)
        case = c[1].selectbox("Cas", list(M.CASES), index=0)
        speed = c[2].slider("Vitesse (s / année)", 0.1, 1.5, 0.5, 0.1)
        go_btn = c[3].button("▶ Lancer", type="primary", width="stretch")
        tb = pd.DataFrame(run(M.SCENARIOS[sc], M.CASES[case], MK)["table"])
        kpi_ph = st.empty()
        chart_ph = st.empty()
        gauge_ph = st.empty()

        def frame(i):
            d = tb.iloc[: i + 1]
            row = tb.iloc[i]
            with kpi_ph.container():
                cc = st.columns(5)
                cc[0].metric("Année", int(row["Année"]))
                cc[1].metric("Chiffre d'affaires", mdh(row["Chiffre d'affaires"], 0))
                cc[2].metric("EBITDA", mdh(row["EBITDA économique"], 0))
                cc[3].metric("Trésorerie", mdh(row["Trésorerie (fin)"], 0))
                cc[4].metric("Dette + crédit-bail", mdh(row["Dette bancaire (fin)"] + row["Crédit-bail (encours)"], 0))
            fig = make_subplots(rows=1, cols=2, column_widths=[.65, .35],
                                specs=[[{"secondary_y": True}, {"type": "indicator"}]])
            fig.add_bar(x=d["Année"], y=d["Chiffre d'affaires"], name="CA", marker_color="#9fb7c9", row=1, col=1)
            fig.add_bar(x=d["Année"], y=d["EBITDA économique"], name="EBITDA", marker_color=COL[sc], row=1, col=1)
            fig.add_scatter(x=d["Année"], y=d["Trésorerie (fin)"], name="Trésorerie", line=dict(color="#e9a83a", width=4),
                            row=1, col=1, secondary_y=True)
            dv = row["DSCR"]
            fig.add_trace(go.Indicator(
                mode="gauge+number", value=0 if np.isnan(dv) else dv, number=dict(suffix="x", valueformat=".2f"),
                title=dict(text="DSCR de l'année"),
                gauge=dict(axis=dict(range=[0, 3]), bar=dict(color=COL[sc]),
                           steps=[dict(range=[0, 1.2], color="rgba(200,85,61,.35)"),
                                  dict(range=[1.2, 1.5], color="rgba(233,168,58,.35)"),
                                  dict(range=[1.5, 3], color="rgba(106,153,78,.3)")],
                           threshold=dict(line=dict(color="red", width=4), value=1.2))), row=1, col=2)
            fig.update_xaxes(range=[2026.5, 2038.5], row=1, col=1)
            fig.update_yaxes(range=[0, max(1700, tb["Chiffre d'affaires"].max() * 1.05)], row=1, col=1)
            fig.update_yaxes(range=[min(-150, tb["Trésorerie (fin)"].min() * 1.1), max(200, tb["Trésorerie (fin)"].max() * 1.1)],
                             row=1, col=1, secondary_y=True)
            fig.update_layout(barmode="overlay")
            chart_ph.plotly_chart(fig_layout(fig, 430), width="stretch", key=f"film{i}{time.time()}")
            ev = {2027: "🏗️ Début des travaux, premiers tirages", 2028: "🏭 Mise en service au 01/07 (retard éventuel)",
                  2029: "📈 Montée en cadence, réserve de trésorerie", 2030: "🏦 Début de l'amortissement de la dette, tests de covenants",
                  2032: "⚙️ Régime de croisière", 2036: "✅ Dernières échéances bancaires", 2038: "🏁 Fin de l'horizon, valeur terminale"}
            gauge_ph.info(ev.get(int(row["Année"]), "Exploitation courante"))

        if go_btn:
            for i in range(len(tb)):
                frame(i)
                time.sleep(speed)
        else:
            frame(len(tb) - 1)

    elif mode.startswith("🎲"):
        c = st.columns(4)
        sc = c[0].selectbox("Scénario", list("ABC"), index=1, format_func=lambda k: M.SCENARIOS[k].name)
        total = c[1].select_slider("Tirages", [300, 600, 1000, 2000], 600)
        batch = c[2].select_slider("Taille des lots", [10, 25, 50, 100], 25)
        start = c[3].button("▶ Démarrer", type="primary", width="stretch")
        vol = {"price": 0.02, "volume": 0.06, "materials": 0.03, "energy": 0.10, "rate": 0.005,
               "delay_mean": 2.0, "capex_tri": (-0.03, 0.0, 0.25)}
        stat_ph, chart_ph = st.empty(), st.empty()
        if start:
            draws = M.draw_mc(total, vol, seed=int(time.time()) % 10000)
            rows, conv = [], []
            for s0 in range(0, total, batch):
                rows += M.monte_carlo(M.SCENARIOS[sc], M.Shocks(), MK, draws, s0, s0 + batch)
                df = pd.DataFrame(rows)
                conv.append((len(df), df["VAN projet"].mean(), (df["DSCR min"] < 1.2).mean(), (df["VAN projet"] < 0).mean()))
                cv = pd.DataFrame(conv, columns=["n", "VAN moy", "P(DSCR<1,2)", "P(VAN<0)"])
                with stat_ph.container():
                    cc = st.columns(4)
                    cc[0].metric("Tirages", f"{len(df)}/{total}")
                    cc[1].metric("VAN moyenne", mdh(df["VAN projet"].mean()))
                    cc[2].metric("P(VAN < 0)", pct((df["VAN projet"] < 0).mean(), 1))
                    cc[3].metric("P(bris de covenant DSCR)", pct((df["DSCR min"] < 1.2).mean(), 1))
                fig = make_subplots(rows=1, cols=2, subplot_titles=("Distribution de la VAN", "Convergence des probabilités"))
                fig.add_histogram(x=df["VAN projet"], nbinsx=40, marker_color=COL[sc], row=1, col=1, name="VAN")
                fig.add_scatter(x=cv["n"], y=cv["P(VAN<0)"], name="P(VAN<0)", line=dict(color=COL["B"]), row=1, col=2)
                fig.add_scatter(x=cv["n"], y=cv["P(DSCR<1,2)"], name="P(DSCR<1,2)", line=dict(color=COL["X"]), row=1, col=2)
                fig.update_yaxes(tickformat=".0%", row=1, col=2)
                chart_ph.plotly_chart(fig_layout(fig, 420), width="stretch", key=f"mc{s0}")
                time.sleep(0.05)
            st.success("Simulation terminée.")
        else:
            st.info("Cliquez sur « Démarrer » : les tirages arrivent par lots et les graphiques se mettent à jour en direct.")

    else:
        st.caption("Comme à l'oral : un choc (dépassement du CAPEX et retard) est tiré au sort. L'application "
                   "donne le verdict de chaque montage, puis cherche automatiquement le paquet de mesures "
                   "correctrices le moins coûteux qui rétablit les covenants.")
        c = st.columns(3)
        if c[0].button("🎰 Tirer un choc au sort", type="primary", width="stretch"):
            ph = st.empty()
            rng = np.random.default_rng()
            for _ in range(14):
                ph.markdown(f"### 🎲 CAPEX **+{rng.choice([5,10,15,20,25,30])} %** · retard **{rng.choice([0,3,6,9,12])} mois**")
                time.sleep(0.08)
            ss.draw = (float(rng.choice([0.05, 0.10, 0.15, 0.20, 0.25, 0.30])), int(rng.choice([0, 3, 6, 9, 12])))
            ph.empty()
        manual = c[1].toggle("Saisir le choc manuellement")
        if manual:
            ss.draw = (c[2].slider("CAPEX", 0.0, 0.40, 0.20, 0.05), c[2].slider("Retard (mois)", 0, 18, 6))
        if "draw" in ss:
            cx, dl = ss.draw
            st.markdown(f"## Choc : CAPEX **+{cx:.0%}** · retard **{dl} mois**")
            sh = M.Shocks(capex_overrun=cx, delay_months=dl)
            cols = st.columns(3)
            for col, k in zip(cols, "ABC"):
                kp = run(M.SCENARIOS[k], sh, MK)["kpi"]
                why = []
                if kp["Besoin non financé"] > 0: why.append(f"besoin non financé {kp['Besoin non financé']:.0f} MDH")
                if kp["DSCR min"] < 1.2: why.append(f"DSCR {kp['DSCR min']:.2f}x < 1,20x")
                if kp["Levier max"] > 3.5: why.append(f"levier {kp['Levier max']:.2f}x > 3,5x")
                with col:
                    st.markdown(f"#### {M.SCENARIOS[k].name}")
                    st.metric("VAN", mdh(kp["VAN projet"]))
                    st.markdown(f"<div class='verdict {'ok' if not why else 'ko'}'>{'✅ Soutenable' if not why else '❌ ' + ' · '.join(why)}</div>",
                                unsafe_allow_html=True)
            st.subheader("Recherche automatique des mesures correctrices (scénario B)")
            best = None
            for eqx in (0, 30, 60, 90, 120):
                for sb in (0, 35, 70, 105):
                    for gr in (0, 2):
                        for dc in (0, 25):
                            s2 = replace(sh, extra_equity=eqx, standby_debt=sb, extra_grace=gr, deferred_capex=dc)
                            kp = run(M.SCENARIOS["B"], s2, MK)["kpi"]
                            if kp["Covenants OK"]:
                                cost = eqx * 1.6 + sb * 1.0 + gr * 8 + dc * 0.5  # coût relatif : FP plus chers que la dette
                                if best is None or cost < best[0]:
                                    best = (cost, eqx, sb, gr, dc, kp)
            if best:
                _, eqx, sb, gr, dc, kp = best
                cc = st.columns(4)
                cc[0].metric("Apport complémentaire", mdh(eqx, 0))
                cc[1].metric("Dette de réserve", mdh(sb, 0))
                cc[2].metric("Différé supplémentaire", f"{gr} sem.")
                cc[3].metric("Investissements reportés", mdh(dc, 0))
                st.markdown(f"<div class='verdict ok'>Avec ces mesures : DSCR min {kp['DSCR min']:.2f}x · trésorerie min "
                            f"{kp['Trésorerie min']:.0f} MDH · levier max {kp['Levier max']:.2f}x · VAN {kp['VAN projet']:.0f} MDH "
                            f"(les mesures préservent la solvabilité, pas forcément la création de valeur).</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown("<div class='verdict ko'>Aucun paquet de mesures testé ne suffit : revoir le projet "
                            "(phasage, renégociation du CAPEX) ou ouvrir le capital.</div>", unsafe_allow_html=True)

# ===========================================================================
# 8. Export Power BI
# ===========================================================================
elif page == PAGES[7]:
    st.title("Export vers Power BI")
    st.markdown("Le modèle produit un **schéma en étoile** prêt à être chargé dans Power BI Desktop "
                "(*Obtenir les données → Texte/CSV* ou *Classeur Excel*) : une table de faits annuelle au format long, "
                "une table de faits des indicateurs, et des dimensions Scénario / Cas / Indicateur.")
    facts, kpis = [], []
    for cname, sh in M.CASES.items():
        for k, f in M.SCENARIOS.items():
            r = run(f, sh, MK)
            t = pd.DataFrame(r["table"])
            long = t.melt(id_vars="Année", var_name="Indicateur", value_name="Valeur")
            long.insert(0, "Cas", cname); long.insert(0, "Scénario", k)
            facts.append(long)
            for kk, vv in r["kpi"].items():
                kpis.append({"Scénario": k, "Cas": cname, "Indicateur": kk, "Valeur": float(vv)})
    fact = pd.concat(facts, ignore_index=True)
    fk = pd.DataFrame(kpis)
    dim_s = pd.DataFrame([{"Scénario": k, **{kk: vv for kk, vv in asdict(f).items()}} for k, f in M.SCENARIOS.items()])
    dim_c = pd.DataFrame([{"Cas": c, **asdict(s)} for c, s in M.CASES.items()])
    dim_i = pd.DataFrame({"Indicateur": sorted(set(fact.Indicateur) | set(fk.Indicateur))})
    st.dataframe(fact.head(50), width="stretch")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nm, d in {"fait_annuel.csv": fact, "fait_kpi.csv": fk, "dim_scenario.csv": dim_s,
                      "dim_cas.csv": dim_c, "dim_indicateur.csv": dim_i}.items():
            z.writestr(nm, d.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"))
    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as w:
        fact.to_excel(w, sheet_name="fait_annuel", index=False); fk.to_excel(w, sheet_name="fait_kpi", index=False)
        dim_s.to_excel(w, sheet_name="dim_scenario", index=False); dim_c.to_excel(w, sheet_name="dim_cas", index=False)
        dim_i.to_excel(w, sheet_name="dim_indicateur", index=False)
    a, b = st.columns(2)
    a.download_button("⬇️ Pack CSV (Power BI)", buf.getvalue(), "tanger2_powerbi_csv.zip", "application/zip",
                      width="stretch", type="primary")
    b.download_button("⬇️ Classeur Excel (Power BI)", xbuf.getvalue(), "tanger2_powerbi.xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    st.subheader("Mesures DAX suggérées")
    st.code("""VAN projet = CALCULATE(SUM(fait_kpi[Valeur]), fait_kpi[Indicateur] = "VAN projet")
DSCR min = CALCULATE(SUM(fait_kpi[Valeur]), fait_kpi[Indicateur] = "DSCR min")
Respect covenant = IF([DSCR min] >= 1.2, "✅", "❌")
Trésorerie = CALCULATE(SUM(fait_annuel[Valeur]), fait_annuel[Indicateur] = "Trésorerie (fin)")
EBITDA = CALCULATE(SUM(fait_annuel[Valeur]), fait_annuel[Indicateur] = "EBITDA économique")""", language="dax")
    st.caption("Relations : fait_annuel[Scénario] → dim_scenario[Scénario] ; fait_annuel[Cas] → dim_cas[Cas] ; "
               "idem pour fait_kpi. Un segment (slicer) sur Scénario et Cas reproduit le sélecteur de cas de l'onglet 02. "
               "Variante « live » : Power BI → Obtenir les données → Script Python → exécuter powerbi/export_powerbi.py.")
