# QuantVerse v2 GitHub Showcase

QuantVerse v2 is a Python-based public-data global equity selection and
portfolio research platform with USD FX normalization, stock scoring,
return-forecasting diagnostics, a portfolio optimization league, risk
diagnostics, walk-forward validation, scientific audit gates and PDF/Excel
outputs.

## What To Show First

1. Run `python scripts/run_quantverse_v2_demo.py --config configs/global_quant_research.yaml`.
2. Open `data/processed/quantverse_v2_demo_summary.json`.
3. Review `data/processed/global_portfolio_league.csv`.
4. Review `data/processed/global_portfolio_league_weights.csv`.
5. Open `output/pdf/quantverse_v2_research_report.pdf`.
6. Open `output/excel/quantverse_v2_research_output.xlsx`.

## Why The Project Is Credible

- It uses explicit source, FX and market-cap evidence gates.
- It refuses unsupported exact-top-100 and point-in-time claims.
- It compares candidates with Equal Weight and random portfolios.
- It exposes model status labels instead of hiding blocked or diagnostic models.
- It separates public-data research evidence from stronger institutional claims.

## Current Boundary

The current engine is a public-data research system. It does not provide
personalized financial recommendations, live execution, tax handling, official
point-in-time constituent history or institutional model approval.
