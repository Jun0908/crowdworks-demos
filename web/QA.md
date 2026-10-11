# Web app verification

## Invoice and sales-list demos: QA inventory

- Introduction links open `/invoices/` and `/leads/`; each demo links to the introduction and other demos.
- Invoices: text sample 3 files, optional scan sample 2 files, own PDF upload; reference date and recipient name; OCR progress; search, review/deadline filters; detail and original PDF dialogs; CSV/XLSX/JSON downloads.
- Leads: 26 sample records; upload/edit JSON and sample reset; eight area checkboxes and review/summary toggle; candidate/exclusion tabs; search and charcoal filter; candidate CSV, exclusion CSV and XLSX downloads; dedupe funnel.
- Error paths: invalid JSON, missing fields, no selected area, broken PDF, file limits; no exports after failed runs or changed inputs.
- Desktop 1440×1000 and mobile 390×844: initial and processed states, result controls, detail/preview dialogs and introduction case links; contained table scrolling, no document overflow.
- Evidence: compare sample output with original logic, parse downloaded files, capture screenshots, monitor runtime errors and network requests during uploaded-data processing.

## Additional demo verification (2026-10-11)

- Python: 91 tests passed, including original engine checks and 17 new adapter cases (input validation, CSV/XLSX protection, per-request isolation and OCR label normalization).
- Leads: 26 → 19 by ID → 18 by name/contact → 14 candidates, 4 exclusions; charcoal 7 / 2 / 5. Selecting Tokorozawa returns 6 candidates; no selected area produces an actionable error.
- Leads exports parsed: 14 candidate CSV rows, 4 exclusion CSV rows and a 4-sheet XLSX. Search/no-match, charcoal filter, both tabs, JSON editing, invalid JSON and sample reset passed.
- Uploaded JSON containing HTML-shaped names renders as text; processing made no network requests and did not modify later sample results.
- Invoice text sample: 3 actual PDFs, total ¥187,990. All 5 PDFs including Japanese OCR: total ¥624,070; due dates 2026-10-10, 10-15, 10-16, 10-31, 11-20. OCR rows remain marked for review; raw OCR evidence and label corrections are retained.
- Invoice exports parsed: 5 CSV/JSON records, correct due-date order, and a 2-sheet XLSX. Changed reference date, search/no-match, review/overdue filters, detail and PDF preview passed.
- Broken PDF and more than 5 uploaded files produce clear errors; exports are disabled after failure or input changes.
- Desktop 1440×1000 and mobile 390×844: inspected initial/results views and detail/preview dialogs; no document horizontal overflow. Both new links from the introduction and cross-demo navigation work. No browser runtime errors.

## Agentic Agency introduction: QA inventory

- Content: agency identity, broad service areas, Grok Bot workflow explicitly labeled as design; Koushin is a deliverable example. The supplied document's closing question is excluded.
- Controls: header/footer section links, all demo CTAs and screenshot link; demo return link leads to the agency introduction.
- Functional flow: agency → demo → sample calculation → agency; verify 80 / 37 / 19 / 7.
- Visual: desktop 1440×1000 and mobile 390×844, hero, team, showcase, workflow, roadmap and footer; no clipping or overflow.
- Exploratory: 320px viewport, direct `/demo/` refresh and keyboard skip link. No interaction on the introduction implies contacting or submitting to a Bot.

- Default sample: 250 inputs, 80 targets, 37 three-month contracts, 19 old-method misses, 7 issues, 3 exclusions.
- Runtime: initialize Python in a Worker, click extraction, confirm live result replaces the saved sample.
- Inputs: target month, 0–2 month lookahead, all three conventions, sample reset, CSV upload.
- Table: four tabs, search, AM filter, pagination, no-match state, keyboard navigation.
- Downloads: open generated XLSX, parse 80 CSV records, inspect 13-message ZIP; repeat after changing conditions.
- Error cases: missing CSV columns, invalid date/month, empty data, zero matching contracts; no stale exports after input changes.
- Data isolation: repeated requests do not share input records; uploaded data does not appear in network requests.
- Visual: desktop 1440×1000 and mobile 390×844; no page overflow; dialogs and all actions reachable.
- Deployment: public URL serves the full app and calculation assets; run sample on deployed origin.

## Verification record (2026-10-11)

- Python tests: 74 passed (62 original engine tests + 12 browser adapter cases).
- Chrome desktop: actual Worker calculation returned 80 / 37 / 19 / 7; no page errors.
- Lookahead of one month: 135 targets. All three end-date conventions executed successfully.
- Downloaded CSV: 80 records; XLSX: 16 sheets; ZIP: 13 message files. Files parsed successfully.
- All four table tabs, search/no-match, AM filter, forward/back pagination and sample reset passed.
- Missing CSV columns produced an actionable message. 1900-01 produced zero targets and a valid workbook.
- Custom CSV: one target; HTML-shaped names rendered as text; zero network requests during processing.
- Desktop 1440×1000 and mobile 390×844: no document horizontal overflow. Mobile extraction and help dialog passed.
- Visually inspected initial state, results table, comparison, export actions and mobile layout.
- Public deployment: verified in a fresh unauthenticated Chrome context, recalculated 80 / 37 / 19 / 7, downloaded and parsed a 16-sheet XLSX; no page errors.
- Vercel production URL: https://koushin-checker-jun0908.vercel.app — repeated anonymous browsing, live extraction (80 / 37 / 19 / 7) and Excel download verification; no page errors.

## Introduction page and demo route (2026-10-11)

- `/` presents the product introduction; `/demo/` hosts the existing interactive app.
- Desktop 1440×1000 and mobile 390×844: introduction page visually inspected; no horizontal overflow.
- Introduction CTA → demo → live extraction (80 / 37 / 19 / 7) → Excel download → return to introduction passed locally.
- FAQ expansion works; demo assets and Worker resolve from the shared site root.
- Vercel production: anonymous introduction → /demo/ → live extraction (80 / 37 / 19 / 7) → 16-sheet XLSX download → introduction passed; no browser errors.

- Agentic Agency local result: all section anchors and six demo links resolve; 1440px, 390px and 320px layouts have no horizontal overflow. Desktop/mobile screenshots reviewed. Sample recalculation returned 80 / 37 / 19 / 7; direct demo refresh and return link passed; keyboard skip link works; no browser errors. Supplied document closing question is absent.

- Production (anonymous Chrome): introduction links and cross-demo navigation passed. Leads returned 26 / 14 / 8 / 4; invoice text PDFs returned 3 / 187990; all 5 PDFs including OCR returned 5 / 624070 / 1 overdue / 2 due soon / 2 reviews. Downloaded public XLSX files parsed successfully. Existing renewal demo recalculated 80 / 37 / 19 / 7. No browser runtime errors.

## Three-demo introduction gallery (2026-10-11)

- Introduction now presents three equal cards with actual app screenshots, sample results, input options, actions and downloadable outputs. Hero shortcuts also open each demo directly.
- Fresh local browser runs for screenshot capture: invoice text PDFs returned 3 / ¥187,990; leads returned 26 input / 14 candidates.
- Desktop 1440×1000 and mobile 390×844 screenshots visually reviewed. All screenshots load. Widths 320, 390, 768, 1024 and 1440 have no horizontal page overflow.
- All section anchors resolve. Each gallery CTA opens its matching demo, and each demo returns to the introduction.
- The gallery appears before the Bot-team design. Current working tools and future Grok API integration remain explicitly distinguished.
