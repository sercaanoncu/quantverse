# Artifact Readability QA

This file records the PDF, Excel, and HTML readability checks for QuantVerse v2 generated outputs.

## PDF QA

| PDF | Pages | First-page text chars | Visual render result | Notes |
| --- | ----- | --------------------- | -------------------- | ----- |
| `output/pdf/quantverse_v2_research_report.pdf` | 7 | 2434 | First page rendered and readable | Contains executive summary, not-promoted decision, blocker language, chart and table |
| `output/thesis/quantverse_doctoral_dissertation_full.pdf` | 74 | 666 | First page rendered and readable | States not investment advice, no exact top-100 claim and no institutional PIT validation |
| `output/thesis/quantverse_doctoral_defense_presentation_full.pdf` | 55 | 320 | First page rendered and readable | Presentation-style page, not a raw table dump |

Rendered PNG paths:

- `tmp/pdfs/quantverse_v2_research_report_page1.png`
- `tmp/pdfs/quantverse_doctoral_dissertation_full_page1.png`
- `tmp/pdfs/quantverse_doctoral_defense_presentation_full_page1.png`

The `pdftoppm` wrapper reported a local path error in this Codex/Windows environment. The direct bundled Poppler executable worked:

`<codex-runtime>/dependencies/native/poppler/Library/bin/pdftoppm.exe`

Direct Poppler emitted font warnings for `Symbol` and `ArialUnicode`, but generated non-empty PNGs. Visual inspection found the first pages readable and structurally valid.

## Excel QA

Workbook:

`output/excel/quantverse_v2_research_output.xlsx`

Required sheets were present. Total sheet count: 29.

Required checked sheets:

- `START_HERE`
- `EXECUTIVE_SUMMARY`
- `SELECTED_STOCKS`
- `STOCK_SCORES`
- `RETURN_FORECASTS`
- `MODEL_LEAGUE`
- `MODEL_SELECTION`
- `FINAL_WEIGHTS`
- `RISK_METRICS`
- `RISK_CONTRIBUTIONS`
- `WALK_FORWARD`
- `RANDOM_PERCENTILES`
- `ROBUSTNESS`
- `EXPOSURE_REGION`
- `EXPOSURE_COUNTRY`
- `EXPOSURE_CURRENCY`
- `TOP_HOLDINGS_EXPLANATION`
- `FORECAST_VALIDATION`
- `WARNINGS`
- `CLAIM_CONTROL`

## HTML QA

HTML report:

`output/html/quantverse_v2_research_report.html`

Checked sections:

- `Executive Summary`: present
- `Stock Scoring`: present
- `Portfolio Model League`: present
- `Robust Model Selection`: present
- `Walk-Forward`: present
- `Exposure`: present
- `Limitations`: present

## Fixes Applied

- Added an explicit `Limitations` section to the v2 research report builder so HTML/PDF artifacts expose the release blockers directly.
- Adjusted a negated claim-control phrase to avoid the literal forbidden phrase `guaranteed alpha` in generated report text.

## Readability Decision

The generated v2 report, Excel workbook, HTML report, thesis PDF, and defense PDF pass release-candidate readability QA.
