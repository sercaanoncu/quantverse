# QuantVerse Product User Guide

This guide explains how to run QuantVerse as a local research product. It is not
investment advice.

## One-Command Quickstart

```powershell
python scripts/quantverse_healthcheck.py
```

If the healthcheck passes, run:

```powershell
python scripts/quantverse_latest_run_summary.py
```

To regenerate outputs, run:

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml
```

## 1. Install

For normal use:

```powershell
python -m pip install -e .
```

For development and tests:

```powershell
python -m pip install -e ".[dev]"
```

## 2. Run The Full Pipeline

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml
```

This refreshes processed outputs and report files. It may use cached market data
when available.

## 2.1 Summarize The Latest Local Run

```powershell
python scripts/quantverse_latest_run_summary.py
```

This reads existing `data/processed` outputs and prints a compact terminal
summary. It does not download data or rerun the pipeline.

## 3. Run Tests

```powershell
python -m pytest -q
```

For full local quality gates:

```powershell
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m compileall src scripts
```

## 4. Open Reports

- PDF: `output/pdf/quantverse_analysis_report.pdf`
- HTML: `output/html/quantverse_report.html`

If the files are missing, run the full pipeline again.

## 5. Where Outputs Are Written

- `data/processed/`: CSV and JSON evidence.
- `reports/figures/`: generated figures.
- `output/pdf/`: PDF report.
- `output/html/`: static HTML report.

## 6. Major Output Files

- `portfolio_weights_matrix.csv`: compact portfolio allocation matrix.
- `portfolio_holdings_long.csv`: long-format holdings by portfolio.
- `model_league_summary.csv`: model role and league summary.
- `model_promotion_gate.csv`: promotion decision checks.
- `champion_selection_summary.json`: final champion/challenger decision.
- `asset_class_momentum_metric_recompute_check.csv`: forensic metric check.
- `asset_class_momentum_weight_audit.csv`: weight-level forensic audit.
- `var_exception_tests.csv`: VaR backtesting evidence.

## 7. Interpret The Final Model Decision

Equal Weight remains the broad default champion because it is simple,
diversified and robust. Asset-Class Momentum Rotation has the best current OOS
CAGR point estimate, but remains a research candidate because risk and
robustness checks are not strong enough for broad promotion.

## 8. Explain Equal Weight vs Asset-Class Momentum

Equal Weight is the hard benchmark. Asset-Class Momentum is an active challenger
that rotates between asset classes using trailing information. Higher return
does not automatically mean better final decision quality.

## 9. Avoid Misusing Results

Do not treat any output as a buy/sell recommendation. Do not claim guaranteed
returns. Do not use this as a live trading system without execution, monitoring,
limits, taxes, slippage and model approval.

## 10. Troubleshooting

### Missing Script

Run the command from the repository root. Confirm `scripts/run_full_pipeline.py`
and `scripts/quantverse_healthcheck.py` exist.

### yfinance Or Cache Issue

Retry later or clear only the cache files you understand. Public data providers
can change availability and rate limits.

### Python Path Issue

Run:

```powershell
python -m pip install -e ".[dev]"
```

Then confirm imports point to this repository, not an older local clone.

### Pytest Failure

Read the first failing test. Do not chase model performance. Fix only the broken
contract or update documentation if the expected behavior intentionally changed.

### PDF Output Missing

Run:

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml
```

If it still fails, check whether `reportlab` is installed through the dev setup.
