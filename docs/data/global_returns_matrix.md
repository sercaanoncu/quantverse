# Global Returns Matrix

The global returns matrix builder combines the current equity universe with
crypto, commodity/real-asset and defensive proxy universes, then converts
adjusted-close prices into return matrices.

Tests use local synthetic CSVs. Live yfinance fetching is optional and is not a
required CI dependency. Assets are not silently dropped: insufficient price
coverage is written to `global_returns_coverage_report.csv`.

The base currency defaults to USD. The builder preserves local simple/log
returns and also writes USD-normalized simple/log returns where configured FX
series are available. Missing FX rates are not fabricated; affected assets are
marked `fx_missing` in `global_fx_normalization_report.csv`, and global USD
promotion remains blocked for selected investable assets with missing FX.
