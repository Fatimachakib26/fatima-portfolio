import streamlit as st

from core import db, forms, repo, ui
from core.scoring import CATEGORIES, GRAVITY_SCALE, LEVEL_TREATMENT, LEVELS, PROBABILITY_SCALE, level, score

ui.header("📋", "Registre des risques", "Identification, cotation P × G automatique, criticité, responsables, contrôles et recommandations. R01 à R08 proviennent du projet EMSI.")
can_write = ui.can("risks.write")
if not can_write:
    ui.readonly("Consultation seule : la modification du registre est réservée à la fonction risques et à l'administrateur (séparation des tâches).")

r = repo.risks_df()
f1, f2, f3 = st.columns([3, 1.2, 1.2])
q = f1.text_input("Rechercher", placeholder="Identifiant, événement, cause, responsable…")
cats = f2.multiselect("Catégorie", CATEGORIES)
lvls = f3.multiselect("Niveau", LEVELS)
v = r.copy()
if q:
    blob = v[["id", "title", "event", "causes", "consequences", "owner", "control_ids", "recommendation"]].astype(str).agg(" ".join, axis=1).str.lower()
    v = v[blob.str.contains(q.lower(), regex=False)]
if cats:
    v = v[v.category.isin(cats)]
if lvls:
    v = v[v.level.isin(lvls)]
v = v.sort_values(["score", "id"], ascending=[False, True])
v["Démo"] = v.is_demo.map({1: "Démo", 0: ""})
st.dataframe(v[["id", "title", "category", "probability", "gravity", "score", "level", "owner", "control_ids", "recommendation", "Démo"]].rename(columns={
    "id": "ID", "title": "Risque", "category": "Catégorie", "probability": "P", "gravity": "G", "score": "P × G", "level": "Criticité",
    "owner": "Responsable", "control_ids": "Contrôles", "recommendation": "Recommandation"}), hide_index=True, use_container_width=True, height=330,
    column_config={"P × G": st.column_config.ProgressColumn("P × G", min_value=0, max_value=25, format="%d")})
st.caption(f"{len(v)} risque(s) affiché(s)")

FIELDS = [
    {"key": "title", "label": "Intitulé du risque", "required": True, "full": True},
    {"key": "category", "label": "Catégorie", "type": "select", "options": CATEGORIES},
    {"key": "basis", "label": "Fondement", "type": "select", "options": ["Constat", "Hypothèse"]},
    {"key": "event", "label": "Description de l'événement", "type": "textarea", "required": True},
    {"key": "causes", "label": "Causes", "type": "textarea"},
    {"key": "consequences", "label": "Conséquences", "type": "textarea"},
    {"key": "probability", "label": "Probabilité (1 à 5)", "type": "slider", "min": 1, "max": 5, "default": 3,
     "help": " · ".join(f"{k} = {v[0]}" for k, v in PROBABILITY_SCALE.items())},
    {"key": "gravity", "label": "Gravité (1 à 5)", "type": "slider", "min": 1, "max": 5, "default": 3,
     "help": " · ".join(f"{k} = {v[0]}" for k, v in GRAVITY_SCALE.items())},
    {"key": "justification", "label": "Justification de la cotation", "type": "textarea"},
    {"key": "owner", "label": "Responsable", "required": True},
    {"key": "control_ids", "label": "Contrôles associés", "help": "Ex. : C01, C04"},
    {"key": "coso_principles", "label": "Principes COSO", "help": "Ex. : P10, P12"},
    {"key": "recommendation", "label": "Recommandation", "type": "textarea"},
]


def history(rid, values, before):
    p, g = int(values["probability"]), int(values["gravity"])
    db.update("risks", rid, {"updated_at": db.now(), "updated_by": ui.user()["email"]})
    if not before or int(before.get("probability", 0)) != p or int(before.get("gravity", 0)) != g:
        db.execute("insert into risk_history (risk_id,probability,gravity,score,recorded_at) values (?,?,?,?,?)", (rid, p, g, p * g, db.now()))


tab_detail, tab_edit = st.tabs(["🔎 Fiche détaillée", "✏️ Ajouter / modifier"])
with tab_detail:
    if not r.empty:
        rid = st.selectbox("Risque", list(r.id), format_func=lambda i: f"{i} – {r.set_index('id').title[i]}", key="detail_sel")
        x = r.set_index("id").loc[rid]
        st.markdown(ui.level_pill(x.level, int(x.score)) + f" &nbsp; <span class='ch-badge'>{x.category}</span> <span class='ch-badge'>{x.basis}</span>"
                    + (" <span class='ch-badge' style='background:#ede9fe;color:#5b21b6'>Démo</span>" if x.is_demo else ""), unsafe_allow_html=True)
        a, b, c = st.columns(3)
        a.markdown(f"**Événement redouté**  \n{x.event}")
        b.markdown(f"**Causes**  \n{x.causes or '–'}")
        c.markdown(f"**Conséquences**  \n{x.consequences or '–'}")
        a.markdown(f"**Cotation**  \nP = {x.probability} ({PROBABILITY_SCALE[x.probability][0]}) × G = {x.gravity} ({GRAVITY_SCALE[x.gravity][0]}) = **{x.score}**")
        b.markdown(f"**Justification**  \n{x.justification or '–'}")
        c.markdown(f"**Traitement attendu**  \n{LEVEL_TREATMENT[x.level]}")
        st.markdown(f"**Recommandation :** {x.recommendation or '–'}  \n**Responsable :** {x.owner} · **Contrôles :** {x.control_ids or '–'} · **COSO :** {x.coso_principles or '–'}")
        hist = repo.table_df("risk_history", "recorded_at")
        hist = hist[hist.risk_id == rid]
        if len(hist) > 1:
            st.line_chart(hist.set_index(hist.recorded_at.str.slice(0, 10)).score, height=160)
        if st.button("✨ Analyser ce risque avec Risk Advisor"):
            st.session_state.advisor_prompt = f"Analyse le risque {rid} : explique son score P × G, relie-le aux principes COSO et propose une recommandation complète."
            st.switch_page("views/assistant.py")
with tab_edit:
    if not can_write:
        st.info("Votre rôle ne permet pas de modifier le registre.")
    else:
        mode = st.radio("Action", ["Nouveau risque", "Modifier un risque existant"], horizontal=True)
        if mode == "Nouveau risque":
            forms.entity_form("risks", "Risque", FIELDS, None, "R", 2, extra_create={"is_demo": 0}, on_saved=history)
        elif not r.empty:
            rid = st.selectbox("Risque à modifier", list(r.id), format_func=lambda i: f"{i} – {r.set_index('id').title[i]}")
            row = db.query("select * from risks where id=?", [rid])[0]
            st.markdown("Score actuel : " + ui.level_pill(level(score(row["probability"], row["gravity"])), score(row["probability"], row["gravity"])), unsafe_allow_html=True)
            forms.entity_form("risks", "Risque", FIELDS, row, "R", 2, on_saved=history)
            forms.delete_button("risks", "Risque", rid, on_deleted=lambda i: db.execute("delete from risk_history where risk_id=?", [i]))
