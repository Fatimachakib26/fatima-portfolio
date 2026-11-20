"""Page — Portefeuilles : fiche détaillée et gestion de la bibliothèque."""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import compute
from components.charts import PLOTLY_CONFIG, base_figure, donut_chart, grouped_bars, wealth_chart, drawdown_chart
from components.data_service import MarketBundle, render_data_alerts, source_text
from components.explain import explain, section
from components.formatting import num, pct
from components.kpi_cards import banner, empty_state
from components.metric import afficher_metrique, metric_row
from components.navbar import render_navbar
from components.state import get_market, get_params
from components.workspace import get_library, period_returns, portfolio_returns, selection_bar
from config import CRISES, AppParams
from core import library as lib
from core.analysis import cumulative_attribution, marginal_contributions, monthly_table, weight_sensitivity
from core.backtest import crisis_performance
from core.indicators import calculer_indicateurs, sharpe_annonce
from core.optimization import EQUAL, target_portfolio
from core.portfolio import buy_and_hold_returns, risk_contributions
from core.returns import estimate, simple_returns

params: AppParams = get_params()
bundle: MarketBundle = get_market()
render_navbar("Portefeuilles", "Fiche détaillée de chaque portefeuille et bibliothèque")
render_data_alerts(bundle)
if not bundle.ok:
    empty_state("Aucune donnée exploitable", "Cliquez sur Actualiser ou modifiez la sélection d'actifs.", "📡")
    st.stop()

library = get_library(params, bundle)
sel = selection_bar(library, bundle, params)
names = list(library)
focus = st.session_state.get("focus_portfolio", sel.portfolios[0] if sel.portfolios else names[0])
name = st.selectbox("Portefeuille étudié", names, index=names.index(focus) if focus in names else 0, key="pf_choice")
st.session_state["focus_portfolio"] = name
entry = library[name]
SRC = source_text(bundle)
rf = params.risk_free_rate

assets_r, bench_r, ppy = period_returns(sel, bundle)
if len(assets_r) < 3:
    banner("Période trop courte pour l'analyse.", "warn", "⏳")
    st.stop()
pr = portfolio_returns([name, EQUAL], library, assets_r, bench_r)
r = pr.get(name)
if r is None:
    st.stop()
w = entry.weights
is_ref = entry.type == "reference"
ind = calculer_indicateurs(r, bench_r if not is_ref else None, rf, ppy, poids=None if is_ref else w, source=SRC,
                           sujet=name, nom_benchmark=bundle.benchmark or "SPY")

html_badge = f'<span class="qi-chip" style="border-color:{entry.couleur};color:{entry.couleur}">● {lib.TYPES.get(entry.type, entry.type)}</span>'
st.markdown(f"{html_badge} <span style='color:var(--muted);font-size:.85rem'>{entry.description} · créé le "
            f"{entry.date_creation[:10]}</span>", unsafe_allow_html=True)

tabs = st.tabs(["🧩 Composition", "❓ Pourquoi ces poids ?", "📈 Performance", "🧾 Attribution", "🛡️ Risque",
                "🎭 Promesse contre réalité", "🗂️ Gérer la bibliothèque"])

# ------------------------------------------------------------------ Composition
with tabs[0]:
    if is_ref:
        st.info(f"{name} est l'indice de référence : 100 % dans l'ETF {name}.")
    else:
        c1, c2 = st.columns([1.3, 1], gap="medium")
        with c1, st.container(border=True):
            section("Poids par actif", f"Plafond actuel : {pct(params.weight_max, 0)}")
            st.plotly_chart(grouped_bars(w.to_frame("Poids"), 320, colors=[entry.couleur], y_title="Poids",
                                         hline=params.weight_max, hline_label="plafond"), width="stretch",
                            config=PLOTLY_CONFIG)
        with c2, st.container(border=True):
            section("Répartition du capital")
            st.plotly_chart(donut_chart(w, 300), width="stretch", config=PLOTLY_CONFIG)
        cap = entry.parametres.get("poids_max", params.weight_max)
        at_cap = [a for a, v in w.items() if v >= cap - 1e-4]
        at_zero = [a for a, v in w.items() if v < 0.005]
        metric_row([dict(res=ind.get("nombre_effectif"), key="pf_neff", icon="🧩", foot=f"{int((w > 0.005).sum())} actifs détenus")])
        explain("Les barres et l'anneau montrent la part du capital de chaque actif.",
                f"Actifs au plafond : <b>{', '.join(at_cap) or 'aucun'}</b> ; actifs exclus (0 %) : "
                f"<b>{', '.join(at_zero) or 'aucun'}</b>.")

# ------------------------------------------------------------------ Pourquoi ces poids ?
with tabs[1]:
    if entry.type != "automatique" or not entry.parametres.get("periode_estimation"):
        st.info("Ce portefeuille n'est pas issu d'une optimisation automatique : ses poids ont été saisis ou "
                "proviennent d'un autre portefeuille. Ses paramètres d'origine sont listés ci-dessous.")
        st.json(entry.parametres)
    else:
        P = entry.parametres
        d0, d1 = pd.Timestamp(P["periode_estimation"][0]), pd.Timestamp(P["periode_estimation"][1])
        r_est = simple_returns(bundle.daily_prices).loc[d0:d1]          # [no look-ahead] période d'estimation
        est = estimate(r_est, 252, P["estimateur"])
        st.markdown(f"**Paramètres utilisés** : estimation du {d0:%d/%m/%Y} au {d1:%d/%m/%Y} ({num(P['observations'], 0)} "
                    f"séances) · covariance {'empirique' if P['estimateur'] == 'sample' else 'de Ledoit-Wolf'} · "
                    f"taux sans risque {pct(P['taux_sans_risque'])} · poids entre {pct(P['poids_min'], 0)} et "
                    f"{pct(P['poids_max'], 0)}")
        mc = marginal_contributions(w, est.mu, est.cov, P["taux_sans_risque"])
        mc.insert(2, "Volatilité annualisée", est.vol[w.index])
        status = ["au plafond" if v >= P["poids_max"] - 1e-4 else ("à 0 %" if v < 1e-4 else "libre") for v in w]
        mc.insert(1, "Contrainte", status)
        with st.container(border=True):
            section("Entrées de l'optimisation et contraintes actives")
            show = mc.copy()
            for c in ("Poids", "μ annualisé", "Volatilité annualisée"):
                show[c] = show[c].map(lambda v: pct(v, 1))
            for c in ("∂σ/∂w (risque marginal)", "∂Sharpe/∂w"):
                show[c] = show[c].map(lambda v: num(v, 3))
            st.dataframe(show, width="stretch")
            explain("μ et la volatilité sont estimés sur la période d'estimation uniquement. « Au plafond » ou « à 0 % » : "
                    "la contrainte décide du poids, pas l'optimiseur. Pour le Sharpe maximal, ∂Sharpe/∂w est égal pour "
                    "tous les actifs libres à l'optimum : c'est la condition d'optimalité.",
                    f"Meilleur μ : <b>{est.mu.idxmax()}</b> ({pct(est.mu.max(), 1)}) ; plus faible volatilité : "
                    f"<b>{est.vol.idxmin()}</b> ({pct(est.vol.min(), 1)}).")
        if P.get("objectif") == "optimisation":
            objective = "max_sharpe" if "Sharpe" in name else "min_variance"
            with st.container(border=True):
                section("Sensibilité des poids aux rendements espérés",
                        "Variation des poids optimaux si le μ d'UN actif change de ±1 point (tout le reste identique)")
                mode = st.radio("Contraintes", [f"Celles du portefeuille (plafond {pct(P['poids_max'], 0)})",
                                                "Sans plafond (0 à 100 %)"], horizontal=True, key="sens_mode")
                cap_s = P["poids_max"] if mode.startswith("Celles") else 1.0
                with st.spinner("12 optimisations…"):
                    sens = weight_sensitivity(est.mu, est.cov, P["taux_sans_risque"], P["poids_min"], cap_s, objective)
                sens = sens.where(sens.abs() > 1e-5, 0.0)   # supprime le bruit numérique
                zmax = max(float(sens.abs().max().max()) * 100, 1.0)
                fig = go.Figure(go.Heatmap(z=sens.values * 100, x=sens.columns, y=sens.index, zmid=0, zmin=-zmax, zmax=zmax,
                                           colorscale=[[0, "#F43F5E"], [0.5, "#161743"], [1, "#22D3EE"]],
                                           text=[[f"{v:+.1f}".replace(".", ",") for v in row] for row in sens.values * 100],
                                           texttemplate="%{text}", hovertemplate="%{y}<br>%{x} : %{z:+.1f} points<extra></extra>",
                                           colorbar=dict(title="points", thickness=10)))
                fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
                biggest = sens.abs().max(axis=1).idxmax()
                if sens.abs().max().max() < 1e-3:
                    banner("Aucun poids ne bouge : les contraintes figent la solution (actifs au plafond ou à 0 %). "
                           "Le plafond protège ici contre la sensibilité de Markowitz — choisissez « Sans plafond » "
                           "pour voir l'effet brut.", "info", "🔒")
                explain("Chaque ligne : on modifie le rendement espéré d'un seul actif de ±1 point et on réoptimise. "
                        "Chaque case : variation du poids de l'actif en colonne, en points de pourcentage.",
                        f"Le choc le plus déstabilisant est <b>{biggest}</b> : jusqu'à "
                        f"{num(sens.abs().max(axis=1).max() * 100, 1)} points de poids déplacés pour 1 point de "
                        "rendement espéré — alors que μ est estimé avec une erreur de plusieurs points. C'est la "
                        "principale fragilité de Markowitz.")

# ------------------------------------------------------------------ Performance
with tabs[2]:
    metric_row([
        dict(res=ind.get("rendement_annualise"), key="pf_ann", icon="📈", foot=sel.period, signed=True),
        dict(res=ind.get("volatilite"), key="pf_vol", icon="🌊", foot=sel.period),
        dict(res=ind.get("sharpe"), key="pf_sh", icon="⚖️", foot=sel.period),
        dict(res=ind.get("drawdown_max"), key="pf_dd", icon="📉", foot=sel.period),
    ])
    with st.container(border=True):
        section(f"Valeur de 100 investis — {sel.label}", "Achat au début de la période aux poids de la bibliothèque, puis conservation")
        comp = pd.DataFrame({name: r} | ({EQUAL: pr[EQUAL]} if name != EQUAL and EQUAL in pr else {}))
        st.plotly_chart(wealth_chart(comp, bench_r.rename(bundle.benchmark) if (sel.show_bench and bench_r is not None and not is_ref) else None,
                                     400, baseline=True), width="stretch", config=PLOTLY_CONFIG)
    if ppy == 252 and len(r) > 40:
        with st.container(border=True):
            section("Rendements mensuels et annuels", "Composés à partir des rendements quotidiens")
            mt = monthly_table(r)
            MONTHS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]
            mt.columns = [MONTHS[c - 1] if isinstance(c, (int, np.integer)) else c for c in mt.columns]
            z = mt.values * 100
            fig = go.Figure(go.Heatmap(z=z, x=list(mt.columns), y=[str(y) for y in mt.index], zmid=0,
                                       colorscale=[[0, "#F43F5E"], [0.5, "#161743"], [1, "#22C55E"]],
                                       text=[["" if np.isnan(v) else f"{v:+.1f}".replace(".", ",") for v in row] for row in z],
                                       texttemplate="%{text}", hovertemplate="%{y} · %{x} : %{z:+.2f} %<extra></extra>",
                                       colorbar=dict(title="%", thickness=10)))
            fig.update_layout(height=60 + 34 * len(mt), margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(type="category"))
            st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
            months = mt.drop(columns="Année")
            explain("Chaque case : rendement du mois (en %). La dernière colonne donne l'année complète.",
                    f"Meilleur mois : {num(np.nanmax(months.values) * 100, 1)} % ; pire mois : "
                    f"{num(np.nanmin(months.values) * 100, 1)} % ; {int((months.values > 0).sum())} mois positifs sur "
                    f"{int(np.isfinite(months.values).sum())}.")

# ------------------------------------------------------------------ Attribution
with tabs[3]:
    if is_ref:
        st.info("Attribution non applicable à un indice détenu en une seule ligne.")
    else:
        ca = cumulative_attribution(assets_r, w)
        with st.container(border=True):
            section("D'où vient la performance ?", "Contribution cumulée de chaque actif à la valeur de 1 investi")
            fig = base_figure("", 400)
            from components.charts import asset_colors
            colors = asset_colors(list(bundle.assets))
            for a in ca.columns:
                if w[a] > 0.0005:
                    fig.add_trace(go.Scatter(x=ca.index, y=ca[a], name=a, stackgroup="c", mode="lines",
                                             line=dict(width=0.5, color=colors.get(a)),
                                             hovertemplate=f"<b>{a}</b> : %{{y:+.1%}}<extra></extra>"))
            fig.update_yaxes(tickformat=".0%", title="Contribution cumulée")
            fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.12, yanchor="top", xanchor="left", x=0))
            st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
            final = ca.iloc[-1].sort_values(ascending=False)
            total = float((1 + r).prod() - 1)
            explain("Contribution de l'actif i à la date t : Σ V_{s−1} · w_{i,s−1} · r_{i,s}, avec les poids qui dérivent. "
                    "L'empilement redonne exactement le rendement cumulé du portefeuille.",
                    f"Rendement cumulé {pct(total, 1)} = somme des contributions ({pct(final.sum(), 1)}). Premier "
                    f"contributeur : <b>{final.index[0]}</b> ({pct(final.iloc[0], 1)}), soit "
                    f"{pct(final.iloc[0] / total if total else np.nan, 0)} du total.")

# ------------------------------------------------------------------ Risque
with tabs[4]:
    metric_row([
        dict(res=ind.get("var95_hist"), key="pf_var", icon="⚠️", foot=sel.period),
        dict(res=ind.get("cvar95"), key="pf_cvar", icon="🧨", foot=sel.period),
        dict(res=ind.get("beta"), key="pf_beta", icon="🔗", foot=f"contre {bundle.benchmark}"),
        dict(res=ind.get("duree_drawdown"), key="pf_ddd", icon="⏳", foot=sel.period),
    ])
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        section("Drawdown", sel.label)
        st.plotly_chart(drawdown_chart(r.to_frame(name), 300), width="stretch", config=PLOTLY_CONFIG)
    with c2, st.container(border=True):
        section("Contribution au risque", "Covariance de la période sélectionnée")
        if not is_ref:
            rc = risk_contributions(w, assets_r.cov() * ppy)
            st.plotly_chart(grouped_bars(rc[["Poids", "Part du risque"]], 300), width="stretch", config=PLOTLY_CONFIG)
    full = simple_returns(bundle.clean.prices)
    series = {name: lib.entry_returns(entry, full[bundle.assets], full[bundle.benchmark] if bundle.benchmark else None)}
    cp = crisis_performance(series, CRISES)
    if len(cp):
        with st.container(border=True):
            section("Tests de résistance historiques", "Poids actuels appliqués aux crises passées")
            cp_show = cp.copy()
            for c in ("Rendement cumulé", "Drawdown maximal"):
                cp_show[c] = cp_show[c].map(lambda v: pct(v, 1))
            st.dataframe(cp_show, hide_index=True, width="stretch")
            banner("Les crises de 2020 et 2022 se situent dans la période d'estimation : ces poids « connaissaient » "
                   "déjà ces événements. Analyse descriptive, pas une validation.", "warn", "⚠️")

# ------------------------------------------------------------------ Promesse contre réalité
with tabs[5]:
    if entry.type != "automatique" or not entry.parametres.get("periode_estimation"):
        st.info("Disponible pour les portefeuilles optimisés automatiquement (ils ont une période d'estimation).")
    else:
        P = entry.parametres
        d0, d1 = pd.Timestamp(P["periode_estimation"][0]), pd.Timestamp(P["periode_estimation"][1])
        r_est = simple_returns(bundle.daily_prices).loc[d0:d1]
        est = estimate(r_est, 252, P["estimateur"])
        ann = sharpe_annonce(w, est.mu, est.cov, P["taux_sans_risque"], est.start, est.end, est.n_obs, SRC, name)
        r_test = simple_returns(bundle.daily_prices).loc[d1:].iloc[1:]
        real = calculer_indicateurs(buy_and_hold_returns(r_test, w), None, rf, 252, source=SRC, sujet=name)
        metric_row([
            dict(res=ann, key="pr_ann", icon="📣", foot="estimation", title="Sharpe annoncé"),
            dict(res=real["sharpe"], key="pr_real", icon="🧪", foot="test (achat puis conservation)", title="Sharpe réalisé"),
            dict(res=real["rendement_annualise"], key="pr_ret", icon="📈", foot=f"annoncé : {pct(ann.entree('ret'), 1)}",
                 title="Rendement réalisé"),
            dict(res=real["volatilite"], key="pr_vol", icon="🌊", foot=f"annoncée : {pct(ann.entree('vol'), 1)}",
                 title="Volatilité réalisée"),
        ])
        explain("À gauche, ce que promettait l'optimiseur avec μ et Σ estimés ; à droite, ce qui s'est passé sur la "
                "période de test avec les mêmes poids.",
                f"Sharpe {num(ann.valeur)} annoncé contre <b>{num(real['sharpe'].valeur)}</b> réalisé "
                f"({num(real['sharpe'].valeur - ann.valeur, 2, signed=True)}) ; rendement {pct(ann.entree('ret'), 1)} "
                f"annoncé contre {pct(real['rendement_annualise'].valeur, 1)} réalisé.")

# ------------------------------------------------------------------ Gérer la bibliothèque
with tabs[6]:
    custom = st.session_state.setdefault("library_custom", {})
    lo, hi = params.weight_min, params.weight_max
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        section("Constructeur personnalisé", f"Bornes : {pct(lo, 0)} à {pct(hi, 0)} par actif")
        vals = {a: st.number_input(f"{a} (%)", 0.0, 100.0, round(100 / len(bundle.assets), 1), 0.5, key=f"cb_{a}")
                for a in bundle.assets}
        wts = {a: v / 100 for a, v in vals.items()}
        total = sum(wts.values())
        st.markdown(f"**Somme : {pct(total, 1)}**" + (" ✅" if abs(total - 1) < 1e-6 else " — doit valoir 100 %"))
        if st.button("Normaliser à 100 %", key="cb_norm") and total > 0:
            for a, v in lib.normalize(wts).items():
                st.session_state[f"cb_{a}"] = round(100 * v, 2)
            st.rerun()
        new_name = st.text_input("Nom du portefeuille", key="cb_name", placeholder="ex. Mon allocation prudente")
        if st.button("💾 Enregistrer", key="cb_save"):
            errs = lib.validate(wts, lo, hi, tol=1e-3) + ([] if new_name.strip() else ["Donnez un nom au portefeuille."])
            if new_name in library:
                errs.append(f"« {new_name} » existe déjà.")
            if errs:
                for e in errs:
                    banner(e, "error", "⛔")
            else:
                custom[new_name] = lib.Entry(new_name, lib.normalize(wts), "personnalise", "Saisi à la main",
                                             lib.next_color(library), parametres={"poids_min": lo, "poids_max": hi})
                st.toast(f"« {new_name} » enregistré", icon="✅")
                st.rerun()
    with c2, st.container(border=True):
        section("Portefeuille cible sur la frontière", "Estimé sur la période d'estimation")
        kind = st.radio("Cible", ["Rendement", "Volatilité"], horizontal=True, key="tg_kind")
        val = st.number_input("Valeur annuelle cible (%)", 1.0, 100.0, 35.0 if kind == "Rendement" else 30.0, 0.5, key="tg_val")
        est0 = estimate(simple_returns(bundle.daily_prices).loc[:pd.Timestamp(params.split_date)], 252, params.cov_method)
        try:
            tp = target_portfolio(est0.mu, est0.cov, rf, lo, hi, target_return=val / 100 if kind == "Rendement" else None,
                                  target_vol=val / 100 if kind == "Volatilité" else None)
            st.markdown(f"Rendement espéré {pct(tp.expected_return, 1)} · volatilité {pct(tp.volatility, 1)} · "
                        f"Sharpe {num(tp.sharpe)}")
            st.dataframe(tp.weights.map(lambda v: pct(v, 1)).rename("Poids").to_frame().T, width="stretch")
            tname = f"Cible {kind.lower()} {num(val, 1)} %"
            if st.button("💾 Enregistrer ce portefeuille cible", key="tg_save"):
                custom[tname] = lib.Entry(tname, {k: float(v) for k, v in tp.weights.items()}, "cible",
                                          f"{kind} cible {num(val, 1)} % sur la frontière", lib.next_color(library),
                                          parametres=lib.params_dict(est0, rf, lo, hi, f"cible_{kind.lower()}"))
                st.toast(f"« {tname} » enregistré", icon="✅")
                st.rerun()
        except ValueError as exc:
            banner(str(exc), "warn", "⚠️")
    with st.container(border=True):
        section("Bibliothèque", f"{len(library)} portefeuilles · les portefeuilles automatiques sont recalculés quand les paramètres changent")
        st.dataframe(pd.DataFrame([{"Nom": e.nom, "Type": lib.TYPES.get(e.type, e.type), "Description": e.description,
                                    "Créé le": e.date_creation[:16].replace("T", " ")} for e in library.values()]),
                     hide_index=True, width="stretch")
        c3, c4, c5 = st.columns(3)
        target = c3.selectbox("Portefeuille", names, key="lib_target")
        if c3.button("Dupliquer", key="lib_dup"):
            tmp = dict(library)
            new = lib.duplicate(tmp, target)
            custom[new] = tmp[new]
            st.rerun()
        new_label = c4.text_input("Nouveau nom", key="lib_newname")
        if c4.button("Renommer", key="lib_ren", disabled=target not in custom):
            try:
                if new_label in library:
                    raise ValueError(f"« {new_label} » existe déjà.")
                lib.rename(custom, target, new_label)
                st.rerun()
            except ValueError as exc:
                banner(str(exc), "error", "⛔")
        if c5.button("Supprimer", key="lib_del", disabled=target not in custom,
                     help="Seuls les portefeuilles personnalisés peuvent être supprimés."):
            custom.pop(target, None)
            st.rerun()
        c6, c7 = st.columns(2)
        c6.download_button("⬇️ Exporter la bibliothèque (JSON)", lib.to_json(library).encode("utf-8"),
                           "bibliotheque_portefeuilles.json", "application/json", width="stretch")
        up = c7.file_uploader("Importer (JSON)", type="json", key="lib_import")
        if up is not None and st.session_state.get("lib_imported") != up.name:
            try:
                imported = lib.from_json(up.read().decode("utf-8"))
                added = 0
                for k, e in imported.items():
                    if k not in library:
                        custom[k] = e
                        added += 1
                st.session_state["lib_imported"] = up.name
                st.toast(f"{added} portefeuille(s) importé(s)", icon="✅")
                st.rerun()
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                banner(f"Fichier invalide : {exc}", "error", "⛔")
