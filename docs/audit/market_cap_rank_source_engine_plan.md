# Market-Cap/Rank Source Engine Plan

## Current Exact Top-100 Blocker

QuantVerse cannot claim that a global equity sleeve is an exact top-100
market-cap-ranked universe unless every row has auditable market-cap, rank,
source, provider, source URL, rank universe and as-of-date evidence. Current
index-constituent or proxy rows may be useful research inputs, but they are not
point-in-time historical constituents and they are not automatically exact
market-cap top-100 evidence.

Required message when evidence is incomplete:

`Exact top-100 market-cap claim is not supported for these sleeves.`

Turkish reporting text:

`Bu sleeve exact top-100 olarak tanitilamaz; cunku market-cap/rank kaniti, kaynak URL/provider veya as-of date eksiktir.`

## Sleeve Status Logic

- `exact_market_cap_rank`: all required fields are present and internally valid.
- `index_proxy`: index or ETF/proxy constituent evidence only; not exact top-100.
- `manual_review_required`: the row needs human source review before promotion.
- `api_market_cap_enriched`: market-cap/rank came from a documented API source.
- `missing_market_cap_rank`: cap or rank is missing or non-positive.
- `invalid_source`: source name, provider, URL, rank universe, venue or date is missing.
- `stale_source`: as-of date is too old for a current universe claim.
- `duplicate_rank`: duplicate rank inside the same sleeve, as-of date and rank universe.
- `currency_missing`: market-cap currency cannot be audited.

## Evidence Required For Exact Top-100

Each evidence row must carry:

- `ticker`
- `name`
- `sleeve`
- `region`
- `country`
- `exchange`
- `currency`
- `asset_type`
- `market_cap_native`
- `market_cap_usd`
- `market_cap_rank`
- `rank_universe`
- `rank_method`
- `source_name`
- `source_url`
- `source_provider`
- `as_of_date`
- `retrieved_at`
- `source_method`
- `exact_proxy_status`
- `evidence_status`
- `notes`

Exact status is blocked if rank, market cap, source URL, source provider/name,
as-of date, rank universe, region, country, exchange or currency is missing.
Duplicate ranks inside the same sleeve/as-of/rank universe are also blockers.
Index-proxy rows cannot be upgraded to exact status without independent evidence.

## Black-Litterman Prerequisite

Black-Litterman requires defensible market-cap priors. A positive
`market_cap_usd` value is not enough by itself. QuantVerse now requires valid
market-cap/rank/source/as-of evidence before Black-Litterman can be used as
allocation evidence. Otherwise it remains `blocked_by_data`.

## Generated Evidence Outputs

The validator writes generated outputs under `data/processed/`:

- `global_market_cap_rank_evidence_report.csv`
- `global_exact_proxy_classification_report.csv`
- `global_market_cap_rank_blockers.csv`
- `global_black_litterman_prerequisite_report.csv`

These files are generated evidence artifacts and must not be committed unless a
future task explicitly requests it.

## Sprint 2B Scope

Sprint 2B may attempt source population from existing local sourced CSVs or
configured public data already used by the project. If sources are missing,
incomplete, access-restricted, current-only, or not official enough, the correct
result is a documented blocker, not fabricated ranks or market caps.

## Sprint 2B Source-Coverage Result

Current local source coverage is insufficient for exact equity top-100 support.
The configured source candidate files are missing and only `.example.csv` schema
templates are present. Therefore the correct state is:

- NASDAQ / NYSE / broader US: `source_unavailable` until sourced CSVs exist.
- Europe / Germany / broader Europe: `source_unavailable` until sourced CSVs exist.
- UK: `source_unavailable` until sourced CSVs exist.
- BIST / Turkey: `source_unavailable` until sourced CSVs exist.
- Japan: `source_unavailable` until sourced CSVs exist.
- China/HK: `source_unavailable` until sourced CSVs exist.
- Crypto top 100: may be `api_market_cap_enriched` only when generated
  CoinGecko-style market-cap/rank evidence is present; it cannot support equity
  market-cap priors.
- Commodities and defensive assets: proxy sleeves, not exact top-100 equity
  evidence.

The global master portfolio must remain `insufficient_inputs` or `not promoted`
until sourced equity files exist and pass the evidence gate.
