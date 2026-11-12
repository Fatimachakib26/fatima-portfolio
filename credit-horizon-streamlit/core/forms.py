"""Formulaires CRUD génériques (validation, enregistrement, audit, confirmation de suppression)."""
from __future__ import annotations

from contextlib import nullcontext
from datetime import date

import streamlit as st

from . import db, ui


def field_input(f: dict, value, key: str):
    t, label = f.get("type", "text"), f["label"] + (" *" if f.get("required") else "")
    if t == "textarea":
        return st.text_area(label, value=value or "", key=key, height=90, help=f.get("help"))
    if t == "select":
        opts = f["options"]
        return st.selectbox(label, opts, index=opts.index(value) if value in opts else 0, key=key, help=f.get("help"))
    if t == "slider":
        return st.slider(label, f.get("min", 0), f.get("max", 100), int(value if value not in (None, "") else f.get("min", 0)), key=key, help=f.get("help"))
    if t == "date":
        try:
            v = date.fromisoformat(value) if value else None
        except ValueError:
            v = None
        d = st.date_input(label, value=v, key=key, format="DD/MM/YYYY", help=f.get("help"))
        return d.isoformat() if d else ""
    return st.text_input(label, value=value or "", key=key, help=f.get("help"))


def entity_form(table: str, label: str, fields: list[dict], row: dict | None, id_prefix: str, pad: int, sep: str = "",
                extra_create: dict | None = None, on_saved=None, cols: int = 2):
    """Affiche le formulaire ; retourne l'identifiant enregistré ou None."""
    is_new = row is None
    row = row or {}
    with st.form(f"form_{table}_{row.get('id', 'new')}", clear_on_submit=is_new):
        values = {}
        grid = st.columns(cols)
        i = 0
        for f in fields:
            target = nullcontext() if f.get("full") or f.get("type") == "textarea" else grid[i % cols]
            if not (f.get("full") or f.get("type") == "textarea"):
                i += 1
            with target:
                values[f["key"]] = field_input(f, row.get(f["key"], f.get("default")), f"{table}_{row.get('id', 'new')}_{f['key']}")
        ok = st.form_submit_button("Enregistrer", type="primary")
    if not ok:
        return None
    missing = [f["label"] for f in fields if f.get("required") and not str(values[f["key"]]).strip()]
    if missing:
        st.error("Champs obligatoires manquants : " + ", ".join(missing))
        return None
    values = {k: (v.strip() if isinstance(v, str) else v) for k, v in values.items()}
    if is_new:
        new_id = db.next_id(table, id_prefix, pad, sep)
        db.insert(table, {"id": new_id, **values, **(extra_create or {})})
        ui.audit("Création", label, new_id)
        rid = new_id
    else:
        changed = [k for k in values if str(row.get(k, "")) != str(values[k])]
        db.update(table, row["id"], values)
        ui.audit("Modification", label, row["id"], "Champs modifiés : " + (", ".join(changed) or "aucun"))
        rid = row["id"]
    if on_saved:
        on_saved(rid, values, row)
    ui.toast_ok(f"{label} {rid} enregistré(e).")
    st.rerun()


def delete_button(table: str, label: str, rid: str, on_deleted=None):
    with st.popover(f"🗑️ Supprimer {rid}"):
        st.write(f"Supprimer définitivement **{rid}** ? Cette action est tracée dans le journal d'audit.")
        if st.button("Confirmer la suppression", key=f"del_{table}_{rid}", type="primary"):
            db.delete(table, rid)
            if on_deleted:
                on_deleted(rid)
            ui.audit("Suppression", label, rid)
            ui.toast_ok(f"{label} {rid} supprimé(e).")
            st.rerun()
