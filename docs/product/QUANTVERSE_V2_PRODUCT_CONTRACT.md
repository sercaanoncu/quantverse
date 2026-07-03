# QuantVerse v2 Product Contract

## Product Definition

QuantVerse v2 is a public-data quantitative equity research platform that builds
a sourced current equity universe, computes USD-normalized returns, scores and
selects stocks, estimates expected returns, builds multiple portfolio
allocations, runs risk diagnostics, performs walk-forward validation where
feasible, compares against Equal Weight and random portfolios, and generates
explainable outputs.

It is not investment advice, a live trading system, or an institutional
point-in-time backtest.

## Required User Tasks

1. Stock scoring.
2. Stock selection.
3. Expected-return forecasting.
4. Portfolio allocation.
5. Portfolio risk analysis.
6. Portfolio expected-return analysis.
7. Backtest or walk-forward validation.
8. Model league comparison.
9. Explainable PDF, Excel and README outputs.
10. CV/GitHub showcase outputs.

## Required Model League

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

## Model Status Contract

Every model must carry one explicit `actual_status` value:

- `actually_run`
- `benchmark_only`
- `diagnostic_only`
- `blocked_by_data`
- `blocked_by_implementation`
- `future_candidate`

Diagnostic models may support research interpretation. They must not be
presented as promotion-grade allocation evidence.

## Promotion And Claim Contract

- Equal Weight and random portfolios remain hard benchmarks.
- A portfolio candidate must pass constraint, drawdown, CVaR, cost, benchmark
  and robustness checks before stronger claims are allowed.
- Official exact top-100 market-cap support is unavailable unless a dated source
  file proves it.
- Current-universe walk-forward validation must be labeled as public-data
  research, not point-in-time institutional evidence.
- Black-Litterman requires valid priors and views before it can be stronger than
  diagnostic research.

## Output Contract

- Stock scores: `data/processed/global_stock_scores.csv`
- Return forecasts: `data/processed/global_stock_return_forecasts.csv`
- Model league: `data/processed/global_portfolio_league.csv`
- Model weights: `data/processed/global_portfolio_league_weights.csv`
- Risk report: `data/processed/global_portfolio_risk_report.csv`
- Walk-forward summary: `data/processed/global_walk_forward_summary.json`
- Demo summary: `data/processed/quantverse_v2_demo_summary.json`
- PDF report: `output/pdf/quantverse_v2_research_report.pdf`
- Excel output: `output/excel/quantverse_v2_research_output.xlsx`
