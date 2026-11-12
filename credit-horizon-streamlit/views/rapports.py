from datetime import date

import streamlit as st

from core import advisor, exports, repo, ui

ui.header("📥", "Rapports et exportations", "Tous les documents sont générés à partir des données enregistrées au moment de l'export.")
s = repo.snapshot()
d = date.today().isoformat()
PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
items = [
    ("📚 Rapport complet de gestion des risques", "Synthèse, registre, cartographie, contrôles, COSO, RACI, recommandations, plan d'action.", lambda: exports.pdf_full(s), f"rapport-gestion-risques-{d}.pdf", PDF),
    ("📝 Synthèse exécutive", "Indicateurs clés, top 5, recommandations prioritaires, actions P1.", lambda: exports.pdf_executive(s), f"synthese-executive-{d}.pdf", PDF),
    ("🏛️ Rapport COSO 2013", "Diagnostic des 5 composantes et des 17 principes.", lambda: exports.pdf_coso(s), f"rapport-coso-{d}.pdf", PDF),
    ("🟥 Cartographie des risques", "Matrice 5 × 5 et classement par criticité.", lambda: exports.pdf_heatmap(s), f"cartographie-risques-{d}.pdf", PDF),
    ("📌 Plan d'action correctif", "Actions priorisées, recommandations, anomalies ouvertes.", lambda: exports.pdf_action_plan(s), f"plan-action-{d}.pdf", PDF),
    ("📊 Registre Excel complet", "Classeur multi-onglets : registre, contrôles, COSO, recommandations, plan, anomalies, RACI.", lambda: exports.excel(s), f"credit-horizon-registre-{d}.xlsx", XLSX),
    ("🧾 Registre des risques (CSV)", "Séparateur « ; », UTF-8, compatible Excel.", lambda: exports.csv(s["risks"]), f"registre-risques-{d}.csv", "text/csv"),
    ("🐞 Anomalies (CSV)", "Registre unique des anomalies et dérogations (C04).", lambda: exports.csv(s["anomalies"]), f"anomalies-{d}.csv", "text/csv"),
    ("📌 Plan d'action (CSV)", "Export du plan d'action correctif.", lambda: exports.csv(s["actions"]), f"plan-action-{d}.csv", "text/csv"),
]
cols = st.columns(3)
for i, (title, desc, fn, fname, mime) in enumerate(items):
    with cols[i % 3].container(border=True):
        st.markdown(f"**{title}**")
        st.caption(desc)
        st.download_button("Télécharger", fn(), fname, mime, key=f"dl{i}", use_container_width=True)

with st.container(border=True):
    st.markdown("**✨ Rapport rédigé par Risk Advisor (IA)**")
    st.caption("L'assistant rédige un rapport narratif à partir des données réelles ; vous pouvez ensuite le télécharger en PDF.")
    if st.button("Générer le rapport IA", type="primary"):
        prompt = ("Prépare un rapport de gestion des risques complet et professionnel destiné à la direction générale : synthèse, cartographie et risques prioritaires, "
                  "diagnostic COSO, dispositif de contrôle, anomalies, plan d'action, recommandations au format RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → "
                  "INDICATEUR DE SUIVI, et prochaines étapes.")
        st.session_state.ai_report = st.write_stream(advisor.ask([{"role": "user", "content": prompt}], s))
        ui.audit("Rapport IA", "Risk Advisor", advisor.status()["provider"])
    if st.session_state.get("ai_report"):
        st.download_button("📄 Télécharger le rapport IA (PDF)", exports.markdown_pdf("Rapport de gestion des risques – Risk Advisor", st.session_state.ai_report),
                           f"rapport-ia-{d}.pdf", PDF)
