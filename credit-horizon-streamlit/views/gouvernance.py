import pandas as pd
import streamlit as st

from core import auth, ui
from core.db import SEED

ui.header("🧭", "Gouvernance et matrice RACI",
          "R = Responsible (réalise) · A = Accountable (valide) · C = Consulted · I = Informed. Séparation des tâches et délégations d'autorisation.")
actors, acts = SEED["raci_actors"], SEED["raci_activities"]
COLORS = {"R": "background-color:#0f7a58;color:#fff;font-weight:700", "A": "background-color:#04261c;color:#fff;font-weight:700",
          "A/R": "background-color:#063b2b;color:#6ee7b7;font-weight:700", "C": "background-color:#e0f2fe;color:#075985;font-weight:700",
          "I": "background-color:#f1f5f9;color:#475569;font-weight:700", "–": "color:#cbd5e1"}
df = pd.DataFrame([{"Activité": f"{a['n']}. {a['activity']}", "Bloc": a["block"], **{f"{x['group']} · {x['label']}": a["roles"][x["key"]] for x in actors}} for a in acts])
with st.container(border=True):
    st.markdown("**Matrice RACI des décisions (14 activités × 6 acteurs)**")
    st.dataframe(df.style.map(lambda v: COLORS.get(v, ""), subset=df.columns[2:]), hide_index=True, use_container_width=True, height=530)

isra = lambda c: c in ("R", "A", "A/R")  # noqa: E731
blocks = ["Constitution", "Analyse / contrôle", "Autorisation"]
single_a = [sum(c in ("A", "A/R") for c in a["roles"].values()) == 1 for a in acts]
checks = [(x["label"], [b for b in blocks if any(a["block"] == b and isra(a["roles"][x["key"]]) for a in acts)]) for x in actors]
ok = all(single_a) and all(len(bl) < 3 for _, bl in checks)
l, r = st.columns(2)
with l.container(border=True):
    st.markdown("**Contrôle automatique de la séparation des tâches**")
    (st.success if ok else st.error)("Séparation respectée : aucun acteur ne cumule constitution, analyse et autorisation." if ok else "Conflit de séparation des tâches détecté.")
    st.markdown(f"- {'✅' if all(single_a) else '❌'} Une seule responsabilité finale (A) par activité : {sum(single_a)}/14")
    for name, bl in checks:
        st.markdown(f"- {'❌' if len(bl) == 3 else '✅'} **{name}** — R/A sur : {', '.join(bl) or 'aucun bloc critique'}")
    st.caption("L'avis des risques (6) et l'autorisation (7) sont distincts ; le décaissement (8) relève de la finance, la direction étant informée.")
with r.container(border=True):
    st.markdown("**Délégations d'autorisation** (Réalise / Valide / Est informé)")
    st.dataframe(pd.DataFrame(SEED["delegations"]).rename(columns={"decision": "Décision", "realise": "Réalise", "valide": "Valide", "informe": "Est informé"}),
                 hide_index=True, use_container_width=True)
    st.caption("Les plafonds chiffrés de délégation ne sont pas fournis par le cas : ils seront fixés par la direction (action A01).")
with st.container(border=True):
    st.markdown("**Traduction applicative : droits par rôle (contrôle C03)**")
    st.dataframe(pd.DataFrame([{"Droit": auth.PERMISSION_LABELS[p], **{auth.ROLES[ro]: "✅" if ro in roles else "–" for ro in auth.ROLES}}
                               for p, roles in auth.PERMISSIONS.items()]), hide_index=True, use_container_width=True)
