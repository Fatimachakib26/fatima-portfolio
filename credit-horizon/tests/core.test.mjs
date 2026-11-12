import { test } from "node:test";
import assert from "node:assert/strict";
import { computeScore, levelFromScore, appetiteFromLevel } from "../src/lib/scoring.ts";
import { analyzeDossier, monthlyInstallment } from "../src/lib/dossier-analysis.ts";
import { SEED_DOSSIERS } from "../src/lib/seed-dossiers.ts";
import { SEED_RISKS } from "../src/lib/seed-data.ts";

test("seuils de criticité du rapport (tableau 3.3)", () => {
  assert.equal(levelFromScore(4), "Faible");
  assert.equal(levelFromScore(5), "Modéré");
  assert.equal(levelFromScore(9), "Modéré");
  assert.equal(levelFromScore(10), "Élevé");
  assert.equal(levelFromScore(15), "Élevé");
  assert.equal(levelFromScore(16), "Critique");
  assert.equal(computeScore(9, 0), 5); // bornage 1..5
});

test("cotations R01–R08 conformes au rapport", () => {
  const expected = { R01: [15, "Élevé"], R02: [12, "Élevé"], R03: [20, "Critique"], R04: [9, "Modéré"], R05: [12, "Élevé"], R06: [10, "Élevé"], R07: [16, "Critique"], R08: [12, "Élevé"] };
  for (const r of SEED_RISKS) {
    const s = computeScore(r.probability, r.gravity);
    assert.deepEqual([s, levelFromScore(s)], expected[r.id], r.id);
  }
  assert.equal(appetiteFromLevel("Critique"), "inacceptable");
});

test("dossier complet de démo : transmissible, sans décision d'octroi", () => {
  const a = analyzeDossier(SEED_DOSSIERS[0], new Date("2026-11-12"));
  assert.equal(a.completeness.rate, 100);
  assert.equal(a.blocking, false);
  assert.match(a.status, /transmissible pour avis/);
  assert.match(a.disclaimer, /ne constitue en aucun cas une décision d'octroi/);
  assert.doesNotMatch(a.synthesis, /accord(é|er)|refus/i);
});

test("dossier incomplet de démo : blocage, incohérences détectées", () => {
  const a = analyzeDossier(SEED_DOSSIERS[1], new Date("2026-11-12"));
  assert.equal(a.blocking, true);
  const codes = a.inconsistencies.map((i) => i.code);
  for (const c of ["NAME_MISMATCH", "REVENUE_GAP", "DEBT_INCOH", "PRODUCT_DURATION", "CONCORDANCE"]) assert.ok(codes.includes(c), c);
  assert.ok(a.completeness.missingDocs.length >= 3);
  assert.ok(a.missingInfo.some((m) => /ICE/.test(m.message)));
  assert.ok(a.vigilance.some((v) => v.code === "LOSS"));
  assert.ok(a.linkedRisks.includes("R01"));
});

test("échéance mensuelle", () => {
  assert.equal(Math.round(monthlyInstallment(12000, 12, 0)), 1000);
  assert.ok(monthlyInstallment(100000, 48) > 100000 / 48);
});
