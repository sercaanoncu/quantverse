# QuantVerse v2 Release Notes

QuantVerse v2 is a public-data global equity research, portfolio model comparison, and risk analytics project. It produces research candidates and evidence reports, but it does not provide investment advice and does not promote an institutional global USD master portfolio.

## What QuantVerse v2 Does

- Builds a current public-provider global equity research universe.
- Generates USD-normalized return matrices where the public-data FX path is available.
- Scores stocks using deterministic public-data research features.
- Compares portfolio construction models under constraints.
- Evaluates Equal Weight and random portfolios as mandatory benchmarks.
- Runs walk-forward validation on the current public-data universe.
- Produces risk, exposure, forecast-diagnostic, robustness, and claim-control outputs.
- Generates PDF, HTML, Excel, thesis-style, and defense-style research artifacts.

## Major Modules

- Universe and source validation
- Return matrix and FX normalization checks
- Stock scoring
- Portfolio model league
- Robust model selection
- Random portfolio benchmarking
- Walk-forward validation
- Forecast diagnostics
- Exposure and risk reporting
- Publish-readiness claim controls
- Generated artifact validation

## Model League

The v2 model league includes constrained and benchmark-aware public-data research models. Models are evaluated for weight validity, constraints, risk metrics, walk-forward evidence, benchmark comparison, random-portfolio percentile, robustness, and limitations.

## Final Model Selection Logic

The final research model is selected by `robust_public_data_evidence_gate`. The model selection result is not equivalent to a promoted global USD master portfolio.

Final validation generated output showed:

- Final selected model: `Policy Constrained`
- Final model decision: `not promoted`
- Publish readiness: `research_publish_ready_with_limitations`

Clean-room generated output also selected `Policy Constrained` and retained the same `not promoted` decision. If a future public-data rerun selects a different research model, that must be treated as generated-output drift and the latest validation run should be treated as the source of truth for the current artifact set.

## Outputs

- `data/processed/quantverse_v2_demo_summary.json`
- `data/processed/global_final_model_decision.json`
- `data/processed/global_model_selection_report.csv`
- `data/processed/global_portfolio_league.csv`
- `data/processed/global_portfolio_league_weights.csv`
- `data/processed/global_random_portfolio_percentile_report.csv`
- `data/processed/global_robustness_sensitivity.csv`
- `data/processed/global_forecast_validation_by_horizon.csv`
- `output/pdf/quantverse_v2_research_report.pdf`
- `output/html/quantverse_v2_research_report.html`
- `output/excel/quantverse_v2_research_output.xlsx`
- `output/thesis/quantverse_doctoral_dissertation_full.pdf`
- `output/thesis/quantverse_doctoral_defense_presentation_full.pdf`

The output files above are generated artifacts and should not be committed.

## Validation Result

Release-candidate QA added `scripts/validate_quantverse_v2_artifacts.py`, which checks required generated files, schemas, row counts, model-decision consistency, weight sums, PDF page/text extraction, HTML sections, Excel sheets, and generated-report claim language.

Validation status observed before final rerun:

- Artifact validation: passed
- Required checks: 19
- Failed checks: 0
- Initial pytest: 164 passed
- Clean-room pytest: 164 passed
- Final pytest after adding release QA: 166 passed

## Limitations

- Official exact top-100 market-cap support remains unavailable.
- Point-in-time historical constituent evidence remains unavailable.
- Delisting and institutional corporate-action reconciliation remain unavailable.
- The current walk-forward evidence uses a current public-data universe, not institutional PIT membership.
- Public data can drift between runs.
- Extreme annualized return and Sharpe estimates are warning flags requiring review, not success claims.
- The global master portfolio remains `not promoted`.

## Release Position

QuantVerse v2 is ready to publish as a transparent public-data research project if final validation passes. It is not ready to present as a production trading platform or an institutional point-in-time investment system.
