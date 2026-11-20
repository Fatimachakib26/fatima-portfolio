"""Page 5 — Analyse des actifs.

Prix ajustés, statistiques descriptives, CAPM (bêta, alpha), comparaison
base 100, qualité et origine des données.
"""
import pandas as pd
import streamlit as st

from components.state import get_market, get_params

from components.charts import PLOTLY_CONFIG, base100_chart, capm_chart, price_chart
from components.explain import explain
from components.formatting import num, pct
from core.capm import capm, descriptive_stats
from core.returns import simple_returns
from components.data_service import MarketBundle, render_data_alerts
from components.kpi_cards import banner, card_title, empty_state
from components.navbar import render_navbar
from config import ASSET_UNIVERSE

bundle: MarketBundle = get_market()
params = get_params()
render_navbar("Analyse des actifs", "Étude individuelle et comparaison des actions")
render_data_alerts(bundle)

if not bundle.ok:
    empty_state("Aucune donnée exploitable", "Cliquez sur Actualiser ou modifiez la sélection d'actifs.", "📡")
    st.stop()

tab_asset, tab_compare, tab_data = st.tabs(["📈 Actif", "🆚 Comparaison", "🧾 Qualité des données"])

with tab_asset:
    left, right = st.columns([1, 3], vertical_alignment="bottom")
    t = left.selectbox("Actif", bundle.assets, format_func=lambda x: f"{x} · {ASSET_UNIVERSE.get(x, x)}")
    s = bundle.prices[t]
    right.caption(f"{s.index[0]:%d/%m/%Y} → {s.index[-1]:%d/%m/%Y} · {num(len(s), 0)} observations · "
                  f"devise {bundle.raw.currencies.get(t) or 'inconnue'}")
    with st.container(border=True):
        card_title(f"Prix historique ajusté — {t}", "Clôture ajustée des dividendes et des splits")
        st.plotly_chart(price_chart(s, bundle.raw.currencies.get(t), height=380),
                        width="stretch", config=PLOTLY_CONFIG)
    daily = simple_returns(bundle.daily_prices)
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        card_title("Statistiques descriptives", "Rendements quotidiens, tout l'historique commun")
        ds = descriptive_stats(daily)
        show = pd.DataFrame({
            "Rendement annualisé": ds.iloc[:, 0].map(pct), "Volatilité": ds.iloc[:, 1].map(pct),
            "Pire séance": ds["Pire séance"].map(pct), "Meilleure séance": ds["Meilleure séance"].map(pct),
            "Asymétrie": ds["Asymétrie"].map(num), "Excès de kurtosis": ds["Excès de kurtosis"].map(num),
        })
        st.dataframe(show, width="stretch")
        explain("Excès de kurtosis : 0 pour une loi normale ; au-delà, les variations extrêmes sont plus "
                "fréquentes. Asymétrie négative : les fortes baisses dominent les fortes hausses.",
                f"<b>{t}</b> : pire séance {pct(ds.loc[t, 'Pire séance'])}, kurtosis en excès "
                f"{num(ds.loc[t, 'Excès de kurtosis'])} → normalité "
                f"{'rejetée' if ds.loc[t, 'p Jarque-Bera'] < 0.05 else 'non rejetée'} (Jarque-Bera).")
    with c2, st.container(border=True):
        if bundle.benchmark:
            card_title(f"CAPM — {t} contre {bundle.benchmark}", "Excès de rendement de l'actif vs excès du marché")
            mkt = simple_returns(bundle.clean.prices[bundle.benchmark])
            cp = capm(daily[t], mkt, params.risk_free_rate)
            st.plotly_chart(capm_chart(cp, t, bundle.benchmark, 300), width="stretch", config=PLOTLY_CONFIG)
            explain("Chaque point est une séance. La pente de la droite est le bêta : la sensibilité de l'actif "
                    "au marché (1 = autant que le marché).",
                    f"β = <b>{num(cp['beta'])}</b> : quand le marché varie de 1 %, {t} varie en moyenne de "
                    f"{num(cp['beta'])} %. Alpha annualisé {pct(cp['alpha_annuel'])} "
                    f"(p = {num(cp['p_alpha'], 4)} : {'significatif' if cp['p_alpha'] < 0.05 else 'non significatif'}), "
                    f"R² = {num(cp['r2'])}.")
        else:
            empty_state("Indice de référence indisponible", "Le CAPM nécessite le S&P 500.", "📐")

with tab_compare:
    chosen = st.multiselect("Actions à comparer", bundle.assets, default=bundle.assets[:4])
    show_bench = st.toggle("Afficher l'indice de référence", value=bundle.benchmark is not None,
                           disabled=bundle.benchmark is None)
    with st.container(border=True):
        card_title("Performance comparée (base 100)", "Valeur de 100 investis au début de la période")
        if chosen:
            st.plotly_chart(base100_chart(bundle.prices[chosen], bundle.benchmark_prices if show_bench else None,
                                          height=420), width="stretch", config=PLOTLY_CONFIG)
        else:
            empty_state("Sélectionnez au moins un actif")

with tab_data:
    raw = bundle.raw
    src_label = {"live": "🟢 Yahoo Finance (direct)", "cache": "🟡 Cache local", "missing": "🔴 Indisponible"}
    origin = pd.DataFrame({
        "Source": {t: src_label[s] for t, s in raw.source.items()},
        "Devise": {t: raw.currencies.get(t) or "—" for t in raw.source},
        "Récupéré le": {t: raw.fetched_at[t].strftime("%d/%m/%Y %H:%M") if t in raw.fetched_at else "—"
                        for t in raw.source},
    })
    with st.container(border=True):
        card_title("Origine des données", "Traçabilité de chaque série utilisée")
        st.dataframe(origin, width="stretch")
    with st.container(border=True):
        card_title("Rapport de qualité", "Avant synchronisation sur l'historique commun")
        q = bundle.clean.quality.copy()
        for col in ("Première date", "Dernière date"):
            q[col] = pd.to_datetime(q[col]).dt.strftime("%d/%m/%Y")
        st.dataframe(q, width="stretch",
                     column_config={"% manquantes": st.column_config.NumberColumn(format="percent")})
    banner("Règles de nettoyage : prix ≤ 0 supprimés ; report de la dernière valeur limité à 3 séances "
           "(jours fériés) ; actif exclu au-delà de 10 % de valeurs manquantes ; seules les dates communes "
           "à tous les actifs sont conservées. Aucun report vers l'arrière : pas d'information future.",
           "info", "🧹")
