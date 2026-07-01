# Sourced Equity Population Report

Run date: 2026-07-02

## Summary

The six required current equity candidate CSV files were populated under
`data/universe/sources/` using Yahoo Finance screener output accessed through
`yfinance`. This is a public finance data provider, not an official exchange
or index-provider top-100 certificate.

The files are valid current research inputs. They are not point-in-time
historical constituents and they do not support official exact top-100
market-cap claims.

## Files Created

| File | Rows | Provider | Source URL pattern | As-of date | Status |
|---|---:|---|---|---|---|
| `data/universe/sources/us_candidates.csv` | 100 | Yahoo Finance via yfinance | `https://finance.yahoo.com/quote/{ticker}` | 2026-07-02 | API market-cap enriched current candidates. |
| `data/universe/sources/europe_candidates.csv` | 100 | Yahoo Finance via yfinance | `https://finance.yahoo.com/quote/{ticker}` | 2026-07-02 | API market-cap enriched current candidates; cross-listing/domicile review required. |
| `data/universe/sources/uk_candidates.csv` | 100 | Yahoo Finance via yfinance | `https://finance.yahoo.com/quote/{ticker}` | 2026-07-02 | API market-cap enriched current LSE-listed candidates; many rows can be foreign London listings. |
| `data/universe/sources/turkey_candidates.csv` | 100 | Yahoo Finance via yfinance | `https://finance.yahoo.com/quote/{ticker}` | 2026-07-02 | API market-cap enriched current Borsa Istanbul candidates; market-cap anomalies require review. |
| `data/universe/sources/china_candidates.csv` | 100 | Yahoo Finance via yfinance | `https://finance.yahoo.com/quote/{ticker}` | 2026-07-02 | API market-cap enriched current China/Hong Kong candidates. |
| `data/universe/sources/japan_candidates.csv` | 100 | Yahoo Finance via yfinance | `https://finance.yahoo.com/quote/{ticker}` | 2026-07-02 | API market-cap enriched current JPX candidates. |

## Sources Checked

| Source | URL | Role | Used for row-level CSV? | Reason |
|---|---|---|---|---|
| Yahoo Finance screener | `https://finance.yahoo.com/screener/new` | Public finance screener with market-cap fields. | Yes | Accessible through yfinance and returned tickers, exchanges, currencies and market caps. |
| Nasdaq stock screener | `https://www.nasdaq.com/market-activity/stocks/screener` | Official public US screener. | No | Useful official reference, but automated row-level global population was not built from it in this sprint. |
| London Stock Exchange market data | `https://www.londonstockexchange.com/market-data/all` | Official UK market reference. | No | Public page is useful for manual verification; row-level automated top-100 market-cap CSV was not used. |
| Borsa Istanbul BIST 100 page | `https://www.borsaistanbul.com/en/index/xu100` | Official index reference. | No | It supports index context but not the generated row-level current candidate CSV. |
| Japan Exchange Group ranking page | `https://www.jpx.co.jp/english/markets/statistics-equities/misc/08.html` | Official market-cap ranking reference. | No | Official downloadable/manual source should be preferred for a future exact JPX top-100 sprint. |

## Validation Results

Command:

```powershell
python scripts/validate_source_universe_inputs.py --config configs/source_universe_validation.yaml
```

Result: `validated`.

Command:

```powershell
python scripts/build_current_global_universe.py --config configs/current_global_universe.yaml
python scripts/validate_real_global_universe.py
```

Result:

- Current global universe rows: 600.
- Source universe missing market-cap rows: 0.
- Exact market-cap-ranked top-100 supported sleeves: 0.
- Exact top-100 support remains unsupported for all six equity sleeves.

## Market-Cap and Rank Coverage

Market caps were sourced from Yahoo Finance screener output and converted to
USD where non-USD currencies were returned. Ranks were computed within the same
Yahoo screener retrieval batch and same-date candidate file.

This supports `api_market_cap_enriched` current research status. It does not
support official exact top-100 status.

## Known Limitations

- Yahoo Finance is not an official exchange or index provider.
- Europe and UK files may contain cross-listed foreign companies.
- Country fields represent the intended sleeve/listing context, not always
  legal domicile.
- Current membership is not point-in-time historical evidence.
- Delisting, corporate-action and full survivorship controls are not present.
- Exact top-100 market-cap claim is not supported for these sleeves.

## Required Next Fix

Replace or reconcile these public-provider candidate files with official or
vendor-grade files containing source URL, provider, as-of date, rank universe,
market cap, market-cap rank, domicile/listing classification and point-in-time
effective dates.
