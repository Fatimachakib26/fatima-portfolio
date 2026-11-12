import { state, save, audit, nextId, splitIds, snapshot, resetDemo, SEED, type Row } from "./store";
import { computeKpis } from "./logic/kpis";
import { levelFromScore, LEVEL_TREATMENT, LEVELS, PROBABILITY_SCALE, GRAVITY_SCALE, type Level } from "./logic/scoring";
import { analyzeDossier, CHECKLIST, PRODUCTS, GUARANTEE_TYPES, isRequired } from "./logic/dossier-analysis";
import { offlineAnswer } from "./logic/offline-advisor";
import { md } from "./markdown";

/* ================================================================ constantes */
const ROLES: Record<string, string> = { admin: "Administrateur", directeur: "Directeur", analyste: "Analyste risques", commercial: "Commercial", controleur: "Contrôleur interne" };
const PERMS: Record<string, string[]> = {
  "risks.write": ["admin", "analyste"],
  "controls.write": ["admin", "controleur"],
  "coso.write": ["admin", "controleur"],
  "actions.write": ["admin", "directeur", "analyste", "controleur"],
  "recommendations.write": ["admin", "analyste", "controleur"],
  "anomalies.create": ["admin", "directeur", "analyste", "commercial", "controleur"],
  "anomalies.write": ["admin", "directeur", "analyste", "controleur"],
  "dossiers.write": ["admin", "analyste", "commercial"],
  "audit.view": ["admin", "directeur", "controleur"],
  "demo.reset": ["admin"],
};
const PERM_LABELS: Record<string, string> = {
  "risks.write": "Modifier le registre des risques", "controls.write": "Gérer les fiches de contrôle", "coso.write": "Mettre à jour le diagnostic COSO",
  "actions.write": "Piloter le plan d'action", "recommendations.write": "Gérer les recommandations", "anomalies.create": "Déclarer une anomalie",
  "anomalies.write": "Traiter / clôturer une anomalie", "dossiers.write": "Saisir les dossiers TPE", "audit.view": "Consulter le journal d'audit", "demo.reset": "Réinitialiser les données",
};
const can = (p: string) => !!state.user && PERMS[p]?.includes(state.user.role);
const CAT_COLORS: Record<string, string> = { Crédit: "#2a78d6", Liquidité: "#eb6834", Opérationnel: "#1baf7a", Conformité: "#6250d6", Stratégique: "#e87ba4" };
const LVL_COLORS: Record<Level, string> = { Faible: "#16a34a", Modéré: "#eab308", Élevé: "#f97316", Critique: "#dc2626" };
const CELL: Record<Level, string> = { Faible: "#bbf7d0", Modéré: "#fef08a", Élevé: "#fed7aa", Critique: "#fca5a5" };

const NAV = [
  { group: "Pilotage", items: [["dashboard", "Dashboard exécutif", "◧"]] },
  { group: "Risques", items: [["registre", "Registre des risques", "☰"], ["cartographie", "Cartographie", "▦"], ["dossiers", "Dossiers TPE", "▤"], ["appetence", "Appétence au risque", "◎"]] },
  { group: "Contrôle interne", items: [["coso", "Diagnostic COSO", "⌂"], ["controles", "Fiches de contrôle", "⛨"], ["suivi", "Suivi & anomalies", "✓"], ["gouvernance", "Gouvernance RACI", "⇄"]] },
  { group: "Intelligence", items: [["assistant", "Risk Advisor IA", "✦"], ["rapports", "Rapports & exports", "⇩"], ["administration", "Administration", "⚙"]] },
];

/* ================================================================ utilitaires */
const esc = (v: unknown) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
const fmtMAD = (n: unknown) => (n === "" || n == null || isNaN(Number(n)) ? "–" : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(n)) + " MAD");
const today = () => new Date().toISOString().slice(0, 10);
const pill = (l: Level, s?: number) => `<span class="pill" style="background:${LVL_COLORS[l]}">${l}${s !== undefined ? ` · ${s}` : ""}</span>`;
const badge = (t: string, cls = "") => `<span class="badge ${cls}">${esc(t)}</span>`;
const demo = (r: Row) => (r.is_demo ? `<span class="badge demo">Démo</span>` : "");
const tone = (s: string) =>
  ["Terminé", "Clôturée", "Efficace", "Opérationnel", "Mise en œuvre", "Satisfaisant"].includes(s) ? "ok"
  : ["En cours", "En déploiement", "Partiel"].includes(s) ? "info"
  : ["Ouverte", "Bloqué", "Déficient", "Critique"].some((x) => s.startsWith(x)) || s.startsWith("Incomplet") ? "bad"
  : ["À faire", "À lancer", "À concevoir"].includes(s) ? "warn" : "";
const header = (icon: string, title: string, sub: string, actions = "") =>
  `<div class="ph"><div class="ph-t"><div class="ph-i">${icon}</div><div><h1>${title}</h1><p>${sub}</p></div></div><div class="ph-a">${actions}</div></div>`;
const readonly = (t: string) => `<div class="note">🔒 ${t}</div>`;
const card = (title: string, body: string, extra = "") => `<section class="card ${extra}">${title ? `<h2>${title}</h2>` : ""}${body}</section>`;

let toastTimer: any;
function toast(msg: string, bad = false) {
  const el = document.getElementById("toast")!;
  el.textContent = msg;
  el.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = "toast"), 3200);
}

function download(name: string, content: string, type = "text/csv;charset=utf-8") {
  try {
    const blob = new Blob([content], { type });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast(`Fichier ${name} généré.`);
  } catch {
    toast("Le téléchargement n'est pas autorisé dans cet affichage.", true);
  }
}
function csv(rows: Row[], cols: [string, string][]) {
  const e = (v: unknown) => {
    const s = String(v ?? "").replace(/\r?\n/g, " ");
    return /[";]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return "﻿" + [cols.map((c) => e(c[1])).join(";"), ...rows.map((r) => cols.map((c) => e(r[c[0]])).join(";"))].join("\r\n");
}

/* ================================================================ état d'interface */
const ui: any = { selRisk: null, dossier: null, draft: null, cosoTab: 1, suiviTab: "actions", chat: [] as { role: string; content: string }[], filter: "" };

/* ================================================================ graphiques SVG */
function donut(data: { label: string; value: number; color: string }[]) {
  const total = data.reduce((a, d) => a + d.value, 0) || 1;
  let a0 = -Math.PI / 2;
  const R = 70, r = 44, cx = 90, cy = 90;
  const arcs = data.map((d) => {
    const a1 = a0 + (d.value / total) * Math.PI * 2;
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const p = (rad: number, a: number) => `${cx + rad * Math.cos(a)},${cy + rad * Math.sin(a)}`;
    const mid = (a0 + a1) / 2;
    const path = `<path d="M${p(R, a0)} A${R},${R} 0 ${large} 1 ${p(R, a1 - 0.0001)} L${p(r, a1 - 0.0001)} A${r},${r} 0 ${large} 0 ${p(r, a0)} Z" fill="${d.color}" stroke="#fff" stroke-width="2"><title>${esc(d.label)} : ${d.value}</title></path>
      <text x="${cx + 57 * Math.cos(mid)}" y="${cy + 57 * Math.sin(mid) + 4}" text-anchor="middle" class="svg-v">${d.value}</text>`;
    a0 = a1;
    return path;
  });
  return `<div class="chart-row"><svg viewBox="0 0 180 180" class="donut" role="img" aria-label="Répartition par catégorie">${arcs.join("")}<text x="90" y="88" text-anchor="middle" class="svg-big">${total}</text><text x="90" y="104" text-anchor="middle" class="svg-s">risques</text></svg>
    <ul class="legend">${data.map((d) => `<li><i style="background:${d.color}"></i>${esc(d.label)} <b>${d.value}</b></li>`).join("")}</ul></div>`;
}

function bars(data: { label: string; value: number; color: string }[]) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const W = 300, H = 170, bw = 44, gap = (W - data.length * bw) / (data.length + 1);
  return `<svg viewBox="0 0 ${W} ${H + 24}" class="chart" role="img" aria-label="Répartition par niveau">
    ${[0, 0.5, 1].map((t) => `<line x1="0" x2="${W}" y1="${H - t * (H - 20)}" y2="${H - t * (H - 20)}" class="grid"/>`).join("")}
    ${data.map((d, i) => {
      const h = (d.value / max) * (H - 20), x = gap + i * (bw + gap);
      return `<rect x="${x}" y="${H - h}" width="${bw}" height="${Math.max(h, 0)}" rx="4" fill="${d.color}"><title>${d.label} : ${d.value}</title></rect>
        <text x="${x + bw / 2}" y="${H - h - 5}" text-anchor="middle" class="svg-v">${d.value}</text>
        <text x="${x + bw / 2}" y="${H + 16}" text-anchor="middle" class="svg-s">${d.label}</text>`;
    }).join("")}</svg>`;
}

function lines(points: { label: string; avg: number; max: number }[]) {
  const W = 320, H = 160, L = 26, n = points.length;
  const X = (i: number) => L + (n <= 1 ? 0 : (i * (W - L - 10)) / (n - 1));
  const Y = (v: number) => H - (v / 25) * (H - 10);
  const path = (k: "avg" | "max") => points.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p[k])}`).join(" ");
  return `<svg viewBox="0 0 ${W} ${H + 40}" class="chart" role="img" aria-label="Évolution des scores">
    ${[0, 5, 10, 15, 20, 25].map((v) => `<line x1="${L}" x2="${W}" y1="${Y(v)}" y2="${Y(v)}" class="grid"/><text x="${L - 5}" y="${Y(v) + 4}" text-anchor="end" class="svg-s">${v}</text>`).join("")}
    <path d="${path("max")}" fill="none" stroke="#2a78d6" stroke-width="2"/><path d="${path("avg")}" fill="none" stroke="#0f7a58" stroke-width="2"/>
    ${points.map((p, i) => `<circle cx="${X(i)}" cy="${Y(p.max)}" r="4" fill="#2a78d6"><title>${p.label} – max ${p.max}</title></circle><circle cx="${X(i)}" cy="${Y(p.avg)}" r="4" fill="#0f7a58"><title>${p.label} – moyen ${p.avg}</title></circle>
      <text x="${X(i)}" y="${H + 16}" text-anchor="middle" class="svg-s">${p.label}</text>`).join("")}
    <g transform="translate(${L},${H + 32})"><rect width="14" height="3" y="-4" fill="#2a78d6"/><text x="18" class="svg-s">Score maximal</text><rect x="110" width="14" height="3" y="-4" fill="#0f7a58"/><text x="128" class="svg-s">Score moyen</text></g></svg>`;
}

function heatmap(risks: Row[], compact = false, clickable = false) {
  let h = `<div class="hm ${compact ? "compact" : ""}"><div class="hm-y">Probabilité</div><div class="hm-grid">`;
  for (let p = 5; p >= 1; p--) {
    h += `<div class="hm-lab">${p}${compact ? "" : `<small>${PROBABILITY_SCALE[p - 1].label}</small>`}</div>`;
    for (let g = 1; g <= 5; g++) {
      const s = p * g, l = levelFromScore(s);
      const here = risks.filter((r) => Number(r.probability) === p && Number(r.gravity) === g);
      h += `<div class="hm-cell" style="background:${CELL[l]}" title="P=${p} × G=${g} = ${s} (${l})"><span class="hm-s">${s}</span>${here
        .map((r) => `<button class="chip ${ui.selRisk === r.id ? "sel" : ""}" ${clickable ? `data-act="sel-risk" data-id="${r.id}"` : ""} title="${esc(r.title)}">${r.id}</button>`)
        .join("")}</div>`;
    }
  }
  h += `<div></div>${[1, 2, 3, 4, 5].map((g) => `<div class="hm-lab x">${g}${compact ? "" : `<small>${GRAVITY_SCALE[g - 1].label}</small>`}</div>`).join("")}</div></div>
    <div class="hm-x">Gravité</div><div class="legend inline">${LEVELS.map((l) => `<span><i style="background:${LVL_COLORS[l]}"></i>${l}</span>`).join("")}</div>`;
  return h;
}

/* ================================================================ formulaires modaux */
type Field = { k: string; l: string; t?: "text" | "textarea" | "select" | "number" | "date" | "range"; o?: string[]; req?: boolean; full?: boolean; min?: number; max?: number; hint?: string };
let modalSubmit: ((v: Row) => string | void) | null = null;

function openModal(title: string, fields: Field[], values: Row, onSubmit: (v: Row) => string | void) {
  modalSubmit = onSubmit;
  const f = fields
    .map((x) => {
      const v = values[x.k] ?? (x.t === "range" ? x.min ?? 0 : "");
      const label = `${x.l}${x.req ? " *" : ""}`;
      let input = "";
      if (x.t === "textarea") input = `<textarea name="${x.k}" ${x.req ? "required" : ""}>${esc(v)}</textarea>`;
      else if (x.t === "select") input = `<select name="${x.k}">${x.o!.map((o) => `<option ${o === v ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
      else if (x.t === "range") input = `<div class="range"><input type="range" name="${x.k}" min="${x.min}" max="${x.max}" value="${v}" oninput="this.nextElementSibling.textContent=this.value"><output>${v}</output></div>`;
      else input = `<input name="${x.k}" type="${x.t || "text"}" value="${esc(v)}" ${x.req ? "required" : ""}>`;
      return `<label class="${x.full || x.t === "textarea" ? "full" : ""}"><span>${label}</span>${input}${x.hint ? `<small>${esc(x.hint)}</small>` : ""}</label>`;
    })
    .join("");
  document.getElementById("modal")!.innerHTML = `<div class="ov" data-act="close-modal"></div><div class="mdl" role="dialog" aria-modal="true"><div class="mdl-h"><h3>${esc(title)}</h3><button data-act="close-modal" aria-label="Fermer">✕</button></div>
    <form id="mform" class="mform">${f}<div class="err full" id="merr"></div><div class="full right"><button type="button" class="btn ghost" data-act="close-modal">Annuler</button><button class="btn">Enregistrer</button></div></form></div>`;
  document.getElementById("modal")!.className = "open";
}
function closeModal() {
  document.getElementById("modal")!.className = "";
  document.getElementById("modal")!.innerHTML = "";
  modalSubmit = null;
}
function confirmBox(text: string, onYes: () => void) {
  document.getElementById("modal")!.innerHTML = `<div class="ov" data-act="close-modal"></div><div class="mdl small" role="alertdialog"><div class="mdl-h"><h3>Confirmation</h3></div><p>${esc(text)}</p>
    <div class="right"><button class="btn ghost" data-act="close-modal">Annuler</button><button class="btn danger" id="yes">Confirmer</button></div></div>`;
  document.getElementById("modal")!.className = "open";
  document.getElementById("yes")!.onclick = () => {
    closeModal();
    onYes();
  };
}

/* ================================================================ pages */
function pLogin() {
  return `<div class="login"><div class="hero">${LOGO}<h1>Maîtriser le risque,<br>accompagner la croissance des TPE.</h1>
    <p>Registre P × G, cartographie 5 × 5, analyse des dossiers TPE, diagnostic COSO 2013, contrôle interne, gouvernance RACI, appétence au risque et assistant « Risk Advisor ».</p>
    <small>Projet EMSI · Génie Financier – Contrôle interne &amp; gestion des risques financiers</small></div>
    <div class="login-r"><h2>Choisissez votre rôle</h2><p class="muted">Version de démonstration : chaque rôle dispose de droits différents (séparation des tâches).</p>
    <div class="roles">${SEED.demo_users.map((u: Row) => `<button class="role" data-act="login" data-role="${u.role}"><b>${ROLES[u.role]}</b><span>${esc(u.name)}</span></button>`).join("")}</div>
    <div class="note demo-note">🧪 Cas académique fictif « Crédit Horizon » (EMSI). Les données marquées « Démo » sont des données de démonstration. Vos modifications sont conservées dans ce navigateur.</div></div></div>`;
}

function pDashboard() {
  const s = snapshot(), k = computeKpis(s as any), r = s.risks;
  const cats = Object.keys(CAT_COLORS).map((c) => ({ label: c, value: r.filter((x) => x.category === c).length, color: CAT_COLORS[c] })).filter((d) => d.value);
  const lv = LEVELS.map((l) => ({ label: l, value: r.filter((x) => x.level === l).length, color: LVL_COLORS[l] }));
  const months = Array.from(new Set(s.history.map((h) => String(h.recorded_at).slice(0, 7)))).sort();
  const M = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  const evo = months.map((m) => {
    const last: Record<string, number> = {};
    s.history.filter((h) => String(h.recorded_at).slice(0, 7) <= m).forEach((h) => (last[h.risk_id] = h.score));
    const v = Object.entries(last).filter(([id]) => r.some((x) => x.id === id)).map(([, x]) => x);
    return { label: M[Number(m.slice(5)) - 1], avg: v.length ? +(v.reduce((a, b) => a + b, 0) / v.length).toFixed(1) : 0, max: v.length ? Math.max(...v) : 0 };
  });
  const top = [...r].sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).slice(0, 5);
  const pend = s.actions.filter((a) => a.status !== "Terminé").slice(0, 6);
  const closure = s.anomalies.length ? Math.round((k.closedAnomalies / s.anomalies.length) * 100) : 0;
  const ind = (l: string, v: number) => `<div class="ind"><div><span>${l}</span><b>${v} %</b></div><div class="bar"><i style="width:${v}%"></i></div></div>`;
  return header("◧", "Dashboard exécutif", "Vue consolidée de l'exposition aux risques, du dispositif de contrôle interne et de l'avancement des actions correctives.", `<a class="btn em" href="#assistant">Analyse IA de la situation →</a>`) +
    `<div class="kpis">
      ${kpi("Risques recensés", k.total, `Score moyen ${k.avgScore.toFixed(1)} / 25`, "brand")}${kpi("Risques critiques", k.critical, `${k.high} risques élevés`, "red")}
      ${kpi("Contrôles opérationnels", `${k.operationalControls}/${k.totalControls}`, `${k.coveredRisks}/${k.total} risques couverts`, "green")}
      ${kpi("Actions en attente", k.pendingActions, `Avancement moyen ${k.actionProgress} %`, "amber")}
      ${kpi("Anomalies ouvertes", k.openAnomalies, `${k.overdueAnomalies} en retard`, k.overdueAnomalies ? "red" : "brand")}
      ${kpi("Maturité COSO", `${k.avgMaturity.toFixed(1)}/5`, `${k.deficientPrinciples}/17 principes déficients`, "amber")}</div>
    <div class="g3">${card("Répartition par catégorie", donut(cats))}${card("Répartition par niveau de criticité", `<p class="muted s">1–4 Faible · 5–9 Modéré · 10–15 Élevé · 16–25 Critique</p>${bars(lv)}`)}
      ${card("Évolution des risques", `<p class="muted s">Dernière cotation P × G connue en fin de mois</p>${lines(evo)}`)}</div>
    <div class="g2w">${card("Top 5 des risques prioritaires", table(["#", "Risque", "Catégorie", "P", "G", "Criticité", "Responsable"], top.map((x, i) => [
      `<b class="muted">${i + 1}</b>`, `<b>${x.id}</b> · ${esc(x.title)}`, `<span class="dot" style="background:${CAT_COLORS[x.category]}"></span>${esc(x.category)}`, x.probability, x.gravity, pill(x.level, x.score), `<small>${esc(x.owner)}</small>`])) + `<a class="lnk" href="#registre">Registre complet →</a>`)}
      ${card("Cartographie synthétique", heatmap(r, true) + `<a class="lnk" href="#cartographie">Ouvrir →</a>`)}</div>
    <div class="g2">${card("Indicateurs de contrôle interne", ind("Couverture des risques par au moins un contrôle", Math.round((k.coveredRisks / Math.max(1, k.total)) * 100)) +
      ind("Contrôles opérationnels ou efficaces", Math.round((k.operationalControls / Math.max(1, k.totalControls)) * 100)) + ind("Taux de clôture des anomalies", closure) +
      ind("Avancement du plan d'action", k.actionProgress) + ind("Principes COSO non déficients", Math.round(((17 - k.deficientPrinciples) / 17) * 100)) +
      `<p class="muted s">Dossiers TPE suspendus (règle de blocage C01) : ${k.dossiersBlocked}/${k.dossiers}</p>`)}
      ${card("Actions correctives en attente", `<ul class="list">${pend.map((a) => `<li>${badge(a.priority, a.priority === "P1" ? "bad" : a.priority === "P2" ? "warn" : "")}<div><b>${a.id}</b> · ${esc(a.title)}<small>${esc(a.owner)} · ${esc(a.due)}</small></div><div class="mini"><div class="bar"><i style="width:${a.progress}%"></i></div><small>${a.progress} %</small></div></li>`).join("")}</ul><a class="lnk" href="#suivi">Plan d'action →</a>`)}</div>`;
}
const kpi = (l: string, v: unknown, h: string, t: string) => `<div class="kpi ${t}"><span>${l}</span><b>${v}</b><small>${h}</small></div>`;
const table = (head: string[], rows: unknown[][], cls = "") =>
  `<div class="tw"><table class="${cls}"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;

const RISK_FIELDS: Field[] = [
  { k: "title", l: "Intitulé du risque", req: true, full: true },
  { k: "category", l: "Catégorie", t: "select", o: Object.keys(CAT_COLORS) },
  { k: "basis", l: "Fondement", t: "select", o: ["Constat", "Hypothèse"] },
  { k: "event", l: "Description de l'événement", t: "textarea", req: true },
  { k: "causes", l: "Causes", t: "textarea" },
  { k: "consequences", l: "Conséquences", t: "textarea" },
  { k: "probability", l: "Probabilité (1 à 5)", t: "range", min: 1, max: 5, hint: PROBABILITY_SCALE.map((p) => `${p.v} = ${p.label}`).join(" · ") },
  { k: "gravity", l: "Gravité (1 à 5)", t: "range", min: 1, max: 5, hint: GRAVITY_SCALE.map((p) => `${p.v} = ${p.label}`).join(" · ") },
  { k: "justification", l: "Justification de la cotation", t: "textarea" },
  { k: "owner", l: "Responsable", req: true },
  { k: "control_ids", l: "Contrôles associés", hint: "Ex. : C01, C04" },
  { k: "coso_principles", l: "Principes COSO", hint: "Ex. : P10, P12" },
  { k: "recommendation", l: "Recommandation", t: "textarea" },
];

function pRegistre() {
  const r = snapshot().risks.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const w = can("risks.write");
  const sel = r.find((x) => x.id === ui.selRisk) || r[0];
  const rows = r.map((x) => `<tr class="click ${sel?.id === x.id ? "selr" : ""}" data-act="sel-risk" data-id="${x.id}" data-text="${esc([x.id, x.title, x.event, x.causes, x.consequences, x.owner, x.category, x.level, x.control_ids].join(" ").toLowerCase())}">
    <td><b>${x.id}</b> ${demo(x)}</td><td><b>${esc(x.title)}</b><small class="clamp">${esc(x.event)}</small></td><td><span class="dot" style="background:${CAT_COLORS[x.category] || "#94a3b8"}"></span>${esc(x.category)}</td>
    <td class="c">${x.probability}</td><td class="c">${x.gravity}</td><td class="c"><b class="big">${x.score}</b></td><td>${pill(x.level)}</td><td><small>${esc(x.owner)}</small></td>
    <td>${splitIds(x.control_ids).map((c) => badge(c, "brand")).join(" ")}</td></tr>`).join("");
  return header("☰", "Registre des risques", "Identification, cotation P × G automatique, criticité, responsables, contrôles et recommandations. R01 à R08 proviennent du projet EMSI.",
    w ? `<button class="btn" data-act="risk-new">+ Nouveau risque</button>` : "") +
    (w ? "" : readonly("Consultation seule : le registre est modifié par la fonction risques et l'administrateur (séparation des tâches).")) +
    card("", `<div class="toolbar"><input id="q" type="search" placeholder="Rechercher (identifiant, événement, cause, responsable…)" value="${esc(ui.filter)}" autocomplete="off"><span class="muted s" id="qcount">${r.length} risque(s)</span></div>
      <div class="tw"><table id="rtable"><thead><tr><th>ID</th><th>Risque / événement</th><th>Catégorie</th><th>P</th><th>G</th><th>P × G</th><th>Criticité</th><th>Responsable</th><th>Contrôles</th></tr></thead><tbody>${rows}</tbody></table></div>`) +
    (sel ? riskSheet(sel, w) : "");
}

function riskSheet(x: Row, w: boolean) {
  const P = PROBABILITY_SCALE[x.probability - 1], G = GRAVITY_SCALE[x.gravity - 1];
  const hist = state.history.filter((h) => h.risk_id === x.id);
  return card(`Fiche ${x.id} – ${esc(x.title)}`, `<div class="row-b">${pill(x.level, x.score)} ${badge(x.category)} ${badge(x.basis, "warn")} ${demo(x)}</div>
    <div class="g3 tight"><div><h4>Événement redouté</h4><p>${esc(x.event)}</p></div><div><h4>Causes</h4><p>${esc(x.causes) || "–"}</p></div><div><h4>Conséquences</h4><p>${esc(x.consequences) || "–"}</p></div>
    <div><h4>Cotation</h4><p>P = ${x.probability} (${P.label}) × G = ${x.gravity} (${G.label}) = <b>${x.score}</b></p></div><div><h4>Justification</h4><p>${esc(x.justification) || "–"}</p></div>
    <div><h4>Traitement attendu</h4><p>${LEVEL_TREATMENT[x.level as Level]}</p></div></div>
    <p><b>Recommandation :</b> ${esc(x.recommendation) || "–"}<br><b>Responsable :</b> ${esc(x.owner)} · <b>Contrôles :</b> ${esc(x.control_ids) || "–"} · <b>COSO :</b> ${esc(x.coso_principles) || "–"}</p>
    <p class="muted s">Historique des cotations : ${hist.map((h) => `${String(h.recorded_at).slice(0, 7)} → ${h.score}`).join(" · ") || "–"}</p>
    <div class="right">${w ? `<button class="btn ghost" data-act="risk-edit" data-id="${x.id}">Modifier</button><button class="btn danger" data-act="risk-del" data-id="${x.id}">Supprimer</button>` : ""}
    <button class="btn em" data-act="ask" data-q="Analyse le risque ${x.id} : explique son score P × G, relie-le aux principes COSO et propose une recommandation complète.">✦ Analyser avec Risk Advisor</button></div>`);
}

function pCarto() {
  const r = snapshot().risks;
  const sel = r.find((x) => x.id === ui.selRisk);
  return header("▦", "Cartographie des risques", "Matrice thermique interactive 5 × 5. Cliquez sur un risque pour afficher sa fiche.") +
    `<div class="g2w">${card("", heatmap(r, false, true))}<div>${sel ? riskSheet(sel, can("risks.write")) : card("Fiche du risque", `<p class="muted">Sélectionnez un risque dans la matrice.</p>`)}
    ${card("Synthèse par zone", [...LEVELS].reverse().map((l) => `<p>${pill(l)} <small>${r.filter((x) => x.level === l).sort((a, b) => b.score - a.score).map((x) => `${x.id} (${x.score})`).join(", ") || "aucun risque"}</small></p>`).join(""))}</div></div>`;
}

/* ---------------------------------------------------------------- dossiers */
const EMPTY_D = () => ({
  company: { name: "", legal_form: "SARL", rc_number: "", ice: "", creation_date: "", sector: "", activity: "", city: "", manager_name: "", employees: "", name_on_documents: "" },
  request: { product: PRODUCTS[0], amount: "", duration_months: "", purpose: "" },
  financials: { fiscal_year: "", revenue_n: "", revenue_n1: "", revenue_bank: "", net_result: "", equity: "", existing_debt: "", existing_monthly_installments: "" },
  documents: Object.fromEntries(CHECKLIST.map((c) => [c.key, ""])),
  guarantees: { type: "Aucune", value: "", description: "" },
  observations: "",
});

function pDossiers() {
  const w = can("dossiers.write");
  if (!ui.draft) {
    const d = state.dossiers.find((x) => x.id === ui.dossier) || state.dossiers[0];
    ui.dossier = d?.id ?? null;
    ui.draft = d ? JSON.parse(JSON.stringify({ company: d.company, request: d.request, financials: d.financials, documents: d.documents, guarantees: d.guarantees, observations: d.observations })) : EMPTY_D();
  }
  const d = ui.draft;
  const list = table(["Référence", "Entreprise", "Financement", "Complétude", "Statut de l'analyse", ""], state.dossiers.map((x) => [
    `<b>${x.id}</b> ${demo(x)}`, `${esc(x.company?.name)}<small>${esc(x.company?.sector)}</small>`, `${fmtMAD(x.request?.amount)}<small>${esc(x.request?.product)} · ${esc(x.request?.duration_months)} mois</small>`,
    `<div class="bar"><i style="width:${x.analysis?.completeness?.rate ?? 0}%"></i></div><small>${x.analysis?.completeness?.rate ?? 0} %</small>`, badge(x.status, tone(x.status)),
    `<button class="btn ghost sm" data-act="dos-open" data-id="${x.id}">Ouvrir</button>`]));
  const T = (part: string, k: string, label: string, type = "text", hint = "") =>
    `<label><span>${label}</span><input data-d="${part}.${k}" type="${type}" value="${esc(d[part][k])}" ${w ? "" : "disabled"}>${hint ? `<small>${hint}</small>` : ""}</label>`;
  const S = (part: string, k: string, label: string, opts: readonly string[]) =>
    `<label><span>${label}</span><select data-d="${part}.${k}" ${w ? "" : "disabled"}>${opts.map((o) => `<option ${o === d[part][k] ? "selected" : ""}>${esc(o)}</option>`).join("")}</select></label>`;
  const docs = CHECKLIST.map((c) => {
    const req = c.stage === "avant_avis" && isRequired(c.key, d);
    return `<div class="doc"><div>${esc(c.label)}<small>${c.scope} · ${c.stage === "avant_decision" ? "exigé avant la décision" : req ? "obligatoire avant avis" : "non requis pour ce dossier"}</small></div><div class="seg">${[["oui", "Oui"], ["non", "Non"], ["na", "N/A"]]
      .map(([v, l]) => `<button type="button" class="${d.documents[c.key] === v ? "on " + v : ""}" data-act="doc" data-k="${c.key}" data-v="${v}" ${w ? "" : "disabled"}>${l}</button>`).join("")}</div></div>`;
  }).join("");
  return header("▤", "Analyse intelligente des dossiers TPE", "Complétude documentaire (contrôle C01), informations manquantes, incohérences, points de vigilance et synthèse. La plateforme ne prend aucune décision d'octroi.",
    w ? `<button class="btn ghost" data-act="dos-new">+ Nouveau dossier</button>` : "") +
    (w ? "" : readonly("Consultation seule : la saisie des dossiers est réservée aux commerciaux, analystes et administrateurs.")) +
    card("Dossiers enregistrés", list) +
    `<div class="g2w"><div id="dform"><p class="muted"><b>${ui.dossier ? `Dossier ${ui.dossier}` : "Nouveau dossier"}</b> – l'analyse se met à jour pendant la saisie.</p>
      ${card("1. Informations de l'entreprise", `<div class="fg">${T("company", "name", "Raison sociale *")}${S("company", "legal_form", "Forme juridique", ["SARL", "SARLAU", "SA", "SNC", "Entreprise individuelle", "Auto-entrepreneur", "Coopérative"])}${T("company", "creation_date", "Date de création", "date")}
        ${T("company", "rc_number", "N° registre de commerce")}${T("company", "ice", "ICE")}${T("company", "city", "Ville")}${T("company", "manager_name", "Dirigeant")}${T("company", "employees", "Effectif", "number")}${T("company", "name_on_documents", "Raison sociale sur les pièces", "text", "Contrôle de concordance")}</div>`)}
      ${card("2. Activité et financement demandé", `<div class="fg">${T("company", "sector", "Secteur d'activité")}${T("company", "activity", "Description de l'activité")}${S("request", "product", "Type de financement", PRODUCTS)}
        ${T("request", "amount", "Montant demandé (MAD) *", "number")}${T("request", "duration_months", "Durée (mois) *", "number")}${T("request", "purpose", "Objet du financement")}</div>`)}
      ${card("3. Informations financières (MAD)", `<div class="fg">${T("financials", "fiscal_year", "Exercice")}${T("financials", "revenue_n", "CA exercice N", "number")}${T("financials", "revenue_n1", "CA exercice N-1", "number")}
        ${T("financials", "revenue_bank", "CA selon relevés bancaires", "number", "Contrôle de cohérence")}${T("financials", "net_result", "Résultat net", "number")}${T("financials", "equity", "Fonds propres", "number")}
        ${T("financials", "existing_debt", "Dettes financières existantes", "number")}${T("financials", "existing_monthly_installments", "Mensualités existantes", "number")}</div>`)}
      ${card("4. Pièces justificatives – grille de vérification (C01)", docs)}
      ${card("5. Garanties", `<div class="fg">${S("guarantees", "type", "Nature de la garantie", GUARANTEE_TYPES)}${T("guarantees", "value", "Valeur estimée (MAD)", "number")}${T("guarantees", "description", "Description")}</div>`)}
      ${card("6. Observations de l'analyste", `<textarea data-d="observations" ${w ? "" : "disabled"} placeholder="Appréciation motivée, éléments vérifiés, points restant à confirmer…">${esc(d.observations)}</textarea>`)}
    </div><div class="sticky"><div id="analysis">${analysisPanel()}</div>
      <div class="right">${w ? `<button class="btn" data-act="dos-save">Enregistrer et analyser</button>${ui.dossier ? `<button class="btn danger" data-act="dos-del">Supprimer</button>` : ""}` : ""}
      ${ui.dossier && can("anomalies.create") ? `<button class="btn ghost" data-act="dos-anom">Inscrire l'anomalie (C04)</button>` : ""}
      ${ui.dossier ? `<button class="btn em" data-act="ask" data-q="Analyse le dossier ${ui.dossier} : complétude, incohérences, vigilance, risques concernés et diligences à mener avant l'avis de la fonction risques.">✦ Synthèse Risk Advisor</button>` : ""}</div></div></div>`;
}

function analysisPanel() {
  const a = analyzeDossier(ui.draft);
  const ic = (s: string) => (s === "alerte" ? "🔴" : s === "attention" ? "🟠" : "🔵");
  const sec = (t: string, items: any[]) => (items.length ? `<h4>${t} (${items.length})</h4><ul class="find">${items.map((i) => `<li>${ic(i.severity)} ${esc(i.message)} ${i.risk ? `<small>(${i.risk})</small>` : ""}</li>`).join("")}</ul>` : "");
  return card("Résultat de l'analyse", `<p class="muted s">Aide à l'analyse – aucune décision d'octroi</p><div class="status ${a.blocking ? "bad" : "ok"}">${a.blocking ? "⛔" : "✅"} ${a.status}</div>
    <p class="s">Complétude documentaire : ${a.completeness.present}/${a.completeness.required}</p><div class="bar"><i style="width:${a.completeness.rate}%"></i></div>
    ${sec("Pièces manquantes", a.completeness.missingDocs.map((m) => ({ message: m, severity: "alerte" })))}${sec("Incohérences", a.inconsistencies)}${sec("Informations manquantes", a.missingInfo)}${sec("Points de vigilance", a.vigilance)}
    ${a.ratios.length ? `<h4>Ratios calculés (seuils indicatifs)</h4>${a.ratios.map((r) => `<div class="kv"><span>${esc(r.label)}</span><b>${esc(r.value)}</b></div>`).join("")}` : ""}
    ${a.linkedRisks.length ? `<p>Risques concernés : ${a.linkedRisks.map((x) => badge(x, "brand")).join(" ")}</p>` : ""}
    <h4>Synthèse d'analyse</h4><p>${esc(a.synthesis)}</p><div class="note">${esc(a.disclaimer)}</div>`);
}

/* ---------------------------------------------------------------- COSO */
function pCoso() {
  const w = can("coso.write");
  const comp = state.components.find((c) => c.id === ui.cosoTab)!;
  const pr = state.principles.filter((p) => p.component_id === comp.id);
  const col: Record<string, string> = { Déficient: "bad", Partiel: "warn", Satisfaisant: "ok", "Non évalué": "" };
  const cnt = (a: string) => state.principles.filter((p) => p.assessment === a).length;
  return header("⌂", "Diagnostic COSO 2013", "Cinq composantes et dix-sept principes : constats, lacunes, risques, recommandations, responsables et indicateurs de suivi.") +
    (w ? "" : readonly("Consultation seule : le diagnostic COSO est mis à jour par le contrôle interne et l'administrateur.")) +
    `<div class="g2">${card("Maturité par composante (1 à 5)", state.components.map((c) => `<div class="ind"><div><span>${c.id}. ${esc(c.name)}</span><b>${c.maturity}/5</b></div><div class="bar"><i style="width:${c.maturity * 20}%"></i></div></div>`).join(""))}
    ${card("Appréciation des 17 principes", `<div class="kpis small">${["Déficient", "Partiel", "Satisfaisant", "Non évalué"].map((a) => kpi(a, cnt(a), "principes", col[a] === "bad" ? "red" : col[a] === "warn" ? "amber" : col[a] === "ok" ? "green" : "brand")).join("")}</div>
      <div class="pgrid">${state.principles.map((p) => `<button class="pchip ${col[p.assessment]} ${p.component_id === comp.id ? "sel" : ""}" data-act="coso-tab" data-id="${p.component_id}" title="${esc(p.title)} : ${p.assessment}">${p.id}</button>`).join("")}</div>`)}</div>
    <div class="tabs">${state.components.map((c) => `<button class="${c.id === comp.id ? "on" : ""}" data-act="coso-tab" data-id="${c.id}">${c.id}. ${esc(c.name)}</button>`).join("")}</div>
    <div class="g2w">${card(`${comp.id}. ${esc(comp.name)} (${esc(comp.principles)})`, `<p class="muted"><i>${esc(comp.question)}</i></p>
      <div class="g2 tight"><div><h4>Constats</h4><p>${esc(comp.findings)}</p></div><div class="box bad"><h4>Lacunes identifiées</h4><p>${esc(comp.gaps)}</p></div>
      <div><h4>Risques associés</h4><p>${splitIds(comp.risk_ids).map((r) => badge(r, "brand")).join(" ")}</p><h4>Responsables</h4><p>${esc(comp.owner)}</p></div>
      <div class="box ok"><h4>Recommandations</h4><p>${esc(comp.recommendations)}</p></div><div><h4>Indicateurs de suivi</h4><p>${esc(comp.indicators)}</p></div>
      <div><h4>Maturité</h4><p><b>${comp.maturity}/5</b> ${demo(comp)}</p></div></div>${w ? `<div class="right"><button class="btn ghost" data-act="coso-edit" data-id="${comp.id}">Modifier la composante</button></div>` : ""}`)}
    ${card("Principes de la composante", pr.map((p) => `<div class="princ"><div><b class="pid">${p.id}</b> ${esc(p.title)}<div>${badge(p.assessment, col[p.assessment])} ${badge(p.nature, "violet")} ${splitIds(p.risk_ids).map((r) => badge(r, "brand")).join(" ")}</div><small>${esc(p.diagnostic)}</small></div>
      ${w ? `<select data-act-change="assess" data-id="${p.id}" aria-label="Appréciation ${p.id}">${["Non évalué", "Déficient", "Partiel", "Satisfaisant"].map((a) => `<option ${a === p.assessment ? "selected" : ""}>${a}</option>`).join("")}</select>` : ""}</div>`).join(""))}</div>`;
}

/* ---------------------------------------------------------------- contrôles */
const CTRL_FIELDS: Field[] = [
  { k: "name", l: "Intitulé du contrôle", req: true, full: true },
  { k: "nature", l: "Type de contrôle", t: "select", o: ["Préventif", "Détectif", "Correctif", "Détectif et correctif"] },
  { k: "status", l: "Statut", t: "select", o: ["À concevoir", "En déploiement", "Opérationnel", "Efficace", "Déficient"] },
  { k: "objective", l: "Objectif du contrôle", t: "textarea", req: true },
  { k: "risk_ids", l: "Risque(s) couvert(s)", hint: "Ex. : R01, R08" },
  { k: "owner", l: "Responsable", req: true },
  { k: "procedure", l: "Description de la procédure", t: "textarea" },
  { k: "supervision", l: "Supervision" },
  { k: "frequency", l: "Fréquence", req: true },
  { k: "evidence", l: "Preuve attendue", t: "textarea" },
  { k: "indicator", l: "Indicateur de performance", t: "textarea" },
  { k: "anomaly_treatment", l: "Traitement des anomalies", t: "textarea" },
  { k: "last_review", l: "Dernière revue", t: "date" },
];
function pControles() {
  const w = can("controls.write"), r = snapshot().risks;
  const matrix = table(["Risque", ...state.controls.map((c) => c.id), "Couverture"], r.map((x) => {
    const n = state.controls.filter((c) => splitIds(c.risk_ids).includes(x.id)).length;
    return [`<b>${x.id}</b> <small>${esc(x.title.slice(0, 42))}</small> ${pill(x.level)}`, ...state.controls.map((c) => (splitIds(c.risk_ids).includes(x.id) ? `<b class="ok-t">●</b>` : "")),
      badge(n === 0 ? "Non couvert" : n === 1 ? "1 – dépendance" : `${n} contrôles`, n === 0 ? "bad" : n === 1 ? "warn" : "ok")];
  }), "center");
  return header("⛨", "Contrôle interne – fiches de contrôle", "Objectif, risque couvert, type, procédure, responsable, fréquence, preuve attendue, indicateur et traitement des anomalies.", w ? `<button class="btn" data-act="ctrl-new">+ Nouvelle fiche</button>` : "") +
    (w ? "" : readonly("Consultation seule : les fiches sont gérées par le contrôle interne et l'administrateur.")) +
    card("Matrice de couverture risques × contrôles", matrix + `<p class="muted s">Un risque couvert par un seul contrôle constitue un point de dépendance à surveiller en priorité.</p>`) +
    `<div class="g2">${state.controls.map((c) => card(`${c.id} · ${esc(c.name)}`, `<div class="row-b">${badge(c.nature, "violet")} ${badge(c.status, tone(c.status))} ${splitIds(c.risk_ids).map((x) => badge(x, "brand")).join(" ")} ${demo(c)}</div>
      <dl>${[["Objectif", c.objective], ["Procédure", c.procedure], ["Responsable", c.owner], ["Supervision", c.supervision], ["Fréquence", c.frequency], ["Preuve attendue", c.evidence], ["Indicateur", c.indicator], ["Traitement des anomalies", c.anomaly_treatment], ["Dernière revue", c.last_review || "–"]]
        .map(([k, v]) => `<dt>${k}</dt><dd>${esc(v) || "–"}</dd>`).join("")}</dl>${w ? `<div class="right"><button class="btn ghost sm" data-act="ctrl-edit" data-id="${c.id}">Modifier</button><button class="btn danger sm" data-act="ctrl-del" data-id="${c.id}">Supprimer</button></div>` : ""}`)).join("")}</div>`;
}

/* ---------------------------------------------------------------- suivi */
const ACT_FIELDS: Field[] = [
  { k: "title", l: "Intitulé de l'action", req: true, full: true }, { k: "priority", l: "Priorité", t: "select", o: ["P1", "P2", "P3"] },
  { k: "status", l: "Statut", t: "select", o: ["À faire", "En cours", "Terminé", "Bloqué"] }, { k: "owner", l: "Responsable", req: true }, { k: "due", l: "Échéance" },
  { k: "deliverable", l: "Livrable / preuve", full: true }, { k: "risk_ids", l: "Risques traités" }, { k: "control_ids", l: "Contrôles concernés" },
  { k: "progress", l: "Avancement (%)", t: "range", min: 0, max: 100 },
];
const REC_FIELDS: Field[] = [
  { k: "risk_id", l: "RISQUE", req: true, hint: "Ex. : R03" }, { k: "status", l: "Statut", t: "select", o: ["À lancer", "En cours", "Mise en œuvre", "Abandonnée"] },
  { k: "coso_gap", l: "LACUNE COSO", t: "textarea", req: true }, { k: "action", l: "ACTION CORRECTIVE", t: "textarea", req: true },
  { k: "owner", l: "RESPONSABLE", req: true }, { k: "basis", l: "Fondement", t: "select", o: ["Constat", "Hypothèse"] }, { k: "indicator", l: "INDICATEUR DE SUIVI", t: "textarea", req: true },
];
const ANOM_FIELDS: Field[] = [
  { k: "detected_on", l: "Date de détection", t: "date", req: true }, { k: "dossier_ref", l: "Dossier / référence" }, { k: "nature", l: "Nature de l'anomalie", t: "textarea", req: true },
  { k: "severity", l: "Gravité", t: "select", o: ["Mineure", "Significative", "Majeure", "Critique"] }, { k: "status", l: "Statut", t: "select", o: ["Ouverte", "En cours", "Clôturée"] },
  { k: "risk_id", l: "Risque lié", hint: "Ex. : R01" }, { k: "control_id", l: "Contrôle lié", hint: "Ex. : C04" }, { k: "owner", l: "Responsable du traitement", req: true },
  { k: "due_on", l: "Échéance de régularisation", t: "date" }, { k: "escalation", l: "Niveau d'escalade (charte, art. 11)", t: "range", min: 1, max: 3 }, { k: "resolution", l: "Résolution / preuve de clôture", t: "textarea" },
];
function pSuivi() {
  const t = ui.suiviTab, td = today();
  const tabs = `<div class="tabs">${[["actions", "Plan d'action"], ["recos", "Recommandations"], ["anoms", "Anomalies"]].map(([k, l]) => `<button class="${t === k ? "on" : ""}" data-act="suivi-tab" data-id="${k}">${l}</button>`).join("")}</div>`;
  let body = "";
  if (t === "actions") {
    const w = can("actions.write"), a = snapshot().actions;
    body = `<div class="kpis small">${kpi("Avancement moyen", `${a.length ? Math.round(a.reduce((x, y) => x + Number(y.progress), 0) / a.length) : 0} %`, `${a.filter((x) => x.status !== "Terminé").length} action(s) ouverte(s)`, "brand")}${kpi("Actions P1 ouvertes", a.filter((x) => x.priority === "P1" && x.status !== "Terminé").length, "Conditionnent le reste du dispositif", "red")}</div>` +
      (w ? `<div class="right"><button class="btn" data-act="act-new">+ Nouvelle action</button></div>` : readonly("Le pilotage du plan d'action est réservé à la direction, aux risques et au contrôle interne.")) +
      card("", table(["Prio.", "Action", "Responsable", "Échéance", "Livrable", "Liens", "Statut", "Avancement", ""], a.map((x) => [badge(x.priority, x.priority === "P1" ? "bad" : x.priority === "P2" ? "warn" : ""), `<b>${x.id}</b> ${esc(x.title)} ${demo(x)}`, `<small>${esc(x.owner)}</small>`, `<small>${esc(x.due)}</small>`, `<small>${esc(x.deliverable)}</small>`, `<small>${esc(x.risk_ids)}<br>${esc(x.control_ids)}</small>`, badge(x.status, tone(x.status)), `<div class="bar"><i style="width:${x.progress}%"></i></div><small>${x.progress} %</small>`, w ? `<button class="btn ghost sm" data-act="act-edit" data-id="${x.id}">Modifier</button>` : ""])));
  } else if (t === "recos") {
    const w = can("recommendations.write");
    body = (w ? `<div class="right"><button class="btn" data-act="rec-new">+ Nouvelle recommandation</button></div>` : "") + state.recommendations.map((x) => card("", `<div class="row-b"><b>${x.id}</b> ${badge(x.status, tone(x.status))} ${badge(x.basis, "warn")} ${demo(x)} ${w ? `<button class="btn ghost sm" data-act="rec-edit" data-id="${x.id}">Modifier</button>` : ""}</div>
      <div class="chain">${[["RISQUE", x.risk_id], ["LACUNE COSO", x.coso_gap], ["ACTION CORRECTIVE", x.action], ["RESPONSABLE", x.owner], ["INDICATEUR DE SUIVI", x.indicator]].map(([k, v]) => `<div><b>${k}</b>${esc(v)}</div>`).join("")}</div>`)).join("");
  } else {
    const an = snapshot().anomalies, open = an.filter((x) => x.status !== "Clôturée"), late = open.filter((x) => x.due_on && x.due_on < td);
    body = `<div class="kpis small">${kpi("Anomalies", an.length, "au registre", "brand")}${kpi("Ouvertes", open.length, "non clôturées", "amber")}${kpi("En retard", late.length, "échéance dépassée", "red")}${kpi("Niveau 3", open.filter((x) => Number(x.escalation) === 3).length, "remontée direction générale", "red")}</div>` +
      `<div class="right">${can("anomalies.create") ? `<button class="btn" data-act="anom-new">+ Déclarer une anomalie</button>` : ""}</div>` +
      card("", table(["ID", "Détectée", "Dossier", "Nature", "Gravité", "Risque / contrôle", "Responsable", "Échéance", "Escalade", "Statut", ""], an.map((x) => {
        const isLate = x.status !== "Clôturée" && x.due_on && x.due_on < td;
        return [`<b>${x.id}</b> ${demo(x)}`, `<small>${x.detected_on}</small>`, `<small>${esc(x.dossier_ref)}</small>`, `<small>${esc(x.nature)}${x.resolution ? `<br><span class="ok-t">✓ ${esc(x.resolution)}</span>` : ""}</small>`,
          badge(x.severity, x.severity === "Critique" ? "bad" : x.severity === "Majeure" ? "warn" : ""), `<small>${esc(x.risk_id)} ${x.control_id ? "/ " + esc(x.control_id) : ""}</small>`, `<small>${esc(x.owner)}</small>`,
          `<small class="${isLate ? "bad-t" : ""}">${x.due_on || "–"}${isLate ? " (retard)" : ""}</small>`, badge("N" + x.escalation, Number(x.escalation) === 3 ? "bad" : Number(x.escalation) === 2 ? "warn" : ""), badge(x.status, tone(x.status)),
          can("anomalies.write") ? `<button class="btn ghost sm" data-act="anom-edit" data-id="${x.id}">Traiter</button>` : ""];
      })));
  }
  return header("✓", "Suivi des recommandations et des anomalies", "Plan d'action priorisé, chaînes de recommandations (Risque → Lacune COSO → Action → Responsable → Indicateur) et registre unique des anomalies (C04).") + tabs + body;
}

/* ---------------------------------------------------------------- gouvernance */
function pGouv() {
  const actors = SEED.raci_actors, acts = SEED.raci_activities;
  const cls: Record<string, string> = { R: "r", A: "a", "A/R": "ar", C: "c", I: "i", "–": "n" };
  const blocks = ["Constitution", "Analyse / contrôle", "Autorisation"];
  const isRA = (c: string) => ["R", "A", "A/R"].includes(c);
  const singleA = acts.filter((a: Row) => Object.values(a.roles).filter((c: any) => c === "A" || c === "A/R").length === 1).length;
  const checks = actors.map((x: Row) => ({ label: x.label, b: blocks.filter((b) => acts.some((a: Row) => a.block === b && isRA(a.roles[x.key]))) }));
  const ok = singleA === acts.length && checks.every((c: Row) => c.b.length < 3);
  const groups: string[] = Array.from(new Set(actors.map((a: Row) => a.group)));
  return header("⇄", "Gouvernance et matrice RACI", "R = Responsible (réalise) · A = Accountable (valide) · C = Consulted · I = Informed. Séparation des tâches et délégations d'autorisation.") +
    card("Matrice RACI des décisions (14 activités × 6 acteurs)", `<div class="tw"><table class="raci"><thead><tr><th rowspan="2">Activité</th><th rowspan="2">Bloc</th>${groups.map((g) => `<th colspan="${actors.filter((a: Row) => a.group === g).length}" class="c">${esc(g)}</th>`).join("")}</tr>
      <tr>${actors.map((a: Row) => `<th class="c">${esc(a.label)}</th>`).join("")}</tr></thead><tbody>${acts.map((a: Row) => `<tr><td>${a.n}. ${esc(a.activity)}</td><td>${badge(a.block)}</td>${actors.map((x: Row) => `<td class="c"><span class="raci-c ${cls[a.roles[x.key]]}">${a.roles[x.key]}</span></td>`).join("")}</tr>`).join("")}</tbody></table></div>`) +
    `<div class="g2">${card("Contrôle automatique de la séparation des tâches", `<div class="status ${ok ? "ok" : "bad"}">${ok ? "✅ Séparation respectée : aucun acteur ne cumule constitution, analyse et autorisation." : "⛔ Conflit de séparation des tâches."}</div>
      <p>${singleA === acts.length ? "✅" : "❌"} Une seule responsabilité finale (A) par activité : ${singleA}/${acts.length}</p>${checks.map((c: Row) => `<p>${c.b.length === 3 ? "❌" : "✅"} <b>${esc(c.label)}</b> <small>— R/A sur : ${c.b.join(", ") || "aucun bloc critique"}</small></p>`).join("")}
      <p class="muted s">L'avis des risques (6) et l'autorisation (7) sont distincts ; le décaissement (8) relève de la finance, la direction étant seulement informée.</p>`)}
    ${card("Délégations d'autorisation", table(["Décision", "Réalise", "Valide", "Est informé"], SEED.delegations.map((d: Row) => [`<b>${esc(d.decision)}</b>`, `<small>${esc(d.realise)}</small>`, `<small>${esc(d.valide)}</small>`, `<small>${esc(d.informe)}</small>`])) + `<p class="muted s">Les plafonds chiffrés de délégation ne sont pas fournis par le cas (action A01).</p>`)}</div>` +
    card("Traduction applicative : droits par rôle (contrôle C03)", table(["Droit", ...Object.values(ROLES)], Object.entries(PERMS).map(([p, roles]) => [PERM_LABELS[p], ...Object.keys(ROLES).map((r) => (roles.includes(r) ? `<b class="ok-t">✓</b>` : `<span class="muted">–</span>`))]), "center"));
}

/* ---------------------------------------------------------------- appétence */
function pAppetence() {
  const r = snapshot().risks;
  const zone = (l: Level) => (l === "Critique" ? "inacceptable" : l === "Élevé" ? "renforcee" : "acceptable");
  return header("◎", "Charte d'appétence au risque", "Charte qualitative : ce que Crédit Horizon accepte, accepte sous conditions ou refuse. Sans modèle PD/LGD ; les seuils chiffrés seront fixés par la direction.") +
    `<div class="g3">${SEED.appetite_levels.map((l: Row) => `<section class="card app ${l.key}"><h2>${l.key === "acceptable" ? "✅" : l.key === "renforcee" ? "⚠️" : "⛔"} ${esc(l.title)}</h2><p>${esc(l.description)}</p><ul>${l.examples.map((e: string) => `<li>${esc(e)}</li>`).join("")}</ul>
      <h4>Risques du registre dans cette zone</h4><p>${r.filter((x) => zone(x.level) === l.key).sort((a, b) => b.score - a.score).map((x) => pill(x.level, x.score).replace(x.level, x.id + " " + x.level)).join(" ") || "<i>aucun</i>"}</p></section>`).join("")}</div>
    <p class="muted s">Lecture applicative : Faible/Modéré → acceptable sous contrôle ; Élevé → autorisation renforcée ; Critique → hors appétence en l'état, renforcement immédiat.</p>
    <div class="g2">${card("Principes généraux (article 3)", `<ol>${SEED.charter_principles.map((p: string) => `<li>${esc(p)}</li>`).join("")}</ol>`)}
    ${card("Mécanismes d'escalade (article 11)", SEED.escalation.map((e: Row) => `<p><span class="lvl l${e.level}">N${e.level}</span> <b>${esc(e.title)}</b><br><small>${esc(e.text)}</small></p>`).join(""))}</div>` +
    card("Appétence par catégorie de risque", table(["Catégorie", "Appétence qualitative", "Limites et situations inacceptables"], SEED.appetite_by_category.map((c: Row) => [`<b>${c.category}</b>`, esc(c.appetite), `<span class="bad-t">${esc(c.limits)}</span>`])));
}

/* ---------------------------------------------------------------- assistant */
const CAPS = [
  ["Analyser le registre", "Analyse l'ensemble du registre des risques : risques prioritaires, répartition et couverture par les contrôles."],
  ["Expliquer les scores P × G", "Explique les scores P × G de chaque risque du registre."],
  ["Risques prioritaires", "Identifie les risques prioritaires et justifie l'ordre de traitement."],
  ["Relier aux principes COSO", "Relie chaque risque aux principes COSO 2013 concernés."],
  ["Incohérences documentaires", "Détecte les incohérences documentaires et les pièces manquantes dans les dossiers TPE."],
  ["Proposer des contrôles", "Propose des contrôles internes et identifie les risques insuffisamment couverts."],
  ["Recommandations", "Génère des recommandations au format RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI."],
  ["Plan d'action", "Construis le plan d'action priorisé à partir de l'avancement actuel."],
  ["Analyser les anomalies", "Analyse les anomalies : tendances, retards et escalades."],
  ["Synthèse exécutive", "Rédige une synthèse exécutive de la situation des risques et du contrôle interne."],
  ["Rapport de gestion des risques", "Prépare un rapport de gestion des risques : synthèse, recommandations et plan d'action."],
];
function pAssistant() {
  return header("✦", "Risk Advisor – Assistant", "Consultant virtuel en gestion des risques et COSO 2013. Il raisonne uniquement sur les données enregistrées dans la plateforme et ne prend aucune décision d'octroi.",
    ui.chat.length ? `<button class="btn ghost" data-act="chat-reset">Nouvelle conversation</button>` : "") +
    `<div class="note">Cette version autonome fonctionne sans serveur : les réponses sont produites par le moteur d'analyse intégré, à partir des données réelles de la plateforme. La version Streamlit se connecte au modèle Claude lorsqu'une clé API est configurée.</div>
    <div class="caps">${CAPS.map(([l, q]) => `<button data-act="ask" data-q="${esc(q)}">${l}</button>`).join("")}</div>
    <div class="chat" id="chat">${ui.chat.map((m: Row) => `<div class="msg ${m.role}">${m.role === "user" ? esc(m.content) : `<div class="md">${md(m.content)}</div>`}</div>`).join("") || `<p class="muted c">Choisissez une analyse ou posez votre question.</p>`}</div>
    <form id="askf" class="askf"><input id="askq" placeholder="Ex. : Pourquoi R03 est-il le risque le plus critique ? Quels contrôles pour R07 ?" autocomplete="off"><button class="btn">Envoyer</button></form>`;
}

/* ---------------------------------------------------------------- rapports */
function pRapports() {
  return header("⇩", "Rapports et exportations", "Exports générés à partir des données enregistrées au moment de l'export.") +
    `<div class="g3">${[
      ["exp-risks", "Registre des risques (CSV)", "Séparateur « ; », UTF-8, compatible Excel et Power BI."],
      ["exp-controls", "Fiches de contrôle (CSV)", "Les huit contrôles et leurs attributs."],
      ["exp-coso", "Diagnostic COSO (CSV)", "Les 17 principes et leur appréciation."],
      ["exp-recos", "Recommandations (CSV)", "Chaînes Risque → Lacune → Action → Responsable → Indicateur."],
      ["exp-actions", "Plan d'action (CSV)", "Actions priorisées et avancement."],
      ["exp-anoms", "Anomalies (CSV)", "Registre unique des anomalies (C04)."],
      ["exp-json", "Sauvegarde complète (JSON)", "Toutes les données de la plateforme, réimportables."],
      ["exp-print", "Synthèse imprimable", "Ouvre une synthèse exécutive mise en page pour l'impression ou le PDF."],
    ].map(([a, t, d]) => `<button class="card exp" data-act="${a}"><b>${t}</b><small>${d}</small></button>`).join("")}</div>
    <div class="note">Le rapport PDF complet (registre, cartographie, contrôles, COSO, RACI, recommandations, plan d'action) est fourni avec ce site : <b>Credit_Horizon_Rapport_Risques.pdf</b>.</div>
    ${card("Importer une sauvegarde", `<input type="file" id="imp" accept="application/json"><p class="muted s">Restaure un fichier JSON exporté depuis cette plateforme.</p>`)}`;
}

/* ---------------------------------------------------------------- administration */
function pAdmin() {
  if (!can("audit.view")) return header("⚙", "Administration", "") + readonly("L'administration est réservée à l'administrateur, au directeur et au contrôleur interne.");
  return header("⚙", "Administration", "Rôles, journal d'audit et données de démonstration.", can("demo.reset") ? `<button class="btn danger" data-act="reset">Réinitialiser les données de démonstration</button>` : "") +
    card("Rôles disponibles", table(["Rôle", "Droits"], Object.entries(ROLES).map(([k, l]) => [`<b>${l}</b>`, Object.entries(PERMS).filter(([, r]) => r.includes(k)).map(([p]) => badge(PERM_LABELS[p])).join(" ")]))) +
    card(`Journal d'audit (${state.audit.length})`, state.audit.length ? table(["Date", "Utilisateur", "Action", "Objet", "Détail"], state.audit.slice(0, 200).map((a) => [`<small>${new Date(a.at).toLocaleString("fr-FR")}</small>`, `<small>${esc(a.user)} (${ROLES[a.role] || "–"})</small>`, badge(a.action, a.action === "Suppression" ? "bad" : a.action.startsWith("Création") ? "ok" : ""), `${esc(a.entity)} <b>${esc(a.id)}</b>`, `<small>${esc(a.details)}</small>`])) : `<p class="muted">Aucune opération enregistrée.</p>`);
}

/* ================================================================ rendu */
const PAGES: Record<string, () => string> = { dashboard: pDashboard, registre: pRegistre, cartographie: pCarto, dossiers: pDossiers, coso: pCoso, controles: pControles, suivi: pSuivi, gouvernance: pGouv, appetence: pAppetence, assistant: pAssistant, rapports: pRapports, administration: pAdmin };
const LOGO = `<div class="logo"><svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#0a4d38"/><path d="M12 42 Q32 14 52 42" fill="none" stroke="#10b981" stroke-width="5" stroke-linecap="round"/><path d="M8 46h48" stroke="#d1fae5" stroke-width="4" stroke-linecap="round"/><circle cx="32" cy="24" r="5" fill="#34d399"/></svg><div><b>CRÉDIT HORIZON</b><small>RISK INTELLIGENCE</small></div></div>`;

function route() {
  const h = location.hash.replace("#", "");
  return PAGES[h] ? h : "dashboard";
}

function render() {
  const app = document.getElementById("app")!;
  if (!state.user) {
    app.innerHTML = pLogin();
    return;
  }
  const cur = route();
  app.innerHTML = `<aside id="side">${LOGO}<nav>${NAV.map((g) => `<div class="ng">${g.group}</div>${g.items.map(([k, l, i]) => `<a href="#${k}" class="${k === cur ? "on" : ""}"><i>${i}</i>${l}</a>`).join("")}`).join("")}</nav>
    <div class="me"><b>${esc(state.user.name)}</b><small>${ROLES[state.user.role]}</small><button data-act="logout">Changer de rôle</button></div></aside>
    <div class="main"><header class="top"><button class="burger" data-act="menu" aria-label="Menu">☰</button>${LOGO}</header>
    <div class="demo-bar">🧪 <b>Environnement de démonstration</b> – cas académique fictif EMSI. Les éléments marqués « Démo » sont des données de démonstration.</div>
    <main>${PAGES[cur]()}</main><footer>CRÉDIT HORIZON RISK INTELLIGENCE · Projet EMSI · Aide à la décision : aucune décision d'octroi automatique</footer></div>`;
  if (cur === "registre") applyFilter();
  const chat = document.getElementById("chat");
  if (chat) chat.scrollTop = chat.scrollHeight;
}

function applyFilter() {
  const q = ui.filter.toLowerCase().trim();
  let n = 0;
  document.querySelectorAll<HTMLTableRowElement>("#rtable tbody tr").forEach((tr) => {
    const show = !q || (tr.dataset.text || "").includes(q);
    tr.style.display = show ? "" : "none";
    if (show) n++;
  });
  const c = document.getElementById("qcount");
  if (c) c.textContent = `${n} risque(s)`;
}

function ask(q: string) {
  ui.chat.push({ role: "user", content: q });
  ui.chat.push({ role: "assistant", content: offlineAnswer(snapshot() as any, q, ui.dossier && /dossier/i.test(q) ? ui.dossier : undefined) });
  audit("Requête IA", "Risk Advisor", "", q.slice(0, 200));
  save();
  if (route() !== "assistant") location.hash = "assistant";
  else render();
}

function validate(fields: Field[], v: Row) {
  const miss = fields.filter((f) => f.req && !String(v[f.k] ?? "").trim()).map((f) => f.l);
  return miss.length ? "Champs obligatoires manquants : " + miss.join(", ") : "";
}

function crudModal(kind: string, rows: Row[], fields: Field[], label: string, prefix: string, pad: number, sep: string, row: Row | null, defaults: Row = {}) {
  openModal(row ? `Modifier ${row.id}` : `Nouveau : ${label}`, fields, row ? { ...row } : defaults, (v) => {
    const err = validate(fields, v);
    if (err) return err;
    for (const f of fields) if (f.t === "range") v[f.k] = Number(v[f.k]);
    if (row) {
      const before = { ...row };
      Object.assign(row, v);
      if (kind === "risk" && (before.probability !== row.probability || before.gravity !== row.gravity))
        state.history.push({ risk_id: row.id, probability: row.probability, gravity: row.gravity, score: row.probability * row.gravity, recorded_at: new Date().toISOString() });
      audit("Modification", label, row.id);
      toast(`${label} ${row.id} mis(e) à jour.`);
    } else {
      const id = nextId(rows, prefix, pad, sep);
      const nr = { id, ...v, is_demo: false, ...(kind === "anom" ? { declared_by: state.user!.name } : {}) };
      rows.push(nr);
      if (kind === "risk") {
        state.history.push({ risk_id: id, probability: nr.probability, gravity: nr.gravity, score: nr.probability * nr.gravity, recorded_at: new Date().toISOString() });
        ui.selRisk = id;
      }
      audit("Création", label, id);
      toast(`${label} ${id} créé(e).`);
    }
    save();
  });
}

/* ================================================================ événements */
document.addEventListener("click", (e) => {
  const el = (e.target as HTMLElement).closest<HTMLElement>("[data-act]");
  if (!el) {
    if (!(e.target as HTMLElement).closest("#side") && document.body.classList.contains("menu")) document.body.classList.remove("menu");
    return;
  }
  const act = el.dataset.act!, id = el.dataset.id!;
  const find = (rows: Row[]) => rows.find((r) => String(r.id) === id) || null;
  switch (act) {
    case "login":
      state.user = { role: el.dataset.role, name: SEED.demo_users.find((u: Row) => u.role === el.dataset.role).name };
      audit("Connexion", "Session", el.dataset.role!);
      save();
      location.hash = "dashboard";
      return render();
    case "logout":
      state.user = null;
      save();
      return render();
    case "menu":
      return document.body.classList.toggle("menu");
    case "close-modal":
      return closeModal();
    case "sel-risk":
      ui.selRisk = id;
      return render();
    case "risk-new":
      return crudModal("risk", state.risks, RISK_FIELDS, "Risque", "R", 2, "", null, { category: "Crédit", basis: "Constat", probability: 3, gravity: 3 });
    case "risk-edit":
      return crudModal("risk", state.risks, RISK_FIELDS, "Risque", "R", 2, "", find(state.risks));
    case "risk-del":
      return confirmBox(`Supprimer définitivement le risque ${id} ?`, () => {
        state.risks = state.risks.filter((r) => r.id !== id);
        state.history = state.history.filter((h) => h.risk_id !== id);
        ui.selRisk = null;
        audit("Suppression", "Risque", id);
        save();
        toast(`Risque ${id} supprimé.`);
        render();
      });
    case "ctrl-new":
      return crudModal("ctrl", state.controls, CTRL_FIELDS, "Contrôle", "C", 2, "", null, { nature: "Préventif", status: "À concevoir" });
    case "ctrl-edit":
      return crudModal("ctrl", state.controls, CTRL_FIELDS, "Contrôle", "C", 2, "", find(state.controls));
    case "ctrl-del":
      return confirmBox(`Supprimer la fiche ${id} ?`, () => {
        state.controls = state.controls.filter((r) => r.id !== id);
        audit("Suppression", "Contrôle", id);
        save();
        render();
      });
    case "act-new":
      return crudModal("act", state.actions, ACT_FIELDS, "Action", "A", 2, "", null, { priority: "P2", status: "À faire", progress: 0 });
    case "act-edit":
      return crudModal("act", state.actions, ACT_FIELDS, "Action", "A", 2, "", find(state.actions));
    case "rec-new":
      return crudModal("rec", state.recommendations, REC_FIELDS, "Recommandation", "REC", 2, "", null, { status: "À lancer", basis: "Constat" });
    case "rec-edit":
      return crudModal("rec", state.recommendations, REC_FIELDS, "Recommandation", "REC", 2, "", find(state.recommendations));
    case "anom-new":
      return crudModal("anom", state.anomalies, ANOM_FIELDS, "Anomalie", "AN", 3, "-", null, { detected_on: today(), severity: "Significative", status: "Ouverte", escalation: 1 });
    case "anom-edit":
      return crudModal("anom", state.anomalies, ANOM_FIELDS, "Anomalie", "AN", 3, "-", find(state.anomalies));
    case "suivi-tab":
      ui.suiviTab = id;
      return render();
    case "coso-tab":
      ui.cosoTab = Number(id);
      return render();
    case "coso-edit": {
      const c = state.components.find((x) => x.id === Number(id))!;
      openModal(`Modifier – ${c.name}`, [
        { k: "findings", l: "Constats", t: "textarea" }, { k: "gaps", l: "Lacunes", t: "textarea" }, { k: "risk_ids", l: "Risques associés" }, { k: "owner", l: "Responsables" },
        { k: "recommendations", l: "Recommandations", t: "textarea" }, { k: "indicators", l: "Indicateurs de suivi", t: "textarea" }, { k: "maturity", l: "Maturité (1 à 5)", t: "range", min: 1, max: 5 },
      ], { ...c }, (v) => {
        Object.assign(c, v, { maturity: Number(v.maturity) });
        audit("Modification", "Composante COSO", String(c.id));
        save();
        toast("Composante mise à jour.");
      });
      return;
    }
    case "dos-open":
      ui.dossier = id;
      ui.draft = null;
      return render();
    case "dos-new":
      ui.dossier = null;
      ui.draft = EMPTY_D();
      return render();
    case "doc":
      ui.draft.documents[el.dataset.k!] = el.dataset.v;
      el.parentElement!.querySelectorAll("button").forEach((b) => (b.className = ""));
      el.className = "on " + el.dataset.v;
      document.getElementById("analysis")!.innerHTML = analysisPanel();
      return;
    case "dos-save": {
      if (!String(ui.draft.company.name).trim()) return toast("La raison sociale est obligatoire.", true);
      const a = analyzeDossier(ui.draft);
      if (ui.dossier) {
        const d = state.dossiers.find((x) => x.id === ui.dossier)!;
        Object.assign(d, JSON.parse(JSON.stringify(ui.draft)), { analysis: a, status: a.status });
        audit("Modification + réanalyse", "Dossier TPE", d.id, a.status);
      } else {
        const nid = nextId(state.dossiers.filter((x) => x.id.startsWith(`TPE-${new Date().getFullYear()}`)), `TPE-${new Date().getFullYear()}`, 3, "-");
        state.dossiers.unshift({ id: nid, ...JSON.parse(JSON.stringify(ui.draft)), analysis: a, status: a.status, created_by: state.user!.name, created_at: new Date().toISOString(), is_demo: false });
        ui.dossier = nid;
        audit("Création + analyse", "Dossier TPE", nid, a.status);
      }
      save();
      toast(`Dossier ${ui.dossier} enregistré : ${a.status}.`);
      return render();
    }
    case "dos-del":
      return confirmBox(`Supprimer le dossier ${ui.dossier} ?`, () => {
        state.dossiers = state.dossiers.filter((x) => x.id !== ui.dossier);
        audit("Suppression", "Dossier TPE", ui.dossier);
        ui.dossier = null;
        ui.draft = null;
        save();
        render();
      });
    case "dos-anom": {
      const a = analyzeDossier(ui.draft);
      const nature = a.completeness.missingDocs.length ? "Dossier incomplet – pièces manquantes : " + a.completeness.missingDocs.join(" ; ") : a.inconsistencies[0] ? "Incohérence : " + a.inconsistencies[0].message : "Anomalie relevée lors de l'analyse du dossier";
      const nid = nextId(state.anomalies, "AN", 3, "-");
      state.anomalies.push({ id: nid, detected_on: today(), dossier_ref: ui.dossier, nature, severity: a.inconsistencies.some((i) => i.severity === "alerte") ? "Majeure" : "Significative", risk_id: "R01", control_id: "C01", owner: "Fonction risques", due_on: "", status: "Ouverte", escalation: 1, resolution: "", declared_by: state.user!.name, is_demo: false });
      audit("Création", "Anomalie", nid, `Depuis ${ui.dossier}`);
      save();
      return toast(`Anomalie ${nid} inscrite au registre (C04).`);
    }
    case "ask":
      return ask(el.dataset.q!);
    case "chat-reset":
      ui.chat = [];
      return render();
    case "reset":
      return confirmBox("Restaurer toutes les données de démonstration du rapport ? Vos modifications seront perdues.", () => {
        resetDemo();
        ui.draft = null;
        ui.dossier = null;
        toast("Données de démonstration restaurées.");
        render();
      });
    case "exp-risks":
      return download("registre-risques.csv", csv(snapshot().risks, [["id", "Identifiant"], ["title", "Risque"], ["event", "Événement"], ["causes", "Causes"], ["consequences", "Conséquences"], ["category", "Catégorie"], ["probability", "Probabilité"], ["gravity", "Gravité"], ["score", "Score P×G"], ["level", "Criticité"], ["owner", "Responsable"], ["control_ids", "Contrôles"], ["coso_principles", "Principes COSO"], ["recommendation", "Recommandation"]]));
    case "exp-controls":
      return download("controles.csv", csv(state.controls, [["id", "Id"], ["name", "Contrôle"], ["nature", "Type"], ["objective", "Objectif"], ["risk_ids", "Risques"], ["procedure", "Procédure"], ["owner", "Responsable"], ["frequency", "Fréquence"], ["evidence", "Preuve"], ["indicator", "Indicateur"], ["anomaly_treatment", "Traitement des anomalies"], ["status", "Statut"]]));
    case "exp-coso":
      return download("coso-principes.csv", csv(state.principles, [["id", "Principe"], ["title", "Intitulé"], ["component_id", "Composante"], ["nature", "Nature"], ["assessment", "Appréciation"], ["diagnostic", "Diagnostic"], ["risk_ids", "Risques"]]));
    case "exp-recos":
      return download("recommandations.csv", csv(state.recommendations, [["id", "Id"], ["risk_id", "Risque"], ["coso_gap", "Lacune COSO"], ["action", "Action corrective"], ["owner", "Responsable"], ["indicator", "Indicateur de suivi"], ["status", "Statut"]]));
    case "exp-actions":
      return download("plan-action.csv", csv(state.actions, [["id", "Id"], ["priority", "Priorité"], ["title", "Action"], ["owner", "Responsable"], ["due", "Échéance"], ["deliverable", "Livrable"], ["risk_ids", "Risques"], ["status", "Statut"], ["progress", "Avancement %"]]));
    case "exp-anoms":
      return download("anomalies.csv", csv(state.anomalies, [["id", "Id"], ["detected_on", "Détectée le"], ["dossier_ref", "Dossier"], ["nature", "Nature"], ["severity", "Gravité"], ["risk_id", "Risque"], ["control_id", "Contrôle"], ["owner", "Responsable"], ["due_on", "Échéance"], ["status", "Statut"], ["escalation", "Escalade"]]));
    case "exp-json":
      return download("credit-horizon-sauvegarde.json", JSON.stringify({ ...state, user: null }, null, 1), "application/json");
    case "exp-print":
      return printSummary();
  }
});

document.addEventListener("submit", (e) => {
  const f = e.target as HTMLFormElement;
  e.preventDefault();
  if (f.id === "mform" && modalSubmit) {
    const v: Row = Object.fromEntries(new FormData(f).entries());
    const err = modalSubmit(v);
    if (err) {
      document.getElementById("merr")!.textContent = err;
      return;
    }
    closeModal();
    render();
  } else if (f.id === "askf") {
    const q = (document.getElementById("askq") as HTMLInputElement).value.trim();
    if (q) ask(q);
  }
});

document.addEventListener("input", (e) => {
  const t = e.target as HTMLInputElement;
  if (t.id === "q") {
    ui.filter = t.value;
    return applyFilter();
  }
  const path = t.dataset.d;
  if (path && ui.draft) {
    const [part, key] = path.split(".");
    if (key) ui.draft[part][key] = t.value;
    else ui.draft[part] = t.value;
    document.getElementById("analysis")!.innerHTML = analysisPanel();
  }
});

document.addEventListener("change", (e) => {
  const t = e.target as HTMLSelectElement;
  if (t.dataset.d && ui.draft) {
    const [part, key] = t.dataset.d.split(".");
    ui.draft[part][key] = t.value;
    if (key === "type" || key === "product") render();
    else document.getElementById("analysis")!.innerHTML = analysisPanel();
  } else if (t.dataset.actChange === "assess") {
    const p = state.principles.find((x) => x.id === t.dataset.id)!;
    p.assessment = t.value;
    audit("Modification", "Principe COSO", p.id, `Appréciation : ${t.value}`);
    save();
    toast(`Principe ${p.id} : ${t.value}.`);
    render();
  } else if (t.id === "imp") {
    const file = (t as unknown as HTMLInputElement).files?.[0];
    if (!file) return;
    file.text().then((txt) => {
      try {
        const data = JSON.parse(txt);
        if (!Array.isArray(data.risks)) throw new Error();
        Object.assign(state, data, { user: state.user });
        audit("Import", "Sauvegarde", file.name);
        save();
        toast("Sauvegarde importée.");
        render();
      } catch {
        toast("Fichier invalide : choisissez une sauvegarde JSON de la plateforme.", true);
      }
    });
  }
});

window.addEventListener("hashchange", () => {
  document.body.classList.remove("menu");
  render();
  window.scrollTo(0, 0);
});

function printSummary() {
  const s = snapshot(), k = computeKpis(s as any);
  const w = window.open("", "_blank");
  if (!w) return toast("Ouverture d'une nouvelle fenêtre impossible dans cet affichage.", true);
  const top = [...s.risks].sort((a, b) => b.score - a.score).slice(0, 5);
  w.document.write(`<!doctype html><meta charset="utf-8"><title>Synthèse exécutive – Crédit Horizon</title><style>body{font:13px system-ui;margin:32px;color:#0f1f1a}h1{color:#063b2b}table{border-collapse:collapse;width:100%;margin:10px 0}th{background:#063b2b;color:#fff;text-align:left}td,th{border:1px solid #cbd5e1;padding:5px}</style>
    <h1>CRÉDIT HORIZON – Synthèse exécutive</h1><p>Édité le ${new Date().toLocaleString("fr-FR")} · cas académique fictif EMSI</p>
    <p>${k.total} risques (${k.critical} critiques, ${k.high} élevés), score moyen ${k.avgScore.toFixed(1)}. ${k.operationalControls}/${k.totalControls} contrôles opérationnels ; ${k.coveredRisks}/${k.total} risques couverts. ${k.deficientPrinciples}/17 principes COSO déficients. Plan d'action : ${k.actionProgress} %. Anomalies ouvertes : ${k.openAnomalies} (${k.overdueAnomalies} en retard).</p>
    <h2>Top 5 des risques</h2><table><tr><th>Id</th><th>Risque</th><th>P</th><th>G</th><th>Score</th><th>Niveau</th></tr>${top.map((r) => `<tr><td>${r.id}</td><td>${esc(r.title)}</td><td>${r.probability}</td><td>${r.gravity}</td><td>${r.score}</td><td>${r.level}</td></tr>`).join("")}</table>
    <h2>Recommandations</h2><table><tr><th>Risque</th><th>Lacune COSO</th><th>Action</th><th>Responsable</th><th>Indicateur</th></tr>${s.recommendations.map((r) => `<tr><td>${r.risk_id}</td><td>${esc(r.coso_gap)}</td><td>${esc(r.action)}</td><td>${esc(r.owner)}</td><td>${esc(r.indicator)}</td></tr>`).join("")}</table><script>print()<\/script>`);
  w.document.close();
}

render();
