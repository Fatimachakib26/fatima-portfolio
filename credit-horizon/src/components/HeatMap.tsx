"use client";
import { useState } from "react";
import { LEVEL_STYLE, levelFromScore, PROBABILITY_SCALE, GRAVITY_SCALE } from "@/lib/scoring";

const CELL_BG: Record<string, string> = {
  Faible: "bg-emerald-100 hover:bg-emerald-200",
  Modéré: "bg-yellow-100 hover:bg-yellow-200",
  Élevé: "bg-orange-200 hover:bg-orange-300",
  Critique: "bg-red-300 hover:bg-red-400",
};

/** Matrice thermique 5 × 5 : probabilité (lignes, 5 en haut) × gravité (colonnes). */
export default function HeatMap({ risks, compact = false, onSelect, selected }: { risks: any[]; compact?: boolean; onSelect?: (r: any) => void; selected?: string | null }) {
  const [hover, setHover] = useState<string | null>(null);
  return (
    <div className="w-full">
      <div className="flex">
        <div className="flex w-6 items-center justify-center">
          <span className="-rotate-90 whitespace-nowrap text-[11px] font-bold uppercase tracking-wider text-slate-500">Probabilité</span>
        </div>
        <div className="flex-1">
          <div className="grid gap-1" style={{ gridTemplateColumns: `${compact ? "20px" : "110px"} repeat(5, minmax(0, 1fr))` }}>
            {[5, 4, 3, 2, 1].map((p) => (
              <Row key={p} p={p} compact={compact} risks={risks} hover={hover} setHover={setHover} onSelect={onSelect} selected={selected} />
            ))}
            <div />
            {[1, 2, 3, 4, 5].map((g) => (
              <div key={g} className="pt-1 text-center text-[11px] font-semibold text-slate-600">
                {g}
                {!compact && <div className="text-[10px] font-normal text-slate-400">{GRAVITY_SCALE[g - 1].label}</div>}
              </div>
            ))}
          </div>
          <div className="mt-1 text-center text-[11px] font-bold uppercase tracking-wider text-slate-500">Gravité</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap justify-center gap-3 text-[11px] text-slate-600">
        {(["Faible", "Modéré", "Élevé", "Critique"] as const).map((l) => (
          <span key={l} className="inline-flex items-center gap-1.5">
            <span className={`h-3 w-3 rounded ${LEVEL_STYLE[l].bg}`} /> {l}
          </span>
        ))}
      </div>
    </div>
  );
}

function Row({ p, compact, risks, hover, setHover, onSelect, selected }: any) {
  return (
    <>
      <div className="flex flex-col items-end justify-center pr-1 text-right text-[11px] font-semibold text-slate-600">
        {p}
        {!compact && <span className="text-[10px] font-normal text-slate-400">{PROBABILITY_SCALE[p - 1].label}</span>}
      </div>
      {[1, 2, 3, 4, 5].map((g) => {
        const score = p * g;
        const level = levelFromScore(score);
        const here = risks.filter((r: any) => Number(r.probability) === p && Number(r.gravity) === g);
        return (
          <div
            key={g}
            className={`relative flex ${compact ? "min-h-[44px]" : "min-h-[84px]"} flex-wrap content-start gap-1 rounded-lg p-1.5 transition ${CELL_BG[level]}`}
            title={`P=${p} × G=${g} = ${score} (${level})${here.length ? " — " + here.map((r: any) => r.id).join(", ") : ""}`}
          >
            <span className="absolute bottom-1 right-1.5 text-[10px] font-semibold text-slate-700/50">{score}</span>
            {here.map((r: any) => (
              <button
                key={r.id}
                type="button"
                onClick={() => onSelect?.(r)}
                onMouseEnter={() => setHover(r.id)}
                onMouseLeave={() => setHover(null)}
                className={`relative rounded-md bg-white px-1.5 py-0.5 text-[11px] font-bold shadow-sm ring-1 ring-slate-300 transition hover:scale-110 ${
                  selected === r.id ? "ring-2 ring-brand-700" : ""
                } ${onSelect ? "cursor-pointer" : "cursor-default"}`}
              >
                {r.id}
                {hover === r.id && !compact && (
                  <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1.5 w-56 -translate-x-1/2 rounded-lg bg-brand-950 px-2.5 py-2 text-left text-[11px] font-normal text-white shadow-xl">
                    <b>{r.id}</b> – {r.title}
                    <br />
                    P {r.probability} × G {r.gravity} = <b>{score}</b> ({level})
                  </span>
                )}
              </button>
            ))}
          </div>
        );
      })}
    </>
  );
}
