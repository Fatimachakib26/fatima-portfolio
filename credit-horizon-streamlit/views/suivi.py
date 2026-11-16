from datetime import date

import streamlit as st

from core import db, forms, repo, ui

ui.header("🧾", "Suivi des recommandations et des anomalies",
          "Plan d'action priorisé, chaînes de recommandations (Risque → Lacune COSO → Action → Responsable → Indicateur) et registre unique des anomalies (C04).")
today = date.today().isoformat()
ta, tr, tn = st.tabs(["📌 Plan d'action", "💡 Recommandations", "🐞 Anomalies"])

with ta:
    a = repo.table_df("actions", "priority, id")
    ui.kpis([("Avancement moyen du plan", f"{round(a.progress.mean()) if len(a) else 0} %", f"{int((a.status != 'Terminé').sum())} action(s) ouverte(s)", "brand"),
             ("Actions P1 ouvertes", int(((a.priority == "P1") & (a.status != "Terminé")).sum()), "Conditionnent le reste du dispositif", "red")])
    st.dataframe(a[["priority", "id", "title", "owner", "due", "deliverable", "risk_ids", "control_ids", "status", "progress"]].rename(columns={
        "priority": "Prio.", "id": "ID", "title": "Action", "owner": "Responsable", "due": "Échéance", "deliverable": "Livrable / preuve",
        "risk_ids": "Risques", "control_ids": "Contrôles", "status": "Statut", "progress": "Avancement"}), hide_index=True, use_container_width=True,
        column_config={"Avancement": st.column_config.ProgressColumn("Avancement", min_value=0, max_value=100, format="%d %%")})
    if ui.can("actions.write"):
        F = [{"key": "title", "label": "Intitulé de l'action", "required": True, "full": True},
             {"key": "priority", "label": "Priorité", "type": "select", "options": ["P1", "P2", "P3"]},
             {"key": "status", "label": "Statut", "type": "select", "options": ["À faire", "En cours", "Terminé", "Bloqué"]},
             {"key": "owner", "label": "Responsable", "required": True}, {"key": "due", "label": "Échéance"},
             {"key": "deliverable", "label": "Livrable / preuve", "full": True}, {"key": "risk_ids", "label": "Risques traités"},
             {"key": "control_ids", "label": "Contrôles concernés"}, {"key": "progress", "label": "Avancement (%)", "type": "slider", "min": 0, "max": 100}]
        with st.expander("✏️ Ajouter / modifier une action"):
            sel = st.selectbox("Action", ["Nouvelle action"] + list(a.id), key="act_sel")
            row = None if sel == "Nouvelle action" else db.query("select * from actions where id=?", [sel])[0]
            forms.entity_form("actions", "Action", F, row, "A", 2, extra_create={"is_demo": 0})
            if row:
                forms.delete_button("actions", "Action", sel)
    else:
        ui.readonly("Le pilotage du plan d'action est réservé à la direction, aux risques et au contrôle interne.")

with tr:
    rec = repo.table_df("recommendations")
    for x in rec.to_dict("records"):
        with st.container(border=True):
            st.markdown(f"**{x['id']}** · <span class='ch-badge'>{x['status']}</span> <span class='ch-badge' style='background:#fef3c7;color:#92400e'>{x['basis']}</span>"
                        + (" <span class='ch-badge' style='background:#ede9fe;color:#5b21b6'>Démo</span>" if x["is_demo"] else ""), unsafe_allow_html=True)
            st.markdown("<div class='ch-chain'>" + "".join(f"<div><b>{k} →</b>{v}</div>" for k, v in [
                ("RISQUE", x["risk_id"]), ("LACUNE COSO", x["coso_gap"]), ("ACTION CORRECTIVE", x["action"]), ("RESPONSABLE", x["owner"]), ("INDICATEUR", x["indicator"])])
                + "</div>", unsafe_allow_html=True)
    if ui.can("recommendations.write"):
        F = [{"key": "risk_id", "label": "RISQUE", "required": True, "help": "Ex. : R03"},
             {"key": "status", "label": "Statut", "type": "select", "options": ["À lancer", "En cours", "Mise en œuvre", "Abandonnée"]},
             {"key": "coso_gap", "label": "LACUNE COSO", "type": "textarea", "required": True},
             {"key": "action", "label": "ACTION CORRECTIVE", "type": "textarea", "required": True},
             {"key": "owner", "label": "RESPONSABLE", "required": True},
             {"key": "basis", "label": "Fondement", "type": "select", "options": ["Constat", "Hypothèse"]},
             {"key": "indicator", "label": "INDICATEUR DE SUIVI", "type": "textarea", "required": True}]
        with st.expander("✏️ Ajouter / modifier une recommandation"):
            sel = st.selectbox("Recommandation", ["Nouvelle recommandation"] + list(rec.id), key="rec_sel")
            row = None if sel.startswith("Nouvelle") else db.query("select * from recommendations where id=?", [sel])[0]
            forms.entity_form("recommendations", "Recommandation", F, row, "REC", 2, extra_create={"is_demo": 0})
            if row:
                forms.delete_button("recommendations", "Recommandation", sel)

with tn:
    an = repo.table_df("anomalies", "detected_on desc, id desc")
    opened = an[an.status != "Clôturée"]
    late = opened[(opened.due_on != "") & (opened.due_on < today)]
    m = st.columns(4)
    m[0].metric("Anomalies", len(an))
    m[1].metric("Ouvertes", len(opened))
    m[2].metric("En retard", len(late))
    m[3].metric("Niveau 3 (direction générale)", int((opened.escalation == 3).sum()))
    statut = st.multiselect("Statut", ["Ouverte", "En cours", "Clôturée"], default=["Ouverte", "En cours"])
    v = an[an.status.isin(statut)].copy()
    v["Retard"] = [("⚠️" if s_ != "Clôturée" and d and d < today else "") for s_, d in zip(v.status, v.due_on)]
    v["escalation"] = "N" + v.escalation.astype(str)
    st.dataframe(v[["id", "detected_on", "dossier_ref", "nature", "severity", "risk_id", "control_id", "owner", "due_on", "Retard", "escalation", "status", "declared_by"]].rename(columns={
        "id": "ID", "detected_on": "Détectée", "dossier_ref": "Dossier", "nature": "Nature", "severity": "Gravité", "risk_id": "Risque", "control_id": "Contrôle",
        "owner": "Responsable", "due_on": "Échéance", "escalation": "Escalade", "status": "Statut", "declared_by": "Déclarée par"}), hide_index=True, use_container_width=True)
    F = [{"key": "detected_on", "label": "Date de détection", "type": "date", "required": True, "default": today},
         {"key": "dossier_ref", "label": "Dossier / référence"},
         {"key": "nature", "label": "Nature de l'anomalie", "type": "textarea", "required": True},
         {"key": "severity", "label": "Gravité", "type": "select", "options": ["Mineure", "Significative", "Majeure", "Critique"]},
         {"key": "status", "label": "Statut", "type": "select", "options": ["Ouverte", "En cours", "Clôturée"]},
         {"key": "risk_id", "label": "Risque lié", "help": "Ex. : R01"}, {"key": "control_id", "label": "Contrôle lié", "help": "Ex. : C04"},
         {"key": "owner", "label": "Responsable du traitement", "required": True}, {"key": "due_on", "label": "Échéance de régularisation", "type": "date"},
         {"key": "escalation", "label": "Niveau d'escalade (charte, art. 11)", "type": "slider", "min": 1, "max": 3, "default": 1},
         {"key": "resolution", "label": "Résolution / preuve de clôture", "type": "textarea"}]
    if ui.can("anomalies.create"):
        with st.expander("➕ Déclarer une anomalie", expanded=False):
            forms.entity_form("anomalies", "Anomalie", F, None, "AN", 3, "-", extra_create={"declared_by": ui.user()["name"], "is_demo": 0})
    if ui.can("anomalies.write"):
        with st.expander("✏️ Traiter / clôturer une anomalie"):
            sel = st.selectbox("Anomalie", list(an.id), key="an_sel")
            if sel:
                forms.entity_form("anomalies", "Anomalie", F, db.query("select * from anomalies where id=?", [sel])[0], "AN", 3, "-")
                forms.delete_button("anomalies", "Anomalie", sel)
