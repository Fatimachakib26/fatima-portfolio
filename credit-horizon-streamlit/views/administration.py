import pandas as pd
import streamlit as st

from core import advisor, auth, db, ui

ui.header("⚙️", "Administration", "Utilisateurs et rôles, état technique de la plateforme et journal d'audit.")
a = advisor.status()
ui.kpis([("Base de données", "SQLite", db.DB_PATH.name, "brand"),
         ("IA générative", "Claude" if a["provider"] == "anthropic" else "Moteur local", a["model"], "green" if a["provider"] == "anthropic" else "amber"),
         ("Utilisateurs", len(db.query("select id from users")), "comptes enregistrés", "brand")])

if ui.can("users.manage"):
    with st.container(border=True):
        st.markdown("**Utilisateurs et rôles**")
        users = pd.DataFrame(db.query("select id, email, name, role, active, is_demo, created_at from users order by id"))
        users["role"] = users.role.map(auth.ROLES)
        users["active"] = users.active.map({1: "Actif", 0: "Désactivé"})
        users["is_demo"] = users.is_demo.map({1: "Démo", 0: ""})
        st.dataframe(users.rename(columns={"email": "E-mail", "name": "Nom", "role": "Rôle", "active": "Statut", "is_demo": "Démo", "created_at": "Créé le"}),
                     hide_index=True, use_container_width=True)
        t1, t2 = st.tabs(["➕ Nouvel utilisateur", "✏️ Modifier un utilisateur"])
        with t1, st.form("new_user", clear_on_submit=True):
            x, y = st.columns(2)
            name, email = x.text_input("Nom complet"), y.text_input("E-mail")
            role = x.selectbox("Rôle", list(auth.ROLES), format_func=auth.ROLES.get)
            pwd = y.text_input("Mot de passe (8 caractères min.)", type="password")
            if st.form_submit_button("Créer", type="primary"):
                email = email.strip().lower()
                if len(name.strip()) < 2 or "@" not in email or len(pwd) < 8:
                    st.error("Nom, e-mail valide et mot de passe de 8 caractères minimum obligatoires.")
                elif db.query("select 1 from users where email=?", [email]):
                    st.error("Un compte existe déjà avec cet e-mail.")
                else:
                    db.execute("insert into users (email,name,role,password_hash,created_at) values (?,?,?,?,?)", (email, name.strip(), role, auth.hash_password(pwd), db.now()))
                    ui.audit("Création", "Utilisateur", email, f"Rôle : {role}")
                    ui.toast_ok(f"Compte {email} créé.")
                    st.rerun()
        with t2:
            rows = db.query("select * from users order by id")
            uid = st.selectbox("Utilisateur", [r["id"] for r in rows], format_func=lambda i: next(f"{r['name']} ({r['email']})" for r in rows if r["id"] == i))
            u = next(r for r in rows if r["id"] == uid)
            me = uid == ui.user()["id"]
            with st.form(f"edit_user_{uid}"):
                name = st.text_input("Nom", u["name"])
                role = st.selectbox("Rôle", list(auth.ROLES), list(auth.ROLES).index(u["role"]), format_func=auth.ROLES.get, disabled=me)
                active = st.checkbox("Compte actif", bool(u["active"]), disabled=me)
                pwd = st.text_input("Nouveau mot de passe (facultatif)", type="password")
                if st.form_submit_button("Enregistrer", type="primary"):
                    if pwd and len(pwd) < 8:
                        st.error("Mot de passe : 8 caractères minimum.")
                    else:
                        db.execute("update users set name=?, role=?, active=? where id=?", (name.strip(), role, int(active), uid))
                        if pwd:
                            db.execute("update users set password_hash=? where id=?", (auth.hash_password(pwd), uid))
                        ui.audit("Modification", "Utilisateur", u["email"])
                        ui.toast_ok("Utilisateur mis à jour.")
                        st.rerun()
            if me:
                st.caption("Vous ne pouvez pas modifier votre propre rôle ni désactiver votre compte.")
    with st.container(border=True):
        st.markdown("**Données de démonstration**")
        st.caption("Restaure les risques, contrôles, COSO, actions, anomalies et dossiers du cas EMSI. Les comptes utilisateurs sont conservés.")
        with st.popover("🔄 Réinitialiser les données de démonstration"):
            st.write("Toutes les modifications métier seront remplacées par les données du rapport.")
            if st.button("Confirmer la réinitialisation", type="primary"):
                db.reset_demo()
                ui.audit("Réinitialisation", "Données de démonstration", "*")
                ui.toast_ok("Données de démonstration restaurées.")
                st.rerun()
else:
    ui.readonly("La gestion des utilisateurs est réservée à l'administrateur. Vous avez accès au journal d'audit.")

with st.container(border=True):
    st.markdown("**Journal d'audit** (200 dernières opérations)")
    st.dataframe(pd.DataFrame(db.query("select at as Date, user_email as Utilisateur, action as Action, entity as Objet, entity_id as Identifiant, details as Détail "
                                       "from audit_log order by id desc limit 200")), hide_index=True, use_container_width=True)
