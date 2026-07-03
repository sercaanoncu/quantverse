# QuantVerse v2 Release Candidate Audit

This audit records the pre-push release-candidate checks for QuantVerse v2 on branch `integrate-fx-marketcap-gates`.

QuantVerse v2 is publish-ready only as a public-data research and risk analytics project with visible limitations. It is not investment advice, not an official exact top-100 equity universe, not an institutional point-in-time backtest, and not a live trading system.

| Area | Check | Result | Evidence | Fix Applied | Status |
| ---- | ----- | ------ | -------- | ----------- | ------ |
| Branch | Current branch is the release branch | `integrate-fx-marketcap-gates` | `git branch --show-current` | None | Pass |
| Commit history | Recent v2 commits are present | Latest observed commit: `551692a Add publish readiness quality gates` | `git log --oneline -50` | None | Pass |
| Generated outputs | `data/processed`, `output`, and generated current universe should not be tracked | 37 legacy tracked `data/processed` files were found | `git ls-files data/processed output data/universe/current_global_equity_universe.csv` | Added ignore rules and removed `data/processed` from the index with `git rm --cached -r data/processed` | Fixed |
| README demo | One-command v2 demo exists | `python scripts/run_quantverse_v2_demo.py --config configs/global_quant_research.yaml` | Clean-room run completed | None | Pass |
| Demo summary | Required summary JSON exists | `data/processed/quantverse_v2_demo_summary.json` | Validator schema check | Added artifact validator | Pass |
| Model selection | Model selection report exists | `data/processed/global_model_selection_report.csv`, 13 rows | Artifact QA | Added artifact validator | Pass |
| Final decision | Final model decision JSON exists | `data/processed/global_final_model_decision.json` | Artifact QA | Added artifact validator | Pass |
| Random benchmark | Random portfolio percentile output exists | `data/processed/global_random_portfolio_percentile_report.csv`, 13 rows | Artifact QA | Added artifact validator | Pass |
| Robustness | Robustness sensitivity output exists | `data/processed/global_robustness_sensitivity.csv`, 48 rows | Artifact QA | Added artifact validator | Pass |
| Exposure | Region/country/currency exposure outputs exist | Excel exposure sheets and generated CSV outputs | Excel QA | None | Pass |
| Forecast validation | Forecast validation output exists | `data/processed/global_forecast_validation_by_horizon.csv`, 4 rows | Artifact QA | Added artifact validator | Pass |
| PDF report | Research PDF exists and has text | `output/pdf/quantverse_v2_research_report.pdf`, 7 pages | pypdf and Poppler render | Added missing `Limitations` section | Pass |
| HTML report | HTML report exists and has major sections | `output/html/quantverse_v2_research_report.html` | HTML section check | Added missing `Limitations` section | Pass |
| Excel workbook | Workbook exists and has required sheets | `output/excel/quantverse_v2_research_output.xlsx`, 29 sheets | XLSX workbook XML check | None | Pass |
| Thesis PDF | Full thesis PDF exists | `output/thesis/quantverse_doctoral_dissertation_full.pdf`, 74 pages | pypdf and Poppler render | None | Pass |
| Defense PDF | Full defense PDF exists | `output/thesis/quantverse_doctoral_defense_presentation_full.pdf`, 55 pages | pypdf and Poppler render | None | Pass |
| Showcase | Showcase docs exist | `docs/showcase/*` | File inspection | None | Pass |
| CV bullets | CV wording is limitation-aware | No unsupported claim found | Claim-language review | None | Pass |
| LinkedIn post | Public wording is honest | No unsupported claim found | Claim-language review | None | Pass |
| Bank interview | Talk track is defensible | No unsupported claim found | Claim-language review | None | Pass |
| Forbidden claims | Generated reports avoid unsupported claims | Validator found zero forbidden report hits | `scripts/validate_quantverse_v2_artifacts.py` | Changed generated report wording from `guaranteed alpha` to `alpha guarantees` in a negated sentence | Pass |

## Release Decision

The release candidate is acceptable for GitHub publication as a public-data QuantVerse v2 research artifact if final validation remains green. The correct public statement is:

- `publish_readiness_status`: `research_publish_ready_with_limitations`
- Global master portfolio promotion: `not promoted`
- Official exact top-100 claim: not supported
- Institutional point-in-time backtest claim: not supported
- Investment advice: no

## Notes

Clean-room and local generated outputs can select different final research models when public provider data changes between runs. This is acceptable only because each run is self-consistent, the decision remains `not promoted`, and generated outputs are not committed.
