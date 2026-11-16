import pandas as pd
import streamlit as st

from core import charts, repo, ui

ui.header("📊", "Dashboard exécutif", "Vue consolidée de l'exposition aux risques, du dispositif de contrôle interne et de l'avancement des actions correctives.")
s = repo.snapshot()
k = repo.kpis(s)
r = s["risks"]

ui.kpis([
    ("Risques recensés", k["total"], f"Score moyen {k['avg_score']:.1f} / 25", "brand"),
    ("Risques critiques", k["critical"], f"{k['high']} risques élevés", "red"),
    ("Contrôles opérationnels", f"{k['operational_controls']}/{k['total_controls']}", f"{k['covered_risks']}/{k['total']} risques couverts", "green"),
    ("Actions en attente", k["pending_actions"], f"Avancement moyen {k['action_progress']} %", "amber"),
    ("Anomalies ouvertes", k["open_anomalies"], f"{k['overdue_anomalies']} en retard", "red" if k["overdue_anomalies"] else "brand"),
    ("Maturité COSO", f"{k['avg_maturity']:.1f}/5", f"{k['deficient_principles']}/17 principes déficients", "amber"),
])

g1, g2, g3 = st.columns(3)
with g1.container(border=True):
    st.markdown("**Répartition des risques par catégorie**")
    st.plotly_chart(charts.donut_categories(r), use_container_width=True, config={"displayModeBar": False})
with g2.container(border=True):
    st.markdown("**Répartition par niveau de criticité**")
    st.caption("1–4 Faible · 5–9 Modéré · 10–15 Élevé · 16–25 Critique")
    st.plotly_chart(charts.bar_levels(r), use_container_width=True, config={"displayModeBar": False})
with g3.container(border=True):
    st.markdown("**Évolution des risques**")
    st.caption("Dernière cotation P × G connue en fin de mois")
    st.plotly_chart(charts.evolution(s["history"], list(r.id)), use_container_width=True, config={"displayModeBar": False})

t1, t2 = st.columns([3, 2])
with t1.container(border=True):
    st.markdown("**Top 5 des risques prioritaires**")
    top = r.sort_values(["score", "id"], ascending=[False, True]).head(5)
    st.dataframe(top[["id", "title", "category", "probability", "gravity", "score", "level", "owner"]].rename(columns={
        "id": "ID", "title": "Risque", "category": "Catégorie", "probability": "P", "gravity": "G", "score": "P × G", "level": "Criticité", "owner": "Responsable"}),
        hide_index=True, use_container_width=True,
        column_config={"P × G": st.column_config.ProgressColumn("P × G", min_value=0, max_value=25, format="%d")})
with t2.container(border=True):
    st.markdown("**Cartographie synthétique**")
    st.plotly_chart(charts.heatmap(r, compact=True), use_container_width=True, config={"displayModeBar": False})

b1, b2 = st.columns(2)
with b1.container(border=True):
    st.markdown("**Indicateurs de contrôle interne**")
    an = s["anomalies"]
    closure = round(k["closed_anomalies"] / len(an) * 100) if len(an) else 0
    for label, v in [("Couverture des risques par au moins un contrôle", round(k["covered_risks"] / max(1, k["total"]) * 100)),
                     ("Contrôles opérationnels ou efficaces", round(k["operational_controls"] / max(1, k["total_controls"]) * 100)),
                     ("Taux de clôture des anomalies", closure), ("Avancement du plan d'action", k["action_progress"]),
                     ("Principes COSO non déficients", round((17 - k["deficient_principles"]) / 17 * 100))]:
        st.progress(v / 100, text=f"{label} — **{v} %**")
    st.caption(f"Dossiers TPE suspendus (règle de blocage C01) : {k['dossiers_blocked']}/{k['dossiers']}")
with b2.container(border=True):
    st.markdown("**Actions correctives en attente**")
    a = s["actions"]
    pend = a[a.status != "Terminé"].sort_values(["priority", "id"])
    st.dataframe(pend[["priority", "id", "title", "owner", "due", "progress"]].rename(columns={
        "priority": "Prio.", "id": "ID", "title": "Action", "owner": "Responsable", "due": "Échéance", "progress": "Avancement"}),
        hide_index=True, use_container_width=True, column_config={"Avancement": st.column_config.ProgressColumn("Avancement", min_value=0, max_value=100, format="%d %%")})

st.page_link("views/assistant.py", label="Demander à Risk Advisor une analyse de la situation", icon="✨")
