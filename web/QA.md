# Web app verification

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
