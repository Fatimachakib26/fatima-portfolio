"use client";
import { Fragment, type ReactNode } from "react";

// Rendu Markdown minimal et sûr (aucun HTML brut injecté) pour les réponses de l'IA.
function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    const k = `${keyBase}-${i++}`;
    if (t.startsWith("**")) out.push(<strong key={k}>{t.slice(2, -2)}</strong>);
    else if (t.startsWith("`")) out.push(<code key={k}>{t.slice(1, -1)}</code>);
    else out.push(<em key={k}>{t.slice(1, -1)}</em>);
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const cells = (line: string) =>
  line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());

export default function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r/g, "").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;
  while (i < lines.length) {
    const line = lines[i];
    const k = `b${key++}`;
    if (!line.trim()) {
      i++;
      continue;
    }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const lvl = h[1].length;
      const content = inline(h[2], k);
      blocks.push(lvl <= 2 ? <h2 key={k}>{content}</h2> : lvl === 3 ? <h3 key={k}>{content}</h3> : <h4 key={k}>{content}</h4>);
      i++;
      continue;
    }
    if (line.trim().startsWith("|") && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const head = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(cells(lines[i++]));
      blocks.push(
        <div key={k} className="overflow-x-auto">
          <table>
            <thead>
              <tr>{head.map((c, j) => <th key={j}>{inline(c, `${k}h${j}`)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>{r.map((c, j) => <td key={j}>{inline(c, `${k}r${ri}c${j}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (/^\s*>/.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, ""));
      blocks.push(<blockquote key={k}>{inline(buf.join(" "), k)}</blockquote>);
      continue;
    }
    if (/^\s*([-*•])\s+/.test(line)) {
      const items: { text: string; sub: boolean }[] = [];
      while (i < lines.length && /^\s*([-*•])\s+/.test(lines[i])) {
        items.push({ text: lines[i].replace(/^\s*[-*•]\s+/, ""), sub: /^\s{2,}/.test(lines[i]) });
        i++;
      }
      blocks.push(
        <ul key={k}>
          {items.map((it, j) => (
            <li key={j} className={it.sub ? "ml-4 list-[circle]" : ""}>
              {inline(it.text, `${k}${j}`)}
            </li>
          ))}
        </ul>,
      );
      continue;
    }
    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*\d+[.)]\s+/, ""));
      blocks.push(
        <ol key={k}>
          {items.map((it, j) => (
            <li key={j}>{inline(it, `${k}${j}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }
    if (/^-{3,}\s*$/.test(line)) {
      blocks.push(<hr key={k} className="my-3 border-slate-200" />);
      i++;
      continue;
    }
    const buf: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*\||\s*>|\s*[-*•]\s|\s*\d+[.)]\s)/.test(lines[i])) buf.push(lines[i++]);
    if (!buf.length) buf.push(lines[i++]);
    blocks.push(
      <p key={k}>
        {buf.map((b, j) => (
          <Fragment key={j}>
            {j > 0 && <br />}
            {inline(b, `${k}${j}`)}
          </Fragment>
        ))}
      </p>,
    );
  }
  return <>{blocks}</>;
}
