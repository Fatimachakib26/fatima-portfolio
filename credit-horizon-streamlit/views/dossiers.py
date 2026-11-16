import json
from datetime import date

import pandas as pd
import streamlit as st

from core import advisor, db, repo, ui
from core.analysis import CHECKLIST, GUARANTEE_TYPES, LEGAL_FORMS, PRODUCTS, analyze_dossier, is_required

ui.header("📁", "Analyse intelligente des dossiers TPE",
          "Complétude documentaire (contrôle C01), informations manquantes, incohérences, points de vigilance et synthèse. "
          "La plateforme ne prend aucune décision d'octroi.")
can_write = ui.can("dossiers.write")
dossiers = repo.dossiers()

with st.container(border=True):
    st.markdown("**Dossiers enregistrés**")
    if dossiers:
        st.dataframe(pd.DataFrame([{
            "Référence": d["id"], "Entreprise": d["company"].get("name"), "Secteur": d["company"].get("sector"),
            "Produit": d["request"].get("product"), "Montant (MAD)": pd.to_numeric(d["request"].get("amount"), errors="coerce"),
            "Durée (mois)": d["request"].get("duration_months"), "Complétude": d["analysis"]["completeness"]["rate"],
            "Incohérences": len(d["analysis"]["inconsistencies"]), "Statut de l'analyse": d["status"], "Saisi par": d["created_by"],
            "Démo": "Démo" if d["is_demo"] else ""} for d in dossiers]), hide_index=True, use_container_width=True,
            column_config={"Complétude": st.column_config.ProgressColumn("Complétude", min_value=0, max_value=100, format="%d %%"),
                           "Montant (MAD)": st.column_config.NumberColumn(format="%d")})

options = [d["id"] for d in dossiers] + (["➕ Nouveau dossier"] if can_write else [])
if not options:
    st.stop()
sel = st.selectbox("Ouvrir un dossier", options, format_func=lambda i: i if i.startswith("➕") else f"{i} – {next(d for d in dossiers if d['id'] == i)['company'].get('name')}")
existing = None if sel.startswith("➕") else next(d for d in dossiers if d["id"] == sel)
if not can_write:
    ui.readonly("Consultation seule : la saisie des dossiers est réservée aux commerciaux, analystes risques et administrateurs.")

src = existing or {"company": {"legal_form": "SARL"}, "request": {"product": PRODUCTS[0]}, "financials": {}, "documents": {}, "guarantees": {"type": "Aucune"}, "observations": ""}
k = f"d_{sel}_"


def T(label, part, key, **kw):
    return st.text_input(label, value=str(src[part].get(key) or ""), key=k + part + key, disabled=not can_write, **kw)


def N(label, part, key, help=None):
    v = src[part].get(key)
    raw = st.text_input(label, value="" if v in (None, "") else str(v), key=k + part + key, disabled=not can_write, help=help)
    return raw.replace(" ", "").replace(",", ".")


def S(label, part, key, options):
    v = src[part].get(key)
    return st.selectbox(label, options, index=options.index(v) if v in options else 0, key=k + part + key, disabled=not can_write)


form_col, res_col = st.columns([3, 2], gap="large")
with form_col:
    with st.container(border=True):
        st.markdown("**1. Informations de l'entreprise**")
        a, b, c = st.columns(3)
        company = {
            "name": a.text_input("Raison sociale *", value=src["company"].get("name", ""), key=k + "name", disabled=not can_write),
            "legal_form": b.selectbox("Forme juridique", LEGAL_FORMS, index=LEGAL_FORMS.index(src["company"].get("legal_form", "SARL")) if src["company"].get("legal_form") in LEGAL_FORMS else 0, key=k + "lf", disabled=not can_write),
        }
        cd = src["company"].get("creation_date")
        try:
            cdv = date.fromisoformat(cd) if cd else None
        except ValueError:
            cdv = None
        d_ = c.date_input("Date de création", value=cdv, key=k + "cd", format="DD/MM/YYYY", disabled=not can_write, min_value=date(1950, 1, 1))
        company["creation_date"] = d_.isoformat() if d_ else ""
        with a:
            company["rc_number"] = T("N° registre de commerce", "company", "rc_number")
            company["manager_name"] = T("Dirigeant", "company", "manager_name")
        with b:
            company["ice"] = T("ICE", "company", "ice")
            company["employees"] = N("Effectif", "company", "employees")
        with c:
            company["city"] = T("Ville", "company", "city")
            company["name_on_documents"] = T("Raison sociale figurant sur les pièces", "company", "name_on_documents", help="Sert au contrôle de concordance")
    with st.container(border=True):
        st.markdown("**2. Activité et financement demandé**")
        a, b, c = st.columns(3)
        with a:
            company["sector"] = T("Secteur d'activité", "company", "sector")
            request = {"product": S("Type de financement", "request", "product", PRODUCTS)}
        with b:
            request["amount"] = N("Montant demandé (MAD) *", "request", "amount")
        with c:
            request["duration_months"] = N("Durée (mois) *", "request", "duration_months")
        company["activity"] = T("Description de l'activité", "company", "activity")
        request["purpose"] = T("Objet du financement", "request", "purpose")
    with st.container(border=True):
        st.markdown("**3. Informations financières (MAD)**")
        a, b, c, d4 = st.columns(4)
        with a:
            fin = {"fiscal_year": T("Exercice", "financials", "fiscal_year"), "net_result": N("Résultat net", "financials", "net_result")}
        with b:
            fin["revenue_n"] = N("CA exercice N", "financials", "revenue_n")
            fin["equity"] = N("Fonds propres", "financials", "equity")
        with c:
            fin["revenue_n1"] = N("CA exercice N-1", "financials", "revenue_n1")
            fin["existing_debt"] = N("Dettes financières existantes", "financials", "existing_debt")
        with d4:
            fin["revenue_bank"] = N("CA selon relevés bancaires", "financials", "revenue_bank", help="Contrôle de cohérence")
            fin["existing_monthly_installments"] = N("Mensualités existantes", "financials", "existing_monthly_installments")
    with st.container(border=True):
        st.markdown("**4. Pièces justificatives – grille de vérification (C01, tableau 5.5)**")
        docs = {}
        probe = {"request": request, "guarantees": {"type": st.session_state.get(k + "gtype", src["guarantees"].get("type", "Aucune"))}}
        for key, label, scope, stage in CHECKLIST:
            req = stage == "avant_avis" and is_required(key, probe)
            hint = "exigé avant la décision" if stage == "avant_decision" else ("obligatoire avant avis" if req else "non requis pour ce dossier")
            cur = src["documents"].get(key, "")
            labels = {"oui": "Oui", "non": "Non", "na": "N/A", "": "—"}
            choice = st.radio(f"{label}  \n:gray[{scope} · {hint}]", ["oui", "non", "na", ""], index=["oui", "non", "na", ""].index(cur if cur in labels else ""),
                              format_func=labels.get, horizontal=True, key=k + "doc" + key, disabled=not can_write)
            docs[key] = choice
    with st.container(border=True):
        st.markdown("**5. Garanties**")
        a, b, c = st.columns(3)
        gt = src["guarantees"].get("type", "Aucune")
        guarantees = {"type": a.selectbox("Nature de la garantie", GUARANTEE_TYPES, index=GUARANTEE_TYPES.index(gt) if gt in GUARANTEE_TYPES else 0, key=k + "gtype", disabled=not can_write)}
        with b:
            guarantees["value"] = N("Valeur estimée (MAD)", "guarantees", "value")
        with c:
            guarantees["description"] = T("Description", "guarantees", "description")
    with st.container(border=True):
        st.markdown("**6. Observations de l'analyste**")
        observations = st.text_area("Appréciation motivée, éléments vérifiés, points restant à confirmer", value=src.get("observations", ""), key=k + "obs", disabled=not can_write)

payload = {"company": company, "request": request, "financials": fin, "documents": docs, "guarantees": guarantees, "observations": observations}
an = analyze_dossier(payload)

with res_col:
    with st.container(border=True):
        st.markdown("**Résultat de l'analyse** · aide à l'analyse – aucune décision d'octroi")
        (st.error if an["blocking"] else st.success)(an["status"])
        cpl = an["completeness"]
        st.progress(cpl["rate"] / 100, text=f"Complétude documentaire : {cpl['present']}/{cpl['required']} ({cpl['rate']} %)")
        icon = {"alerte": "🔴", "attention": "🟠", "info": "🔵"}
        if cpl["missing_docs"]:
            st.markdown("**Pièces manquantes**\n" + "\n".join(f"- 🔴 {m}" for m in cpl["missing_docs"]))
        for title, key in (("Incohérences", "inconsistencies"), ("Informations manquantes", "missing_info"), ("Points de vigilance", "vigilance")):
            if an[key]:
                st.markdown(f"**{title} ({len(an[key])})**\n" + "\n".join(f"- {icon[i['severity']]} {i['message']} _({i['risk']})_" for i in an[key]))
        if cpl["pending_before_decision"]:
            st.caption("À produire avant décision : " + " ; ".join(cpl["pending_before_decision"]))
        if an["ratios"]:
            st.markdown("**Ratios calculés (seuils indicatifs)**")
            st.dataframe(pd.DataFrame(an["ratios"], columns=["Ratio", "Valeur"]), hide_index=True, use_container_width=True)
        if an["linked_risks"]:
            st.markdown("Risques concernés : " + " ".join(f"<span class='ch-badge'>{x}</span>" for x in an["linked_risks"]), unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Synthèse d'analyse**")
        st.write(an["synthesis"])
        st.markdown(f"<div class='ch-warn'>{an['disclaimer']}</div>", unsafe_allow_html=True)

    if can_write:
        c1, c2 = st.columns(2)
        if c1.button("💾 Enregistrer et analyser", type="primary", use_container_width=True):
            if not company["name"].strip():
                st.error("La raison sociale est obligatoire.")
            else:
                pj, aj = json.dumps(payload, ensure_ascii=False), json.dumps(an, ensure_ascii=False)
                if existing:
                    db.execute("update dossiers set payload=?, analysis=?, status=?, updated_at=? where id=?", (pj, aj, an["status"], db.now(), existing["id"]))
                    ui.audit("Modification + réanalyse", "Dossier TPE", existing["id"], an["status"])
                    ui.toast_ok(f"Dossier {existing['id']} enregistré : {an['status']}.")
                else:
                    nid = db.next_id("dossiers", f"TPE-{date.today().year}", 3, "-")
                    db.insert("dossiers", {"id": nid, "payload": pj, "analysis": aj, "status": an["status"], "created_by": ui.user()["name"],
                                           "is_demo": 0, "created_at": db.now(), "updated_at": db.now()})
                    ui.audit("Création + analyse", "Dossier TPE", nid, an["status"])
                    ui.toast_ok(f"Dossier {nid} créé : {an['status']}.")
                st.rerun()
        if existing and c2.button("🗑️ Supprimer", use_container_width=True):
            st.session_state["confirm_del_dossier"] = existing["id"]
        if st.session_state.get("confirm_del_dossier") == sel:
            st.warning(f"Supprimer définitivement le dossier {sel} ?")
            y, n = st.columns(2)
            if y.button("Confirmer", type="primary"):
                db.delete("dossiers", sel)
                ui.audit("Suppression", "Dossier TPE", sel)
                st.session_state.pop("confirm_del_dossier")
                ui.toast_ok(f"Dossier {sel} supprimé.")
                st.rerun()
            if n.button("Annuler"):
                st.session_state.pop("confirm_del_dossier")
                st.rerun()
    if existing and ui.can("anomalies.create") and an["blocking"]:
        if st.button("🐞 Inscrire l'anomalie au registre (C04)", use_container_width=True):
            nature = ("Dossier incomplet – pièces manquantes : " + " ; ".join(cpl["missing_docs"])) if cpl["missing_docs"] else ("Incohérence : " + an["inconsistencies"][0]["message"])
            aid = db.next_id("anomalies", "AN", 3, "-")
            db.insert("anomalies", {"id": aid, "detected_on": date.today().isoformat(), "dossier_ref": existing["id"], "nature": nature[:1900],
                                    "severity": "Majeure" if any(i["severity"] == "alerte" for i in an["inconsistencies"]) else "Significative",
                                    "risk_id": "R01", "control_id": "C01", "owner": "Fonction risques", "due_on": "", "status": "Ouverte",
                                    "escalation": 1, "resolution": "", "declared_by": ui.user()["name"], "is_demo": 0})
            ui.audit("Création", "Anomalie", aid, f"Depuis le dossier {existing['id']}")
            ui.toast_ok(f"Anomalie {aid} inscrite au registre.")
            st.rerun()
    if existing and st.button("✨ Synthèse rédigée par Risk Advisor (IA)", use_container_width=True):
        prompt = (f"Rédige une synthèse d'analyse professionnelle du dossier {existing['id']} : complétude documentaire, informations manquantes, incohérences, "
                  "points de vigilance, risques du registre concernés et contrôles applicables, puis les diligences à mener avant l'avis de la fonction risques. "
                  "Rappelle qu'aucune décision d'octroi ne peut être prise par l'outil.")
        with st.container(border=True):
            st.write_stream(advisor.ask([{"role": "user", "content": prompt}], repo.snapshot(), focus=existing["id"]))
