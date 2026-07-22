# QuantVerse Sample Outputs

Last verified data date: 2026-07-17.

Values are public-data research estimates. A future rerun can change them as
provider data, the current universe, or the as-of date changes.

## QuantVerse v2 Global Equity Research

- Run ID: `qv2-2026-07-17-259efc27e54d3d25`.
- Universe rows: 890.
- Assets with returns: 100.
- Standard-history eligible assets: 99.
- Short-history diagnostics: 1 (`SPCX`).
- Selected stocks: 40.
- Final public-data research model: Equal Weight.
- Final holdings: 40 at 2.5% each.
- Weight sum: 1.0.
- Institutional/global-master promotion: `not_promoted`.

### Current Evidence

- Full-sample arithmetic annual return: 69.48%.
- Full-sample CAGR: 94.56%.
- Full-sample volatility: 23.90%.
- Full-sample Sharpe: 2.9072.
- Full-sample max drawdown: -20.45%.
- Full-sample daily CVaR 95: -3.17%.
- Walk-forward folds: 12.
- OOS observations: 252.
- OOS Equal Weight Sharpe: 2.5936.
- OOS Inverse Volatility Sharpe: 2.6706.

The annual return and CAGR are short-sample warning flags. Inverse Volatility
does not replace Equal Weight because its paired Sharpe-difference confidence
interval crosses zero and robustness is diagnostic only.

## Legacy ETF/Multi-Asset Pipeline

- Date range: 2017-11-10 to 2026-07-17.
- Return matrix: 2,266 daily rows x 37 investable instruments.
- Risk-free proxy: `^IRX`, 3.7763% annual on 2026-07-17.
- Equal Weight walk-forward Sharpe: about 0.79.
- Asset-Class Momentum Rotation is the annual-return challenger winner.
- It does not replace Equal Weight as broad champion because Sharpe uncertainty,
  subperiod consistency, drawdown, and universe-sensitivity evidence are not
  strong enough.
- ML downside-risk remains diagnostic.

This is a different universe and evidence layer from the v2 global equity
research path.

## Main Artifacts

| Path | Contents |
|---|---|
| `data/processed/quantverse_v2_demo_summary.json` | v2 scope, model, metrics, limitations, run identity |
| `data/processed/global_final_model_decision.json` | final evidence gate and model decision |
| `data/processed/global_portfolio_league_weights.csv` | full model/ticker weights |
| `data/processed/global_walk_forward_model_comparison.csv` | comparable OOS model metrics |
| `data/processed/global_walk_forward_uncertainty.csv` | paired block-bootstrap uncertainty |
| `data/processed/global_scientific_sanity_issues.csv` | scoped red flags and promotion blockers |
| `output/pdf/quantverse_v2_research_report.pdf` | v2 research report |
| `output/html/quantverse_v2_research_report.html` | v2 HTML report |
| `output/excel/quantverse_v2_research_output.xlsx` | v2 research workbook |
| `output/pdf/quantverse_visual_scientific_audit_report.pdf` | chart-led scientific audit |
| `output/excel/quantverse_explainable_global_stock_output.xlsx` | explainable workbook and full weights |

## Correct Reading

Read data quality, run identity, model status, full weights, walk-forward
evidence, uncertainty, downside risk, costs, robustness, and blockers before
reading return point estimates. None of these artifacts is investment advice
or proof of future outperformance.
