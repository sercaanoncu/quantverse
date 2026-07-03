# QuantVerse

QuantVerse is a Python public-data global equity selection, portfolio allocation,
return-forecasting and risk-validation research platform.

It is a research and decision-support project. It is not investment advice, a
live trading system, or an institutional point-in-time backtest.

## What It Does

- Builds and validates a sourced current global equity candidate universe.
- Computes local and USD-normalized simple/log return matrices.
- Scores stocks using coverage, market-cap liquidity proxy, momentum, volatility,
  drawdown, risk-adjusted return and diversification diagnostics.
- Produces expected-return diagnostics with a random-walk baseline, momentum,
  mean-reversion, rolling mean and ridge regression checks.
- Compares a portfolio model league against Equal Weight and random portfolios.
- Selects the final public-data model through a robust evidence gate using
  walk-forward, risk, transaction-cost, random-benchmark and Equal Weight checks.
- Reports portfolio return, volatility, Sharpe, Sortino, drawdown, VaR, CVaR,
  stress scenarios and risk contributions.
- Runs current-universe public-data walk-forward validation with chronological
  train/test windows.
- Generates PDF, HTML, Excel, thesis-style and showcase outputs.

## One-Command v2 Demo

```powershell
python scripts/run_quantverse_v2_demo.py --config configs/global_quant_research.yaml
```

Primary demo summary:

```text
data/processed/quantverse_v2_demo_summary.json
```

Fast local healthcheck:

```powershell
python scripts/quantverse_healthcheck.py
```

Summarize already generated local outputs:

```powershell
python scripts/quantverse_latest_run_summary.py
```

## Model League

The v2 league makes every model explicit, including models that are diagnostic
or blocked by missing prerequisites.

- Equal Weight
- Random Portfolios
- Inverse Volatility
- GMV / Global Minimum Variance
- Max Sharpe
- Min CVaR
- HRP
- Risk Parity
- Black-Litterman
- ML Forecast
- Ensemble Forecast
- Forecast-Enhanced Constrained Portfolio
- Policy Constrained

Each row carries an `actual_status` such as `actually_run`, `benchmark_only`,
`diagnostic_only`, `blocked_by_data`, `blocked_by_implementation` or
`future_candidate`.

## Main Outputs

- Stock scores: `data/processed/global_stock_scores.csv`
- Return forecasts: `data/processed/global_stock_return_forecasts.csv`
- Model league: `data/processed/global_portfolio_league.csv`
- Model weights: `data/processed/global_portfolio_league_weights.csv`
- Robust model selection: `data/processed/global_model_selection_report.csv`
- Final model decision: `data/processed/global_final_model_decision.json`
- Random percentile benchmark: `data/processed/global_random_portfolio_percentile_report.csv`
- Exposure interpretation: `data/processed/global_top_holdings_explanation.csv`
- Forecast validation: `data/processed/global_forecast_validation_by_horizon.csv`
- Risk report: `data/processed/global_portfolio_risk_report.csv`
- Walk-forward comparison: `data/processed/global_walk_forward_model_comparison.csv`
- Walk-forward summary: `data/processed/global_walk_forward_summary.json`
- v2 PDF: `output/pdf/quantverse_v2_research_report.pdf`
- v2 HTML: `output/html/quantverse_v2_research_report.html`
- v2 Excel: `output/excel/quantverse_v2_research_output.xlsx`
- Full thesis PDF: `output/thesis/quantverse_doctoral_dissertation_full.pdf`
- Full defense PDF: `output/thesis/quantverse_doctoral_defense_presentation_full.pdf`

Generated `data/processed/*` and `output/*` files are reproducible artifacts and
are not source files.

## Current Status

QuantVerse v2 is positioned as a public-data research engine. The system can
score real public-provider stocks, build model weights, evaluate risk and run a
current-universe walk-forward validation.

The project does not claim official exact top-100 membership, point-in-time
historical constituent validity, institutional delisting reconciliation,
production execution readiness, or future performance.

## Methodology

The methodology is grounded in portfolio theory, financial statistics,
econometrics, machine-learning validation and risk management:

- Simple returns are used for portfolio aggregation.
- Log returns remain available for statistical diagnostics.
- Equal Weight and random portfolios remain hard benchmarks.
- Expected-return optimizers are treated conservatively because mean estimates
  are noisy.
- VaR, CVaR, drawdown, stress tests and risk contributions are reported beside
  return metrics.
- ML and return forecasts are diagnostic unless validation supports a stronger
  decision role.
- Walk-forward validation is chronological and must not use future data.
- Final model selection is conservative: diagnostic or blocked models cannot be
  final selected models, and active models do not displace Equal Weight unless
  return, risk, cost and benchmark evidence supports that decision.

## Legacy ETF/Multi-Asset Pipeline

The original multi-asset ETF pipeline remains available:

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml
```

Legacy ETF/multi-asset report outputs:

```text
output/html/quantverse_report.html
output/pdf/quantverse_analysis_report.pdf
```

The professional public namespace is `quantverse`; the older `project`
namespace is preserved for backward compatibility.

```python
from quantverse.pipeline import PipelineConfig, run_full_pipeline
from quantverse.risk.validation import var_exception_tests
from quantverse.reporting.pdf_report import generate_pdf_report
```

## Install

```powershell
python -m pip install -e .
python -m pip install -e ".[dev]"
```

## Validation

```powershell
python -m pytest -q
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m compileall src scripts
```

## Key Documentation

- Product contract: `docs/product/QUANTVERSE_V2_PRODUCT_CONTRACT.md`
- Master roadmap: `docs/roadmap/QUANTVERSE_MASTER_PROJECT_PLAN.md`
- Reality check: `docs/audit/QUANTVERSE_V2_CORE_ENGINE_REALITY_CHECK.md`
- Methodology mapping: `docs/thesis/methodology_literature_mapping.md`
- GitHub showcase: `docs/showcase/README_GITHUB_SHOWCASE.md`
- CV bullets: `docs/showcase/CV_BULLETS.md`
- Bank interview talk track: `docs/showcase/BANK_INTERVIEW_TALK_TRACK.md`

## Codex Context Pack

Future Codex runs should start from `.codex/CONTEXT.md`,
`.codex/VALIDATION.md` and `docs/roadmap/QUANTVERSE_MASTER_PROJECT_PLAN.md`.

## Limitations

Public-provider data is useful for research and demonstration, but stronger
institutional use would require licensed data, point-in-time constituents,
delisting and corporate-action reconciliation, robust FX calendar alignment,
model approval, monitoring, access control, execution logic and independent
reconciliation.
