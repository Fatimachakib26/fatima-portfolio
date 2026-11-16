import streamlit as st

from core import charts, repo, ui
from core.scoring import CATEGORIES, LEVEL_TREATMENT

ui.header("🟥", "Cartographie des risques", "Matrice thermique interactive 5 × 5 (probabilité × gravité). Survolez une cellule pour voir les risques.")
r = repo.risks_df()
cat = st.multiselect("Catégories", CATEGORIES, default=sorted(r.category.unique()))
rf = r[r.category.isin(cat)]
left, right = st.columns([3, 2])
with left.container(border=True):
    st.plotly_chart(charts.heatmap(rf), use_container_width=True, config={"displayModeBar": False})
with right.container(border=True):
    st.markdown("**Fiche du risque**")
    if rf.empty:
        st.info("Aucun risque pour ces catégories.")
    else:
        rid = st.selectbox("Risque", list(rf.sort_values("score", ascending=False).id), format_func=lambda i: f"{i} – {rf.set_index('id').title[i]}")
        x = rf.set_index("id").loc[rid]
        st.markdown(ui.level_pill(x.level, int(x.score)) + f" &nbsp; <span class='ch-badge'>{x.category}</span>", unsafe_allow_html=True)
        st.write(x.event)
        st.markdown(f"**P = {x.probability} × G = {x.gravity} = {x.score}** — {LEVEL_TREATMENT[x.level]}")
        st.caption(x.justification)
        st.markdown(f"**Responsable :** {x.owner}  \n**Contrôles :** {x.control_ids or 'aucun'}")
with st.container(border=True):
    st.markdown("**Classement par criticité**")
    rk = rf.sort_values(["score", "id"], ascending=[False, True]).copy()
    rk["Traitement attendu"] = rk.level.map(LEVEL_TREATMENT)
    st.dataframe(rk[["id", "title", "probability", "gravity", "score", "level", "Traitement attendu"]].rename(columns={
        "id": "ID", "title": "Risque", "probability": "P", "gravity": "G", "score": "Score", "level": "Niveau"}), hide_index=True, use_container_width=True)
