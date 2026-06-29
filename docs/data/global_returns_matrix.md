# Global Returns Matrix

The global returns matrix builder combines the current equity universe with
crypto, commodity/real-asset and defensive proxy universes, then converts
adjusted-close prices into return matrices.

Tests use local synthetic CSVs. Live yfinance fetching is optional and is not a
required CI dependency. Assets are not silently dropped: insufficient price
coverage is written to `global_returns_coverage_report.csv`.

The base currency defaults to USD. Full FX normalization is not implemented in
this sprint; non-USD assets are explicitly flagged in
`global_fx_normalization_report.csv`.
