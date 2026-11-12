"""CRÉDIT HORIZON RISK INTELLIGENCE – application Streamlit (projet EMSI).

Lancement : streamlit run app.py
"""
import time

import streamlit as st

from core import auth, db, ui
from core.advisor import status as ai_status

st.set_page_config(page_title="CRÉDIT HORIZON · Risk Intelligence", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
db.init()
ui.inject_css()


def login_page():
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown(
            """<div style="background:linear-gradient(135deg,#04261c,#063b2b 55%,#0d6047);border-radius:22px;padding:34px 30px;color:#fff;min-height:430px">
            <div style="display:flex;gap:10px;align-items:center"><svg viewBox="0 0 64 64" width="44" height="44"><rect width="64" height="64" rx="14" fill="#0a4d38"/>
            <path d="M12 42 Q32 14 52 42" fill="none" stroke="#10b981" stroke-width="5" stroke-linecap="round"/><path d="M8 46h48" stroke="#d1fae5" stroke-width="4" stroke-linecap="round"/>
            <circle cx="32" cy="24" r="5" fill="#34d399"/></svg><div><b style="font-size:1.25rem;letter-spacing:.03em">CRÉDIT HORIZON</b>
            <div style="font-size:.7rem;letter-spacing:.3em;color:#34d399;font-weight:700">RISK INTELLIGENCE</div></div></div>
            <h2 style="color:#fff;margin-top:46px;font-size:2rem;line-height:1.2">Maîtriser le risque,<br>accompagner la croissance des TPE.</h2>
            <p style="color:#d1fae5;opacity:.85">Registre P × G, cartographie 5 × 5, diagnostic COSO 2013, contrôle interne, gouvernance RACI,
            appétence au risque, assistant IA « Risk Advisor » et tableaux de bord Power BI.</p>
            <p style="color:#a7f3d0;opacity:.7;font-size:.8rem;margin-top:40px">Projet EMSI · Génie Financier – Contrôle interne &amp; gestion des risques financiers</p></div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.subheader("Connexion")
        with st.form("login"):
            email = st.text_input("Adresse e-mail", value=st.session_state.get("prefill", ""))
            pwd = st.text_input("Mot de passe", type="password", value=db.SEED["demo_password"] if st.session_state.get("prefill") else "")
            ok = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
        if ok:
            tries = st.session_state.get("tries", 0)
            if tries >= 5 and time.time() - st.session_state.get("last_try", 0) < 120:
                st.error("Trop de tentatives. Réessayez dans deux minutes.")
            else:
                rows = db.query("select * from users where email = ?", [email.strip().lower()])
                u = rows[0] if rows else None
                if u and u["active"] and auth.check_password(pwd, u["password_hash"]):
                    st.session_state.user = {k: u[k] for k in ("id", "email", "name", "role")}
                    st.session_state.tries = 0
                    db.audit(st.session_state.user, "Connexion", "Session", str(u["id"]))
                    st.rerun()
                else:
                    st.session_state.tries = tries + 1
                    st.session_state.last_try = time.time()
                    st.error("Identifiants incorrects ou compte désactivé.")
        st.markdown(f'<div class="ch-demo"><b>Comptes de démonstration</b> – mot de passe commun : <code>{db.SEED["demo_password"]}</code><br>'
                    "Cliquez sur un rôle pour pré-remplir le formulaire.</div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, u in enumerate(db.SEED["demo_users"]):
            if cols[i % 2].button(auth.ROLES[u["role"]], key=f"demo_{u['role']}", use_container_width=True):
                st.session_state.prefill = u["email"]
                st.rerun()


if not ui.user():
    login_page()
    st.stop()

u = ui.user()
P = lambda path, title, icon, default=False: st.Page(path, title=title, icon=icon, default=default)  # noqa: E731
pages = {
    "Pilotage": [
        P("views/dashboard.py", "Dashboard exécutif", "📊", True),
        P("views/powerbi.py", "Power BI", "📈"),
    ],
    "Risques": [
        P("views/registre.py", "Registre des risques", "📋"),
        P("views/cartographie.py", "Cartographie", "🟥"),
        P("views/dossiers.py", "Dossiers TPE", "📁"),
        P("views/appetence.py", "Appétence au risque", "🎯"),
    ],
    "Contrôle interne": [
        P("views/coso.py", "Diagnostic COSO", "🏛️"),
        P("views/controles.py", "Fiches de contrôle", "🛡️"),
        P("views/suivi.py", "Suivi & anomalies", "🧾"),
        P("views/gouvernance.py", "Gouvernance RACI", "🧭"),
    ],
    "Intelligence": [
        P("views/assistant.py", "Risk Advisor IA", "✨"),
        P("views/rapports.py", "Rapports & exports", "📥"),
    ],
}
if auth.can(u["role"], "audit.view"):
    pages["Intelligence"].append(P("views/administration.py", "Administration", "⚙️"))

st.logo("assets/logo.svg", size="large", icon_image="assets/icon.svg")
nav = st.navigation(pages, expanded=True)
with st.sidebar:
    st.divider()
    st.markdown(f"**{u['name']}**  \n{auth.ROLES[u['role']]}")
    a = ai_status()
    st.caption(f"IA : {'Claude · ' + a['model'] if a['provider'] == 'anthropic' else 'moteur local (aucune clé API)'}")
    if st.button("Se déconnecter", use_container_width=True):
        st.session_state.clear()
        st.rerun()

ui.demo_banner()
ui.flush_toast()
nav.run()
st.caption("CRÉDIT HORIZON RISK INTELLIGENCE · Projet EMSI · Aide à la décision : aucune décision d'octroi automatique.")
