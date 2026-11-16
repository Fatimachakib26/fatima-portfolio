import pandas as pd
import streamlit as st

from core import db, forms, repo, ui

ui.header("🛡️", "Contrôle interne – fiches de contrôle",
          "Objectif, risque couvert, type, procédure, responsable, fréquence, preuve attendue, indicateur de performance et traitement des anomalies.")
can_write = ui.can("controls.write")
if not can_write:
    ui.readonly("Consultation seule : les fiches de contrôle sont gérées par le contrôle interne et l'administrateur.")
c = repo.table_df("controls")
r = repo.risks_df()

with st.container(border=True):
    st.markdown("**Matrice de couverture risques × contrôles** · ● = le contrôle couvre le risque")
    rows = []
    for x in r.itertuples():
        row = {"Risque": f"{x.id} {x.title[:46]}", "Niveau": x.level}
        n = 0
        for ctrl in c.itertuples():
            hit = x.id in repo.split_ids(ctrl.risk_ids)
            row[ctrl.id] = "●" if hit else ""
            n += hit
        row["Couverture"] = "Non couvert" if n == 0 else ("1 – dépendance" if n == 1 else f"{n} contrôles")
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption("Un risque couvert par un seul contrôle constitue un point de dépendance à surveiller en priorité (rapport, section 5.2).")

FIELDS = [
    {"key": "name", "label": "Intitulé du contrôle", "required": True, "full": True},
    {"key": "nature", "label": "Type de contrôle", "type": "select", "options": ["Préventif", "Détectif", "Correctif", "Détectif et correctif"]},
    {"key": "status", "label": "Statut", "type": "select", "options": ["À concevoir", "En déploiement", "Opérationnel", "Efficace", "Déficient"]},
    {"key": "objective", "label": "Objectif du contrôle", "type": "textarea", "required": True},
    {"key": "risk_ids", "label": "Risque(s) couvert(s)", "help": "Ex. : R01, R08"},
    {"key": "owner", "label": "Responsable", "required": True},
    {"key": "procedure", "label": "Description de la procédure", "type": "textarea"},
    {"key": "supervision", "label": "Supervision"},
    {"key": "frequency", "label": "Fréquence", "required": True},
    {"key": "evidence", "label": "Preuve attendue", "type": "textarea"},
    {"key": "indicator", "label": "Indicateur de performance", "type": "textarea"},
    {"key": "anomaly_treatment", "label": "Traitement des anomalies", "type": "textarea"},
    {"key": "last_review", "label": "Dernière revue", "type": "date"},
]

q = st.text_input("Rechercher une fiche", placeholder="Ex. : délégation, liquidité, C05…")
view = c[c.astype(str).agg(" ".join, axis=1).str.lower().str.contains(q.lower(), regex=False)] if q else c
cols = st.columns(2)
for i, x in enumerate(view.to_dict("records")):
    with cols[i % 2].container(border=True):
        st.markdown(f"#### {x['id']} · {x['name']}")
        st.markdown(f"<span class='ch-badge' style='background:#ede9fe;color:#5b21b6'>{x['nature']}</span> <span class='ch-badge'>{x['status']}</span> "
                    + " ".join(f"<span class='ch-badge' style='background:#dbeafe;color:#1e3a8a'>{rid}</span>" for rid in repo.split_ids(x["risk_ids"]))
                    + (" <span class='ch-badge' style='background:#ede9fe;color:#5b21b6'>Démo</span>" if x["is_demo"] else ""), unsafe_allow_html=True)
        for lab, key in [("Objectif", "objective"), ("Procédure", "procedure"), ("Responsable", "owner"), ("Supervision", "supervision"), ("Fréquence", "frequency"),
                         ("Preuve attendue", "evidence"), ("Indicateur", "indicator"), ("Traitement des anomalies", "anomaly_treatment"), ("Dernière revue", "last_review")]:
            st.markdown(f"**{lab} :** {x[key] or '–'}")

if can_write:
    st.divider()
    st.subheader("Ajouter / modifier une fiche")
    mode = st.radio("Action", ["Nouvelle fiche", "Modifier une fiche"], horizontal=True)
    if mode == "Nouvelle fiche":
        forms.entity_form("controls", "Contrôle", FIELDS, None, "C", 2, extra_create={"is_demo": 0})
    else:
        cid = st.selectbox("Fiche", list(c.id), format_func=lambda i: f"{i} – {c.set_index('id').name[i]}")
        forms.entity_form("controls", "Contrôle", FIELDS, db.query("select * from controls where id=?", [cid])[0], "C", 2)
        forms.delete_button("controls", "Contrôle", cid)
