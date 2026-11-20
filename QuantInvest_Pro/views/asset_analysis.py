"""Page — Actifs : fiche détaillée de chaque action."""
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import (PLOTLY_CONFIG, asset_colors, base100_chart, base_figure, capm_chart, distribution_chart,
                               drawdown_chart, grouped_bars)
from components.data_service import MarketBundle, render_data_alerts, source_text
from components.explain import explain, section
from components.formatting import num, pct
from components.kpi_cards import banner, card_title, empty_state
from components.metric import metric_row
from components.navbar import render_navbar
from components.state import get_market, get_params
from components.workspace import get_library
from config import ASSET_UNIVERSE
from core.analysis import cumulative_attribution
from core.capm import capm, descriptive_stats
from core.fundamentals import FIELDS, get_profile, sector_fr
from core.indicators import calculer_indicateurs
from core.portfolio import buy_and_hold_returns, risk_contributions
from core.returns import simple_returns

bundle: MarketBundle = get_market()
params = get_params()
render_navbar("Actifs", "Fiche détaillée de chaque action")
render_data_alerts(bundle)
if not bundle.ok:
    empty_state("Aucune donnée exploitable", "Cliquez sur Actualiser ou modifiez la sélection d'actifs.", "📡")
    st.stop()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def profile(t: str) -> dict:
    return get_profile(t)


assets = bundle.assets
focus = st.session_state.get("focus_asset", assets[0])
t = st.selectbox("Action étudiée", assets, index=assets.index(focus) if focus in assets else 0,
                 format_func=lambda x: f"{x} · {ASSET_UNIVERSE.get(x, x)}", key="asset_choice")
st.session_state["focus_asset"] = t
daily = simple_returns(bundle.clean.prices)
r_all = daily[t]
bench = daily[bundle.benchmark] if bundle.benchmark else None
prices = bundle.clean.prices[t]
SRC = source_text(bundle)
rf = params.risk_free_rate
cur = bundle.raw.currencies.get(t) or "devise inconnue"

tabs = st.tabs(["🏢 Profil", "📈 Prix et performance", "🛡️ Risque", "📑 Données fondamentales",
                "🧩 Rôle dans les portefeuilles", "🆚 Comparaison", "🧾 Qualité des données"])


def nd(v, fmt=lambda x: x):
    return "non disponible" if v is None or (isinstance(v, float) and np.isnan(v)) else fmt(v)


# ------------------------------------------------------------------ Profil
with tabs[0]:
    with st.spinner("Lecture du profil Yahoo Finance…"):
        prof = profile(t)
    c1, c2 = st.columns([1, 1.6], gap="medium")
    with c1, st.container(border=True):
        card_title(nd(prof.get("longName")) if prof.get("longName") else t, t)
        rows = {"Secteur": sector_fr(prof.get("sector")), "Industrie": nd(prof.get("industry")),
                "Pays": nd(prof.get("country")),
                "Capitalisation": nd(prof.get("marketCap"), lambda v: f"{num(v / 1e9, 0)} milliards {prof.get('currency') or ''}"),
                "Devise de cotation": nd(prof.get("currency")) if prof.get("currency") else cur,
                "Effectif": nd(prof.get("fullTimeEmployees"), lambda v: num(v, 0))}
        st.dataframe(pd.Series(rows, name="Valeur").to_frame(), width="stretch")
        st.caption(f"Source : {prof.get('_source')}")
    with c2, st.container(border=True):
        card_title("Activité")
        desc = prof.get("longBusinessSummary")
        st.markdown((desc[:900] + ("…" if len(desc) > 900 else "")) if desc else "Description non disponible.")
        st.caption("Description fournie par Yahoo Finance, en anglais.")

# ------------------------------------------------------------------ Prix et performance
with tabs[1]:
    c1, c2, c3 = st.columns([3, 1.2, 1.2])
    per = c1.segmented_control("Période", ["1 mois", "6 mois", "1 an", "3 ans", "Depuis le début", "Personnalisée"],
                               default="1 an", required=True, key="asset_per")
    log_y = c2.toggle("Échelle logarithmique", key="asset_log")
    as_price = c3.toggle("Prix (sinon base 100)", key="asset_price")
    end = prices.index[-1]
    starts = {"1 mois": end - timedelta(days=31), "6 mois": end - timedelta(days=183), "1 an": end - timedelta(days=365),
              "3 ans": end - timedelta(days=3 * 365), "Depuis le début": prices.index[0]}
    if per == "Personnalisée":
        rng = st.date_input("Dates", (prices.index[0].date(), end.date()), format="DD/MM/YYYY", key="asset_rng")
        s0, s1 = (pd.Timestamp(rng[0]), pd.Timestamp(rng[1])) if len(rng) == 2 else (prices.index[0], end)
    else:
        s0, s1 = starts[per], end
    seg = prices.loc[s0:s1]
    with st.container(border=True):
        if as_price:
            card_title(f"Prix ajusté de {t} et moyennes mobiles", f"{seg.index[0]:%d/%m/%Y} – {seg.index[-1]:%d/%m/%Y} · {cur}")
            fig = base_figure("", 400)
            fig.add_trace(go.Scatter(x=seg.index, y=seg, name=t, line=dict(color="#A855F7", width=2)))
            for w_, col in ((50, "#22D3EE"), (200, "#F59E0B")):
                ma = prices.rolling(w_).mean().loc[s0:s1]  # moyenne des w_ séances précédentes (aucune donnée future)
                fig.add_trace(go.Scatter(x=ma.index, y=ma, name=f"Moyenne mobile {w_} séances", line=dict(color=col, width=1.4, dash="dot")))
            fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.12, yanchor="top", xanchor="left", x=0))
            if log_y:
                fig.update_yaxes(type="log")
        else:
            card_title(f"{t} contre {bundle.benchmark or 'l’indice'} (base 100)", f"{seg.index[0]:%d/%m/%Y} – {seg.index[-1]:%d/%m/%Y}")
            b = bundle.clean.prices[bundle.benchmark].loc[s0:s1] if bundle.benchmark else None
            fig = base100_chart(seg.to_frame(t), b, 400, log_y=log_y)
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
        perf = float(seg.iloc[-1] / seg.iloc[0] - 1)
        bperf = float(b.iloc[-1] / b.iloc[0] - 1) if (not as_price and b is not None) else None
        explain("Prix ajusté : dividendes et divisions d'actions intégrés. Les moyennes mobiles lissent le prix sur 50 et "
                "200 séances (lecture de tendance, sans valeur prédictive démontrée).",
                f"Sur la période : {t} {pct(perf, 1, signed=True)}" + (f" contre {pct(bperf, 1, signed=True)} pour "
                f"{bundle.benchmark}." if bperf is not None else "."))
    yearly = (1 + r_all).groupby(r_all.index.year).prod() - 1
    with st.container(border=True):
        card_title("Rendements annuels", "Années civiles (l'année en cours est partielle)")
        fig = base_figure("", 280)
        fig.add_trace(go.Bar(x=[str(y) for y in yearly.index], y=yearly.values,
                             marker_color=["#22C55E" if v >= 0 else "#F43F5E" for v in yearly.values],
                             text=[pct(v, 0) for v in yearly.values], textposition="outside",
                             hovertemplate="%{x} : %{y:.1%}<extra></extra>"))
        fig.update_traces(cliponaxis=False)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

# ------------------------------------------------------------------ Risque
with tabs[2]:
    ind = calculer_indicateurs(r_all, bench, rf, 252, source=SRC, sujet=t, nom_benchmark=bundle.benchmark or "SPY")
    metric_row([dict(res=ind.get("volatilite"), key="a_vol", icon="🌊"), dict(res=ind.get("var95_hist"), key="a_var", icon="⚠️"),
                dict(res=ind.get("cvar95"), key="a_cvar", icon="🧨"), dict(res=ind.get("beta"), key="a_beta", icon="🔗")])
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        card_title("Volatilité glissante (63 séances) et bêta glissant (126 séances)")
        vol = r_all.rolling(63).std() * np.sqrt(252)
        fig = base_figure("", 300)
        fig.add_trace(go.Scatter(x=vol.index, y=vol, name="Volatilité annualisée", line=dict(color="#A855F7")))
        if bench is not None:
            beta = r_all.rolling(126).cov(bench) / bench.rolling(126).var()
            fig.add_trace(go.Scatter(x=beta.index, y=beta, name="Bêta (axe de droite)", yaxis="y2", line=dict(color="#22D3EE")))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Bêta"))
        fig.update_yaxes(tickformat=".0%", selector=dict(anchor="x"))
        fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.15, yanchor="top", xanchor="left", x=0))
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    with c2, st.container(border=True):
        card_title("Drawdown")
        st.plotly_chart(drawdown_chart(r_all.to_frame(t), 300), width="stretch", config=PLOTLY_CONFIG)
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        card_title("Distribution des rendements contre loi normale")
        st.plotly_chart(distribution_chart(r_all, ind["var95_hist"].valeur, ind["var95_param"].valeur, 320), width="stretch",
                        config=PLOTLY_CONFIG)
    with c2, st.container(border=True):
        if bench is not None:
            cp = capm(r_all, bench, rf)
            card_title(f"CAPM — {t} contre {bundle.benchmark}")
            st.plotly_chart(capm_chart(cp, t, bundle.benchmark, 320), width="stretch", config=PLOTLY_CONFIG)
    explain("La volatilité et le bêta varient dans le temps : une estimation unique (celle de Markowitz) les fige.",
            f"Volatilité glissante entre {pct(vol.min(), 0)} et {pct(vol.max(), 0)} ; excès de kurtosis "
            f"{num(ind['kurtosis'].valeur)} : les pertes extrêmes sont {'plus fréquentes' if ind['kurtosis'].valeur > 1 else 'proches de ce'} "
            "que prévoit la loi normale.")

# ------------------------------------------------------------------ Données fondamentales
with tabs[3]:
    prof = profile(t)
    q = prof.get("mostRecentQuarter")
    qd = pd.Timestamp(q, unit="s").strftime("%d/%m/%Y") if isinstance(q, (int, float)) and q else "non disponible"
    dy = prof.get("dividendYield")
    rows = {"PER (12 derniers mois)": nd(prof.get("trailingPE"), lambda v: num(v, 1)),
            "PER prévisionnel": nd(prof.get("forwardPE"), lambda v: num(v, 1)),
            "Rendement du dividende": nd(dy, lambda v: pct(v / 100 if v > 0.2 else v, 2)),
            "Marge nette": nd(prof.get("profitMargins"), lambda v: pct(v, 1)),
            "Croissance du chiffre d'affaires (sur un an)": nd(prof.get("revenueGrowth"), lambda v: pct(v, 1)),
            "Rentabilité des capitaux propres": nd(prof.get("returnOnEquity"), lambda v: pct(v, 1)),
            "Dernier trimestre publié": qd}
    with st.container(border=True):
        card_title(f"Données fondamentales — {t}", f"Source : {prof.get('_source')} · lu le {(prof.get('_date') or '')[:10]}")
        st.dataframe(pd.Series(rows, name="Valeur").to_frame(), width="stretch")
        explain("Ces données comptables ne sont pas utilisées par l'optimisation de Markowitz, qui ne regarde que les "
                "rendements passés. Elles aident à comprendre pourquoi un actif est volatil ou cher.",
                "Les champs « non disponible » ne sont pas fournis par Yahoo Finance pour cette action ; les valeurs "
                "sont celles du jour de lecture et ne sont pas historisées.")

# ------------------------------------------------------------------ Rôle dans les portefeuilles
with tabs[4]:
    library = get_library(params, bundle)
    test_r = daily[assets].loc[daily.index > pd.Timestamp(params.split_date)]
    cov = daily[assets].loc[:pd.Timestamp(params.split_date)].cov() * 252
    rows = []
    for n, e in library.items():
        if e.type == "reference" or t not in e.poids:
            continue
        w = e.weights.reindex(assets).fillna(0)
        contrib = cumulative_attribution(test_r, w).iloc[-1]
        total = float((1 + buy_and_hold_returns(test_r, w)).prod() - 1)
        rows.append({"Portefeuille": n, "Poids": w[t], "Contribution au rendement (test)": contrib[t],
                     "Part du rendement": contrib[t] / total if total else np.nan,
                     "Part du risque (estimation)": risk_contributions(w, cov).loc[t, "Part du risque"]})
    role = pd.DataFrame(rows).set_index("Portefeuille")
    with st.container(border=True):
        card_title(f"Rôle de {t} dans chaque portefeuille de la bibliothèque",
                   "Poids estimés jusqu'à la date de séparation · contribution mesurée sur la période de test")
        st.dataframe(role.map(lambda v: pct(v, 1)), width="stretch")
        corr = daily[assets].corr()[t].drop(t).sort_values()
        st.plotly_chart(grouped_bars(corr.to_frame("Corrélation avec " + t), 260, pct_axis=False, colors=["#A855F7"]),
                        width="stretch", config=PLOTLY_CONFIG)
        if len(role):
            heavy = role["Poids"].idxmax()
            explain("Part du rendement : fraction du gain total du portefeuille due à cet actif. Part du risque : "
                    "fraction de la volatilité du portefeuille due à cet actif (décomposition d'Euler).",
                    f"{t} pèse le plus dans <b>{heavy}</b> ({pct(role.loc[heavy, 'Poids'], 0)} du capital, "
                    f"{pct(role.loc[heavy, 'Part du risque (estimation)'], 0)} du risque). Actif le moins corrélé à {t} : "
                    f"<b>{corr.index[0]}</b> ({num(corr.iloc[0])}).")

# ------------------------------------------------------------------ Comparaison
with tabs[5]:
    chosen = st.multiselect("Actions à comparer", assets, default=assets[:4], key="asset_cmp")
    show_bench = st.toggle("Afficher l'indice de référence", value=bundle.benchmark is not None,
                           disabled=bundle.benchmark is None, key="asset_cmp_b")
    with st.container(border=True):
        card_title("Performance comparée (base 100)", "Valeur de 100 investis au début de l'historique commun")
        if chosen:
            st.plotly_chart(base100_chart(bundle.prices[chosen], bundle.benchmark_prices if show_bench else None, 420, log_y=True),
                            width="stretch", config=PLOTLY_CONFIG)
        ds = descriptive_stats(daily[chosen or assets])
        st.dataframe(pd.DataFrame({"Rendement annualisé": ds.iloc[:, 0].map(pct), "Volatilité": ds.iloc[:, 1].map(pct),
                                   "Pire séance": ds["Pire séance"].map(pct), "Excès de kurtosis": ds["Excès de kurtosis"].map(num)}),
                     width="stretch")

# ------------------------------------------------------------------ Qualité des données
with tabs[6]:
    raw = bundle.raw
    q = bundle.clean.quality.loc[[t]] if t in bundle.clean.quality.index else None
    z = (r_all - r_all.mean()) / r_all.std()
    extremes = r_all[z.abs() > 5]
    with st.container(border=True):
        card_title(f"Qualité des données — {t}", f"Source : {raw.source.get(t, '?')} · devise {cur}")
        if q is not None:
            qq = q.copy()
            for c in ("Première date", "Dernière date"):
                qq[c] = pd.to_datetime(qq[c]).dt.strftime("%d/%m/%Y")
            st.dataframe(qq, width="stretch",
                         column_config={"% manquantes": st.column_config.NumberColumn(format="percent")})
        st.markdown(f"**Rendements extrêmes (au-delà de 5 écarts-types)** : {len(extremes)} séance(s)")
        if len(extremes):
            st.dataframe(pd.DataFrame({"Date": extremes.index.strftime("%d/%m/%Y"), "Rendement": extremes.map(lambda v: pct(v, 2)),
                                       "Écarts-types": z[extremes.index].map(lambda v: num(v, 1))}), hide_index=True, width="stretch")
        explain("Un rendement au-delà de 5 écarts-types n'arrive presque jamais avec une loi normale (une fois tous les "
                "millions d'années). Ici, ce sont de vrais événements (résultats trimestriels, krach), pas des erreurs : "
                "ils sont conservés.",
                f"{len(extremes)} séance(s) extrême(s) sur {num(len(r_all), 0)} pour {t}.")
    banner("Règles de nettoyage : prix ≤ 0 supprimés ; report de la dernière valeur limité à 3 séances (jours fériés) ; "
           "actif exclu au-delà de 10 % de valeurs manquantes ; seules les dates communes à tous les actifs sont "
           "conservées. Aucun report vers l'arrière : pas d'information future.", "info", "🧹")
