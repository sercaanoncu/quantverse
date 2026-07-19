# QuantVerse v2 Release Notes

## Release Position

QuantVerse v2 is a public-data global equity research, model-comparison, and
risk-analytics project. Current verdict:

**RESEARCH_READY_WITH_LIMITATIONS**

It is not investment advice, an official exact top-100 universe, an
institutional point-in-time backtest, a production trading system, or a
promoted global USD master portfolio.

## Current Clean-Run Decision

| Item | Result |
|---|---|
| Data as of | 2026-07-17 |
| Run ID | `qv2-2026-07-17-259efc27e54d3d25` |
| Universe rows | 890 |
| Assets with returns | 100 |
| Selected stocks | 40 |
| Final public-data research model | Equal Weight |
| Final holdings | 40 |
| Decision | `not promoted` |
| Institutional/global-master promotion | `not_promoted` |
| Publish scope | public-data research with limitations |

Equal Weight is selected because no active challenger clears all comparable
walk-forward, paired uncertainty, robustness, random-benchmark, cost,
downside-risk, and metric-review gates. It is not hard-coded as winner.

## Scientific Hardening

- strict portfolio-weight and missing-return contracts;
- security identity, ticker-history, and feature-history controls;
- crypto/stable-value master-input gates;
- explicit optimizer failure and infeasibility states;
- true chronological walk-forward daily OOS evidence;
- same-protocol OOS random portfolio benchmarking;
- paired circular block-bootstrap model differences;
- metric-review warnings in active selection gates;
- corrected Sharpe, Sortino, Calmar, VaR/CVaR, and benchmark overlap semantics;
- valid log-space Monte Carlo support;
- deterministic run/data/config/input fingerprints;
- mixed-run and cross-artifact reconciliation;
- independent reference math checks;
- explicit v2, legacy candidate, and institutional decision scopes.

## Model League

Actually run: Inverse Volatility, GMV, HRP, Risk Parity, and Min CVaR.

Benchmark: Equal Weight. Random portfolios are a benchmark distribution and
cannot be selected.

Diagnostic only: Max Sharpe, Black-Litterman, Policy Constrained,
Forecast-Enhanced Constrained, ML Forecast, and Ensemble Forecast.

## Current Limitations

- only 252 OOS observations;
- current-universe survivorship/current-membership bias;
- no official dated exact top-100 market-cap evidence;
- no complete point-in-time delisting/corporate-action database;
- no nested OOS robustness across every tested policy dimension;
- incomplete multiple-testing control;
- economic-country exposure unavailable;
- simplified costs and no execution/capacity layer;
- no production model approval, monitoring, limits, access control, or audit trail.

## Generated Outputs

Generated `data/processed/*` and `output/*` artifacts are excluded from source
commits. The current package includes PDF, HTML, Excel, visual audit,
presentation, cross-artifact reconciliation, and independent math evidence.

## Validation Gates

Release requires:

```text
python scripts/run_quantverse_v2_demo.py --config configs/global_equity_research.yaml
python scripts/run_full_pipeline.py --config configs/base.yaml
python scripts/validate_quantverse_v2_artifacts.py
python scripts/qa/verify_quantverse_reference_math.py
python -m pytest -q
python -m black src scripts tests
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m compileall src scripts
git diff --check
```

The exact final test count belongs in the final release response because tests
can be added during the audit.
