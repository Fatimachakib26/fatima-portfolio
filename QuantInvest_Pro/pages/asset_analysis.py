"""Page 5 — Analyse des actifs.

Étape 2 : prix historiques ajustés, comparaison base 100, qualité et origine
des données. Statistiques descriptives et CAPM : étapes 3 et 6.
"""
import pandas as pd
import streamlit as st

from components.charts import PLOTLY_CONFIG, base100_chart, price_chart
from components.data_service import MarketBundle, render_data_alerts
from components.kpi_cards import banner, card_title, empty_state
from components.navbar import render_navbar
from config import ASSET_UNIVERSE

bundle: MarketBundle = st.session_state["market"]
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
    right.caption(f"{s.index[0]:%d/%m/%Y} → {s.index[-1]:%d/%m/%Y} · {len(s):,} observations · "
                  f"devise {bundle.raw.currencies.get(t) or 'inconnue'}")
    with st.container(border=True):
        card_title(f"Prix historique ajusté — {t}", "Clôture ajustée des dividendes et des splits")
        st.plotly_chart(price_chart(s, bundle.raw.currencies.get(t), height=380),
                        use_container_width=True, config=PLOTLY_CONFIG)
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        card_title("Rendements & statistiques descriptives")
        empty_state("Étape 3", "Rendements, moyenne, volatilité, skewness, kurtosis, normalité.", "🧮")
    with c2, st.container(border=True):
        card_title("CAPM — bêta vs benchmark")
        empty_state("Étape 6", "Régression des rendements de l'actif sur ceux du marché.", "📐")

with tab_compare:
    chosen = st.multiselect("Actions à comparer", bundle.assets, default=bundle.assets[:4])
    show_bench = st.toggle("Afficher le benchmark", value=bundle.benchmark is not None,
                           disabled=bundle.benchmark is None)
    with st.container(border=True):
        card_title("Performance comparée (base 100)", "Valeur de 100 investis au début de la période")
        if chosen:
            st.plotly_chart(base100_chart(bundle.prices[chosen], bundle.benchmark_prices if show_bench else None,
                                          height=420), use_container_width=True, config=PLOTLY_CONFIG)
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
        st.dataframe(origin, use_container_width=True)
    with st.container(border=True):
        card_title("Rapport de qualité", "Avant synchronisation sur l'historique commun")
        q = bundle.clean.quality.copy()
        for col in ("Première date", "Dernière date"):
            q[col] = pd.to_datetime(q[col]).dt.strftime("%d/%m/%Y")
        st.dataframe(q, use_container_width=True,
                     column_config={"% manquantes": st.column_config.NumberColumn(format="percent")})
    banner("Règles de nettoyage : prix ≤ 0 supprimés ; report de la dernière valeur limité à 3 séances "
           "(jours fériés) ; actif exclu au-delà de 10 % de valeurs manquantes ; seules les dates communes "
           "à tous les actifs sont conservées. Aucun report vers l'arrière : pas d'information future.",
           "info", "🧹")
