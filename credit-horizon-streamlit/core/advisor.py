"""Risk Advisor : assistant IA (Claude via l'API Anthropic) + moteur d'analyse local de secours.

La clé API reste côté serveur (variable d'environnement ou secrets Streamlit), jamais dans le navigateur.
L'assistant reçoit les données réelles de la plateforme et ne doit rien inventer.
"""
from __future__ import annotations

import os
import unicodedata
from typing import Iterator

from . import repo
from .db import SEED
from .scoring import GRAVITY_SCALE, LEVEL_TREATMENT, PROBABILITY_SCALE

RULES = """Tu es « Risk Advisor », l'assistant IA de la plateforme CRÉDIT HORIZON RISK INTELLIGENCE.
Tu te comportes comme un consultant senior en gestion des risques financiers et en contrôle interne (COSO 2013), au service d'un organisme de financement des TPE.

RÈGLES IMPÉRATIVES
1. Réponds toujours en français professionnel, clair et structuré (titres Markdown, listes, tableaux si utile).
2. Utilise EXCLUSIVEMENT les données de la plateforme fournies ci-dessous. Cite les identifiants (R01, C02, P10, REC03, A04, AN-002, TPE-2026-001…).
3. N'invente JAMAIS de chiffres, seuils, montants, noms ou faits. Si une information manque, dis-le (« information non disponible dans la plateforme »). Distingue « constat » et « hypothèse à vérifier ».
4. Ne prends JAMAIS de décision d'octroi ou de refus de crédit. Tu fournis une aide à l'analyse ; la décision relève de l'instance délégataire après avis indépendant de la fonction risques (contrôle C02).
5. Toute recommandation suit OBLIGATOIREMENT la chaîne : **RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI** (tableau Markdown à 5 colonnes).
6. Criticité = Probabilité × Gravité (1 à 25). Seuils : 1–4 Faible ; 5–9 Modéré ; 10–15 Élevé ; 16–25 Critique.
7. Reste concis et termine par des prochaines étapes concrètes.
8. Les données sont celles d'un cas académique fictif (projet EMSI)."""

DEFAULT_MODEL = "claude-sonnet-5-5"


def _secret(name: str) -> str | None:
    v = os.environ.get(name)
    if v:
        return v
    try:
        import streamlit as st
        return st.secrets.get(name)  # type: ignore[no-any-return]
    except Exception:
        return None


def status() -> dict:
    key = _secret("ANTHROPIC_API_KEY")
    return {"provider": "anthropic" if key else "offline", "model": (_secret("ANTHROPIC_MODEL") or DEFAULT_MODEL) if key else "moteur local"}


def build_context(s: dict, focus: str | None = None) -> str:
    k = repo.kpis(s)
    L = ["# DONNÉES DE LA PLATEFORME",
         f"Indicateurs : {k['total']} risques ({k['critical']} critiques, {k['high']} élevés), score moyen {k['avg_score']:.1f} ; "
         f"{k['operational_controls']}/{k['total_controls']} contrôles opérationnels ; {k['covered_risks']}/{k['total']} risques couverts ; "
         f"plan d'action {k['action_progress']} % ({k['pending_actions']} actions ouvertes) ; anomalies ouvertes {k['open_anomalies']} dont {k['overdue_anomalies']} en retard ; "
         f"principes COSO déficients {k['deficient_principles']}/17 ; maturité {k['avg_maturity']:.1f}/5 ; dossiers TPE {k['dossiers']} dont {k['dossiers_blocked']} suspendus.",
         "Échelle P : " + " | ".join(f"{n}={v[0]}" for n, v in PROBABILITY_SCALE.items()),
         "Échelle G : " + " | ".join(f"{n}={v[0]}" for n, v in GRAVITY_SCALE.items()),
         "## Registre des risques"]
    for r in s["risks"].to_dict("records"):
        L.append(f"- {r['id']} {r['title']} | {r['category']} | P={r['probability']} G={r['gravity']} score {r['score']} ({r['level']}) | {r['basis']}\n"
                 f"  Événement : {r['event']} | Causes : {r['causes']} | Conséquences : {r['consequences']} | Justification : {r['justification']}\n"
                 f"  Responsable : {r['owner']} | Contrôles : {r['control_ids']} | COSO : {r['coso_principles']} | Recommandation : {r['recommendation']}")
    L.append("## Contrôles")
    for c in s["controls"].to_dict("records"):
        L.append(f"- {c['id']} {c['name']} ({c['nature']}, {c['status']}) risques {c['risk_ids']} ; objectif {c['objective']} ; responsable {c['owner']} ; "
                 f"fréquence {c['frequency']} ; preuve {c['evidence']} ; indicateur {c['indicator']}")
    L.append("## COSO – composantes")
    for c in s["components"].to_dict("records"):
        L.append(f"- {c['id']}. {c['name']} ({c['principles']}, maturité {c['maturity']}/5) : constats {c['findings']} ; lacunes {c['gaps']} ; risques {c['risk_ids']} ; "
                 f"recommandations {c['recommendations']} ; responsables {c['owner']} ; indicateurs {c['indicators']}")
    L.append("## COSO – principes")
    for p in s["principles"].to_dict("records"):
        L.append(f"- {p['id']} {p['title']} [{p['nature']} ; {p['assessment']}] {p['diagnostic']} ; risques {p['risk_ids']}")
    L.append("## Recommandations")
    for r in s["recommendations"].to_dict("records"):
        L.append(f"- {r['id']} ({r['status']}) {r['risk_id']} → {r['coso_gap']} → {r['action']} → {r['owner']} → {r['indicator']}")
    L.append("## Plan d'action")
    for a in s["actions"].to_dict("records"):
        L.append(f"- {a['id']} [{a['priority']}] {a['title']} — {a['owner']} ; {a['due']} ; {a['status']} ({a['progress']} %) ; risques {a['risk_ids']}")
    L.append("## Anomalies")
    for a in s["anomalies"].to_dict("records"):
        L.append(f"- {a['id']} {a['detected_on']} ({a['dossier_ref']}) {a['nature']} — {a['severity']} ; risque {a['risk_id']} ; contrôle {a['control_id']} ; "
                 f"{a['status']} ; escalade N{a['escalation']} ; échéance {a['due_on']}")
    L.append("## Dossiers TPE")
    for d in s["dossiers"]:
        an = d["analysis"]
        L.append(f"- {d['id']}{' (EN COURS D’EXAMEN)' if d['id'] == focus else ''} {d['company'].get('name')} : {d['request'].get('product')} "
                 f"{d['request'].get('amount')} MAD / {d['request'].get('duration_months')} mois ; {d['status']} ; complétude {an['completeness']['rate']} % ; "
                 f"pièces manquantes : {'; '.join(an['completeness']['missing_docs']) or 'aucune'} ; incohérences : {' | '.join(i['message'] for i in an['inconsistencies']) or 'aucune'} ; "
                 f"vigilance : {' | '.join(i['message'] for i in an['vigilance']) or 'aucune'}")
    L.append("## RACI (R réalise, A valide, C consulté, I informé)")
    actors = SEED["raci_actors"]
    for a in SEED["raci_activities"]:
        L.append(f"- {a['n']}. {a['activity']} : " + ", ".join(f"{x['label']}={a['roles'][x['key']]}" for x in actors))
    L.append("## Charte d'appétence : " + " ; ".join(SEED["charter_principles"]))
    for lv in SEED["appetite_levels"]:
        L.append(f"- {lv['title']} : {lv['description']}")
    L.append("## Hypothèses : " + " ; ".join(f"{h['id']} {h['text']}" for h in SEED["hypotheses"]))
    return "\n".join(L)


def ask(messages: list[dict], s: dict, focus: str | None = None) -> Iterator[str]:
    """Génère la réponse au fil de l'eau. Repli automatique sur le moteur local si l'API est indisponible."""
    question = messages[-1]["content"]
    key = _secret("ANTHROPIC_API_KEY")
    if not key:
        yield offline_answer(s, question, focus)
        return
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        system = RULES + "\n\n" + build_context(s, focus)
        with client.messages.stream(model=_secret("ANTHROPIC_MODEL") or DEFAULT_MODEL, max_tokens=3000, system=system,
                                    messages=[{"role": m["role"], "content": m["content"]} for m in messages[-20:]]) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:  # réseau, clé invalide, quota…
        yield (f"\n\n> ⚠️ Service d'IA indisponible ({type(e).__name__}). Réponse du moteur d'analyse local, "
               "à partir des données réelles de la plateforme.\n\n" + offline_answer(s, question, focus))


# ------------------------------------------------------------------ moteur local
def _n(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _chain(s: dict, ids: list[str] | None = None) -> str:
    risks = {r["id"]: r for r in s["risks"].to_dict("records")}
    rows = ["| RISQUE | LACUNE COSO | ACTION CORRECTIVE | RESPONSABLE | INDICATEUR DE SUIVI |", "|---|---|---|---|---|"]
    done = set()
    for r in s["recommendations"].to_dict("records"):
        if ids and r["risk_id"] not in ids:
            continue
        rk = risks.get(r["risk_id"], {})
        rows.append(f"| **{r['risk_id']}** {rk.get('title', '')} ({rk.get('score', '–')}, {rk.get('level', '–')}) | {r['coso_gap']} | {r['action']} | {r['owner']} | {r['indicator']} |")
        done.add(r["risk_id"])
    for rid, rk in risks.items():
        if (ids and rid not in ids) or rid in done:
            continue
        ctrls = [c for c in s["controls"].to_dict("records") if rid in repo.split_ids(c["risk_ids"])]
        ind = " ; ".join(f"{c['id']} : {c['indicator']}" for c in ctrls) or "Indicateur à définir (aucun contrôle associé)"
        rows.append(f"| **{rid}** {rk['title']} ({rk['score']}, {rk['level']}) | {rk['coso_principles'] or 'Principe COSO à renseigner'} | "
                    f"{rk['recommendation'] or 'Recommandation à définir'} | {rk['owner'] or 'à désigner'} | {ind} |")
    return "\n".join(rows) if len(rows) > 2 else "_Aucune donnée correspondante._"


def offline_answer(s: dict, question: str, focus: str | None = None) -> str:
    import re
    q = _n(question)
    has = lambda *w: any(x in q for x in w)  # noqa: E731
    k = repo.kpis(s)
    risks = sorted(s["risks"].to_dict("records"), key=lambda r: (-r["score"], r["id"]))
    ids = [i for i in dict.fromkeys(re.findall(r"\bR\d{2,3}\b", question.upper())) if any(r["id"] == i for r in risks)]
    dos = set(re.findall(r"TPE-\d{4}-\d{3}", question.upper()))
    if focus:
        dos.add(focus)
    out: list[str] = []

    if dos or has("dossier", "documentaire", "incoheren", "piece"):
        out.append("## Analyse documentaire des dossiers TPE")
        for d in [d for d in s["dossiers"] if not dos or d["id"] in dos]:
            a = d["analysis"]
            out.append(f"### {d['id']} – {d['company'].get('name')}\n- **Statut** : {d['status']} · **Complétude** : {a['completeness']['rate']} %")
            if a["completeness"]["missing_docs"]:
                out.append("- **Pièces manquantes** : " + " ; ".join(a["completeness"]["missing_docs"]))
            for title, key in (("Incohérences", "inconsistencies"), ("Points de vigilance", "vigilance"), ("Informations manquantes", "missing_info")):
                if a[key]:
                    out.append(f"- **{title}** :\n" + "\n".join(f"  - {i['message']} _({i['risk']})_" for i in a[key]))
        out.append("> Aide à l'analyse uniquement : aucune décision d'octroi n'est formulée (circuit avis risques → instance délégataire, C02).")

    for rid in ids:
        r = next(x for x in risks if x["id"] == rid)
        p, g = PROBABILITY_SCALE[r["probability"]], GRAVITY_SCALE[r["gravity"]]
        out.append(f"### {r['id']} – {r['title']}\n- **Catégorie** : {r['category']} · **Fondement** : {r['basis']}\n- **Événement** : {r['event']}\n"
                   f"- **Causes** : {r['causes']}\n- **Conséquences** : {r['consequences']}\n\n"
                   f"**Score P × G** : P = {r['probability']} ({p[0]} – {p[1]}) × G = {r['gravity']} ({g[0]} – {g[1]}) = **{r['score']}** → **{r['level']}**. "
                   f"Traitement attendu : {LEVEL_TREATMENT[r['level']]}\n\nJustification : {r['justification']}")
    if ids:
        out.append("#### Chaîne de recommandation\n" + _chain(s, ids))

    if not ids and has("prioritaire", "priorite", "top", "critique", "registre", "analyse les risques", "analyser"):
        out.append("## Risques prioritaires (criticité P × G)\n| Rang | Risque | P | G | Score | Niveau | Responsable |\n|---|---|---|---|---|---|---|\n" +
                   "\n".join(f"| {i} | **{r['id']}** {r['title']} | {r['probability']} | {r['gravity']} | **{r['score']}** | {r['level']} | {r['owner']} |"
                             for i, r in enumerate(risks[:5], 1)))
        out.append(f"**Lecture** : {k['total']} risques dont {k['critical']} critiques ({', '.join(r['id'] for r in risks if r['level'] == 'Critique') or 'aucun'}) "
                   f"et {k['high']} élevés ; score moyen {k['avg_score']:.1f}. {k['covered_risks']}/{k['total']} risques couverts par un contrôle.")
    if not ids and has("score", "cotation", "explique", "p x g", "p × g"):
        out.append("## Explication des scores P × G\n| Risque | P | G | Score | Niveau | Justification |\n|---|---|---|---|---|---|\n" +
                   "\n".join(f"| {r['id']} | {r['probability']} | {r['gravity']} | {r['score']} | {r['level']} | {r['justification']} |" for r in risks))
    if has("coso", "principe"):
        pr = {p["id"]: p for p in s["principles"].to_dict("records")}
        comp = {c["id"]: c["name"] for c in s["components"].to_dict("records")}
        rows = []
        for r in [x for x in risks if not ids or x["id"] in ids]:
            ps = [pr[p] for p in repo.split_ids(r["coso_principles"]) if p in pr]
            rows.append(f"| {r['id']} | {' ; '.join(p['id'] + ' ' + p['title'] for p in ps) or 'non renseigné'} | "
                        f"{' ; '.join(dict.fromkeys(comp[p['component_id']] for p in ps)) or '–'} | {' ; '.join(p['id'] + ' : ' + p['assessment'] for p in ps) or '–'} |")
        out.append("## Rattachement aux principes COSO 2013\n| Risque | Principes | Composantes | Appréciation |\n|---|---|---|---|\n" + "\n".join(rows))
    if has("controle"):
        rows = []
        for r in [x for x in risks if not ids or x["id"] in ids]:
            cs = [c for c in s["controls"].to_dict("records") if r["id"] in repo.split_ids(c["risk_ids"])]
            rows.append(f"| {r['id']} | {' ; '.join(c['id'] + ' ' + c['name'] for c in cs) or '**Aucun – à concevoir**'} | {' ; '.join(c['status'] for c in cs) or '–'} | {len(cs)} |")
        out.append("## Contrôles internes\n| Risque | Contrôles | Statut | Nombre |\n|---|---|---|---|\n" + "\n".join(rows) +
                   "\n\nUn risque couvert par un seul contrôle constitue un point de dépendance à surveiller en priorité.")
    if has("recommand", "lacune"):
        out.append("## Recommandations\n" + _chain(s, ids or None))
    if has("plan", "action"):
        out.append(f"## Plan d'action (avancement moyen {k['action_progress']} %)\n| Priorité | Action | Responsable | Échéance | Statut | % |\n|---|---|---|---|---|---|\n" +
                   "\n".join(f"| {a['priority']} | {a['id']} {a['title']} | {a['owner']} | {a['due']} | {a['status']} | {a['progress']} |" for a in s["actions"].to_dict("records")))
    if has("anomal", "incident", "derogation"):
        out.append(f"## Anomalies\n{k['open_anomalies']} ouverte(s) dont {k['overdue_anomalies']} en retard ; {k['closed_anomalies']} clôturée(s).\n\n"
                   "| Id | Nature | Gravité | Risque | Statut | Escalade |\n|---|---|---|---|---|---|\n" +
                   "\n".join(f"| {a['id']} | {a['nature']} | {a['severity']} | {a['risk_id']} | {a['status']} | N{a['escalation']} |" for a in s["anomalies"].to_dict("records")))
    if not out or has("synthese", "rapport", "resume", "bilan"):
        top = risks[:3]
        out.append(f"## Synthèse exécutive\n- **Exposition** : {k['total']} risques ({k['critical']} critiques, {k['high']} élevés) ; priorités : "
                   f"{', '.join(r['id'] + ' (' + str(r['score']) + ')' for r in top)}.\n- **Contrôles** : {k['operational_controls']}/{k['total_controls']} opérationnels ; "
                   f"{k['covered_risks']}/{k['total']} risques couverts.\n- **COSO** : {k['deficient_principles']} principes déficients ; maturité {k['avg_maturity']:.1f}/5.\n"
                   f"- **Plan d'action** : {k['action_progress']} % ; **anomalies ouvertes** : {k['open_anomalies']} ({k['overdue_anomalies']} en retard).\n"
                   f"- **Dossiers TPE** : {k['dossiers_blocked']}/{k['dossiers']} suspendus (règle de blocage C01).\n\n**Recommandations prioritaires**\n" +
                   _chain(s, [r["id"] for r in top]))
    return "\n\n".join(out)
