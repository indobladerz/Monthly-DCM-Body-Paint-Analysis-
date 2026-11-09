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
- Not yet automated: `build_report.py` is written for the Jul–Sep 2026 quarter
  (month lists, labels and several narrative figures are fixed in the script),
  and `data/raw/group_inhouse.json` holds main-dealership figures that were
  transcribed by hand from the Inhouse statements. Both need work before an
  unattended run can produce an October report.

| File | What it is |
|---|---|
| `out/report.html` | The report, in Bahasa Indonesia (self-contained, inline SVG charts, print styles) |
| `out/report.pdf` | A4 print of the same report |
| `out/metrics.json` | Every headline figure, scenario, break-even and intercompany gap, as computed |
| `parse_dcm.py` | Parses the statements' text layer into one JSON per month and reconciles each one |
| `data/raw/*.txt` | Text layer of the thirteen statements (Sep 2025 – Sep 2026), as extracted from the PDFs |
| `data/raw/group_inhouse.json` | Main-dealership figures (sales, receivable from the unit, head-office clearing, deposits) from the Inhouse statements, Jul–Sep 2026 |
| `data/<yyyy-mm>.json` | The parsed figures, one file per month |
| `data/recon_exceptions.json` | The three places where the books do not roll forward (Nov 2025 depreciation; Jul/Aug 2026 equity) |
| `build_report.py` | Computes the analysis and writes `out/report.html` |
| `render_pdf.js` | Prints the HTML to PDF with the pre-installed Playwright Chromium |

## Rebuild

```bash
python3 parse_dcm.py      # data/raw/*.txt -> data/*.json, asserts every subtotal to the rupiah
python3 build_report.py   # -> out/report.html, out/metrics.json
node render_pdf.js        # -> out/report.pdf
```

`parse_dcm.py` asserts, for every month, that leaf accounts re-add to sales,
discounts, cost of sales, selling, G&A, opex and net result, that the balance
sheet balances, and that accumulated depreciation moves by the depreciation
charged. `build_report.py` asserts that the ledger table it prints re-adds to
opex for September, the quarter and the year to date, and that the year-to-date
and since-opening losses tie to the balance sheet.
