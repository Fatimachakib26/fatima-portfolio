"""Exports : PDF (fpdf2), Excel (openpyxl), CSV et jeu de données Power BI (modèle en étoile)."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime

import pandas as pd
from fpdf import FPDF

from . import repo
from .db import SEED
from .scoring import LEVEL_COLORS, LEVEL_TREATMENT, level

GREEN = (6, 59, 43)
EMERALD = (16, 185, 129)


def latin(s) -> str:
    """Les polices PDF standard ne couvrent que Latin-1 : normalisation typographique."""
    s = str("" if s is None else s)
    for a, b in {"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "→": "->", "×": "x", "≥": ">=", "≤": "<=", "…": "...",
                 "œ": "oe", "Œ": "OE", " ": " ", " ": " ", "•": "-", "●": "-"}.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "ignore").decode("latin-1")


class Report(FPDF):
    def __init__(self, title: str, subtitle: str = "", landscape: bool = False):
        super().__init__(orientation="L" if landscape else "P", unit="mm", format="A4")
        self.doc_title, self.doc_subtitle = title, subtitle
        self.set_auto_page_break(True, 16)
        self.set_margins(14, 32, 14)
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*GREEN)
        self.cell(0, 8, latin(title), new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(90, 100, 110)
            self.multi_cell(0, 4.6, latin(subtitle), new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def header(self):
        self.set_fill_color(*GREEN)
        self.rect(0, 0, self.w, 24, "F")
        self.set_fill_color(*EMERALD)
        self.rect(0, 24, self.w, 1.2, "F")
        self.set_xy(14, 7)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(100, 6, latin("CRÉDIT HORIZON"))
        self.set_xy(14, 14)
        self.set_text_color(110, 231, 183)
        self.set_font("Helvetica", "B", 7.5)
        self.cell(100, 4, "R I S K   I N T E L L I G E N C E")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 8)
        self.set_xy(self.w - 114, 8)
        self.cell(100, 4, latin(f"Édité le {datetime.now():%d/%m/%Y %H:%M}"), align="R")
        self.set_xy(self.w - 114, 14)
        self.cell(100, 4, "Projet EMSI - cas fictif - données de démonstration".encode("latin-1", "ignore").decode("latin-1"), align="R")
        self.set_y(32)

    def footer(self):
        self.set_y(-11)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(140, 150, 160)
        self.cell(0, 4, latin("CRÉDIT HORIZON RISK INTELLIGENCE - aide à la décision ; aucune décision d'octroi automatique."))
        self.cell(0, 4, f"Page {self.page_no()}/{{nb}}", align="R")

    def h2(self, text: str):
        if self.get_y() > self.h - 40:
            self.add_page()
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*GREEN)
        self.cell(0, 7, latin(text), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*EMERALD)
        self.set_line_width(0.5)
        self.line(14, self.get_y(), 40, self.get_y())
        self.ln(3)

    def para(self, text: str, size: float = 9.5):
        self.set_font("Helvetica", "", size)
        self.set_text_color(40, 50, 60)
        self.multi_cell(0, size * 0.48, latin(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def table(self, head: list[str], rows: list[list], widths: list[float] | None = None, size: float = 7.5, level_col: int | None = None):
        self.set_font("Helvetica", "", size)
        self.set_text_color(30, 41, 59)
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(226, 232, 240)
        with super().table(col_widths=widths, text_align="LEFT", line_height=size * 0.5, padding=1.2,
                           cell_fill_color=(244, 249, 247), cell_fill_mode="ROWS",
                           headings_style=_heading_style(), borders_layout="HORIZONTAL_LINES", first_row_as_headings=True) as t:
            row = t.row()
            for h in head:
                row.cell(latin(h))
            for r in rows:
                row = t.row()
                for i, v in enumerate(r):
                    if level_col is not None and i == level_col and v in LEVEL_COLORS:
                        from fpdf.fonts import FontFace
                        hexc = LEVEL_COLORS[v].lstrip("#")
                        row.cell(latin(v), style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=tuple(int(hexc[j:j + 2], 16) for j in (0, 2, 4))))
                    else:
                        row.cell(latin(v))
        self.ln(3)

    def heatmap(self, risks: pd.DataFrame, x: float = 30, cell: float = 22):
        y0 = self.get_y() + 2
        for p in range(5, 0, -1):
            for g in range(1, 6):
                lv = level(p * g)
                h = LEVEL_COLORS[lv].lstrip("#")
                rgb = [int(h[j:j + 2], 16) for j in (0, 2, 4)]
                self.set_fill_color(*[int(c + (255 - c) * 0.55) for c in rgb])
                self.set_draw_color(255, 255, 255)
                cx, cy = x + (g - 1) * cell, y0 + (5 - p) * cell
                self.rect(cx, cy, cell - 1, cell - 1, "FD")
                self.set_font("Helvetica", "", 7)
                self.set_text_color(110, 110, 110)
                self.text(cx + cell - 5, cy + cell - 3, str(p * g))
                here = risks[(risks.probability == p) & (risks.gravity == g)]
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(15, 23, 42)
                for i, rid in enumerate(here.id):
                    self.text(cx + 2, cy + 5 + i * 4, rid)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(60, 60, 60)
            self.text(x - 5, y0 + (5 - p) * cell + cell / 2 + 1, str(p))
        for g in range(1, 6):
            self.text(x + (g - 1) * cell + cell / 2 - 1, y0 + 5 * cell + 4, str(g))
        self.set_font("Helvetica", "", 8)
        self.text(x + 2 * cell, y0 + 5 * cell + 9, latin("Gravité ->"))
        self.text(x - 12, y0 - 2, latin("Probabilité"))
        self.set_y(y0 + 5 * cell + 13)

    def output_bytes(self) -> bytes:
        return bytes(self.output())


def _heading_style():
    from fpdf.fonts import FontFace
    return FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=GREEN)


def _risk_rows(s):
    r = s["risks"].sort_values(["score", "id"], ascending=[False, True])
    return [[x.id, x.title, x.category, x.probability, x.gravity, x.score, x.level, x.owner] for x in r.itertuples()]


RISK_HEAD = ["Id", "Risque", "Catégorie", "P", "G", "Score", "Niveau", "Responsable"]
RISK_W = [12, 62, 22, 8, 8, 13, 18, 40]


def pdf_executive(s: dict) -> bytes:
    k = repo.kpis(s)
    pdf = Report("Synthèse exécutive", "Situation consolidée des risques, du contrôle interne et du plan d'action.")
    pdf.alias_nb_pages()
    pdf.h2("1. Indicateurs clés")
    pdf.table(["Indicateur", "Valeur"], [
        ["Risques recensés", k["total"]], ["Risques critiques / élevés", f"{k['critical']} / {k['high']}"], ["Score moyen P x G", f"{k['avg_score']:.1f}"],
        ["Contrôles opérationnels", f"{k['operational_controls']} / {k['total_controls']}"], ["Risques couverts", f"{k['covered_risks']} / {k['total']}"],
        ["Avancement du plan d'action", f"{k['action_progress']} %"], ["Anomalies ouvertes (en retard)", f"{k['open_anomalies']} ({k['overdue_anomalies']})"],
        ["Principes COSO déficients", f"{k['deficient_principles']} / 17"], ["Dossiers TPE suspendus", f"{k['dossiers_blocked']} / {k['dossiers']}"],
    ], widths=[110, 72], size=9)
    pdf.h2("2. Top 5 des risques prioritaires")
    pdf.table(RISK_HEAD, _risk_rows(s)[:5], RISK_W, level_col=6)
    top = list(s["risks"].sort_values("score", ascending=False).id[:4])
    pdf.h2("3. Recommandations prioritaires")
    rec = s["recommendations"]
    pdf.table(["Risque", "Lacune COSO", "Action corrective", "Responsable", "Indicateur"],
              [[r.risk_id, r.coso_gap, r.action, r.owner, r.indicator] for r in rec[rec.risk_id.isin(top)].itertuples()], [14, 42, 52, 36, 38], size=7)
    pdf.h2("4. Actions P1")
    a = s["actions"]
    pdf.table(["Id", "Action", "Responsable", "Échéance", "Statut", "%"],
              [[x.id, x.title, x.owner, x.due, x.status, x.progress] for x in a[a.priority == "P1"].itertuples()], [12, 78, 34, 26, 20, 12])
    return pdf.output_bytes()


def pdf_full(s: dict) -> bytes:
    k = repo.kpis(s)
    pdf = Report("Rapport de gestion des risques", "Registre, cartographie, contrôle interne, diagnostic COSO, gouvernance, appétence et plan d'action.")
    pdf.alias_nb_pages()
    pdf.h2("1. Synthèse")
    pdf.para(f"Le registre compte {k['total']} risques dont {k['critical']} critiques et {k['high']} élevés (score moyen {k['avg_score']:.1f}/25). "
             f"{k['covered_risks']} risques sur {k['total']} sont couverts par au moins un contrôle ; {k['operational_controls']} contrôles sur {k['total_controls']} sont opérationnels. "
             f"Le diagnostic COSO identifie {k['deficient_principles']} principes déficients sur 17 (maturité moyenne {k['avg_maturity']:.1f}/5). "
             f"Le plan d'action est avancé à {k['action_progress']} % et {k['open_anomalies']} anomalie(s) restent ouvertes, dont {k['overdue_anomalies']} en retard.")
    pdf.h2("2. Registre des risques")
    pdf.table(RISK_HEAD, _risk_rows(s), RISK_W, level_col=6)
    for r in s["risks"].itertuples():
        pdf.para(f"{r.id} - Causes : {r.causes} | Conséquences : {r.consequences} | Traitement : {LEVEL_TREATMENT[r.level]}", 8)
    pdf.add_page()
    pdf.h2("3. Cartographie des risques")
    pdf.heatmap(s["risks"], x=50, cell=21)
    pdf.h2("4. Fiches de contrôle")
    pdf.table(["Id", "Contrôle", "Type", "Risques", "Responsable", "Fréquence", "Indicateur", "Statut"],
              [[c.id, c.name, c.nature, c.risk_ids, c.owner, c.frequency, c.indicator, c.status] for c in s["controls"].itertuples()],
              [10, 34, 18, 16, 30, 24, 34, 16], size=6.8)
    pdf.h2("5. Diagnostic COSO 2013")
    pdf.table(["Composante", "Lacunes", "Risques", "Recommandations", "Maturité"],
              [[f"{c.id}. {c.name}", c.gaps, c.risk_ids, c.recommendations, f"{c.maturity}/5"] for c in s["components"].itertuples()], [32, 56, 18, 60, 16], size=7)
    pdf.h2("6. Matrice RACI")
    actors = SEED["raci_actors"]
    pdf.table(["Activité"] + [a["label"] for a in actors],
              [[f"{x['n']}. {x['activity']}"] + [x["roles"][a["key"]] for a in actors] for x in SEED["raci_activities"]], [52] + [21.6] * 6, size=7)
    pdf.h2("7. Recommandations (Risque -> Lacune COSO -> Action -> Responsable -> Indicateur)")
    pdf.table(["Risque", "Lacune COSO", "Action", "Responsable", "Indicateur"],
              [[r.risk_id, r.coso_gap, r.action, r.owner, r.indicator] for r in s["recommendations"].itertuples()], [14, 42, 52, 36, 38], size=7)
    pdf.h2("8. Plan d'action")
    pdf.table(["Id", "Prio.", "Action", "Responsable", "Échéance", "Statut", "%"],
              [[a.id, a.priority, a.title, a.owner, a.due, a.status, a.progress] for a in s["actions"].itertuples()], [11, 11, 70, 32, 26, 20, 12])
    return pdf.output_bytes()


def pdf_coso(s: dict) -> bytes:
    pdf = Report("Rapport COSO 2013", "Diagnostic par composante et par principe. Appréciations provisoires et qualitatives.", landscape=True)
    pdf.alias_nb_pages()
    pdf.h2("1. Composantes")
    pdf.table(["Composante", "Constats", "Lacunes", "Risques", "Recommandations", "Responsables", "Indicateurs", "Maturité"],
              [[f"{c.id}. {c.name} ({c.principles})", c.findings, c.gaps, c.risk_ids, c.recommendations, c.owner, c.indicators, f"{c.maturity}/5"]
               for c in s["components"].itertuples()], [30, 48, 42, 18, 48, 30, 38, 15], size=6.8)
    pdf.h2("2. Les 17 principes")
    comp = dict(zip(s["components"].id, s["components"].name))
    pdf.table(["Principe", "Intitulé", "Composante", "Nature", "Diagnostic", "Risques", "Appréciation"],
              [[p.id, p.title, comp.get(p.component_id, ""), p.nature, p.diagnostic, p.risk_ids, p.assessment] for p in s["principles"].itertuples()],
              [14, 60, 38, 28, 84, 20, 25])
    return pdf.output_bytes()


def pdf_heatmap(s: dict) -> bytes:
    pdf = Report("Cartographie des risques", "Matrice probabilité x gravité (5 x 5). Seuils : 1-4 Faible ; 5-9 Modéré ; 10-15 Élevé ; 16-25 Critique.")
    pdf.alias_nb_pages()
    pdf.heatmap(s["risks"], x=50, cell=22)
    pdf.table(RISK_HEAD, _risk_rows(s), RISK_W, level_col=6)
    return pdf.output_bytes()


def pdf_action_plan(s: dict) -> bytes:
    pdf = Report("Plan d'action correctif", "Actions priorisées, chaînes de recommandations et anomalies ouvertes.", landscape=True)
    pdf.alias_nb_pages()
    pdf.h2("1. Plan d'action")
    pdf.table(["Id", "Prio.", "Action", "Responsable", "Échéance", "Livrable", "Risques", "Contrôles", "Statut", "%"],
              [[a.id, a.priority, a.title, a.owner, a.due, a.deliverable, a.risk_ids, a.control_ids, a.status, a.progress] for a in s["actions"].itertuples()],
              [11, 11, 66, 32, 25, 50, 20, 26, 18, 10])
    pdf.h2("2. Recommandations")
    pdf.table(["Id", "RISQUE", "LACUNE COSO", "ACTION CORRECTIVE", "RESPONSABLE", "INDICATEUR", "Statut"],
              [[r.id, r.risk_id, r.coso_gap, r.action, r.owner, r.indicator, r.status] for r in s["recommendations"].itertuples()], [14, 14, 56, 66, 44, 52, 22], size=7)
    an = s["anomalies"]
    pdf.h2("3. Anomalies non clôturées")
    pdf.table(["Id", "Détectée", "Dossier", "Nature", "Gravité", "Risque", "Responsable", "Échéance", "Statut", "Esc."],
              [[a.id, a.detected_on, a.dossier_ref, a.nature, a.severity, a.risk_id, a.owner, a.due_on, a.status, f"N{a.escalation}"]
               for a in an[an.status != "Clôturée"].itertuples()], [16, 20, 26, 80, 20, 14, 32, 20, 18, 12])
    return pdf.output_bytes()


def markdown_pdf(title: str, md: str) -> bytes:
    pdf = Report(title, "Réponse générée par Risk Advisor à partir des données enregistrées dans la plateforme.")
    pdf.alias_nb_pages()
    lines = md.replace("\r", "").split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: ") and lines[i + 1].strip():
            cells = lambda t: [c.strip().replace("**", "") for c in t.strip().strip("|").split("|")]  # noqa: E731
            head = cells(ln)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            rows = [r + [""] * (len(head) - len(r)) for r in rows]
            pdf.table(head, [r[: len(head)] for r in rows], size=7)
            continue
        if ln.startswith("#"):
            pdf.h2(ln.lstrip("#").strip().replace("**", ""))
        elif ln.strip():
            pdf.para(ln.replace("**", "").replace("`", "").lstrip("> ").replace("- ", "  - ", 1) if ln.lstrip().startswith("-") else ln.replace("**", "").lstrip("> "))
        i += 1
    return pdf.output_bytes()


# ------------------------------------------------------------------ Excel / CSV
def excel(s: dict) -> bytes:
    buf = io.BytesIO()
    actors = SEED["raci_actors"]
    raci = pd.DataFrame([{"Activité": f"{a['n']}. {a['activity']}", **{x["label"]: a["roles"][x["key"]] for x in actors}} for a in SEED["raci_activities"]])
    sheets = {
        "Registre des risques": s["risks"].drop(columns=["is_demo"], errors="ignore"),
        "Contrôles": s["controls"].drop(columns=["is_demo"], errors="ignore"),
        "COSO composantes": s["components"].drop(columns=["is_demo"], errors="ignore"),
        "COSO principes": s["principles"].drop(columns=["is_demo"], errors="ignore"),
        "Recommandations": s["recommendations"].drop(columns=["is_demo"], errors="ignore"),
        "Plan d'action": s["actions"].drop(columns=["is_demo"], errors="ignore"),
        "Anomalies": s["anomalies"].drop(columns=["is_demo"], errors="ignore"),
        "Matrice RACI": raci,
    }
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
            ws = xw.sheets[name[:31]]
            from openpyxl.styles import Alignment, Font, PatternFill
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="063B2B")
                c.alignment = Alignment(wrap_text=True, vertical="center")
            for col in ws.columns:
                width = min(60, max(10, max(len(str(c.value or "")) for c in col[:50]) + 2))
                ws.column_dimensions[col[0].column_letter].width = width
                for c in col[1:]:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
    return buf.getvalue()


def csv(df: pd.DataFrame) -> bytes:
    return df.drop(columns=["is_demo"], errors="ignore").to_csv(index=False, sep=";").encode("utf-8-sig")


# ------------------------------------------------------------------ Power BI
def powerbi_tables(s: dict) -> dict[str, pd.DataFrame]:
    """Modèle en étoile prêt pour Power BI (relations décrites dans powerbi/GUIDE_POWER_BI.md)."""
    r = s["risks"]
    dim_risque = r[["id", "title", "category", "event", "causes", "consequences", "probability", "gravity", "score", "level", "owner", "basis", "recommendation"]].rename(
        columns={"id": "RisqueID", "title": "Risque", "category": "Categorie", "event": "Evenement", "causes": "Causes", "consequences": "Consequences",
                 "probability": "Probabilite", "gravity": "Gravite", "score": "Score", "level": "Niveau", "owner": "Responsable", "basis": "Fondement",
                 "recommendation": "Recommandation"})
    dim_risque["OrdreNiveau"] = dim_risque.Niveau.map({"Faible": 1, "Modéré": 2, "Élevé": 3, "Critique": 4})
    c = s["controls"]
    dim_controle = c[["id", "name", "nature", "objective", "owner", "frequency", "evidence", "indicator", "status"]].rename(
        columns={"id": "ControleID", "name": "Controle", "nature": "Type", "objective": "Objectif", "owner": "Responsable", "frequency": "Frequence",
                 "evidence": "Preuve", "indicator": "Indicateur", "status": "Statut"})
    bridge_rc = pd.DataFrame([{"RisqueID": rid, "ControleID": x.id} for x in c.itertuples() for rid in repo.split_ids(x.risk_ids)])
    p = s["principles"]
    comp = s["components"].rename(columns={"id": "ComposanteID", "name": "Composante", "maturity": "Maturite", "findings": "Constats", "gaps": "Lacunes"})[["ComposanteID", "Composante", "Maturite", "Constats", "Lacunes"]]
    dim_principe = p[["id", "component_id", "title", "nature", "assessment", "diagnostic"]].rename(
        columns={"id": "PrincipeID", "component_id": "ComposanteID", "title": "Principe", "nature": "Nature", "assessment": "Appreciation", "diagnostic": "Diagnostic"})
    bridge_rp = pd.DataFrame([{"RisqueID": x.id, "PrincipeID": pid} for x in r.itertuples() for pid in repo.split_ids(x.coso_principles)])
    h = s["history"].copy()
    fact_cot = pd.DataFrame({"RisqueID": h.risk_id, "Date": pd.to_datetime(h.recorded_at, utc=True).dt.date, "Probabilite": h.probability,
                             "Gravite": h.gravity, "Score": h.score, "Niveau": h.score.map(level)})
    an = s["anomalies"]
    fact_anom = an[["id", "detected_on", "dossier_ref", "nature", "severity", "risk_id", "control_id", "owner", "due_on", "status", "escalation"]].rename(
        columns={"id": "AnomalieID", "detected_on": "DateDetection", "dossier_ref": "Dossier", "nature": "Nature", "severity": "Gravite", "risk_id": "RisqueID",
                 "control_id": "ControleID", "owner": "Responsable", "due_on": "Echeance", "status": "Statut", "escalation": "NiveauEscalade"})
    today = date.today().isoformat()
    fact_anom["EnRetard"] = [(s_ != "Clôturée" and bool(d) and d < today) for s_, d in zip(fact_anom.Statut, fact_anom.Echeance)]
    a = s["actions"]
    fact_act = a[["id", "priority", "title", "owner", "due", "deliverable", "risk_ids", "control_ids", "status", "progress"]].rename(
        columns={"id": "ActionID", "priority": "Priorite", "title": "Action", "owner": "Responsable", "due": "Echeance", "deliverable": "Livrable",
                 "risk_ids": "Risques", "control_ids": "Controles", "status": "Statut", "progress": "Avancement"})
    bridge_ar = pd.DataFrame([{"ActionID": x.id, "RisqueID": rid} for x in a.itertuples() for rid in repo.split_ids(x.risk_ids)])
    rec = s["recommendations"].rename(columns={"id": "RecommandationID", "risk_id": "RisqueID", "coso_gap": "LacuneCOSO", "action": "ActionCorrective",
                                               "owner": "Responsable", "indicator": "Indicateur", "basis": "Fondement", "status": "Statut"}).drop(columns=["is_demo"], errors="ignore")
    dos = pd.DataFrame([{"DossierID": d["id"], "Entreprise": d["company"].get("name"), "Secteur": d["company"].get("sector"), "Ville": d["company"].get("city"),
                         "Produit": d["request"].get("product"), "Montant": pd.to_numeric(d["request"].get("amount"), errors="coerce"),
                         "DureeMois": pd.to_numeric(d["request"].get("duration_months"), errors="coerce"), "Completude": d["analysis"]["completeness"]["rate"],
                         "NbIncoherences": len(d["analysis"]["inconsistencies"]), "NbVigilance": len(d["analysis"]["vigilance"]),
                         "Suspendu": d["analysis"]["blocking"], "Statut": d["status"]} for d in s["dossiers"]])
    raci = pd.DataFrame([{"Activite": f"{x['n']}. {x['activity']}", "Bloc": x.get("block", ""), "Acteur": a_["label"], "Groupe": a_["group"], "Role": x["roles"][a_["key"]]}
                         for x in SEED["raci_activities"] for a_ in SEED["raci_actors"]])
    return {"DimRisque": dim_risque, "DimControle": dim_controle, "PontRisqueControle": bridge_rc, "DimComposanteCOSO": comp,
            "DimPrincipeCOSO": dim_principe, "PontRisquePrincipe": bridge_rp, "FaitCotation": fact_cot, "FaitAnomalie": fact_anom,
            "FaitAction": fact_act, "PontActionRisque": bridge_ar, "FaitRecommandation": rec, "FaitDossierTPE": dos, "MatriceRACI": raci}


def powerbi_excel(s: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in powerbi_tables(s).items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
    return buf.getvalue()


def powerbi_zip(s: dict, guide: str, dax: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, df in powerbi_tables(s).items():
            z.writestr(f"{name}.csv", df.to_csv(index=False, sep=";").encode("utf-8-sig"))
        z.writestr("CreditHorizon_PowerBI.xlsx", powerbi_excel(s))
        z.writestr("GUIDE_POWER_BI.md", guide)
        z.writestr("MESURES_DAX.dax", dax)
        z.writestr("metadata.json", json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"), "source": "CRÉDIT HORIZON RISK INTELLIGENCE"}, ensure_ascii=False))
    return buf.getvalue()
