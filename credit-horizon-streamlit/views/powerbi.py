from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import advisor, exports, repo, ui

ui.header("📈", "Power BI", "Jeu de données en étoile prêt à importer dans Power BI Desktop, mesures DAX et intégration du rapport publié.")
root = Path(__file__).resolve().parent.parent / "powerbi"
guide = (root / "GUIDE_POWER_BI.md").read_text(encoding="utf-8")
dax = (root / "MESURES_DAX.dax").read_text(encoding="utf-8")
s = repo.snapshot()
tables = exports.powerbi_tables(s)

url = advisor._secret("POWERBI_EMBED_URL")
if url:
    with st.container(border=True):
        st.markdown("**Rapport Power BI publié**")
        components.iframe(url, height=720, scrolling=True)
else:
    st.info("Aucun rapport Power BI intégré pour l'instant. Après publication dans Power BI Service, ajoutez son URL d'incorporation "
            "dans les secrets Streamlit (`POWERBI_EMBED_URL`) : le rapport s'affichera ici.")

c1, c2, c3 = st.columns(3)
c1.download_button("📦 Jeu de données complet (ZIP : CSV + Excel + DAX + guide)", exports.powerbi_zip(s, guide, dax), "credit-horizon-powerbi.zip", "application/zip", use_container_width=True, type="primary")
c2.download_button("📊 Classeur Excel Power BI", exports.powerbi_excel(s), "CreditHorizon_PowerBI.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
c3.download_button("🧮 Mesures DAX", dax.encode("utf-8"), "MESURES_DAX.dax", "text/plain", use_container_width=True)

with st.container(border=True):
    st.markdown(f"**Modèle de données** — {len(tables)} tables")
    st.dataframe([{"Table": n, "Lignes": len(df), "Colonnes": ", ".join(df.columns)} for n, df in tables.items()], hide_index=True, use_container_width=True)
    t = st.selectbox("Aperçu d'une table", list(tables))
    st.dataframe(tables[t], hide_index=True, use_container_width=True)
with st.expander("📘 Guide pas à pas Power BI"):
    st.markdown(guide)
with st.expander("🧮 Mesures DAX"):
    st.code(dax, language="sql")
