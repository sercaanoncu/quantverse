# QuantVerse

QuantVerse is a multi-asset portfolio research, market-risk validation and
reporting project. It cleans market data, separates investable instruments from
context signals, builds transparent portfolio weights, runs walk-forward
backtests, reports risk diagnostics, and generates formal PDF/HTML outputs.

This project is not investment advice. It is a research and decision-support
pipeline for explaining data, assumptions, portfolio weights, risk metrics,
validation results and model limitations.

## What It Does

- Reads the canonical production configuration from `configs/base.yaml`.
- Builds a multi-asset universe across ETFs, crypto, commodities, bonds and REITs.
- Keeps `^VIX`, `^TNX`, `^IRX` and `DX-Y.NYB` out of portfolio weights; these are
  context/risk signals, not investable portfolio assets.
- Uses `^IRX` as the risk-free proxy when available and records fallback metadata
  when provider data is unavailable.
- Produces Equal Weight, Min Variance, Max Sharpe, HRP, Risk Parity, Inverse
  Volatility and Min CVaR portfolios.
- Does not remove an asset only because its historical return was low; exclusions
  are based on data coverage and investability.
- Shows portfolio composition through `portfolio_weights_matrix.csv` and
  `portfolio_holdings_long.csv`.
- Runs walk-forward backtests with transaction costs.
- Adds a research-grounded champion-challenger layer that tests Equal Weight,
  risk-controlled momentum, trend-following, asset-class rotation, risk-managed
  Equal Weight, Signal-Aware HRP Lite and nested shrinkage challengers under the
  same no-look-ahead walk-forward protocol.
- Separates model leagues: broad default champion, annual-return challenger,
  risk-adjusted champion, defensive/drawdown candidate, research candidate,
  diagnostic-only model and rejected model.
- Produces VaR/CVaR, drawdown, Calmar, Ulcer Index and diversification metrics.
- Adds VaR exception testing, stylized stress scenarios, benchmark comparison,
  transaction-cost sensitivity and moving-block bootstrap robustness outputs.
- Keeps the ML downside-risk model as a diagnostic layer, not a trading signal.
- Generates formal PDF and static HTML research reports.

## Install

Production pipeline only:

```powershell
python -m pip install -e .
```

Development, test, lint and pre-commit tools:

```powershell
python -m pip install -e ".[dev]"
```

Notebook dependencies if needed:

```powershell
python -m pip install -e ".[dev,notebook]"
```

## Public Import Surface

The professional public namespace is `quantverse`. The older `project` namespace
is preserved for backward compatibility.

```python
from quantverse.pipeline import PipelineConfig, run_full_pipeline
from quantverse.risk.validation import var_exception_tests
from quantverse.reporting.pdf_report import generate_pdf_report
```

## Run

Quick local healthcheck:

```powershell
python scripts/quantverse_healthcheck.py
```

Summarize the latest generated local outputs:

```powershell
python scripts/quantverse_latest_run_summary.py
```

Run the full project:

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml
```

Without regenerating the PDF:

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml --skip-pdf
```

Makefile targets:

```bash
make test
make lint
make format
make smoke
make report
```

## Product User Guide

See `docs/product_user_guide.md` for installation, local commands, output
locations, report paths, interpretation notes and troubleshooting.

## Codex Context Pack

Future Codex runs should start from `.codex/CONTEXT.md` and the validation
protocol in `.codex/VALIDATION.md`.

The permanent master roadmap is
`docs/roadmap/QUANTVERSE_MASTER_PROJECT_PLAN.md`.

## Project Healthcheck

Use `python scripts/quantverse_healthcheck.py` for a fast local readiness check.
It does not download data, run pytest or execute the full pipeline.

Use `python scripts/quantverse_latest_run_summary.py` to summarize already
generated local outputs without downloading data or rerunning the pipeline.

## Validation

Current full local validation gate:

```powershell
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m compileall src scripts
python scripts/run_full_pipeline.py --config configs/base.yaml
```

Expected pytest result after the global quant input gate sprint:

```text
102 passed
```

## Main Outputs

- `data/processed/run_metadata.json`
- `data/processed/data_quality_report.csv`
- `data/processed/portfolio_holdings_long.csv`
- `data/processed/portfolio_weights_matrix.csv`
- `data/processed/var_exception_tests.csv`
- `data/processed/stress_scenarios.csv`
- `data/processed/benchmark_comparison.csv`
- `data/processed/transaction_cost_sensitivity.csv`
- `data/processed/statistical_robustness.csv`
- `data/processed/equal_weight_diagnostic.csv`
- `data/processed/challenger_backtest_summary.csv`
- `data/processed/challenger_returns.csv`
- `data/processed/challenger_weights.csv`
- `data/processed/challenger_turnover.csv`
- `data/processed/challenger_vs_equal_weight.csv`
- `data/processed/challenger_subperiod_analysis.csv`
- `data/processed/challenger_rolling_relative_performance.csv`
- `data/processed/challenger_cost_robustness.csv`
- `data/processed/challenger_bootstrap_vs_equal_weight.csv`
- `data/processed/asset_class_momentum_metric_recompute_check.csv`
- `data/processed/asset_class_momentum_weight_audit.csv`
- `data/processed/champion_selection_summary.json`
- `data/processed/research_alpha_leaderboard.csv`
- `data/processed/research_alpha_returns.csv`
- `data/processed/research_alpha_weights.csv`
- `data/processed/research_alpha_turnover.csv`
- `data/processed/research_alpha_vs_equal_weight.csv`
- `data/processed/model_league_summary.csv`
- `data/processed/model_league_summary.json`
- `data/processed/model_promotion_gate.csv`
- `data/processed/model_overfit_diagnostics.csv`
- `data/processed/covariance_model_comparison.csv`
- `data/processed/ml_downside_risk_metrics.csv`
- `data/processed/ml_downside_confusion_matrix.csv`
- `data/processed/ml_downside_drift_report.csv`
- `output/html/quantverse_report.html`
- `output/pdf/quantverse_analysis_report.pdf`

Heavy generated artefacts are reproducible and should not be treated as source
files. For clean-repo transfer, use:

- `docs/audit/QUALITY_SPRINT_TRANSFER_MANIFEST.md`
- `tools/migration/copy_quality_sprint_to_clean_repo.ps1`

## Methodology Principles

Static optimization is not treated as final decision evidence. Walk-forward
results, drawdown, costs, risk metrics, benchmark comparison and diagnostic
stability are more important than a single in-sample Sharpe number.

The return-seeking challenger layer separates "highest-CAGR research candidate"
from "broad champion replacement." In the current evidence layer,
Asset-Class Momentum Rotation has the highest OOS CAGR point estimate, but Equal
Weight remains the benchmark and broad default champion because the challenger
has higher drawdown, weaker subperiod consistency and bootstrap intervals that
cross zero.

The project is structured as benchmark + alpha challenger + risk engine +
validation engine + governance. Risk-controlled momentum and trend models are
treated as alpha challengers. HRP, Risk Parity, CVaR and shrinkage methods are
treated primarily as robust risk-allocation engines. ML remains diagnostic or an
overlay candidate, not a blind daily-return prediction machine.

Black-Litterman is not used in the production report unless dated, sourced and
confidence-scored views are available. XGBoost and LightGBM are not claimed as
core production dependencies unless a validated forecasting use case exists.
LSTM, Transformer, reinforcement-learning and LLM allocation agents are not
implemented as production allocation engines because the current data and
validation design do not justify them.

## Global Stock Selection Roadmap

QuantVerse now includes the first architecture layer for global
security-selection research. The existing ETF and multi-asset pipeline remains
intact. ETFs continue to serve as benchmarks and macro proxies; they are not
replaced by fabricated stock lists.

The global stock-selection engine will not invent top-100 constituents or market
capitalization ranks. Real analysis requires sourced universe files with
tickers, market caps, ranks, dates and providers, plus a returns matrix for
those assets.

Offline entry point:

```powershell
python scripts/run_global_stock_selection.py --config configs/global_stock_selection.yaml
```

If only the template universe is present, the command exits successfully and
explains that a populated sourced universe is required before stock-selection
research can run.

## Global Quant Research Pipeline

QuantVerse now includes a first-pass global quantitative research pipeline for
current universe construction, global returns matrices, master portfolio
candidate comparison and 1/3/6/12 month projection outputs.

Current top-100 style universe mode is forward-looking research only.
Institutional-grade historical claims require point-in-time constituent,
market-cap, FX, corporate-action and delisting data. The system must be allowed
to return `not promoted`; Equal Weight and random portfolios remain hard
benchmarks. This project is not investment advice.

Offline orchestration entry point:

```powershell
python scripts/run_global_quant_research.py --config configs/global_quant_research.yaml
```

If sourced universe or returns inputs are missing, the command exits
successfully with an explicit status instead of fabricating data.

## Project Structure

```text
configs/base.yaml                 canonical production configuration
src/quantverse/                   public namespace wrapper
src/project/config.py             config loading and validation
src/project/pipeline.py           end-to-end production pipeline
src/project/data_pipeline/        universe, fetch, clean and returns
src/project/optimization/         portfolio optimizers
src/project/risk/                 VaR, CVaR, drawdown and validation
src/project/backtest/             walk-forward backtests
src/project/ml/                   downside-risk diagnostic model
src/project/research/             champion-challenger research layer
src/project/reporting/            PDF/HTML reporting
docs/                             methodology, research, audit, validation and governance
tests/                            deterministic contract tests
tools/migration/                  local-only clean-repo transfer helper
```

## Key Documentation

- `docs/reproducibility.md`
- `docs/testing_strategy.md`
- `docs/audit/FINAL_SCORECARD.md`
- `docs/audit/QUANTVERSE_AUDIT.md`
- `docs/audit/EVIDENCE_MATRIX.md`
- `docs/audit/QUALITY_SPRINT_TRANSFER_MANIFEST.md`
- `docs/research/equal_weight_diagnostic.md`
- `docs/research/model_selection_protocol.md`
- `docs/research/annual_return_champion_review.md`
- `docs/research/asset_class_momentum_forensic_audit.md`
- `docs/research/research_grounded_quantverse_architecture.md`
- `docs/research/literature_to_quantverse_implementation_matrix.md`
- `docs/research/model_league_system.md`
- `docs/research/global_stock_selection_engine.md`
- `docs/research/random_portfolio_benchmarking.md`
- `docs/research/global_security_selection_limitations.md`
- `docs/research/risk_covariance_upgrade_plan.md`
- `docs/research/ml_ai_quantverse_strategy.md`
- `docs/research/validation_hardening_plan.md`
- `docs/product_user_guide.md`
- `docs/limitations.md`
- `docs/model_governance.md`
- `docs/validation/market_risk_validation_report.md`
- `docs/model_cards/downside_risk_model_card.md`

## Limitations

The data source is public yfinance. Institutional investment use requires
independent vendor reconciliation. Backtests measure historical behavior and do
not guarantee future performance. The ML layer is diagnostic and weak-signal; it
is not an automated trading rule. The project is designed as a public research
and portfolio analytics project, but it is not a complete production trading
platform.
