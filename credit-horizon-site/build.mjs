// Assemble le site en UN SEUL fichier HTML autonome (aucune dépendance externe, fonctionne hors ligne).
import { build } from "esbuild";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
mkdirSync("dist", { recursive: true });

const r = await build({ entryPoints: ["src/main.ts"], bundle: true, minify: true, write: false, format: "iife", target: "es2019", charset: "utf8", legalComments: "none" });
const js = r.outputFiles[0].text.replace(/<\/script/gi, "<\\/script");
const css = readFileSync("src/styles.css", "utf8");
const html = `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CRÉDIT HORIZON · Risk Intelligence</title>
<meta name="description" content="Plateforme de gestion intelligente des risques financiers pour le financement des TPE – Projet EMSI.">
<link rel="icon" href="data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0a4d38"/><path d="M12 42 Q32 14 52 42" fill="none" stroke="#10b981" stroke-width="5"/><circle cx="32" cy="24" r="5" fill="#34d399"/></svg>')}">
<style>${css}</style></head>
<body><div id="app"></div><div id="modal"></div><div id="toast" class="toast" role="status" aria-live="polite"></div>
<noscript>Activez JavaScript pour utiliser CRÉDIT HORIZON RISK INTELLIGENCE.</noscript>
<script>${js}</script></body></html>`;
writeFileSync("../credit_horizon_site.html", html);
// Version artefact claude.ai : le squelette html/head/body est ajouté à la publication.
const artifact = `<title>Crédit Horizon Risk Intelligence</title>\n<style>${css}</style>\n<div id="app"></div><div id="modal"></div><div id="toast" class="toast" role="status" aria-live="polite"></div>\n<script>${js}</script>\n`;
writeFileSync("dist/credit-horizon-artifact.html", artifact);
console.log("Site généré :", (html.length / 1024).toFixed(0), "Ko");
