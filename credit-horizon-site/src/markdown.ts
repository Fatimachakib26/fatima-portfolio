// Rendu Markdown minimal et sûr (tout le texte est échappé avant mise en forme).
const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
const inline = (s: string) =>
  esc(s).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/(^|[\s(])_([^_]+)_/g, "$1<em>$2</em>");
const cells = (l: string) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

export function md(text: string): string {
  const L = text.replace(/\r/g, "").split("\n");
  const out: string[] = [];
  let i = 0;
  while (i < L.length) {
    const l = L[i];
    if (!l.trim()) { i++; continue; }
    const h = l.match(/^(#{1,4})\s+(.*)$/);
    if (h) { out.push(`<h${Math.min(4, h[1].length + 1)}>${inline(h[2])}</h${Math.min(4, h[1].length + 1)}>`); i++; continue; }
    if (l.trim().startsWith("|") && i + 1 < L.length && /^\s*\|?\s*:?-{2,}/.test(L[i + 1])) {
      const head = cells(l); i += 2;
      const rows: string[][] = [];
      while (i < L.length && L[i].trim().startsWith("|")) rows.push(cells(L[i++]));
      out.push(`<div class="tw"><table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }
    if (/^\s*>/.test(l)) {
      const b: string[] = [];
      while (i < L.length && /^\s*>/.test(L[i])) b.push(L[i++].replace(/^\s*>\s?/, ""));
      out.push(`<blockquote>${inline(b.join(" "))}</blockquote>`); continue;
    }
    if (/^\s*[-*•]\s+/.test(l)) {
      const b: string[] = [];
      while (i < L.length && /^\s*[-*•]\s+/.test(L[i])) b.push(`<li${/^\s{2,}/.test(L[i]) ? ' class="sub"' : ""}>${inline(L[i++].replace(/^\s*[-*•]\s+/, ""))}</li>`);
      out.push(`<ul>${b.join("")}</ul>`); continue;
    }
    if (/^\s*\d+[.)]\s+/.test(l)) {
      const b: string[] = [];
      while (i < L.length && /^\s*\d+[.)]\s+/.test(L[i])) b.push(`<li>${inline(L[i++].replace(/^\s*\d+[.)]\s+/, ""))}</li>`);
      out.push(`<ol>${b.join("")}</ol>`); continue;
    }
    const b: string[] = [];
    while (i < L.length && L[i].trim() && !/^(#{1,4}\s|\s*\||\s*>|\s*[-*•]\s|\s*\d+[.)]\s)/.test(L[i])) b.push(inline(L[i++]));
    if (!b.length) b.push(inline(L[i++]));
    out.push(`<p>${b.join("<br>")}</p>`);
  }
  return out.join("");
}
