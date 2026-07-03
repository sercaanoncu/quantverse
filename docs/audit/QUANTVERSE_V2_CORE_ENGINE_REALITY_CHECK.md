# QuantVerse v2 Core Engine Reality Check

## Purpose

This audit separates the working QuantVerse v2 public-data research engine from
unsupported institutional claims. The project now treats missing vendor-grade
data as a limitation, not as a reason to stop building a useful research demo.

## What Already Works

- Public-provider current equity candidate universes can be built and validated.
- USD-normalized simple and log return matrices can be generated.
- Stock-level scoring is implemented from coverage, momentum, risk, drawdown and
  diversification diagnostics.
- Expected-return diagnostics are generated across 1M, 3M, 6M and 12M horizons.
- A portfolio model league compares benchmark, risk-allocation, expected-return
  and forecast-aware candidates with explicit model status labels.
- Portfolio risk reports cover return, volatility, Sharpe, Sortino, drawdown,
  VaR, CVaR, stress scenarios and risk contributions.
- Current-universe walk-forward validation runs chronologically and states that
  it is not a point-in-time institutional backtest.
- PDF, HTML and Excel outputs are generated from the actual v2 engine outputs.

## What Is Weak Or Unsupported

- Official exact top-100 membership is not supported by independent exchange or
  vendor evidence.
- Point-in-time historical constituent membership is unavailable.
- Delisting and institutional corporate-action reconciliation are unavailable.
- Black-Litterman can be shown only as public-data diagnostic research unless
  dated market-cap priors and documented views are available.
- Forecast models remain diagnostic unless walk-forward validation proves that
  they improve net portfolio decisions after risk, turnover and costs.
- Very high performance point estimates must be treated as red flags until they
  survive source, FX, outlier and robustness review.

## What Is Actual Reusable Code

- `src/project/research/global_stock_scoring.py`
- `src/project/research/global_return_forecasting.py`
- `src/project/research/global_portfolio_league.py`
- `src/project/research/global_portfolio_risk.py`
- `src/project/research/global_walk_forward.py`
- `scripts/run_quantverse_v2_demo.py`
- `scripts/build_quantverse_v2_research_report.py`
- `scripts/build_quantverse_v2_excel_output.py`

## What Is Documentation Or Governance

- Methodology mapping, thesis material, product contract and showcase files
  explain the engine and its boundaries.
- These documents do not replace source data, point-in-time evidence, FX audit
  trails or validation outputs.

## What Blocks Stronger CV/GitHub Credibility

- The README must make the working v2 engine easy to understand quickly.
- Reports must show selected stocks, final weights and model statuses before raw
  tables.
- Claim language must avoid unsupported exact-top-100, live-trading, advice or
  future-performance wording.
- Tests must cover scoring, forecasting, risk, model league, walk-forward and
  claim guards.

## Fixed In This Sprint

- Working v2 scoring, forecasting, model league, risk and walk-forward modules.
- One-command v2 demo orchestration.
- v2 PDF, HTML and Excel outputs built from engine artifacts.
- Full thesis and defense deck generation hooks.
- Showcase package for GitHub, CV, LinkedIn and bank-interview use.
- Deterministic unit tests for core v2 contracts and claim language.

## Future Institutional Data Work

- Official dated top-100 sources.
- Point-in-time constituent databases.
- Delisting and corporate-action reconciliation.
- Vendor-grade price, FX and market-cap history.
- Model approval workflow, monitoring, access control and execution stack.
