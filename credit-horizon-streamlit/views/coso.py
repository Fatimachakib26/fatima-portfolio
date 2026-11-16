import plotly.graph_objects as go
import streamlit as st

from core import charts, db, repo, ui

ui.header("🏛️", "Diagnostic COSO 2013", "Cinq composantes et dix-sept principes : constats, lacunes, risques, recommandations, responsables et indicateurs de suivi.")
can_write = ui.can("coso.write")
if not can_write:
    ui.readonly("Consultation seule : le diagnostic COSO est mis à jour par le contrôle interne et l'administrateur.")
comps = repo.table_df("coso_components")
prin = repo.snapshot()["principles"]

a, b = st.columns([2, 3])
with a.container(border=True):
    st.markdown("**Maturité par composante** (1 = initiale, 5 = optimisée)")
    fig = go.Figure(go.Scatterpolar(r=list(comps.maturity) + [comps.maturity.iloc[0]], theta=list(comps.name) + [comps.name.iloc[0]], fill="toself",
                                    line=dict(color="#0f7a58", width=2), fillcolor="rgba(16,185,129,.25)", marker=dict(size=8)))
    fig.update_layout(**charts.LAYOUT, height=300, polar=dict(radialaxis=dict(range=[0, 5], tickvals=[1, 2, 3, 4, 5])))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
with b.container(border=True):
    st.markdown("**Appréciation des 17 principes**")
    cnt = prin.assessment.value_counts()
    m = st.columns(4)
    for i, lab in enumerate(["Déficient", "Partiel", "Satisfaisant", "Non évalué"]):
        m[i].metric(lab, int(cnt.get(lab, 0)))
    st.caption(f"Constats (faits du cas) : {int(prin.nature.str.startswith('Constat').sum())} · Hypothèses à vérifier : {int((prin.nature == 'Hypothèse à vérifier').sum())}")
    colors = {"Déficient": "#fecaca", "Partiel": "#fde68a", "Satisfaisant": "#bbf7d0", "Non évalué": "#e2e8f0"}
    st.markdown(" ".join(f"<span title='{p.title} : {p.assessment}' style='display:inline-block;margin:2px;padding:6px 8px;border-radius:8px;"
                         f"font-weight:700;font-size:.78rem;background:{colors[p.assessment]}'>{p.id}</span>" for p in prin.itertuples()), unsafe_allow_html=True)

tabs = st.tabs([f"{c.id}. {c.name}" for c in comps.itertuples()])
for tab, c in zip(tabs, comps.to_dict("records")):
    with tab:
        st.markdown(f"**{c['principles']}** — _{c['question']}_ &nbsp; · Maturité : **{c['maturity']}/5**" + (" · <span class='ch-badge' style='background:#ede9fe;color:#5b21b6'>Démo</span>" if c["is_demo"] else ""), unsafe_allow_html=True)
        x, y = st.columns(2)
        x.markdown(f"**Constats**  \n{c['findings']}")
        y.error(f"**Lacunes identifiées**  \n{c['gaps']}")
        x.markdown("**Risques associés**  \n" + " ".join(f"<span class='ch-badge'>{r}</span>" for r in repo.split_ids(c["risk_ids"])), unsafe_allow_html=True)
        y.success(f"**Recommandations**  \n{c['recommendations']}")
        x.markdown(f"**Responsables**  \n{c['owner']}")
        y.markdown(f"**Indicateurs de suivi**  \n{c['indicators']}")
        st.markdown("**Principes**")
        pp = prin[prin.component_id == c["id"]]
        st.dataframe(pp[["id", "title", "nature", "assessment", "diagnostic", "risk_ids"]].rename(columns={
            "id": "Principe", "title": "Intitulé", "nature": "Nature", "assessment": "Appréciation", "diagnostic": "Diagnostic", "risk_ids": "Risques"}),
            hide_index=True, use_container_width=True)
        if can_write:
            with st.expander("✏️ Mettre à jour la composante"):
                with st.form(f"comp_{c['id']}"):
                    vals = {k: st.text_area(lbl, c[k], key=f"c{c['id']}{k}") for k, lbl in [("findings", "Constats"), ("gaps", "Lacunes"), ("recommendations", "Recommandations"), ("indicators", "Indicateurs")]}
                    vals["risk_ids"] = st.text_input("Risques associés", c["risk_ids"])
                    vals["owner"] = st.text_input("Responsables", c["owner"])
                    vals["maturity"] = st.slider("Maturité", 1, 5, int(c["maturity"]))
                    if st.form_submit_button("Enregistrer", type="primary"):
                        db.update("coso_components", c["id"], vals)
                        ui.audit("Modification", "Composante COSO", str(c["id"]))
                        ui.toast_ok("Composante mise à jour.")
                        st.rerun()
            with st.expander("✏️ Apprécier un principe"):
                pid = st.selectbox("Principe", list(pp.id), key=f"psel{c['id']}")
                p = pp.set_index("id").loc[pid]
                with st.form(f"prin_{pid}"):
                    natures = ["Constat", "Hypothèse à vérifier", "Constat et hypothèse"]
                    assess = ["Non évalué", "Déficient", "Partiel", "Satisfaisant"]
                    nv = {"nature": st.selectbox("Nature", natures, natures.index(p.nature)), "assessment": st.selectbox("Appréciation", assess, assess.index(p.assessment)),
                          "diagnostic": st.text_area("Diagnostic", p.diagnostic), "risk_ids": st.text_input("Risques", p.risk_ids)}
                    if st.form_submit_button("Enregistrer", type="primary"):
                        db.update("coso_principles", pid, nv)
                        ui.audit("Modification", "Principe COSO", pid)
                        ui.toast_ok(f"Principe {pid} mis à jour.")
                        st.rerun()
