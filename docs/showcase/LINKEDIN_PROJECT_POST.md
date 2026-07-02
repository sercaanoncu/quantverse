# LinkedIn Project Post Draft

I built QuantVerse v2, a Python public-data quantitative equity research
platform.

The system builds a sourced current equity universe, computes USD-normalized
returns, scores stocks, estimates diagnostic expected returns, compares a
portfolio model league, runs risk analytics, performs current-universe
walk-forward validation and generates PDF/Excel outputs.

The important part is not only the models. The project also includes claim
guards: it separates public-data research from stronger institutional evidence,
keeps Equal Weight and random portfolios as benchmarks, labels Black-Litterman
and ML forecasts carefully, and refuses unsupported exact-top-100 or
point-in-time claims.

Core stack: Python, pandas, NumPy, SciPy, scikit-learn, reportlab, xlsxwriter,
pytest, black and ruff.

This is a research and analytics project, not personal financial advice.
