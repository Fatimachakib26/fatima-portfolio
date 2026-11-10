"""Authentification simple pour la démonstration (PBKDF2-SHA256 + sel, verrouillage après 5 échecs).

Comptes : définis dans .streamlit/secrets.toml (section [users]) si présent,
sinon comptes de démonstration ci-dessous. Ne pas utiliser ces comptes en production.
"""
from __future__ import annotations

import hashlib
import hmac
import time

import streamlit as st

ITERATIONS = 200_000
MAX_ATTEMPTS = 5
LOCK_SECONDS = 60


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()


# Comptes de démonstration (mots de passe : voir README)
_DEMO_USERS = {
    "admin": {"name": "Administrateur", "role": "admin", "salt": "tg2-admin",
              "hash": hash_password("Tanger2026!", "tg2-admin")},
    "jury": {"name": "Membre du jury", "role": "lecteur", "salt": "tg2-jury",
             "hash": hash_password("Jury2026", "tg2-jury")},
}


def _users() -> dict:
    try:
        if "users" in st.secrets:
            return {u: dict(v) for u, v in st.secrets["users"].items()}
    except Exception:
        pass
    return _DEMO_USERS


def check(username: str, password: str) -> dict | None:
    u = _users().get(username.strip().lower())
    if not u:
        hash_password(password, "dummy")  # temps constant
        return None
    if hmac.compare_digest(hash_password(password, u["salt"]), u["hash"]):
        return {"username": username.strip().lower(), "name": u.get("name", username),
                "role": u.get("role", "lecteur")}
    return None


def login_form() -> bool:
    """Affiche l'écran de connexion. Renvoie True si l'utilisateur est authentifié."""
    if st.session_state.get("user"):
        return True
    ss = st.session_state
    ss.setdefault("attempts", 0)
    ss.setdefault("locked_until", 0.0)

    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown(
            "<div class='login-head'><div class='logo'>T2</div>"
            "<h2>Tanger II — Simulateur de montage financier</h2>"
            "<p>Usine de composants automobiles · Détroit Plasturgie Automobile (cas fictif)</p></div>",
            unsafe_allow_html=True,
        )
        locked = time.time() < ss.locked_until
        with st.form("login", clear_on_submit=False):
            user = st.text_input("Identifiant", placeholder="admin")
            pwd = st.text_input("Mot de passe", type="password")
            ok = st.form_submit_button("Se connecter", width="stretch", type="primary",
                                       disabled=locked)
        if locked:
            st.error(f"Trop de tentatives. Réessayez dans {int(ss.locked_until - time.time())} s.")
        elif ok:
            info = check(user, pwd)
            if info:
                ss.user = info
                ss.attempts = 0
                st.rerun()
            else:
                ss.attempts += 1
                left = MAX_ATTEMPTS - ss.attempts
                if left <= 0:
                    ss.locked_until = time.time() + LOCK_SECONDS
                    ss.attempts = 0
                    st.error("Compte verrouillé pendant 60 secondes.")
                else:
                    st.error(f"Identifiant ou mot de passe incorrect ({left} essai(s) restant(s)).")
        with st.expander("Comptes de démonstration"):
            st.markdown("- **admin** / `Tanger2026!` — accès complet (optimiseur, export)\n"
                        "- **jury** / `Jury2026` — lecture et simulations")
    return False


def logout():
    for k in ("user",):
        st.session_state.pop(k, None)
    st.rerun()
