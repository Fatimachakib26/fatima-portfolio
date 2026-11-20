"""Accès sûr à l'état de session : chaque page peut s'exécuter seule
(lien direct, rechargement) sans dépendre de l'ordre d'exécution d'app.py."""
from __future__ import annotations

import streamlit as st

from config import AppParams


def get_params() -> AppParams:
    st.session_state.setdefault("data_status", {"state": "idle", "fetched_at": None})
    return st.session_state.setdefault("params", AppParams())


def get_market():
    if "market" not in st.session_state:
        from components.data_service import load_market_data

        st.session_state["market"] = load_market_data(get_params())
    return st.session_state["market"]
