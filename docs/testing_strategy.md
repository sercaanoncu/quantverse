# QuantVerse Testing Strategy

Date: 2026-07-22

## Purpose

The test strategy does not prove future investment success. It verifies that the
pipeline contracts, data separation rules, portfolio weights, risk validation,
reporting surface, import compatibility, portability and transfer readiness do
not break.

## Test Categories

| Category | Scope |
|---|---|
| Config | `configs/base.yaml` loading, invalid config behavior, VaR/bootstrap parameter validation. |
| Metadata portability | `run_metadata.json` must not leak host-specific absolute paths. |
| Namespace | Public `quantverse.*` imports and legacy `project.*` compatibility. |
| Data | Market signals must not enter investable portfolio weights; low realized return is not a deletion rule. |
| Portfolio | Weight sums, long-only contracts and holdings CSV schema. |
| Canonical portfolio core | Twenty holdings, issuer deduplication, group caps, common OOS dates, all-fold walk-forward, market risk-free alignment and three-part decision roles. |
| Risk validation | VaR exception counts, expected exceptions and Kupiec/Christoffersen edge cases. |
| Stress | Expected stylized scenario names, schema and non-historical-replay label. |
| Benchmark | Equal Weight, HRP, Inverse Volatility and internal 60/40 proxy behavior. |
| Champion-challenger research | No-look-ahead execution, long-only capped target weights, evidence class set and champion summary schema. |
| Research architecture outputs | Model league schema, research alpha leaderboard schema, promotion gate schema and allowed labels. |
| Covariance comparison | EWMA and other covariance estimator comparison output schema. |
| Transaction cost | 0/5/10/25 bps core cost schema, 50 bps challenger robustness and impossible-cost checks. |
| Bootstrap | Confidence interval columns and evidence category set. |
| ML diagnostic | Confusion matrix, drift schema and diagnostic-not-trading-rule framing. |
| Reporting | PDF import, HTML smoke generation and CLI help. |
| Hygiene | No local absolute path leakage in source, docs or lightweight CSV/JSON outputs. |
| Transfer readiness | Manifest, do-not-copy list, dry-run copy command and Git-free helper script. |

## Deliberately Avoided Tests

- No unit test depends on live `yfinance` downloads because those tests would be
  brittle.
- No test claims future returns or investment success.
- No pixel-perfect PDF snapshot test is used; final PDF QA is handled through
  render-and-inspect checks.
- No meaningless test count inflation is used.
- No LSTM, Transformer, RL or LLM trading-agent test exists because those models
  are deliberately not production allocation engines in this project.

## Quality Gate

Run these commands from the project root:

```powershell
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m pyright
python -m compileall src scripts
python scripts/qa/verify_quantverse_reference_math.py
python scripts/validate_quantverse_v2_artifacts.py
```

Latest validated pytest result:

```text
411 passed
```

If deterministic tests are added or removed later, update README and
reproducibility docs to match the actual `pytest -q` output.

Passing criterion: every command exits successfully. Generated artifacts remain
uncommitted, and no push is performed without explicit approval.
