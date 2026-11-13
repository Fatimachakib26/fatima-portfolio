import { state, save, audit, nextId, splitIds, snapshot, resetBaseline, replaceState, setPersist, maturity, SEED, type Row } from "./store";
import { identity, connectStore, queueSave, saveRoles, saveFile, capability, searchPeople, profiles, sharedStore, type Identity } from "./platform";
import { computeKpis } from "./logic/kpis";
import { levelFromScore, LEVEL_TREATMENT, PROBABILITY_SCALE, GRAVITY_SCALE, type Level } from "./logic/scoring";
import { analyzeDossier, CHECKLIST, PRODUCTS, GUARANTEE_TYPES, isRequired } from "./logic/dossier-analysis";
import { offlineAnswer } from "./logic/offline-advisor";
import { buildContext, ADVISOR_RULES } from "./logic/ai-context";
import { md } from "./markdown";
import marts from "../../data-pipeline/data/marts/sba_marts.json";

/* ================================================================ rôles et droits */
const ROLES: Record<string, string> = {
  admin: "Administrateur", direction: "Direction générale", risques: "Fonction risques",
  commercial: "Chargé d'affaires", controle: "Contrôle interne", lecteur: "Lecture seule",
};
const PERMS: Record<string, string[]> = {
  "risks.write": ["admin", "risques"],
  "controls.write": ["admin", "controle"],
  "coso.write": ["admin", "controle"],
  "actions.write": ["admin", "direction", "risques", "controle"],
  "recos.write": ["admin", "risques", "controle"],
  "anom.create": ["admin", "direction", "risques", "commercial", "controle"],
  "anom.write": ["admin", "direction", "risques", "controle"],
  "dossiers.write": ["admin", "risques", "commercial"],
  "team.manage": ["admin"],
  "audit.view": ["admin", "direction", "controle"],
};
const PERM_LABELS: Record<string, string> = {
  "risks.write": "Modifier le registre des risques", "controls.write": "Gérer les fiches de contrôle", "coso.write": "Apprécier les principes COSO",
  "actions.write": "Piloter le plan d'action", "recos.write": "Gérer les recommandations", "anom.create": "Déclarer une anomalie",
  "anom.write": "Traiter et clôturer une anomalie", "dossiers.write": "Saisir et analyser les dossiers TPE", "team.manage": "Gérer l'équipe et les rôles",
  "audit.view": "Consulter le journal d'audit",
};

const session: { me: Identity | null; role: string; members: Record<string, string>; ready: boolean; storeError: string } = {
  me: null, role: "lecteur", members: {}, ready: false, storeError: "",
};
const can = (p: string) => PERMS[p]?.includes(session.role) ?? false;
const who = () => `${session.me?.name ?? "—"} (${ROLES[session.role]})`;
function resolveRole() {
  const me = session.me!;
  session.role = me.mode === "local" || me.isOwner ? "admin" : session.members[me.id] || "lecteur";
}

/* ================================================================ utilitaires */
const esc = (v: unknown) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
const nf = new Intl.NumberFormat("fr-FR");
const n0 = (v: number) => nf.format(Math.round(v));
const pct = (v: number | null | undefined, d = 1) => (v == null || isNaN(v) ? "–" : `${(v * 100).toFixed(d).replace(".", ",")} %`);
const usd = (v: number) => (v >= 1e9 ? `${(v / 1e9).toFixed(1).replace(".", ",")} Md$` : v >= 1e6 ? `${(v / 1e6).toFixed(1).replace(".", ",")} M$` : v >= 1e3 ? `${n0(v / 1e3)} k$` : `${n0(v)} $`);
const mad = (v: unknown) => (v === "" || v == null || isNaN(Number(v)) ? "–" : `${n0(Number(v))} MAD`);
const today = () => new Date().toISOString().slice(0, 10);
const fdate = (s: string) => (s ? new Date(s).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" }) : "–");

const LVL: Record<Level, string> = { Faible: "low", Modéré: "mid", Élevé: "high", Critique: "crit" };
const level = (l: Level, s?: number) => `<span class="lvl ${LVL[l]}"><i></i>${l}${s !== undefined ? `<b>${s}</b>` : ""}</span>`;
const STATUS_TONE: Record<string, string> = {
  Terminé: "ok", Clôturée: "ok", Efficace: "ok", Opérationnel: "ok", "Mise en œuvre": "ok", Satisfaisant: "ok",
  "En cours": "info", "En déploiement": "info", Partiel: "warn",
  Ouverte: "bad", Bloqué: "bad", Déficient: "bad", Abandonnée: "mute",
  "À faire": "mute", "À lancer": "mute", Proposé: "mute", "Non évalué": "mute",
};
const status = (s: string) => `<span class="st ${STATUS_TONE[s] ?? (s.startsWith("Incomplet") ? "bad" : s.startsWith("Complet") ? "ok" : "mute")}">${esc(s)}</span>`;
const ids = (v: unknown) => splitIds(v).map((x) => `<span class="ref">${esc(x)}</span>`).join("");

const I: Record<string, string> = {
  overview: "M3 13h8V3H3zM13 21h8V11h-8zM3 21h8v-6H3zM13 3v6h8V3z",
  portfolio: "M3 3v18h18M7 15l4-4 3 3 6-6",
  risks: "M12 3 2 20h20zM12 10v4M12 17h.01",
  dossiers: "M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h5",
  controls: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6zM9 12l2 2 4-4",
  actions: "M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01",
  framework: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5zM20 17v4H6.5",
  advisor: "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4z",
  admin: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  plus: "M12 5v14M5 12h14", down: "M12 3v12M7 10l5 5 5-5M5 21h14", ext: "M14 3h7v7M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5",
  close: "M18 6 6 18M6 6l12 12", menu: "M3 6h18M3 12h18M3 18h18", check: "M20 6 9 17l-5-5", lock: "M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4",
};
const icon = (k: string, cls = "") => `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${I[k]}"/></svg>`;

let toastT: any;
function toast(msg: string, bad = false) {
  const el = document.getElementById("toast")!;
  el.textContent = msg;
  el.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toastT);
  toastT = setTimeout(() => (el.className = "toast"), 3400);
}
function download(name: string, content: string, type = "text/csv;charset=utf-8") {
  Promise.resolve()
    .then(() => saveFile(name, content, type))
    .then(() => toast(`${name} prêt.`))
    .catch((e: any) => toast(e?.code === "dismissed" || e?.code === "not_granted" ? "Téléchargement annulé." : "Le téléchargement n'a pas pu démarrer.", true));
}
function csv(rows: Row[], cols: [string, string][]) {
  const e = (v: unknown) => {
    const s = String(v ?? "").replace(/\r?\n/g, " ");
    return /[";]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return "﻿" + [cols.map((c) => e(c[1])).join(";"), ...rows.map((r) => cols.map((c) => e(r[c[0]])).join(";"))].join("\r\n");
}
function record(action: string, entity: string, id: string, details = "") {
  audit(who(), action, entity, id, details);
  save();
}

/* ================================================================ état d'interface */
const ui: any = { sel: null, view: "table", filter: "", cat: "", dossier: null, draft: null, tab: {}, chat: [] as Row[], busy: false, ai: false, names: {} };
const tab = (page: string, def: string) => ui.tab[page] ?? def;

/* ================================================================ briques d'interface */
const head = (title: string, lead: string, actions = "", eyebrow = "") =>
  `<header class="ph"><div>${eyebrow ? `<p class="eyebrow">${eyebrow}</p>` : ""}<h1>${title}</h1><p class="lead">${lead}</p></div>${actions ? `<div class="ph-a">${actions}</div>` : ""}</header>`;
const panel = (title: string, body: string, opts: { aside?: string; cls?: string; sub?: string } = {}) =>
  `<section class="panel ${opts.cls ?? ""}">${title || opts.aside ? `<div class="panel-h"><div>${title ? `<h2>${title}</h2>` : ""}${opts.sub ? `<p>${opts.sub}</p>` : ""}</div>${opts.aside ?? ""}</div>` : ""}${body}</section>`;
const metric = (label: string, value: string, note = "", tone = "") => `<div class="metric ${tone}"><span>${label}</span><strong>${value}</strong>${note ? `<small>${note}</small>` : ""}</div>`;
const table = (head: string[], rows: unknown[][], opts: { cls?: string; empty?: string; num?: number[] } = {}) =>
  rows.length
    ? `<div class="tw"><table class="${opts.cls ?? ""}"><thead><tr>${head.map((h, i) => `<th class="${opts.num?.includes(i) ? "n" : ""}">${h}</th>`).join("")}</tr></thead><tbody>${rows
        .map((r) => `<tr>${r.map((c, i) => `<td class="${opts.num?.includes(i) ? "n" : ""}">${c}</td>`).join("")}</tr>`)
        .join("")}</tbody></table></div>`
    : `<div class="empty">${opts.empty ?? "Aucun élément."}</div>`;
const btn = (label: string, act: string, extra = "", kind = "") => `<button class="btn ${kind}" data-act="${act}" ${extra}>${label}</button>`;
const tabs = (page: string, items: [string, string, number?][], cur: string) =>
  `<nav class="tabs" role="tablist">${items.map(([k, l, n]) => `<button role="tab" aria-selected="${k === cur}" class="${k === cur ? "on" : ""}" data-act="tab" data-page="${page}" data-id="${k}">${l}${n != null ? `<span>${n}</span>` : ""}</button>`).join("")}</nav>`;
const note = (t: string, kind = "") => `<div class="note ${kind}">${t}</div>`;
const meter = (v: number, max = 1, tone = "") => `<span class="meter ${tone}"><i style="width:${Math.max(0, Math.min(100, (v / max) * 100))}%"></i></span>`;
const readonly = (t: string) => note(`${icon("lock")} ${t}`, "lock");

/* ---------------------------------------------------------------- graphiques */
function columns(data: { label: string; value: number; note?: string; muted?: boolean }[], fmt: (v: number) => string, max?: number) {
  const m = max ?? Math.max(...data.map((d) => d.value), 0.0001);
  return `<div class="cols" role="img" aria-label="${esc(data.map((d) => `${d.label} ${fmt(d.value)}`).join(", "))}">${data
    .map((d) => `<div class="col ${d.muted ? "muted" : ""}" title="${esc(d.label)} : ${fmt(d.value)}${d.note ? " – " + esc(d.note) : ""}"><span class="v">${fmt(d.value)}</span><span class="bar"><i style="height:${(d.value / m) * 100}%"></i></span><span class="l">${esc(d.label)}</span></div>`)
    .join("")}</div>`;
}
function matrix(risks: Row[], compact = false) {
  let h = `<div class="mx ${compact ? "compact" : ""}"><div class="mx-yl">Probabilité</div><div class="mx-g">`;
  for (let p = 5; p >= 1; p--) {
    h += `<div class="mx-ax">${p}${compact ? "" : `<small>${PROBABILITY_SCALE[p - 1].label}</small>`}</div>`;
    for (let g = 1; g <= 5; g++) {
      const s = p * g, l = levelFromScore(s);
      const here = risks.filter((r) => +r.probability === p && +r.gravity === g);
      h += `<div class="mx-c ${LVL[l]}" title="P${p} × G${g} = ${s} (${l})"><em>${s}</em>${here.map((r) => `<button class="mx-r ${ui.sel === r.id ? "on" : ""}" data-act="sel" data-id="${r.id}" title="${esc(r.title)}">${r.id}</button>`).join("")}</div>`;
    }
  }
  h += `<div></div>${[1, 2, 3, 4, 5].map((g) => `<div class="mx-ax x">${g}${compact ? "" : `<small>${GRAVITY_SCALE[g - 1].label}</small>`}</div>`).join("")}</div></div><div class="mx-xl">Gravité</div>`;
  return h;
}

/* ================================================================ modales */
type Field = { k: string; l: string; t?: "text" | "textarea" | "select" | "number" | "date" | "range"; o?: string[]; req?: boolean; full?: boolean; min?: number; max?: number; hint?: string };
let onSubmit: ((v: Row) => string | void) | null = null;
function modal(title: string, fields: Field[], values: Row, submit: (v: Row) => string | void) {
  onSubmit = submit;
  const f = fields.map((x) => {
    const v = values[x.k] ?? (x.t === "range" ? x.min ?? 0 : "");
    const id = `f_${x.k}`;
    let input = "";
    if (x.t === "textarea") input = `<textarea id="${id}" name="${x.k}" ${x.req ? "required" : ""}>${esc(v)}</textarea>`;
    else if (x.t === "select") input = `<select id="${id}" name="${x.k}">${x.o!.map((o) => `<option ${o === String(v) ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
    else if (x.t === "range") input = `<div class="range"><input id="${id}" type="range" name="${x.k}" min="${x.min}" max="${x.max}" value="${v}" oninput="this.nextElementSibling.value=this.value"><output>${v}</output></div>`;
    else input = `<input id="${id}" name="${x.k}" type="${x.t || "text"}" value="${esc(v)}" ${x.req ? "required" : ""}>`;
    return `<div class="fld ${x.full || x.t === "textarea" ? "full" : ""}"><label for="${id}">${x.l}${x.req ? " <i>*</i>" : ""}</label>${input}${x.hint ? `<small>${esc(x.hint)}</small>` : ""}</div>`;
  }).join("");
  document.getElementById("modal")!.innerHTML = `<div class="scrim" data-act="close"></div><div class="dlg" role="dialog" aria-modal="true" aria-labelledby="dlg-t"><div class="dlg-h"><h3 id="dlg-t">${esc(title)}</h3><button class="icon-btn" data-act="close" aria-label="Fermer">${icon("close")}</button></div>
    <form id="mform" class="form">${f}<p class="err full" id="merr" role="alert"></p><div class="full dlg-a"><button type="button" class="btn ghost" data-act="close">Annuler</button><button class="btn primary">Enregistrer</button></div></form></div>`;
  document.getElementById("modal")!.className = "open";
  (document.querySelector("#mform input, #mform textarea, #mform select") as HTMLElement | null)?.focus();
}
function confirmBox(text: string, yes: () => void, label = "Supprimer") {
  document.getElementById("modal")!.innerHTML = `<div class="scrim" data-act="close"></div><div class="dlg small" role="alertdialog" aria-modal="true"><div class="dlg-h"><h3>Confirmer</h3></div><p>${esc(text)}</p>
    <div class="dlg-a"><button class="btn ghost" data-act="close">Annuler</button><button class="btn danger" id="yes">${label}</button></div></div>`;
  document.getElementById("modal")!.className = "open";
  document.getElementById("yes")!.onclick = () => {
    close();
    yes();
  };
}
function close() {
  document.getElementById("modal")!.className = "";
  document.getElementById("modal")!.innerHTML = "";
  onSubmit = null;
}

/* ================================================================ portefeuille de référence (SBA) */
const M: any = marts;
const O = M.overview;
const T = M.tables;
const LOANS = M.files.loans;
const MIN_SAMPLE = 100; // en dessous, un taux de défaut n'est pas interprétable
const AGE_FR: Record<string, string> = {
  "Existing, 5 or more years": "Existante, 5 ans et plus", "Existing or more than 2 years old": "Existante, plus de 2 ans",
  "New, Less than 1 Year old": "Nouvelle, moins d'1 an", "New Business or 2 years or less": "Nouvelle, 2 ans ou moins",
  "Less than 2 years old but at least 1": "1 à 2 ans", "Less than 3 years old but at least 2": "2 à 3 ans", "Less than 4 years old but at least 3": "3 à 4 ans", "Less than 5 years old but at least 4": "4 à 5 ans",
  "Change of Ownership": "Reprise d'entreprise", "Startup, Loan Funds will Open Business": "Création (le prêt finance l'ouverture)", Unanswered: "Non renseigné",
};

/* ================================================================ pages */
function pOverview() {
  const s = snapshot(), k = computeKpis(s as any), r = s.risks;
  const top = [...r].sort((a, b) => b.score - a.score || a.id.localeCompare(b.id)).slice(0, 5);
  const p1 = s.actions.filter((a) => a.priority === "P1" && a.status !== "Terminé");
  const openAn = s.anomalies.filter((a) => a.status !== "Clôturée");
  const late = openAn.filter((a) => a.due_on && a.due_on < today());
  const blocked = s.dossiers.filter((d) => d.analysis?.blocking);
  const todo = [
    ...late.map((a) => [`Anomalie ${a.id} en retard`, esc(String(a.nature).slice(0, 90)), "#actions", "bad"]),
    ...blocked.map((d) => [`Dossier ${d.id} suspendu`, `${esc(d.company?.name)} · ${d.analysis.completeness.missingDocs.length} pièce(s) manquante(s)`, "#dossiers", "warn"]),
    ...p1.slice(0, 5).map((a) => [`${a.id} · priorité 1`, `${esc(a.title)} — ${esc(a.owner)}`, "#actions", ""]),
  ];
  const live = s.controls.filter((c) => ["Opérationnel", "Efficace"].includes(c.status)).length;
  return head("Vue d'ensemble", "Exposition aux risques, état du dispositif de contrôle et actions à mener.", "", new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })) +
    `<div class="metrics">
      ${metric("Risques critiques", `${k.critical}<em>/ ${k.total}</em>`, `${k.high} élevés · score moyen ${k.avgScore.toFixed(1).replace(".", ",")}`, k.critical ? "bad" : "")}
      ${metric("Contrôles en service", `${live}<em>/ ${k.totalControls}</em>`, live ? `${k.coveredRisks}/${k.total} risques couverts` : "aucun contrôle encore déployé", live ? "" : "warn")}
      ${metric("Plan d'action", `${k.actionProgress} %`, `${k.pendingActions} actions ouvertes dont ${p1.length} P1`)}
      ${metric("Anomalies ouvertes", `${k.openAnomalies}`, late.length ? `${late.length} en retard` : "aucune en retard", late.length ? "bad" : "")}
      ${metric("Défaut de référence", pct(O.default_rate), `prêts TPE SBA ${O.cohorts}`)}
    </div>
    <div class="grid g-7-5">
      ${panel("Risques prioritaires", table(["", "Risque", "Criticité", "Traitement attendu"], top.map((x) => [`<span class="ref">${x.id}</span>`, `<a href="#risks" data-act="sel" data-id="${x.id}" class="lk">${esc(x.title)}</a>`, level(x.level, x.score), `<small>${LEVEL_TREATMENT[x.level as Level]}</small>`])), { aside: `<a class="more" href="#risks">Registre</a>` })}
      ${panel("Cartographie", matrix(r, true), { aside: `<button class="more" data-act="view" data-id="matrix">Agrandir</button>` })}
    </div>
    <div class="grid g-7-5">
      ${panel("À traiter", todo.length ? `<ul class="todo">${todo.map(([t, d, h, tone]) => `<li class="${tone}"><a href="${h}"><b>${t}</b><span>${d}</span></a></li>`).join("")}</ul>` : `<div class="empty">Rien d'urgent : aucune anomalie en retard, aucun dossier suspendu, aucune action prioritaire ouverte.</div>`)}
      ${panel("Repère de marché", `<p class="small">Taux de défaut par année d'octroi · prêts garantis SBA 7(a) aux petites entreprises</p>
        ${columns(T.by_cohort.map((c: Row) => ({ label: `${String(c.cohort_fy).slice(2)}`, value: c.default_rate, muted: c.cohort_fy >= 2018 })), (v) => pct(v, 1))}
        <p class="small">Défaut médian <b>${O.median_months_to_default.toFixed(0)} mois</b> après l'octroi ; ${pct(O.share_defaults_within_24m, 0)} des pertes seulement dans les 24 premiers mois.</p>`, { aside: `<a class="more" href="#portfolio">Analyse</a>` })}
    </div>`;
}

function pPortfolio() {
  const sec = T.by_sector as Row[];
  const totalUsd = sec.reduce((a, r) => a + r.approved_usd, 0);
  const big = sec.filter((x) => x.resolved > 1000);
  const age = [...(T.by_business_age as Row[])].sort((a, b) => b.loans - a.loans);
  const newBiz = age.filter((a) => /^New|Startup/i.test(a.business_age));
  const existing = age.find((a) => /5 or more/i.test(a.business_age));
  const newRate = newBiz.reduce((a, r) => a + r.defaults, 0) / Math.max(1, newBiz.reduce((a, r) => a + r.resolved, 0));
  const coll = T.by_collateral as Row[];
  const cy = coll.find((c) => c.collateral === true), cn = coll.find((c) => c.collateral === false);
  const lo = big.reduce((a, b) => (a.default_rate < b.default_rate ? a : b)), hi = big.reduce((a, b) => (a.default_rate > b.default_rate ? a : b));
  const t = tab("portfolio", "analyse");
  const body = t === "analyse"
    ? `<div class="metrics">
        ${metric("Prêts décaissés", n0(O.loans_funded), `${O.cohorts} · ${O.lenders} prêteurs`)}
        ${metric("Taux de défaut", pct(O.default_rate, 2), `${n0(O.defaults)} pertes sur ${n0(O.loans_resolved)} prêts dénoués`, "bad")}
        ${metric("Taux de perte", pct(O.loss_rate, 2), `${usd(O.chargeoff_usd)} passés en perte`)}
        ${metric("Prêt médian", usd(O.median_loan_usd), `durée médiane ${Math.round(O.median_term_months / 12)} ans`)}
        ${metric("Délai médian avant perte", `${O.median_months_to_default.toFixed(0)} mois`, `${pct(O.share_defaults_within_24m, 0)} des pertes avant 24 mois`)}
      </div>
      ${panel("Ce que ces données apprennent à Crédit Horizon", `<ul class="insights">
        <li><div>${ids("R03, C07")}</div><p><b>Le secteur pèse sur le risque.</b> Parmi les secteurs de plus de 1 000 prêts dénoués, le défaut va de ${pct(lo.default_rate)} (${esc(lo.sector.toLowerCase())}) à ${pct(hi.default_rate)} (${esc(hi.sector.toLowerCase())}). Le suivi de la concentration doit comparer chaque secteur du portefeuille à ces repères.</p></li>
        <li><div>${ids("R04, C05")}</div><p><b>Les pertes arrivent tard.</b> La moitié survient plus de ${O.median_months_to_default.toFixed(0)} mois après l'octroi : la surveillance des retards doit couvrir toute la vie du prêt, pas seulement la première année.</p></li>
        <li><div>${ids("R01, R02")}</div><p><b>L'ancienneté compte.</b> Entreprises nouvelles ou en création : ${pct(newRate)} de défaut, contre ${pct(existing?.default_rate)} pour celles de 5 ans et plus. La grille commune d'analyse doit l'intégrer.</p></li>
        <li><div>${ids("Charte")}</div><p><b>La garantie réelle réduit le défaut</b> : ${pct(cn?.default_rate)} sans garantie, ${pct(cy?.default_rate)} avec. Argument pour le niveau « autorisation renforcée » de la charte.</p></li>
      </ul><p class="small">Repère externe : prêts américains du programme SBA 7(a). Ces chiffres ne décrivent pas le portefeuille de Crédit Horizon.</p>`)}
      <div class="grid g-1-1">
        ${panel("Défaut par année d'octroi", columns(T.by_cohort.map((c: Row) => ({ label: `FY${String(c.cohort_fy).slice(2)}`, value: c.default_rate, note: `${n0(c.resolved)} prêts dénoués`, muted: c.cohort_fy >= 2018 })), (v) => pct(v, 1)) +
          `<p class="small">Cohortes 2018 et 2019 en clair : encore des prêts en cours, leur taux peut évoluer.</p>`)}
        ${panel("Délai entre octroi et perte", columns(T.time_to_default.map((b: Row) => ({ label: b.bucket.replace(" mois", ""), value: b.share })), (v) => pct(v, 0)) + `<p class="small">Répartition des ${n0(O.defaults)} prêts passés en perte, en mois.</p>`)}
      </div>
      ${panel("Secteurs d'activité", table(["Secteur", "Prêts", "Part de l'encours", "Taux de défaut", "Taux de perte"], sec.slice(0, 14).map((r) => [esc(r.sector), n0(r.loans), `<div class="mcell">${meter(r.approved_usd / totalUsd, 0.2)}<span>${pct(r.approved_usd / totalUsd)}</span></div>`, `<div class="mcell">${meter(r.default_rate ?? 0, 0.16, "bad")}<span>${pct(r.default_rate)}</span></div>`, pct(r.loss_rate)]), { num: [1, 4] }),
        { sub: `Les trois premiers secteurs représentent ${pct(O.top3_sector_share, 0)} de l'encours (indice de Herfindahl ${O.hhi_sector.toFixed(3).replace(".", ",")}).` })}
      <div class="grid g-1-1-1">
        ${panel("Montant du prêt", table(["Tranche", "Prêts", "Défaut"], T.by_size.map((r: Row) => [esc(r.size_band), n0(r.loans), pct(r.default_rate)]), { num: [1, 2] }))}
        ${panel("Durée", table(["Durée", "Prêts", "Défaut"], T.by_term.map((r: Row) => [esc(r.term_band), n0(r.loans), pct(r.default_rate)]), { num: [1, 2] }))}
        ${panel("Garantie et taux", table(["Caractéristique", "Prêts", "Défaut"], [
          ...coll.map((r: Row) => [r.collateral ? "Avec garantie réelle" : "Sans garantie réelle", n0(r.loans), pct(r.default_rate)]),
          ...(T.by_rate_type as Row[]).map((r) => [r.rate_type === "F" ? "Taux fixe" : "Taux variable", n0(r.loans), pct(r.default_rate)]),
        ], { num: [1, 2] }))}
      </div>
      ${panel("Ancienneté de l'entreprise", table(["Ancienneté déclarée", "Prêts", "Dénoués", "Taux de défaut"], age.map((r) => [esc(AGE_FR[r.business_age] ?? r.business_age), n0(r.loans), n0(r.resolved), r.resolved < MIN_SAMPLE ? `<span class="mute-t" title="Moins de ${MIN_SAMPLE} prêts dénoués : taux non significatif">n.s.</span>` : pct(r.default_rate)]), { num: [1, 2, 3] }), { sub: `Taux non significatif (n.s.) en dessous de ${MIN_SAMPLE} prêts dénoués.` })}`
    : `<div class="grid g-1-1 top">${panel("Source", `<dl class="kv">
          <dt>Éditeur</dt><dd>${esc(M.source.publisher)}</dd>
          <dt>Jeu de données</dt><dd>${esc(M.source.dataset)}<br><small>Identifiant ${esc(M.source.dataset_identifier)}</small></dd>
          <dt>Page officielle</dt><dd><a href="${M.source.landing_page}" target="_blank" rel="noopener">data.sba.gov ${icon("ext")}</a></dd>
          <dt>Fichier analysé</dt><dd><a href="${LOANS.url}" target="_blank" rel="noopener">${esc(LOANS.name)}</a></dd>
          <dt>Situation au</dt><dd>${fdate(O.as_of)} · ${esc(M.source.update_frequency.toLowerCase())}</dd>
          <dt>Licence</dt><dd>${esc(M.source.license)}</dd>
          <dt>Volume brut</dt><dd>${n0(LOANS.rows)} lignes × ${LOANS.columns} colonnes · ${(LOANS.bytes / 1e6).toFixed(1).replace(".", ",")} Mo</dd>
          <dt>Empreinte SHA-256</dt><dd><code class="hash">${LOANS.sha256}</code></dd>
          <dt>Téléchargé le</dt><dd>${fdate(LOANS.downloaded_at)}</dd>
        </dl><p class="small">Vérification : téléchargez le fichier depuis la page officielle et calculez son empreinte (<code>sha256sum</code> sous Linux et macOS, <code>Get-FileHash</code> sous Windows). Une empreinte identique prouve qu'il s'agit exactement du fichier analysé. L'éditeur publie une version par trimestre : un fichier plus récent aura une autre empreinte.</p>`)}
        ${panel("Méthode", `<ol class="steps">
          <li><b>Acquisition</b><span>Téléchargement depuis le portail officiel, contrôle de la taille annoncée, calcul de l'empreinte, manifeste.</span></li>
          <li><b>Profilage</b><span>Chaque colonne lue en texte, sans conversion : vides, valeurs distinctes, formats, écarts avec le dictionnaire officiel.</span></li>
          <li><b>Validation et nettoyage</b><span>Neuf règles numérotées et comptées ; toute ligne écartée est conservée avec la règle qui l'a écartée.</span></li>
          <li><b>Minimisation</b><span>Nom, adresse et code postal des emprunteurs supprimés : inutiles à l'analyse du risque.</span></li>
          <li><b>Tables d'analyse</b><span>Agrégats par cohorte, secteur, montant, durée, ancienneté et garantie, avec des définitions uniques.</span></li>
          <li><b>Contrôle croisé</b><span>Taux de défaut recalculé indépendamment depuis le fichier brut ; totaux de chaque table rapprochés.</span></li>
        </ol>`)}</div>
      ${panel("Réconciliation", `<div class="recon"><div><strong>${n0(LOANS.rows)}</strong><span>lignes brutes</span></div><b>=</b><div><strong>${n0(LOANS.rows - 1146)}</strong><span>lignes retenues</span></div><b>+</b><div><strong>1 146</strong><span>lignes rejetées</span></div></div>
        <div class="grid g-1-1">${table(["Règle", "Motif du rejet", "Lignes"], [["R02", "Doublon exact d'une ligne précédente", "1 136"], ["R07", "Prêt passé en perte sans date de passage en perte", "10"]], { num: [2] })}
        ${table(["Population", "Prêts", "Traitement"], [["Dénoués : remboursés ou passés en perte", n0(O.loans_resolved), "base des taux"], ["En cours, issue non publiée (EXEMPT)", n0(O.loans_active_undisclosed), "exclus : issue inconnue"], ["Non décaissés : annulés ou engagés", n0(LOANS.rows - 1146 - O.loans_funded), "exclus : aucun risque porté"]], { num: [1] })}</div>`)}`;
  return head("Portefeuille de référence", "Données publiques et vérifiables de défaut sur les prêts aux petites entreprises, utilisées comme repère externe pour coter les risques du registre.",
    `<button class="btn ghost" data-act="exp-marts">${icon("down")} Données (CSV)</button>`, `Source officielle · U.S. Small Business Administration · situation au ${fdate(O.as_of)}`) +
    tabs("portfolio", [["analyse", "Analyse"], ["source", "Source et méthode"]], t) + body;
}

/* ---------------------------------------------------------------- risques */
const RISK_FIELDS: Field[] = [
  { k: "title", l: "Intitulé", req: true, full: true },
  { k: "category", l: "Catégorie", t: "select", o: ["Crédit", "Liquidité", "Opérationnel", "Conformité", "Stratégique"] },
  { k: "basis", l: "Fondement", t: "select", o: ["Constat", "Hypothèse"] },
  { k: "event", l: "Événement redouté", t: "textarea", req: true },
  { k: "causes", l: "Causes", t: "textarea" },
  { k: "consequences", l: "Conséquences", t: "textarea" },
  { k: "probability", l: "Probabilité", t: "range", min: 1, max: 5, hint: PROBABILITY_SCALE.map((p) => `${p.v} ${p.label}`).join(" · ") },
  { k: "gravity", l: "Gravité", t: "range", min: 1, max: 5, hint: GRAVITY_SCALE.map((p) => `${p.v} ${p.label}`).join(" · ") },
  { k: "justification", l: "Justification de la cotation", t: "textarea" },
  { k: "owner", l: "Responsable", req: true },
  { k: "control_ids", l: "Contrôles associés", hint: "Identifiants séparés par des virgules, ex. C01, C04" },
  { k: "coso_principles", l: "Principes COSO", hint: "Ex. P10, P12" },
  { k: "recommendation", l: "Recommandation", t: "textarea" },
];

function pRisks() {
  const all = snapshot().risks.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const w = can("risks.write");
  const sel = all.find((x) => x.id === ui.sel);
  const cats = Array.from(new Set(all.map((r) => r.category)));
  const rows = all
    .filter((x) => !ui.cat || x.category === ui.cat)
    .map((x) => `<tr class="row ${sel?.id === x.id ? "on" : ""}" data-act="sel" data-id="${x.id}" tabindex="0" data-text="${esc([x.id, x.title, x.event, x.causes, x.consequences, x.owner, x.level].join(" ").toLowerCase())}">
      <td><span class="ref">${x.id}</span></td><td><b>${esc(x.title)}</b><small>${esc(x.category)} · ${esc(x.owner)}</small></td>
      <td class="n">${x.probability}</td><td class="n">${x.gravity}</td><td>${level(x.level, x.score)}</td><td class="ids">${ids(x.control_ids)}</td></tr>`).join("");
  const view = ui.view === "matrix" ? panel("", matrix(all)) : panel("", `<div class="toolbar"><input id="q" type="search" placeholder="Rechercher un risque, une cause, un responsable" value="${esc(ui.filter)}" aria-label="Rechercher">
      <select id="cat" aria-label="Catégorie"><option value="">Toutes catégories</option>${cats.map((c) => `<option ${c === ui.cat ? "selected" : ""}>${esc(c)}</option>`).join("")}</select><span class="count" id="qn"></span></div>
      <div class="tw"><table id="rt" class="hover"><thead><tr><th></th><th>Risque</th><th class="n">P</th><th class="n">G</th><th>Criticité</th><th>Contrôles</th></tr></thead><tbody>${rows}</tbody></table></div>`);
  return head("Risques", "Registre coté par probabilité × gravité. Criticité : 1–4 faible, 5–9 modéré, 10–15 élevé, 16–25 critique.",
    `<div class="seg" role="group" aria-label="Affichage"><button class="${ui.view !== "matrix" ? "on" : ""}" data-act="view" data-id="table">Registre</button><button class="${ui.view === "matrix" ? "on" : ""}" data-act="view" data-id="matrix">Matrice</button></div>
     <button class="btn ghost" data-act="exp-risks">${icon("down")} CSV</button>${w ? btn(`${icon("plus")} Nouveau risque`, "risk-new", "", "primary") : ""}`) +
    (w ? "" : readonly("Lecture seule : le registre est tenu par la fonction risques.")) +
    `<div class="grid ${sel ? "g-7-5 top" : ""}">${view}${sel ? riskDetail(sel, w) : ""}</div>`;
}

function riskDetail(x: Row, w: boolean) {
  const hist = state.history.filter((h) => h.risk_id === x.id);
  const ctrls = state.controls.filter((c) => splitIds(c.risk_ids).includes(x.id));
  const acts = state.actions.filter((a) => splitIds(a.risk_ids).includes(x.id));
  const rec = state.recommendations.find((r) => r.risk_id === x.id);
  return `<aside class="panel detail" aria-label="Fiche ${x.id}"><div class="panel-h"><div><p class="eyebrow">${x.id} · ${esc(x.category)} · ${esc(x.basis)}</p><h2>${esc(x.title)}</h2></div><button class="icon-btn" data-act="sel" data-id="" aria-label="Fermer la fiche">${icon("close")}</button></div>
    <div class="score-line">${level(x.level, x.score)}<span>P ${x.probability} · ${PROBABILITY_SCALE[x.probability - 1].label}</span><span>G ${x.gravity} · ${GRAVITY_SCALE[x.gravity - 1].label}</span></div>
    <p class="treat">${LEVEL_TREATMENT[x.level as Level]}</p>
    <dl class="kv stack"><dt>Événement redouté</dt><dd>${esc(x.event)}</dd><dt>Causes</dt><dd>${esc(x.causes) || "–"}</dd><dt>Conséquences</dt><dd>${esc(x.consequences) || "–"}</dd>
      <dt>Justification</dt><dd>${esc(x.justification) || "–"}</dd><dt>Responsable</dt><dd>${esc(x.owner)}</dd>
      <dt>Contrôles</dt><dd>${ctrls.map((c) => `<div class="li"><span class="ref">${c.id}</span> ${esc(c.name)} ${status(c.status)}</div>`).join("") || "Aucun contrôle associé"}</dd>
      <dt>Recommandation</dt><dd>${esc(rec?.action ?? x.recommendation) || "–"}</dd>
      <dt>Actions</dt><dd>${acts.map((a) => `<div class="li"><span class="ref">${a.id}</span> ${esc(a.title)} ${status(a.status)}</div>`).join("") || "–"}</dd>
      <dt>Historique</dt><dd>${hist.map((h) => `${fdate(h.recorded_at)} · ${h.score}`).join(" → ")}</dd></dl>
    <div class="dlg-a">${w ? `${btn("Supprimer", "risk-del", `data-id="${x.id}"`, "ghost danger-t")}${btn("Modifier", "risk-edit", `data-id="${x.id}"`, "ghost")}` : ""}${btn(`${icon("advisor")} Analyser`, "ask", `data-q="Analyse le risque ${x.id} : explique sa cotation, son rattachement COSO, les repères du portefeuille de référence et propose une recommandation complète."`, "primary")}</div></aside>`;
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
  if (ui.draft) return dossierEditor(w);
  return head("Dossiers TPE", "Contrôle de complétude (C01), incohérences et points de vigilance avant l'avis de la fonction risques. L'outil n'émet aucune décision d'octroi.",
    w ? btn(`${icon("plus")} Nouveau dossier`, "dos-new", "", "primary") : "") +
    (w ? "" : readonly("Lecture seule : la saisie des dossiers est réservée aux chargés d'affaires et à la fonction risques.")) +
    panel("", table(["Référence", "Entreprise", "Financement", "Complétude", "Analyse", "Saisi par"], state.dossiers.map((d) => [
      `<button class="link" data-act="dos-open" data-id="${d.id}">${d.id}</button>`, `${esc(d.company?.name)}<small>${esc(d.company?.sector)}</small>`,
      `${mad(d.request?.amount)}<small>${esc(d.request?.product)} · ${esc(d.request?.duration_months)} mois</small>`, `<div class="mcell">${meter(d.analysis?.completeness?.rate ?? 0, 100)}<span>${d.analysis?.completeness?.rate ?? 0} %</span></div>`,
      status(d.status), `<small>${esc(d.created_by)}<br>${fdate(d.created_at)}</small>`]), { empty: w ? `<p><b>Aucun dossier.</b> Saisissez une demande de financement : l'analyse de complétude et de cohérence se met à jour pendant la saisie.</p>${btn(`${icon("plus")} Saisir un dossier`, "dos-new", "", "primary")}` : "Aucun dossier saisi." }));
}

function dossierEditor(w: boolean) {
  const d = ui.draft;
  const T_ = (part: string, k: string, label: string, type = "text", hint = "") =>
    `<div class="fld"><label for="d_${part}_${k}">${label}</label><input id="d_${part}_${k}" data-d="${part}.${k}" type="${type}" value="${esc(d[part][k])}" ${w ? "" : "disabled"}>${hint ? `<small>${hint}</small>` : ""}</div>`;
  const S_ = (part: string, k: string, label: string, opts: readonly string[]) =>
    `<div class="fld"><label for="d_${part}_${k}">${label}</label><select id="d_${part}_${k}" data-d="${part}.${k}" ${w ? "" : "disabled"}>${opts.map((o) => `<option ${o === d[part][k] ? "selected" : ""}>${esc(o)}</option>`).join("")}</select></div>`;
  const docs = CHECKLIST.map((c) => {
    const req = c.stage === "avant_avis" && isRequired(c.key, d);
    return `<div class="chk"><div>${esc(c.label)}<small>${c.stage === "avant_decision" ? "Exigé avant la décision" : req ? "Obligatoire avant l'avis" : "Non requis pour ce dossier"}</small></div><div class="seg sm" role="group" aria-label="${esc(c.label)}">${[["oui", "Oui"], ["non", "Non"], ["na", "N/A"]]
      .map(([v, l]) => `<button type="button" class="${d.documents[c.key] === v ? "on " + v : ""}" data-act="doc" data-k="${c.key}" data-v="${v}" ${w ? "" : "disabled"}>${l}</button>`).join("")}</div></div>`;
  }).join("");
  return head(ui.dossier ? `Dossier ${ui.dossier}` : "Nouveau dossier", "Saisissez la demande : l'analyse se recalcule à chaque modification.",
    `${btn("Retour à la liste", "dos-close", "", "ghost")}${w ? btn("Enregistrer", "dos-save", "", "primary") : ""}`) +
    `<div class="grid g-7-5 top"><div class="form-col">
      ${panel("Entreprise", `<div class="form f3">${T_("company", "name", "Raison sociale *")}${S_("company", "legal_form", "Forme juridique", ["SARL", "SARLAU", "SA", "SNC", "Entreprise individuelle", "Auto-entrepreneur", "Coopérative"])}${T_("company", "creation_date", "Date de création", "date")}
        ${T_("company", "rc_number", "Registre de commerce")}${T_("company", "ice", "ICE")}${T_("company", "city", "Ville")}${T_("company", "manager_name", "Dirigeant")}${T_("company", "employees", "Effectif", "number")}${T_("company", "name_on_documents", "Raison sociale sur les pièces", "text", "Sert au contrôle de concordance")}</div>`)}
      ${panel("Activité et financement", `<div class="form f3">${T_("company", "sector", "Secteur d'activité")}${S_("request", "product", "Produit", PRODUCTS)}${T_("request", "amount", "Montant demandé (MAD) *", "number")}
        ${T_("request", "duration_months", "Durée (mois) *", "number")}${T_("company", "activity", "Activité")}${T_("request", "purpose", "Objet du financement")}</div>`)}
      ${panel("Données financières (MAD)", `<div class="form f4">${T_("financials", "fiscal_year", "Exercice")}${T_("financials", "revenue_n", "Chiffre d'affaires N", "number")}${T_("financials", "revenue_n1", "Chiffre d'affaires N-1", "number")}
        ${T_("financials", "revenue_bank", "CA selon relevés bancaires", "number")}${T_("financials", "net_result", "Résultat net", "number")}${T_("financials", "equity", "Fonds propres", "number")}
        ${T_("financials", "existing_debt", "Dettes financières", "number")}${T_("financials", "existing_monthly_installments", "Mensualités en cours", "number")}</div>`)}
      ${panel("Pièces justificatives", docs, { sub: "Grille de vérification du contrôle C01" })}
      ${panel("Garanties", `<div class="form f3">${S_("guarantees", "type", "Nature", GUARANTEE_TYPES)}${T_("guarantees", "value", "Valeur estimée (MAD)", "number")}${T_("guarantees", "description", "Description")}</div>`)}
      ${panel("Observations de l'analyste", `<textarea data-d="observations" aria-label="Observations" ${w ? "" : "disabled"} placeholder="Éléments vérifiés, points à confirmer, appréciation motivée">${esc(d.observations)}</textarea>`)}
    </div><div class="sticky" id="analysis">${analysisPanel()}</div></div>`;
}

function analysisPanel() {
  const a = analyzeDossier(ui.draft);
  const items = (title: string, list: Row[]) =>
    list.length ? `<h3>${title} <span>${list.length}</span></h3><ul class="find">${list.map((i) => `<li class="${i.severity}">${esc(i.message)}${i.risk ? ` <span class="ref">${i.risk}</span>` : ""}</li>`).join("")}</ul>` : "";
  return `<section class="panel analysis"><div class="panel-h"><div><p class="eyebrow">Aide à l'analyse · aucune décision d'octroi</p><h2>${a.blocking ? "Présentation suspendue" : "Transmissible pour avis"}</h2></div></div>
    <div class="verdict ${a.blocking ? "bad" : "ok"}">${a.blocking ? "Le dossier ne peut pas être présenté en l'état : pièce manquante ou incohérence significative (règle de blocage C01)." : "Les pièces requises sont présentes et aucune incohérence significative n'est relevée : le dossier peut être transmis à la fonction risques."}</div>
    <div class="comp"><span>Complétude</span>${meter(a.completeness.rate, 100, a.completeness.rate === 100 ? "ok" : "")}<b>${a.completeness.present}/${a.completeness.required}</b></div>
    ${items("Pièces manquantes", a.completeness.missingDocs.map((m) => ({ message: m, severity: "alerte" })))}${items("Incohérences", a.inconsistencies)}${items("Points de vigilance", a.vigilance)}${items("Informations à compléter", a.missingInfo)}
    ${a.ratios.length ? `<h3>Ratios <span>seuils indicatifs</span></h3><dl class="kv compact">${a.ratios.map((r) => `<dt>${esc(r.label)}</dt><dd>${esc(r.value)}</dd>`).join("")}</dl>` : ""}
    <h3>Synthèse</h3><p class="small">${esc(a.synthesis)}</p>
    <div class="dlg-a">${ui.dossier && can("dossiers.write") ? btn("Supprimer", "dos-del", "", "ghost danger-t") : ""}${ui.dossier && can("anom.create") && a.blocking ? btn("Inscrire l'anomalie", "dos-anom", "", "ghost") : ""}${ui.dossier ? btn(`${icon("advisor")} Synthèse`, "ask", `data-q="Analyse le dossier ${ui.dossier} : complétude, incohérences, vigilance, risques du registre concernés et diligences avant l'avis de la fonction risques."`, "ghost") : ""}</div></section>`;
}

/* ---------------------------------------------------------------- contrôle interne */
const CTRL_FIELDS: Field[] = [
  { k: "name", l: "Intitulé", req: true, full: true },
  { k: "nature", l: "Type", t: "select", o: ["Préventif", "Détectif", "Correctif", "Détectif et correctif"] },
  { k: "status", l: "Statut", t: "select", o: ["Proposé", "En déploiement", "Opérationnel", "Efficace", "Déficient"] },
  { k: "objective", l: "Objectif", t: "textarea", req: true },
  { k: "risk_ids", l: "Risques couverts", hint: "Ex. R01, R08" },
  { k: "owner", l: "Responsable", req: true },
  { k: "procedure", l: "Procédure", t: "textarea" },
  { k: "supervision", l: "Supervision" },
  { k: "frequency", l: "Fréquence", req: true },
  { k: "evidence", l: "Preuve attendue", t: "textarea" },
  { k: "indicator", l: "Indicateur de performance", t: "textarea" },
  { k: "anomaly_treatment", l: "Traitement des anomalies", t: "textarea" },
  { k: "last_review", l: "Dernière revue", t: "date" },
];
function pControls() {
  const t = tab("controls", "fiches");
  const r = snapshot().risks;
  let body = "";
  if (t === "fiches") {
    const w = can("controls.write");
    const cover = table(["Risque", ...state.controls.map((c) => c.id), "Couverture"], r.map((x) => {
      const n = state.controls.filter((c) => splitIds(c.risk_ids).includes(x.id)).length;
      return [`<span class="ref">${x.id}</span> ${esc(x.title.length > 46 ? x.title.slice(0, 46) + "…" : x.title)}`, ...state.controls.map((c) => (splitIds(c.risk_ids).includes(x.id) ? `<span class="dot-on" title="${c.id} couvre ${x.id}">●</span>` : "")),
        n === 0 ? `<span class="st bad">Non couvert</span>` : n === 1 ? `<span class="st warn">1 contrôle</span>` : `<span class="st ok">${n} contrôles</span>`];
    }), { cls: "center" });
    body = (w ? "" : readonly("Lecture seule : les fiches sont tenues par le contrôle interne.")) +
      panel("Couverture des risques", cover, { sub: "Un risque couvert par un seul contrôle est un point de dépendance." }) +
      panel("Fiches de contrôle", state.controls.map((c) => `<details class="sheet"><summary><span class="ref">${c.id}</span><b>${esc(c.name)}</b><span class="tag">${esc(c.nature)}</span>${status(c.status)}</summary>
        <dl class="kv two">${[["Objectif", c.objective], ["Risques couverts", c.risk_ids], ["Procédure", c.procedure], ["Responsable", c.owner], ["Supervision", c.supervision], ["Fréquence", c.frequency], ["Preuve attendue", c.evidence], ["Indicateur", c.indicator], ["Traitement des anomalies", c.anomaly_treatment], ["Dernière revue", c.last_review ? fdate(c.last_review) : "Pas encore revu"]].map(([k, v]) => `<dt>${k}</dt><dd>${esc(v) || "–"}</dd>`).join("")}</dl>
        ${w ? `<div class="dlg-a">${btn("Supprimer", "ctrl-del", `data-id="${c.id}"`, "ghost danger-t")}${btn("Modifier", "ctrl-edit", `data-id="${c.id}"`, "ghost")}</div>` : ""}</details>`).join(""),
        { aside: w ? btn(`${icon("plus")} Nouvelle fiche`, "ctrl-new", "", "ghost") : "" });
  } else {
    const w = can("coso.write");
    body = (w ? "" : readonly("Lecture seule : les principes sont appréciés par le contrôle interne.")) +
      `<div class="coso-row">${state.components.map((c) => {
        const m = maturity(c.id);
        return `<div class="coso"><p class="eyebrow">${esc(c.principles)}</p><h3>${esc(c.name)}</h3><div class="comp">${meter(m ?? 0, 5, m != null && m < 2 ? "bad" : "")}<b>${m == null ? "–" : `${String(m).replace(".", ",")}/5`}</b></div></div>`;
      }).join("")}</div>` +
      `<p class="small">Maturité calculée à partir des principes appréciés (déficient 1 ; partiel 2,5 ; satisfaisant 4,5). Les principes non évalués ne comptent pas.</p>` +
      state.components.map((c) => panel(`${c.id}. ${esc(c.name)}`, table(["Principe", "Intitulé", "Nature", "Diagnostic", "Risques", "Appréciation"], state.principles.filter((p) => p.component_id === c.id).map((p) => [
        `<span class="ref">${p.id}</span>`, esc(p.title), `<small>${esc(p.nature)}</small>`, `<small>${esc(p.diagnostic)}</small>`, ids(p.risk_ids),
        w ? `<select data-ch="assess" data-id="${p.id}" aria-label="Appréciation ${p.id}">${["Non évalué", "Déficient", "Partiel", "Satisfaisant"].map((a) => `<option ${a === p.assessment ? "selected" : ""}>${a}</option>`).join("")}</select>` : status(p.assessment)])),
        { sub: `Lacunes : ${esc(c.gaps)} — Recommandation : ${esc(c.recommendations)}` })).join("");
  }
  return head("Contrôle interne", "Contrôles organisationnels et diagnostic COSO 2013 : 5 composantes, 17 principes.", `<button class="btn ghost" data-act="${t === "fiches" ? "exp-controls" : "exp-coso"}">${icon("down")} CSV</button>`) +
    tabs("controls", [["fiches", "Contrôles", state.controls.length], ["coso", "COSO 2013", 17]], t) + body;
}

/* ---------------------------------------------------------------- plan d'action */
const ACT_FIELDS: Field[] = [
  { k: "title", l: "Action", req: true, full: true }, { k: "priority", l: "Priorité", t: "select", o: ["P1", "P2", "P3"] },
  { k: "status", l: "Statut", t: "select", o: ["À faire", "En cours", "Terminé", "Bloqué"] }, { k: "owner", l: "Responsable", req: true }, { k: "due", l: "Échéance" },
  { k: "deliverable", l: "Livrable ou preuve", full: true }, { k: "risk_ids", l: "Risques traités" }, { k: "control_ids", l: "Contrôles concernés" },
  { k: "progress", l: "Avancement (%)", t: "range", min: 0, max: 100 },
];
const REC_FIELDS: Field[] = [
  { k: "risk_id", l: "Risque", req: true, hint: "Ex. R03" }, { k: "status", l: "Statut", t: "select", o: ["À lancer", "En cours", "Mise en œuvre", "Abandonnée"] },
  { k: "coso_gap", l: "Lacune COSO", t: "textarea", req: true }, { k: "action", l: "Action corrective", t: "textarea", req: true },
  { k: "owner", l: "Responsable", req: true }, { k: "basis", l: "Fondement", t: "select", o: ["Constat", "Hypothèse"] }, { k: "indicator", l: "Indicateur de suivi", t: "textarea", req: true },
];
const ANOM_FIELDS: Field[] = [
  { k: "detected_on", l: "Détectée le", t: "date", req: true }, { k: "dossier_ref", l: "Dossier ou référence" }, { k: "nature", l: "Nature de l'anomalie", t: "textarea", req: true },
  { k: "severity", l: "Gravité", t: "select", o: ["Mineure", "Significative", "Majeure", "Critique"] }, { k: "status", l: "Statut", t: "select", o: ["Ouverte", "En cours", "Clôturée"] },
  { k: "risk_id", l: "Risque lié", hint: "Ex. R01" }, { k: "control_id", l: "Contrôle lié", hint: "Ex. C04" }, { k: "owner", l: "Responsable du traitement", req: true },
  { k: "due_on", l: "Échéance de régularisation", t: "date" }, { k: "escalation", l: "Niveau d'escalade (charte, art. 11)", t: "range", min: 1, max: 3 }, { k: "resolution", l: "Résolution et preuve de clôture", t: "textarea" },
];
function pActions() {
  const s = snapshot();
  const t = tab("actions", "plan");
  let body = "";
  if (t === "plan") {
    const w = can("actions.write");
    body = (w ? "" : readonly("Lecture seule : le plan d'action est piloté par la direction, les risques et le contrôle interne.")) +
      panel("", table(["Priorité", "Action", "Responsable", "Échéance", "Risques", "Statut", "Avancement", ""], s.actions.map((a) => [
        `<span class="prio p${a.priority.slice(1)}">${a.priority}</span>`, `<span class="ref">${a.id}</span> ${esc(a.title)}<small>${esc(a.deliverable)}</small>`, `<small>${esc(a.owner)}</small>`, `<small>${esc(a.due)}</small>`,
        `<span class="ids">${ids(a.risk_ids)}</span>`, status(a.status), `<div class="mcell">${meter(a.progress, 100, a.progress === 100 ? "ok" : "")}<span>${a.progress} %</span></div>`, w ? btn("Mettre à jour", "act-edit", `data-id="${a.id}"`, "ghost sm") : ""])),
        { aside: w ? btn(`${icon("plus")} Action`, "act-new", "", "ghost") : "" });
  } else if (t === "recos") {
    const w = can("recos.write");
    body = `<div class="chains">${s.recommendations.map((r) => `<article class="chain"><header><span class="ref">${r.id}</span>${status(r.status)}<span class="tag">${esc(r.basis)}</span>${w ? btn("Modifier", "rec-edit", `data-id="${r.id}"`, "ghost sm") : ""}</header>
      <ol>${[["Risque", `<span class="ref">${esc(r.risk_id)}</span> ${esc(state.risks.find((x) => x.id === r.risk_id)?.title ?? "")}`], ["Lacune COSO", esc(r.coso_gap)], ["Action corrective", esc(r.action)], ["Responsable", esc(r.owner)], ["Indicateur de suivi", esc(r.indicator)]].map(([k, v]) => `<li><span>${k}</span><p>${v}</p></li>`).join("")}</ol></article>`).join("")}</div>` +
      (w ? `<div class="dlg-a left">${btn(`${icon("plus")} Recommandation`, "rec-new", "", "ghost")}</div>` : "");
  } else {
    const open = s.anomalies.filter((a) => a.status !== "Clôturée");
    const late = open.filter((a) => a.due_on && a.due_on < today());
    body = `<div class="metrics four">${metric("Ouvertes", String(open.length))}${metric("En retard", String(late.length), "", late.length ? "bad" : "")}${metric("Niveau 3", String(open.filter((a) => +a.escalation === 3).length), "remontée à la direction générale")}${metric("Clôturées", String(s.anomalies.length - open.length))}</div>` +
      panel("", table(["Référence", "Détectée", "Nature", "Gravité", "Liens", "Responsable", "Échéance", "Esc.", "Statut", ""], s.anomalies.map((a) => {
        const isLate = a.status !== "Clôturée" && a.due_on && a.due_on < today();
        return [`<span class="ref">${a.id}</span><small>${esc(a.dossier_ref)}</small>`, `<small>${fdate(a.detected_on)}</small>`, `${esc(a.nature)}${a.resolution ? `<small class="ok-t">${esc(a.resolution)}</small>` : ""}<small>Déclarée par ${esc(a.declared_by)}</small>`,
          esc(a.severity), `<span class="ids">${ids(a.risk_id)}${ids(a.control_id)}</span>`, `<small>${esc(a.owner)}</small>`, `<small class="${isLate ? "bad-t" : ""}">${a.due_on ? fdate(a.due_on) : "–"}${isLate ? " · retard" : ""}</small>`, `N${a.escalation}`, status(a.status),
          can("anom.write") ? btn("Traiter", "anom-edit", `data-id="${a.id}"`, "ghost sm") : ""];
      }), { empty: `<p><b>Aucune anomalie enregistrée.</b> Toute anomalie ou dérogation doit être inscrite le jour de sa détection (charte, article 11).</p>${can("anom.create") ? btn(`${icon("plus")} Déclarer une anomalie`, "anom-new", "", "primary") : ""}` }),
      { aside: can("anom.create") && s.anomalies.length ? btn(`${icon("plus")} Déclarer`, "anom-new", "", "ghost") : "" });
  }
  return head("Plan d'action", "Actions correctives priorisées, chaînes de recommandations et registre unique des anomalies et dérogations (C04).",
    `<button class="btn ghost" data-act="${t === "plan" ? "exp-actions" : t === "recos" ? "exp-recos" : "exp-anoms"}">${icon("down")} CSV</button>`) +
    tabs("actions", [["plan", "Actions", s.actions.length], ["recos", "Recommandations", s.recommendations.length], ["anoms", "Anomalies", s.anomalies.filter((a) => a.status !== "Clôturée").length]], t) + body;
}

/* ---------------------------------------------------------------- référentiel */
function pFramework() {
  const t = tab("framework", "charte");
  let body = "";
  if (t === "charte") {
    const r = snapshot().risks;
    const zone = (l: Level) => (l === "Critique" ? "inacceptable" : l === "Élevé" ? "renforcee" : "acceptable");
    body = `<div class="grid g-1-1-1">${SEED.appetite_levels.map((l: Row) => `<section class="panel zone ${l.key}"><h2>${esc(l.title)}</h2><p class="small">${esc(l.description)}</p>
      <ul>${l.examples.map((e: string) => `<li>${esc(e)}</li>`).join("")}</ul><p class="small zr"><b>Risques du registre</b> ${r.filter((x) => zone(x.level) === l.key).map((x) => `<span class="ref">${x.id}</span>`).join("") || "aucun"}</p></section>`).join("")}</div>
      <p class="small">Positionnement : faible et modéré → accepté sous contrôle ; élevé → autorisation renforcée ; critique → hors appétence en l'état.</p>
      <div class="grid g-1-1">${panel("Principes (article 3)", `<ol class="plain">${SEED.charter_principles.map((p: string) => `<li>${esc(p)}</li>`).join("")}</ol>`)}
      ${panel("Escalade (article 11)", SEED.escalation.map((e: Row) => `<div class="esc"><span class="n${e.level}">N${e.level}</span><div><b>${esc(e.title.replace(/^Niveau \d – /, ""))}</b><p class="small">${esc(e.text)}</p></div></div>`).join(""))}</div>` +
      panel("Appétence par catégorie", table(["Catégorie", "Appétence", "Limites et situations inacceptables"], SEED.appetite_by_category.map((c: Row) => [`<b>${esc(c.category)}</b>`, esc(c.appetite), esc(c.limits)])));
  } else {
    const actors = SEED.raci_actors, acts = SEED.raci_activities;
    const blocks = ["Constitution", "Analyse / contrôle", "Autorisation"];
    const ra = (c: string) => ["R", "A", "A/R"].includes(c);
    const conflicts = actors.filter((x: Row) => blocks.every((b) => acts.some((a: Row) => a.block === b && ra(a.roles[x.key]))));
    const singleA = acts.every((a: Row) => Object.values(a.roles).filter((c: any) => c === "A" || c === "A/R").length === 1);
    body = note(conflicts.length || !singleA ? "Conflit de séparation des tâches détecté dans la matrice." : `${icon("check")} Séparation des tâches vérifiée : une seule responsabilité finale par activité, et aucun acteur ne cumule constitution, analyse et autorisation.`, conflicts.length || !singleA ? "bad" : "ok") +
      panel("Matrice RACI", `<div class="tw"><table class="raci"><thead><tr><th>Activité</th>${actors.map((a: Row) => `<th>${esc(a.label)}</th>`).join("")}</tr></thead><tbody>${acts.map((a: Row) => `<tr><td>${a.n}. ${esc(a.activity)}<small>${esc(a.block)}</small></td>${actors.map((x: Row) => `<td><span class="rc r${String(a.roles[x.key]).replace("/", "").replace("–", "n")}">${a.roles[x.key]}</span></td>`).join("")}</tr>`).join("")}</tbody></table></div>`,
        { sub: "R réalise · A valide, responsabilité finale · C consulté · I informé" }) +
      panel("Délégations d'autorisation", table(["Décision", "Réalise", "Valide", "Est informé"], SEED.delegations.map((d: Row) => [`<b>${esc(d.decision)}</b>`, `<small>${esc(d.realise)}</small>`, `<small>${esc(d.valide)}</small>`, `<small>${esc(d.informe)}</small>`])));
  }
  return head("Référentiel", "Charte d'appétence au risque, matrice RACI et délégations d'autorisation.", "") +
    tabs("framework", [["charte", "Charte d'appétence"], ["raci", "Gouvernance RACI"]], t) + body;
}

/* ---------------------------------------------------------------- assistant */
const PROMPTS = [
  ["Où en est le dispositif ?", "Fais une synthèse exécutive : risques prioritaires, état des contrôles, plan d'action, anomalies, et les trois décisions à prendre."],
  ["Risques à traiter en premier", "Quels risques traiter en premier et pourquoi, compte tenu de la chaîne causale entre les risques et des repères du portefeuille de référence ?"],
  ["Recommandations", "Propose des recommandations pour les risques critiques et élevés au format RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI."],
  ["Contrôles à mettre en service", "Quels risques sont insuffisamment couverts et quels contrôles faut-il mettre en service en priorité ?"],
  ["Lire les données de défaut", "Que nous apprennent les données de défaut du portefeuille de référence pour la cotation de R03, R04 et R01 ?"],
  ["Préparer le comité des risques", "Prépare l'ordre du jour et les points de décision d'un comité des risques à partir des données de la plateforme."],
];
function pAdvisor() {
  return head("Risk Advisor", "Assistant d'analyse fondé sur les données de la plateforme et du portefeuille de référence. Il ne prend aucune décision d'octroi.",
    ui.chat.length ? btn("Nouvelle conversation", "chat-reset", "", "ghost") : "") +
    `<div class="advisor"><div class="chat" id="chat" aria-live="polite">${ui.chat.length ? ui.chat.map((m: Row) => `<div class="msg ${m.role}">${m.role === "user" ? esc(m.content) : `<div class="md">${md(m.content)}</div>`}</div>`).join("") :
      `<div class="starter"><p class="small">${ui.ai ? "Connecté au modèle Claude via claude.ai." : "Moteur d'analyse intégré. Ouverte depuis claude.ai, la plateforme utilise le modèle Claude."}</p><div class="prompts">${PROMPTS.map(([l, q]) => `<button data-act="ask" data-q="${esc(q)}"><b>${l}</b><span>${esc(q)}</span></button>`).join("")}</div></div>`}</div>
    <form id="askf" class="ask"><label class="sr" for="askq">Votre question</label><textarea id="askq" rows="1" placeholder="Posez une question sur un risque, un contrôle, un dossier…"></textarea><button class="btn primary" ${ui.busy ? "disabled" : ""}>Envoyer</button></form></div>`;
}

/* ---------------------------------------------------------------- administration */
function pAdmin() {
  const t = tab("admin", can("team.manage") ? "team" : "data");
  let body = "";
  if (t === "team") {
    const me = session.me!;
    const entries = Object.entries(session.members);
    body = me.mode === "local"
      ? note("Copie locale : la gestion d'équipe est disponible quand la plateforme est ouverte depuis claude.ai. Chaque personne y est identifiée par son compte claude.ai ; la plateforme ne gère aucun mot de passe.")
      : panel("Membres et rôles", `<p class="small">L'accès se règle dans le menu <b>Partager</b> de claude.ai. Ici, vous attribuez à chaque membre un rôle métier ; une personne sans rôle consulte en lecture seule.</p>
        ${table(["Membre", "Rôle", ""], [[`<b>${esc(me.name)}</b><small>Propriétaire</small>`, "Administrateur", ""], ...entries.map(([id, role]) => [`<span data-name="${esc(id)}">${esc(ui.names[id] ?? "…")}</span>`,
          `<select data-ch="role" data-id="${esc(id)}" aria-label="Rôle">${Object.entries(ROLES).map(([k, l]) => `<option value="${k}" ${k === role ? "selected" : ""}>${l}</option>`).join("")}</select>`, btn("Retirer", "member-del", `data-id="${esc(id)}"`, "ghost sm")])])}
        <div class="toolbar"><input id="people" type="search" placeholder="Ajouter un membre : rechercher un nom" aria-label="Rechercher une personne"></div><div id="people-res"></div>`) +
      panel("Droits par rôle", table(["Droit", ...Object.values(ROLES)], Object.entries(PERMS).map(([p, roles]) => [PERM_LABELS[p], ...Object.keys(ROLES).map((r) => (roles.includes(r) ? `<span class="dot-on">●</span>` : `<span class="mute-t">–</span>`))]), { cls: "center" }));
  } else if (t === "audit") {
    body = panel("", table(["Date", "Auteur", "Opération", "Objet", "Détail"], state.audit.slice(0, 200).map((a) => [`<small>${new Date(a.at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}</small>`, `<small>${esc(a.who)}</small>`, esc(a.action), `${esc(a.entity)} ${a.id ? `<span class="ref">${esc(a.id)}</span>` : ""}`, `<small>${esc(a.details)}</small>`]), { empty: "Aucune opération enregistrée." }));
  } else {
    body = panel("Exports", `<div class="exports">${[["exp-risks", "Registre des risques", "CSV"], ["exp-controls", "Fiches de contrôle", "CSV"], ["exp-coso", "Diagnostic COSO", "CSV"], ["exp-actions", "Plan d'action", "CSV"], ["exp-recos", "Recommandations", "CSV"], ["exp-anoms", "Anomalies", "CSV"], ["exp-marts", "Portefeuille de référence", "CSV"], ["exp-json", "Sauvegarde complète", "JSON"]]
      .map(([a, l, f]) => `<button class="exp" data-act="${a}"><b>${l}</b><span>${f}</span></button>`).join("")}</div>`) +
      (can("team.manage") ? panel("Restauration", `<p class="small">Importer une sauvegarde remplace toutes les données de l'équipe. Restaurer recharge les données de démonstration et efface les saisies.</p><div class="dlg-a left"><label class="btn ghost file">Importer une sauvegarde<input type="file" id="imp" accept="application/json" hidden></label>${btn("Restaurer les données de démonstration", "reset", "", "ghost danger-t")}</div>`) : "");
  }
  const items: [string, string][] = [];
  if (can("team.manage")) items.push(["team", "Équipe et rôles"]);
  if (can("audit.view")) items.push(["audit", "Journal d'audit"]);
  items.push(["data", "Exports et sauvegardes"]);
  return head("Administration", "Équipe et rôles, journal d'audit, exports et sauvegardes.", "") + tabs("admin", items, t) + body;
}

/* ================================================================ rendu */
const NAV: [string, string][] = [
  ["overview", "Vue d'ensemble"], ["portfolio", "Portefeuille de référence"], ["risks", "Risques"], ["dossiers", "Dossiers TPE"],
  ["controls", "Contrôle interne"], ["actions", "Plan d'action"], ["framework", "Référentiel"], ["advisor", "Risk Advisor"], ["admin", "Administration"],
];
const PAGES: Record<string, () => string> = { overview: pOverview, portfolio: pPortfolio, risks: pRisks, dossiers: pDossiers, controls: pControls, actions: pActions, framework: pFramework, advisor: pAdvisor, admin: pAdmin };
const MARK = `<svg class="mark" viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="9"/><path d="M8 27c4-8.5 8-12.5 12-12.5S28 18.5 32 27" fill="none" stroke-width="2.6" stroke-linecap="round"/><path d="M7 31h26" stroke-width="2.2" stroke-linecap="round"/></svg>`;
const route = () => (PAGES[location.hash.slice(1)] ? location.hash.slice(1) : "overview");

const TREE: [string, [string, string][]][] = [
  ["Pilotage", [["overview", "Vue d'ensemble"], ["portfolio", "Portefeuille de référence"]]],
  ["Risques", [["risks", "Registre des risques"], ["dossiers", "Dossiers TPE"]]],
  ["Contrôle interne", [["controls", "Contrôles et COSO"], ["framework", "Référentiel"]]],
  ["Suivi", [["actions", "Plan d'action"]]],
  ["Outils", [["advisor", "Risk Advisor"], ["admin", "Administration"]]],
];
type MenuItem = [string, string, string?] | null; // [libellé, action ou #page, raccourci]
function menus(): [string, MenuItem[]][] {
  return [
    ["Fichier", [
      ["Exporter le registre des risques (CSV)", "exp-risks"], ["Exporter le plan d'action (CSV)", "exp-actions"], ["Exporter les anomalies (CSV)", "exp-anoms"], null,
      ["Sauvegarde complète (JSON)", "exp-json"], ...(can("team.manage") ? [["Restaurer les données de démonstration", "reset"] as MenuItem] : []),
    ]],
    ["Affichage", NAV.map(([k, l], i) => [l, `#${k}`, `Alt+${i + 1}`] as MenuItem)],
    ["Risques", [
      ...(can("risks.write") ? [["Nouveau risque…", "risk-new"] as MenuItem] : []), ["Registre", "view:table"], ["Matrice probabilité × gravité", "view:matrix"], null,
      ...(can("dossiers.write") ? [["Nouveau dossier TPE…", "dos-new"] as MenuItem] : []), ["Liste des dossiers", "#dossiers"],
    ]],
    ["Contrôle", [["Fiches de contrôle", "goto:controls:fiches"], ["Diagnostic COSO 2013", "goto:controls:coso"], null, ["Charte d'appétence", "goto:framework:charte"], ["Matrice RACI", "goto:framework:raci"]]],
    ["Suivi", [["Plan d'action", "goto:actions:plan"], ["Recommandations", "goto:actions:recos"], ["Anomalies", "goto:actions:anoms"], ...(can("anom.create") ? [null, ["Déclarer une anomalie…", "anom-new"] as MenuItem] : [])]],
    ["Outils", [["Risk Advisor", "#advisor"], ["Portefeuille de référence", "#portfolio"], ["Administration", "#admin"]]],
    ["Aide", [["Raccourcis clavier", "help-keys"], ["À propos de Crédit Horizon", "help-about"]]],
  ];
}

function render() {
  const app = document.getElementById("app")!;
  if (!session.ready) {
    app.innerHTML = `<div class="boot">${MARK}<p>Démarrage de Crédit Horizon…</p></div>`;
    return;
  }
  const cur = route();
  const badge: Record<string, number> = {
    actions: state.anomalies.filter((a) => a.status !== "Clôturée" && a.due_on && a.due_on < today()).length,
    dossiers: state.dossiers.filter((d) => d.analysis?.blocking).length,
  };
  const label = NAV.find((n) => n[0] === cur)![1];
  const syncTxt = session.me?.mode === "local" ? "Copie locale" : sharedStore() ? "Synchronisé avec l'équipe" : "Hors ligne";
  app.innerHTML = `<div class="win">
    <header class="titlebar"><button class="tb-menu" data-act="menu" aria-label="Ouvrir le navigateur">${icon("menu")}</button>${MARK}<b>Crédit Horizon</b><span class="tb-sub">Risk Intelligence — ${label}</span>
      <span class="tb-user"><span class="av">${esc((session.me?.name || "?").split(/\s+/).map((x) => x[0]).slice(0, 2).join("").toUpperCase())}</span>${esc(session.me?.name)} · ${ROLES[session.role]}</span></header>
    <nav class="menubar" aria-label="Menus">${menus().map(([m, items]) => `<details class="mnu"><summary>${m}</summary><div class="mnu-l" role="menu">${items.map((it) => it === null ? `<hr>` :
      `<button role="menuitem" data-act="menu-go" data-go="${it[1]}"><span>${it[0]}</span>${it[2] ? `<kbd>${it[2]}</kbd>` : ""}</button>`).join("")}</div></details>`).join("")}</nav>
    <div class="body">
      <aside class="side" id="side" aria-label="Navigateur">${TREE.map(([g, items]) => `<div class="tg"><div class="tg-h">${g}</div>${items.map(([k, l]) => `<a href="#${k}" class="${k === cur ? "on" : ""}" ${k === cur ? 'aria-current="page"' : ""}>${icon(k)}<span>${l}</span>${badge[k] ? `<em>${badge[k]}</em>` : ""}</a>`).join("")}</div>`).join("")}
        <div class="side-foot">Projet EMSI · Génie financier<br>F. Z. Chakib · I. Mouichou</div></aside>
      <main id="content" tabindex="-1">${session.storeError ? note(esc(session.storeError), "bad") : ""}${session.role === "lecteur" && session.me?.mode === "claude" ? note(`${icon("lock")} Lecture seule : l'administrateur peut vous attribuer un rôle.`, "lock") : ""}${PAGES[cur]()}</main>
    </div>
    <footer class="statusbar"><span class="sb-ok">Prêt</span><span>${state.risks.length} risques · ${state.controls.length} contrôles · ${state.dossiers.length} dossiers · ${state.anomalies.filter((a) => a.status !== "Clôturée").length} anomalies ouvertes</span>
      <span class="sb-demo">Données de démonstration</span><span class="sb-r">${ROLES[session.role]}</span><span class="sb-sync ${sharedStore() ? "on" : ""}">${syncTxt}</span><span>${new Date().toLocaleDateString("fr-FR")}</span></footer></div>`;
  if (cur === "risks") applyFilter();
  const c = document.getElementById("chat");
  if (c) c.scrollTop = c.scrollHeight;
  if (cur === "admin" && tab("admin", "team") === "team" && session.me?.mode === "claude") loadNames();
}

function infoBox(title: string, html: string) {
  document.getElementById("modal")!.innerHTML = `<div class="scrim" data-act="close"></div><div class="dlg small" role="dialog" aria-modal="true"><div class="dlg-h"><h3>${title}</h3><button class="icon-btn" data-act="close" aria-label="Fermer">${icon("close")}</button></div>${html}<div class="dlg-a"><button class="btn primary" data-act="close">Fermer</button></div></div>`;
  document.getElementById("modal")!.className = "open";
}

async function loadNames() {
  const list = Object.keys(session.members).filter((id) => !ui.names[id]);
  if (!list.length) return;
  const p = await profiles(list);
  for (const id of list) ui.names[id] = (p as any)[id]?.name || "Membre";
  document.querySelectorAll<HTMLElement>("[data-name]").forEach((el) => (el.textContent = ui.names[el.dataset.name!] ?? "Membre"));
}

function applyFilter() {
  const q = ui.filter.toLowerCase().trim();
  let n = 0;
  document.querySelectorAll<HTMLTableRowElement>("#rt tbody tr").forEach((tr) => {
    const show = !q || (tr.dataset.text || "").includes(q);
    tr.hidden = !show;
    if (show) n++;
  });
  const c = document.getElementById("qn");
  if (c) c.textContent = `${n} risque${n > 1 ? "s" : ""}`;
}

/* ================================================================ assistant */
function sbaContext() {
  return `## Portefeuille de référence (données publiques vérifiées)
Source : ${M.source.publisher}, ${M.source.dataset}, situation au ${O.as_of}, fichier ${LOANS.name} (SHA-256 ${LOANS.sha256}). Prêts SBA 7(a) ${O.cohorts} aux petites entreprises américaines ; repère externe, pas le portefeuille de Crédit Horizon.
Prêts décaissés ${O.loans_funded}, dénoués ${O.loans_resolved}, défauts ${O.defaults}, taux de défaut ${(O.default_rate * 100).toFixed(2)} %, taux de perte ${(O.loss_rate * 100).toFixed(2)} %, délai médian avant perte ${O.median_months_to_default} mois, part des pertes avant 24 mois ${(O.share_defaults_within_24m * 100).toFixed(1)} %, part des 3 premiers secteurs ${(O.top3_sector_share * 100).toFixed(1)} %.
Par cohorte : ${T.by_cohort.map((c: Row) => `FY${c.cohort_fy} ${(c.default_rate * 100).toFixed(1)} %`).join(", ")}.
Par secteur : ${T.by_sector.slice(0, 12).map((r: Row) => `${r.sector} ${(r.default_rate * 100).toFixed(1)} %`).join(" ; ")}.
Par ancienneté : ${T.by_business_age.map((r: Row) => `${AGE_FR[r.business_age] ?? r.business_age} ${(r.default_rate * 100).toFixed(1)} %`).join(" ; ")}.
Garantie réelle : ${T.by_collateral.map((r: Row) => `${r.collateral ? "avec" : "sans"} ${(r.default_rate * 100).toFixed(1)} %`).join(", ")}.`;
}

async function ask(q: string) {
  if (ui.busy || !q.trim()) return;
  ui.busy = true;
  const snap: any = snapshot();
  const focus = ui.dossier && /dossier/i.test(q) ? ui.dossier : undefined;
  ui.chat.push({ role: "user", content: q }, { role: "assistant", content: "_Analyse en cours…_" });
  if (route() !== "advisor") location.hash = "advisor";
  else render();
  const last = ui.chat[ui.chat.length - 1];
  const paint = () => {
    const el = document.querySelector("#chat .msg.assistant:last-child .md");
    if (el) el.innerHTML = md(last.content);
    const c = document.getElementById("chat");
    if (c) c.scrollTop = c.scrollHeight;
  };
  const sample = await capability("sample");
  if (sample) {
    const conv = ui.chat.slice(0, -1).filter((m: Row) => !m.content.startsWith("_Analyse"));
    const first = conv.findIndex((m: Row) => m.role === "user");
    const pre = `${ADVISOR_RULES}\n\nUtilisateur : ${session.me!.name}, rôle ${ROLES[session.role]}.\n\n${buildContext(snap, focus)}\n\n${sbaContext()}\n\n---\nDemande :\n\n`;
    const input = conv.slice(first).slice(-12).map((m: Row, i: number) => ({ role: m.role, content: i === 0 ? pre + m.content : m.content }));
    try {
      const r = await sample(input, { cache: false, onText: ({ text }: { text: string }) => { last.content = text || "_Rédaction…_"; paint(); } });
      last.content = r.text + (r.truncated ? "\n\n> Réponse écourtée : posez une question plus ciblée." : "");
      ui.ai = true;
    } catch (e: any) {
      const why = e?.code === "not_granted" ? "l'accès à Claude n'a pas été autorisé" : e?.code === "rate_limited" ? "limite d'utilisation de Claude atteinte" : "Claude n'a pas répondu";
      last.content = `> Réponse du moteur d'analyse intégré (${why}).\n\n` + offlineAnswer(snap, q, focus);
    }
  } else {
    last.content = offlineAnswer(snap, q, focus);
  }
  ui.busy = false;
  audit(who(), "Question", "Risk Advisor", "", q.slice(0, 160));
  save();
  render();
}

/* ================================================================ CRUD */
function validate(fields: Field[], v: Row) {
  const miss = fields.filter((f) => f.req && !String(v[f.k] ?? "").trim()).map((f) => f.l);
  return miss.length ? `Champs obligatoires : ${miss.join(", ")}.` : "";
}
function crud(kind: string, rows: Row[], fields: Field[], label: string, prefix: string, pad: number, sep: string, row: Row | null, defaults: Row = {}) {
  modal(row ? `${label} ${row.id}` : `Nouveau : ${label.toLowerCase()}`, fields, row ? { ...row } : defaults, (v) => {
    const err = validate(fields, v);
    if (err) return err;
    for (const f of fields) if (f.t === "range") v[f.k] = Number(v[f.k]);
    if (row) {
      const before = { ...row };
      Object.assign(row, v, { updated_at: today() });
      if (kind === "risk" && (before.probability !== row.probability || before.gravity !== row.gravity))
        state.history.push({ risk_id: row.id, probability: row.probability, gravity: row.gravity, score: row.probability * row.gravity, recorded_at: today() });
      record("Modification", label, row.id);
      toast(`${label} ${row.id} mis à jour.`);
    } else {
      const id = nextId(rows, prefix, pad, sep);
      rows.push({ id, ...v, ...(kind === "anom" ? { declared_by: session.me!.name } : {}), created_at: today() });
      if (kind === "risk") {
        state.history.push({ risk_id: id, probability: v.probability, gravity: v.gravity, score: v.probability * v.gravity, recorded_at: today() });
        ui.sel = id;
      }
      record("Création", label, id);
      toast(`${label} ${id} créé.`);
    }
  });
}

/* ================================================================ événements */
document.addEventListener("click", (e) => {
  if (!(e.target as HTMLElement).closest("details.mnu")) document.querySelectorAll("details.mnu[open]").forEach((d) => d.removeAttribute("open"));
  const el = (e.target as HTMLElement).closest<HTMLElement>("[data-act]");
  if (!el) {
    if (document.body.classList.contains("nav-open") && !(e.target as HTMLElement).closest("#side")) document.body.classList.remove("nav-open");
    return;
  }
  const act = el.dataset.act!, id = el.dataset.id ?? "";
  const find = (rows: Row[]) => rows.find((r) => String(r.id) === id) || null;
  switch (act) {
    case "menu": return void document.body.classList.toggle("nav-open");
    case "menu-go": {
      document.querySelectorAll("details.mnu[open]").forEach((d) => d.removeAttribute("open"));
      const go = el.dataset.go!;
      if (go.startsWith("#")) { location.hash = go.slice(1); return; }
      if (go.startsWith("view:")) { ui.view = go.slice(5); if (route() !== "risks") location.hash = "risks"; return render(); }
      if (go.startsWith("goto:")) { const [, pg, tb] = go.split(":"); ui.tab[pg] = tb; if (route() !== pg) location.hash = pg; return render(); }
      const fake = document.createElement("button");
      fake.dataset.act = go;
      document.body.appendChild(fake);
      fake.click();
      fake.remove();
      return;
    }
    case "help-keys":
      return infoBox("Raccourcis clavier", `<table><tbody>${NAV.map(([, l], i) => `<tr><td><kbd>Alt+${i + 1}</kbd></td><td>${l}</td></tr>`).join("")}<tr><td><kbd>Échap</kbd></td><td>Fermer une fenêtre ou un menu</td></tr><tr><td><kbd>Entrée</kbd></td><td>Ouvrir la fiche du risque sélectionné</td></tr></tbody></table>`);
    case "help-about":
      return infoBox("À propos", `<p><b>Crédit Horizon · Risk Intelligence</b><br>Gestion des risques financiers d'un organisme de financement des TPE : registre P × G, dossiers, contrôle interne COSO 2013, gouvernance, plan d'action et portefeuille de référence SBA.</p><p class="small">Projet EMSI Tanger · Génie financier, 5<sup>e</sup> année · Fatima Zahrae Chakib et Inass Mouichou. Outil d'aide à la décision, sans décision automatique d'octroi. Les anomalies, dossiers et avancements sont des données de démonstration.</p>`);
    case "close": return close();
    case "tab": ui.tab[el.dataset.page!] = id; return render();
    case "view": ui.view = id; if (route() !== "risks") location.hash = "risks"; return render();
    case "sel": ui.sel = id || null; if (route() !== "risks" && id) location.hash = "risks"; return render();
    case "risk-new": return crud("risk", state.risks, RISK_FIELDS, "Risque", "R", 2, "", null, { category: "Crédit", basis: "Constat", probability: 3, gravity: 3 });
    case "risk-edit": return crud("risk", state.risks, RISK_FIELDS, "Risque", "R", 2, "", find(state.risks));
    case "risk-del":
      return confirmBox(`Supprimer le risque ${id} du registre ? Son historique de cotation sera aussi supprimé.`, () => {
        state.risks = state.risks.filter((r) => r.id !== id);
        state.history = state.history.filter((h) => h.risk_id !== id);
        ui.sel = null;
        record("Suppression", "Risque", id);
        toast(`Risque ${id} supprimé.`);
        render();
      });
    case "ctrl-new": return crud("ctrl", state.controls, CTRL_FIELDS, "Contrôle", "C", 2, "", null, { nature: "Préventif", status: "Proposé" });
    case "ctrl-edit": return crud("ctrl", state.controls, CTRL_FIELDS, "Contrôle", "C", 2, "", find(state.controls));
    case "ctrl-del":
      return confirmBox(`Supprimer la fiche ${id} ?`, () => {
        state.controls = state.controls.filter((r) => r.id !== id);
        record("Suppression", "Contrôle", id);
        render();
      });
    case "act-new": return crud("act", state.actions, ACT_FIELDS, "Action", "A", 2, "", null, { priority: "P2", status: "À faire", progress: 0 });
    case "act-edit": return crud("act", state.actions, ACT_FIELDS, "Action", "A", 2, "", find(state.actions));
    case "rec-new": return crud("rec", state.recommendations, REC_FIELDS, "Recommandation", "REC", 2, "", null, { status: "À lancer", basis: "Constat" });
    case "rec-edit": return crud("rec", state.recommendations, REC_FIELDS, "Recommandation", "REC", 2, "", find(state.recommendations));
    case "anom-new": return crud("anom", state.anomalies, ANOM_FIELDS, "Anomalie", "AN", 3, "-", null, { detected_on: today(), severity: "Significative", status: "Ouverte", escalation: 1 });
    case "anom-edit": return crud("anom", state.anomalies, ANOM_FIELDS, "Anomalie", "AN", 3, "-", find(state.anomalies));
    case "dos-new": ui.dossier = null; ui.draft = EMPTY_D(); if (route() !== "dossiers") location.hash = "dossiers"; return render();
    case "dos-open": {
      const d = find(state.dossiers);
      if (!d) return;
      ui.dossier = d.id;
      ui.draft = JSON.parse(JSON.stringify({ company: d.company, request: d.request, financials: d.financials, documents: d.documents, guarantees: d.guarantees, observations: d.observations }));
      return render();
    }
    case "dos-close": ui.draft = null; ui.dossier = null; return render();
    case "doc":
      ui.draft.documents[el.dataset.k!] = el.dataset.v;
      el.parentElement!.querySelectorAll("button").forEach((b) => (b.className = ""));
      el.className = "on " + el.dataset.v;
      document.getElementById("analysis")!.innerHTML = analysisPanel();
      return;
    case "dos-save": {
      if (!String(ui.draft.company.name).trim()) return toast("Indiquez la raison sociale.", true);
      const a = analyzeDossier(ui.draft);
      if (ui.dossier) {
        Object.assign(state.dossiers.find((x) => x.id === ui.dossier)!, JSON.parse(JSON.stringify(ui.draft)), { analysis: a, status: a.status, updated_at: today() });
        record("Modification", "Dossier TPE", ui.dossier, a.status);
      } else {
        const y = new Date().getFullYear();
        ui.dossier = nextId(state.dossiers.filter((x) => x.id.startsWith(`TPE-${y}`)), `TPE-${y}`, 3, "-");
        state.dossiers.unshift({ id: ui.dossier, ...JSON.parse(JSON.stringify(ui.draft)), analysis: a, status: a.status, created_by: session.me!.name, created_at: today() });
        record("Création", "Dossier TPE", ui.dossier, a.status);
      }
      toast(`Dossier ${ui.dossier} enregistré.`);
      return render();
    }
    case "dos-del":
      return confirmBox(`Supprimer le dossier ${ui.dossier} ?`, () => {
        state.dossiers = state.dossiers.filter((x) => x.id !== ui.dossier);
        record("Suppression", "Dossier TPE", ui.dossier);
        ui.dossier = null;
        ui.draft = null;
        render();
      });
    case "dos-anom": {
      const a = analyzeDossier(ui.draft);
      const nid = nextId(state.anomalies, "AN", 3, "-");
      state.anomalies.push({ id: nid, detected_on: today(), dossier_ref: ui.dossier, nature: a.completeness.missingDocs.length ? `Dossier incomplet : ${a.completeness.missingDocs.join(" ; ")}` : `Incohérence : ${a.inconsistencies[0]?.message ?? "relevée à l'analyse"}`, severity: a.inconsistencies.some((i) => i.severity === "alerte") ? "Majeure" : "Significative", risk_id: "R01", control_id: "C01", owner: "Fonction risques", due_on: "", status: "Ouverte", escalation: 1, resolution: "", declared_by: session.me!.name, created_at: today() });
      record("Création", "Anomalie", nid, `Dossier ${ui.dossier}`);
      return toast(`Anomalie ${nid} inscrite au registre.`);
    }
    case "ask": return void ask(el.dataset.q!);
    case "chat-reset": ui.chat = []; return render();
    case "member-del": {
      delete session.members[id];
      saveRoles({ ...session.members }).then(() => toast("Membre retiré.")).catch(() => toast("Modification des rôles impossible.", true));
      record("Retrait", "Membre", "");
      return render();
    }
    case "member-add": {
      session.members[id] = "lecteur";
      ui.names[id] = el.dataset.name;
      saveRoles({ ...session.members }).then(() => toast(`${el.dataset.name} ajouté en lecture seule : choisissez son rôle.`)).catch(() => toast("Modification des rôles impossible.", true));
      record("Ajout", "Membre", "");
      return render();
    }
    case "reset":
      return confirmBox("Restaurer les données de démonstration ? Toutes les saisies seront remplacées, pour toute l'équipe.", () => {
        resetBaseline();
        record("Réinitialisation", "Données", "*");
        toast("Données de démonstration restaurées.");
        render();
      }, "Restaurer");
    case "exp-risks": return download("registre-risques.csv", csv(snapshot().risks, [["id", "Identifiant"], ["title", "Risque"], ["category", "Catégorie"], ["event", "Événement"], ["causes", "Causes"], ["consequences", "Conséquences"], ["probability", "Probabilité"], ["gravity", "Gravité"], ["score", "Score"], ["level", "Criticité"], ["owner", "Responsable"], ["control_ids", "Contrôles"], ["coso_principles", "COSO"], ["recommendation", "Recommandation"]]));
    case "exp-controls": return download("controles.csv", csv(state.controls, [["id", "Id"], ["name", "Contrôle"], ["nature", "Type"], ["objective", "Objectif"], ["risk_ids", "Risques"], ["procedure", "Procédure"], ["owner", "Responsable"], ["frequency", "Fréquence"], ["evidence", "Preuve"], ["indicator", "Indicateur"], ["status", "Statut"], ["last_review", "Dernière revue"]]));
    case "exp-coso": return download("coso.csv", csv(state.principles, [["id", "Principe"], ["title", "Intitulé"], ["component_id", "Composante"], ["nature", "Nature"], ["assessment", "Appréciation"], ["diagnostic", "Diagnostic"], ["risk_ids", "Risques"]]));
    case "exp-actions": return download("plan-action.csv", csv(state.actions, [["id", "Id"], ["priority", "Priorité"], ["title", "Action"], ["owner", "Responsable"], ["due", "Échéance"], ["deliverable", "Livrable"], ["risk_ids", "Risques"], ["status", "Statut"], ["progress", "Avancement"]]));
    case "exp-recos": return download("recommandations.csv", csv(state.recommendations, [["id", "Id"], ["risk_id", "Risque"], ["coso_gap", "Lacune COSO"], ["action", "Action"], ["owner", "Responsable"], ["indicator", "Indicateur"], ["status", "Statut"]]));
    case "exp-anoms": return download("anomalies.csv", csv(state.anomalies, [["id", "Id"], ["detected_on", "Détectée le"], ["dossier_ref", "Dossier"], ["nature", "Nature"], ["severity", "Gravité"], ["risk_id", "Risque"], ["control_id", "Contrôle"], ["owner", "Responsable"], ["due_on", "Échéance"], ["status", "Statut"], ["escalation", "Escalade"]]));
    case "exp-marts": return download("portefeuille-reference-secteurs.csv", csv(T.by_sector, [["sector", "Secteur"], ["loans", "Prêts"], ["approved_usd", "Montant approuvé (USD)"], ["resolved", "Prêts dénoués"], ["defaults", "Défauts"], ["default_rate", "Taux de défaut"], ["chargeoff_usd", "Pertes (USD)"], ["loss_rate", "Taux de perte"]]));
    case "exp-json": return download("credit-horizon-sauvegarde.json", JSON.stringify(state, null, 1), "application/json");
  }
});

document.addEventListener("keydown", (e) => {
  const t = e.target as HTMLElement;
  if (e.key === "Escape") {
    if (document.getElementById("modal")!.className) close();
    document.querySelectorAll("details.mnu[open]").forEach((d) => d.removeAttribute("open"));
  }
  if (e.altKey && /^[1-9]$/.test(e.key) && NAV[+e.key - 1]) {
    e.preventDefault();
    location.hash = NAV[+e.key - 1][0];
  }
  if (e.key === "Enter" && !e.shiftKey && t.id === "askq") {
    e.preventDefault();
    ask((t as HTMLTextAreaElement).value);
  }
  if ((e.key === "Enter" || e.key === " ") && t.matches("tr.row")) {
    e.preventDefault();
    t.click();
  }
});

document.addEventListener("submit", (e) => {
  const f = e.target as HTMLFormElement;
  e.preventDefault();
  if (f.id === "mform" && onSubmit) {
    const v: Row = Object.fromEntries(new FormData(f).entries());
    const err = onSubmit(v);
    if (err) return void (document.getElementById("merr")!.textContent = err);
    close();
    render();
  } else if (f.id === "askf") {
    ask((document.getElementById("askq") as HTMLTextAreaElement).value);
  }
});

let peopleT: any;
document.addEventListener("input", (e) => {
  const t = e.target as HTMLInputElement;
  if (t.id === "q") {
    ui.filter = t.value;
    return applyFilter();
  }
  if (t.id === "people") {
    clearTimeout(peopleT);
    peopleT = setTimeout(async () => {
      const res = (await searchPeople(t.value)).filter((p) => p.id !== session.me?.id && !session.members[p.id]);
      document.getElementById("people-res")!.innerHTML = res.length ? `<ul class="people">${res.slice(0, 8).map((p) => `<li><span>${esc(p.name)}</span>${btn("Ajouter", "member-add", `data-id="${esc(p.id)}" data-name="${esc(p.name)}"`, "ghost sm")}</li>`).join("")}</ul>` : `<p class="small">Aucune personne trouvée. Partagez d'abord la plateforme depuis le menu Partager de claude.ai.</p>`;
    }, 250);
    return;
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
  if (t.id === "cat") {
    ui.cat = t.value;
    return render();
  }
  if (t.dataset.d && ui.draft) {
    const [part, key] = t.dataset.d.split(".");
    ui.draft[part][key] = t.value;
    return key === "type" || key === "product" ? render() : void (document.getElementById("analysis")!.innerHTML = analysisPanel());
  }
  if (t.dataset.ch === "assess") {
    const p = state.principles.find((x) => x.id === t.dataset.id)!;
    p.assessment = t.value;
    record("Appréciation", "Principe COSO", p.id, t.value);
    toast(`${p.id} : ${t.value}.`);
    return render();
  }
  if (t.dataset.ch === "role") {
    session.members[t.dataset.id!] = t.value;
    saveRoles({ ...session.members }).then(() => toast(`Rôle attribué : ${ROLES[t.value]}.`)).catch(() => toast("Modification des rôles impossible.", true));
    record("Rôle", "Membre", "", ROLES[t.value]);
    return;
  }
  if (t.id === "imp") {
    const file = (t as unknown as HTMLInputElement).files?.[0];
    file?.text().then((txt) => {
      if (replaceState(txt)) {
        record("Import", "Sauvegarde", file.name);
        toast("Sauvegarde importée.");
        render();
      } else toast("Ce fichier n'est pas une sauvegarde de la plateforme.", true);
    });
  }
});

document.addEventListener("toggle", (e) => {
  const d = e.target as HTMLDetailsElement;
  if (d.classList?.contains("mnu") && d.open) document.querySelectorAll("details.mnu[open]").forEach((x) => x !== d && x.removeAttribute("open"));
}, true);

window.addEventListener("hashchange", () => {
  document.body.classList.remove("nav-open");
  if (route() !== "dossiers") {
    ui.draft = null;
    ui.dossier = null;
  }
  render();
  window.scrollTo(0, 0);
});

/* ================================================================ démarrage */
(async function boot() {
  render();
  session.me = await identity();
  resolveRole();
  setPersist((json) => queueSave(json, (msg) => {
    session.storeError = msg;
    render();
  }));
  if (session.me.mode === "claude") {
    await connectStore(
      (json) => {
        if (replaceState(json) && session.ready && !document.getElementById("modal")!.className && !ui.draft) render();
      },
      (members) => {
        session.members = members;
        resolveRole();
        if (session.ready) render();
      },
    );
    capability("sample").then((s) => (ui.ai = !!s));
  }
  session.ready = true;
  render();
})();
