import pandas as pd
import streamlit as st

from core import repo, ui
from core.db import SEED
from core.scoring import LEVEL_TREATMENT, appetite_zone

ui.header("🎯", "Charte d'appétence au risque",
          "Charte qualitative : ce que Crédit Horizon accepte, accepte sous conditions ou refuse. Sans modèle PD/LGD ; les seuils chiffrés seront fixés par la direction.")
STY = {"acceptable": ("#ecfdf5", "#065f46", "✅"), "renforcee": ("#fffbeb", "#92400e", "⚠️"), "inacceptable": ("#fef2f2", "#991b1b", "⛔")}
r = repo.risks_df()
cols = st.columns(3)
for col, lv in zip(cols, SEED["appetite_levels"]):
    bg, fg, ic = STY[lv["key"]]
    rs = r[r.level.map(appetite_zone) == lv["key"]].sort_values("score", ascending=False)
    col.markdown(f"<div style='background:{bg};border-radius:16px;padding:16px;min-height:330px;color:#334155'><h4 style='color:{fg};margin-top:0'>{ic} {lv['title']}</h4>"
                 f"<p style='font-size:.88rem'>{lv['description']}</p><ul style='font-size:.82rem'>" + "".join(f"<li>{e}</li>" for e in lv["examples"]) + "</ul>"
                 f"<b style='color:{fg};font-size:.8rem'>Risques du registre dans cette zone</b><br>"
                 + (" ".join(ui.level_pill(f"{x.id} {x.level}", int(x.score)) for x in rs.itertuples()) or "<i>aucun</i>") + "</div>", unsafe_allow_html=True)
st.caption("Lecture applicative : Faible/Modéré → acceptable sous contrôle ; Élevé → autorisation renforcée ; Critique → hors appétence en l'état, renforcement immédiat. "
           + " · ".join(f"{k} : {v}" for k, v in LEVEL_TREATMENT.items()))
a, b = st.columns(2)
with a.container(border=True):
    st.markdown("**Principes généraux (article 3)**")
    st.markdown("\n".join(f"{i}. {p}" for i, p in enumerate(SEED["charter_principles"], 1)))
with b.container(border=True):
    st.markdown("**Mécanismes d'escalade (article 11)**")
    for e in SEED["escalation"]:
        st.markdown(f"**{e['title']}** — {e['text']}")
    st.caption("Le délai de chaque niveau est fixé par la direction (non défini dans le cas).")
with st.container(border=True):
    st.markdown("**Appétence par catégorie de risque (tableau 5.1)**")
    st.dataframe(pd.DataFrame(SEED["appetite_by_category"]).rename(columns={"category": "Catégorie", "appetite": "Appétence qualitative", "limits": "Limites et situations inacceptables"}),
                 hide_index=True, use_container_width=True)
