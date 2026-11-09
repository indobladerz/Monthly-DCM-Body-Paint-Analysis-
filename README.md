# DCM Body & Paint — tinjauan keuangan tiga bulan (Bahasa Indonesia)

Financial-controller review of PT Duta Cendana Mobilindo's body and paint unit
(PT DCM Body Paint, the Toyota body shop opened September 2025) for
July–September 2026, built from the monthly ACCURATE statements in Drive
(`Laporan Keuangan PT DCM Body Paint / Laporan Keuangan DCM BP 2026 /
7. … JULI 2026`, `8. … AGUSTUS 2026`, `9. … SEPTEMBER 2026`). Every month since
opening (September 2025) is parsed as well, for trend, year-to-date and
cumulative-loss figures.

The report has seven sections (executive summary, revenue analysis,
account-by-account sub-ledger, depreciation, balance sheet and integrity tests,
ranked findings, recommendations with scenarios) in Indonesian number
formatting. The depreciation section treats land & building and equipment
separately, as the owner asked; the unit's books carry no land, which the
report says explicitly.

This repository holds only the PT DCM Body Paint analysis. It was moved here
from the Sales-Report-PT.-DCM repository (draft PR #5), which is for the weekly
sales report and should not carry it.

## Source folder and delivery

- Statements come from Google Drive, shared with vwilliam@dutacendana.com:
  `Laporan Keuangan PT DCM Body Paint / Laporan Keuangan DCM BP 2026`
  (folder id `1aIiBImkPam11fKjHbwxIGh7TtNJe4vzU`, owner accspv@dutacendana.com).
- The latest statement already analysed is **September 2026**
  (`9. LAPORAN NERACA & RUGILABA PT. DCM BODYPAINT SEPTEMBER 2026.pdf`, uploaded
  30 Oct 2026). October 2026 is expected in the 2nd–3rd week of November 2026.
  File titles are not consistent from month to month (`RUGILABA` / `RUGI LABA`,
  `PT.` / `PT`), so match on the month name, the year and `BODYPAINT`.
- Planned recipients of the emailed report: vwilliam@toyotadutacendana.com,
  adh@toyotadutacendana.com, accspv.dca@gmail.com, bm@toyotadutacendana.com,
  sm.bp@toyotadutacendana.com, sm.jts.dca@gmail.com.
- The pipeline now builds the report for the newest month in `data/` (see
  "How it works"). `config/baseline.txt` holds the last period already analysed
  and emailed (`2026-09`); a run must never email a period <= that.

| File | What it is |
|---|---|
| `out/report.html` | The report, in Bahasa Indonesia (self-contained, inline SVG charts, print styles) |
| `out/report.pdf` | A4 print of the same report |
| `out/metrics.json` | Every headline figure, scenario, break-even and intercompany gap, as computed |
| `parse_dcm.py` | Parses the statements' text layer into one JSON per month and reconciles each one |
| `data/raw/*.txt` | Text layer of the statements (Sep 2025 – Sep 2026), as extracted from the PDFs; one file per month, discovered by name `<yyyy-mm>.txt` (`2025-09-10.txt` holds two columns) |
| `data/raw/group_inhouse.json` | Main-dealership figures (sales, receivable from the unit, head-office clearing, deposits) from the Inhouse statements, Jul–Sep 2026; keys `YYYY-MM` (legacy `jul`/`aug`/`sep` = 2026), optional per month |
| `data/<yyyy-mm>.json` | The parsed figures, one file per month |
| `data/recon_exceptions.json` | The three places where the books do not roll forward (Nov 2025 depreciation; Jul/Aug 2026 equity) |
| `build_report.py` | Computes the analysis for the newest month (or `--month YYYY-MM`) and writes `out/report.html` and `out/metrics.json` |
| `normalize_drive_text.py` | Turns the Drive connector's text for a statement PDF into `data/raw/<yyyy-mm>.txt` |
| `check_period.py` | Offline guard: does `data/<period>.json` exist, and is the period newer than `config/baseline.txt` |
| `config/targets.json` | Scenario target, policy assumptions and analysis thresholds (not report data) |
| `config/baseline.txt` | Last period already analysed (`2026-09`) |
| `render_email.py` | Lays out `out/email_data.json` (written by `build_report.py`) as a compact Gmail-safe e-mail, `out/email.html`: tables and inline styles only, no charts, under 95 KB, last line is a sentinel `<!-- dcm-bp v1 YYYY-MM hash -->`; also writes `out/email_subject.txt` |
| `routines/dcm-body-paint-monthly.prompt.txt` | The step-by-step procedure the weekly scheduled run follows (Drive check, dedupe against sent mail, parse, build, send) |
| `render_pdf.js` | Prints the HTML to PDF with the pre-installed Playwright Chromium |

## How it works

1. A new monthly PDF appears in Drive. Its text is read with the Drive connector
   (`read_file_content`), saved to a scratch file, and converted with
   `python3 normalize_drive_text.py scratch.txt` into `data/raw/<yyyy-mm>.txt`
   (the month is read from the `Period ...` line).
2. `python3 parse_dcm.py` discovers every `data/raw/<yyyy-mm>.txt`, writes
   `data/<yyyy-mm>.json` and `data/recon_exceptions.json`, and keeps all asserts.
3. `python3 check_period.py YYYY-MM` (exit 0 only if the data exists and the
   period is newer than `config/baseline.txt`).
4. `python3 build_report.py [--month YYYY-MM]` uses the newest month (or the
   given one) and the three months ending there. Month names, labels, the
   quarter label, scenarios and all narrative figures are computed from
   `data/*.json`. Findings are computed (largest account movers, discount and
   incentive rate, gross margin, depreciation, equity and depreciation
   roll-forward, receivables, HO clearing and cash, fixed-asset changes,
   integrity tests), ranked by the rupiah size of the figure discussed, with
   severity from that size relative to the month's net revenue; a finding that
   cannot be computed for the month is omitted. Assumptions (Rp 400 juta target,
   +25% volume, 8-year equipment life, 5% cash yield, policy caps) are read from
   `config/targets.json`; the target scenarios are skipped if the month already
   exceeds the target.
5. `python3 render_email.py` turns the computed figures and findings into
   `out/email.html`. The report itself (`out/report.html`, 122 KB with inline
   charts) is too large and too chart-heavy for Gmail, so the e-mail carries the
   headline figures, the three-month table, the ranked findings, the
   recommendations, the scenarios and the integrity result, without charts.
   The e-mail is sent as the HTML body; no attachment, no PDF.
6. Main-dealership figures (`data/raw/group_inhouse.json`) are optional. If the
   chosen month has no entry, the intercompany findings and dealer references are
   omitted and the report says so in one line; nothing is carried over.

## Rebuild

```bash
python3 parse_dcm.py                       # data/raw/*.txt -> data/*.json, asserts every subtotal to the rupiah
python3 build_report.py --month 2026-09    # -> out/report.html, out/metrics.json (omit --month for the newest)
node render_pdf.js                         # -> out/report.pdf (print of the HTML; not regenerated by the pipeline above)
```

`parse_dcm.py` asserts, for every month, that leaf accounts re-add to sales,
discounts, cost of sales, selling, G&A, opex and net result, and that the balance
sheet balances; it records (does not hide) depreciation and equity roll-forward
gaps in `data/recon_exceptions.json`. `build_report.py` asserts that the ledger
table re-adds to opex for each of the three months, the window and the year to
date; the year-to-date profit against the balance sheet is an integrity-table row.

## Regression test

After any change to the scripts: `python3 -I parse_dcm.py && python3 -I
build_report.py --month 2026-09`, then `git diff --stat -- out/metrics.json
data/2025-*.json data/2026-*.json data/recon_exceptions.json` must be empty.
`out/report.html` may differ only where the hand-written text was replaced by
computed text (and the report date). Run on 2026-11-09 this held: data and
`metrics.json` identical (its month keys are the English abbreviations of the
three months, `sep/aug/jul` for September). A synthetic 2026-10 statement (never committed; amounts perturbed
with all subtotals recomputed) built without error, with Oktober 2026 and
Agustus – Oktober 2026 in the title and labels.
`normalize_drive_text.py` was checked against the Drive text of the August and
September 2026 PDFs: output byte-identical to the committed raw text, and identical
`data/2026-08.json` / `data/2026-09.json`.

## Known limits

- `out/report.pdf` is not regenerated by the Python steps; it still shows the Sep 2026 report until `render_pdf.js` is run.
- The `Drive text -> raw` normalizer was verified on two months only; a changed connector text format would need the normalizer revisited. It refuses to write if the period is not one month or a statement is missing.
- `parse_dcm.py` classifies accounts by their ACCURATE names; a new account type (for example a new fixed-asset class) fails an assert rather than being guessed.
- The report needs three consecutive months ending at the chosen month, positive gross margin and depreciation; otherwise it stops with a message.
- The dealer reference, DCA comparison and recommendation wording are judgement text: the DCA comparison table (typed numbers) was removed; policy figures come from `config/targets.json`.
- Dealer figures for Oct 2026 and later must be typed into `data/raw/group_inhouse.json` by hand; without them that part of the report is simply omitted.
- Findings are ranked by rupiah size of the figure discussed (balances such as cash can outrank the monthly result); the ranking is mechanical, not a materiality judgement.
