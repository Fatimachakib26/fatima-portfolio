# From raw data to a dashboard you can defend

This folder turns an official, public, loan-level dataset into small, verified tables that feed the
Crédit Horizon dashboard (and Power BI). Every step is reproducible and every number can be traced
back to the raw file.

```
data/raw/        the official files, never modified   + MANIFEST.json (URL, size, SHA-256, rows)
data/clean/      one row per valid loan, typed, no personal data   + rejected_rows.csv.gz
data/marts/      small aggregated tables for the dashboard and Power BI (CSV + sba_marts.json)
reports/         data_quality_report.md, cleaning_summary.json
pipeline/        ingest.py → clean.py → marts.py        run.py runs everything
tests/           6 automated checks
```

Run it:

```bash
cd data-pipeline
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                                       # downloads (255 MB) then processes, ~40 s
python -m unittest discover -s tests -t .           # 6 checks
```

---

## Step 0 — Choose a source you can defend

A source is usable for a dashboard when you can answer **yes** to five questions:

| Question | SBA 7(a) FOIA (the source used here) |
|---|---|
| Who publishes it, and are they accountable for it? | U.S. Small Business Administration, Office of the Chief Data Officer |
| Is there an official page and a stable identifier? | https://data.sba.gov/dataset/7a-504-foia · identifier `SBA-OHA-2016-08-001` |
| Can you legally reuse it? | U.S. Government Works (public domain) |
| Is it documented? | Official data dictionary (`7a_504_foia_data_dictionary.xlsx`) |
| Is it raw, at the level of the event you study? | One row per guaranteed loan, with the final outcome (paid in full / charged off) |

Why this one for a TPE lender: it is the largest public file of **small-business loans with their
real outcome**. Moroccan sources (Bank Al-Maghrib, HCP) publish aggregates, not loan-level
records, so they cannot teach you cleaning. SBA data is used here as an **external benchmark**,
never as Crédit Horizon's own portfolio.

We use `FOIA_7a_FY2010_FY2019`: loans approved 2010–2019 have mostly reached maturity, so their
outcome is known. Recent cohorts (2020+) are still running and would understate defaults.

## Step 1 — Acquire, and prove what you acquired (`pipeline/ingest.py`)

1. Download from the official URL (not from a mirror, not from Kaggle).
2. Check the received size equals the `Content-Length` announced by the server.
3. Compute the **SHA-256** fingerprint and write `MANIFEST.json`: URL, date, bytes, hash, rows, columns.
4. Never edit the raw file. Everything downstream is recomputed from it.

The fingerprint is your proof: anyone can download the same file and run `sha256sum` (Linux/macOS) or
`Get-FileHash` (Windows). Same hash = same bytes. The SBA republishes every quarter, so a newer file has
a new hash and a new manifest; that is expected.

## Step 2 — Profile before you touch anything

Read **every column as text** (`dtype=str`, no automatic type guessing) so nothing gets silently converted.
For each column: empty values, distinct values, examples, and compare with the data dictionary.
What profiling found in this file:

| Finding | Why it matters |
|---|---|
| 1,136 exact duplicate rows | would double-count loans |
| `LoanStatus` written `P I F`, dictionary says `PIF` | a filter on `PIF` would find nothing |
| `RevolverStatus` = Y/N, dictionary says 0/1 | dictionaries drift from files: trust the file, document the gap |
| `Program` = `" 7A"` with a leading space | joins and filters fail silently |
| 2 line breaks inside quoted fields | a naive line-by-line reader would split two rows |
| Amounts stored as text (`51000.0`) | must be typed before any sum |
| Borrower name, street, ZIP | personal data, useless for risk analysis |

The full profile is in `reports/data_quality_report.md`.

## Step 3 — Validate and clean with numbered rules (`pipeline/clean.py`)

Each rule is applied in order, counted, and logged. A rejected row is **never deleted silently**:
it goes to `rejected_rows.csv.gz` with the rule that rejected it.

| Rule | What it does | Rows affected |
|---|---|---:|
| R01 | trim spaces in all text fields | 677,670 cells |
| R02 | drop exact duplicates (keep first) | 1,136 rejected |
| R03 | normalise codes (`P I F` → `PIF`, Y/N → booleans) | — |
| R04 | type amounts, rate, term; amount must be > 0 | 0 rejected |
| R05 | type dates (ISO); approval date required | 0 rejected |
| R06 | SBA guarantee ≤ loan amount | 0 rejected |
| R07 | status consistent with dates (a charged-off loan has a charge-off date, after approval) | 10 rejected |
| R08 | remove personal data (name, street, ZIP) | 3 columns dropped |
| R09 | derived fields: NAICS sector, size and term bands, analysis population, default flag, months to default, loss rate | — |

**A lesson from R07.** The first version compared exact dates and rejected 12 rows. Two of them were
loans "paid in full" a few days *before* approval. Looking at the raw values showed that pay-off dates
are published **at month granularity** (first or last day of the month). Those were loans repaid in
their first month, not errors. The rule now compares months, and only the 10 truly inconsistent rows
are rejected. Always read your rejects before trusting a rule.

## Step 4 — Define your measures once

| Measure | Definition |
|---|---|
| Resolved loans | paid in full (`PIF`) + charged off (`CHGOFF`) |
| Default rate | charged-off loans ÷ resolved loans |
| Loss rate | amount charged off ÷ amount approved on resolved loans |
| Excluded | never disbursed (`CANCLD`, `COMMIT`): no risk was taken · `EXEMPT`: outcome not published |

Putting `EXEMPT` loans in the denominator would artificially lower the default rate. Write the
definition next to every number you publish.

## Step 5 — Build small tables for the dashboard (`pipeline/marts.py`)

The dashboard never reads the 545,000-row file. It reads aggregates: by cohort, sector, loan size,
term, business age, collateral, rate type, and the distribution of time to default.
`sba_marts.json` (38 KB) is embedded in the platform; the CSV files are ready for Power BI.
A rate computed on fewer than 100 resolved loans is shown as "n.s." (not significant).

## Step 6 — Prove the numbers before you publish them

| Check | Result |
|---|---|
| Reconciliation: raw = clean + rejected | 545,751 = 544,605 + 1,146 |
| Independent recount from the raw file (dedup, count `CHGOFF` ÷ `PIF`+`CHGOFF`) | 7.999 % vs 7.997 % in the pipeline: the gap is exactly the 10 R07 rejects |
| Every table adds up to the totals | sums of resolved loans and defaults equal the overview, for every breakdown |
| Rates between 0 and 1, no personal data in the clean layer, SHA-256 matches the manifest | automated in `tests/` |

## Step 7 — Push to the dashboard

1. `python run.py` regenerates `data/marts/sba_marts.json`.
2. `cd ../credit-horizon-site && node build.mjs` rebuilds the platform with the new tables.
3. Publish. The "Source et méthode" tab of the platform shows the publisher, URL, as-of date,
   SHA-256, reconciliation and rejects, so anyone can verify the figures.

For Power BI: Get Data → Text/CSV → `data/marts/*.csv` (separator `,`, UTF-8).

## Refreshing every quarter

Update the file name in `pipeline/config.py` (the SBA changes the `asof_YYMMDD` suffix), run
`python run.py --force`, run the tests, read `reports/data_quality_report.md` for new rejects, then rebuild.
