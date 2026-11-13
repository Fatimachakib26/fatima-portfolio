// Assemble la plateforme en un fichier HTML autonome + la version publiée sur claude.ai.
import { build } from "esbuild";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

mkdirSync("dist", { recursive: true });
const r = await build({ entryPoints: ["src/main.ts"], bundle: true, minify: true, write: false, format: "iife", target: "es2020", charset: "utf8", legalComments: "none" });
const js = r.outputFiles[0].text.replace(/<\/script/gi, "<\\/script");
const css = readFileSync("src/styles.css", "utf8");
const fonts = `<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&display=swap">`;
const body = `<div id="app"></div><div id="modal"></div><div id="toast" class="toast" role="status" aria-live="polite"></div>`;

// 1) Fichier autonome (copie locale, ouvrable sans serveur)
writeFileSync("../credit_horizon_site.html", `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crédit Horizon</title><meta name="description" content="Gestion des risques financiers d'un organisme de financement des TPE.">
${fonts}<style>${css}</style></head><body>${body}<script>${js}</script></body></html>`);

// 2) Version claude.ai (le squelette html/head/body est ajouté à la publication)
writeFileSync("dist/credit-horizon-artifact.html", `<title>Crédit Horizon</title>\n${fonts}\n<style>${css}</style>\n${body}\n<script>${js}</script>\n`);
console.log("Construit :", (js.length / 1024).toFixed(0), "Ko de script,", (css.length / 1024).toFixed(0), "Ko de styles");
