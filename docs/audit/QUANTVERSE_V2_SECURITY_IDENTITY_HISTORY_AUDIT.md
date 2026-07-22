# QuantVerse v2 Security Identity And History Audit

## Decision

QuantVerse must not infer security continuity from a ticker string. The current
pipeline therefore treats security identity, listing history and feature-history
sufficiency as explicit upstream eligibility gates. A security can remain visible
for research while being excluded from standard scoring, forecasting, covariance,
walk-forward and portfolio construction.

The documented SPCX conflict is resolved for the current run by a primary-source
listing boundary. No pre-listing observations were observed in the downloaded
current-security series. SPCX is nevertheless excluded from the standard 12-month
ranking because only 25 valid daily returns are available as of 2026-07-21. This
is an eligibility decision, not an investment opinion. The current evidence is
identified by run `qv2-2026-07-21-4453b1fd66455d43`.

## SPCX Forensic Record

| Field | Value | Evidence source | Confidence | Decision implication |
| --- | --- | --- | --- | --- |
| ticker | SPCX | Nasdaq Data Technical News 2026-8 | High | The symbol is a routing label and must be linked to the current security boundary. |
| current_security_name | Space Exploration Technologies Corp. Class A Common Stock | Nasdaq Data Technical News 2026-8; SEC issuer filing | High | Current price and return observations may represent this security only. |
| issuer | Space Exploration Technologies Corp. | SEC filing, CIK 0001181412 | High | Issuer identity is distinct from the prior ETF that used SPCX. |
| current_listing_start_date | 2026-06-12 | Nasdaq Data Technical News 2026-8; SEC filing | High | Earlier unrelated SPCX observations cannot be used. |
| exchange | Nasdaq Global Select Market and Nasdaq Texas | Nasdaq Data Technical News 2026-8 | High | Listing venue is source-verified. |
| stable_identifier | CUSIP 84615Q103 | Nasdaq Data Technical News 2026-8 | High | The current security is not identified by ticker alone. |
| observed_price_history_start_date | 2026-06-12 | `data/processed/global_security_identity_audit.csv` | High for current generated data | The observed provider series begins on the verified listing date. |
| observed_return_history_start_date | 2026-06-15 | `data/processed/global_security_identity_audit.csv` | High for current generated data | Return history starts after the first valid price pair and exchange-calendar alignment. |
| observations_before_current_listing | 0 | `data/processed/global_security_identity_audit.csv` | High for current generated data | No pre-listing contamination was observed in this run. |
| prior_symbol_reuse_status | Known prior unrelated security: The SPAC and New Issue ETF | Nasdaq notice; SEC ticker-change filing | High | Historical SPCX data must not be linked across the issuer boundary. |
| identity_continuity_status | `verified_current_security_from_listing_date` | Manual override backed by Nasdaq and SEC | High | Continuity begins at 2026-06-12; no predecessor continuity is claimed. |
| standard_scoring_eligible | No | `global_feature_history_eligibility.csv` | High | SPCX cannot enter the common 12-month cross-sectional score. |
| walk_forward_eligible | No until the configured common-history requirement is met | `global_security_history_eligibility.csv` | High | Current walk-forward folds cannot treat SPCX as seasoned history. |
| action_required | Retain as `diagnostic_short_history`; exclude from standard selection, forecasts and portfolio inputs | New-listing policy and generated eligibility artifacts | High | The security remains visible without silently promoting incomparable features. |

Primary evidence:

- Nasdaq: <https://m.nasdaqtrader.com/TraderNews.aspx?id=DTN2026-8>
- SEC current issuer evidence:
  <https://www.sec.gov/Archives/edgar/data/1181412/000162828026042466/spaceexplorationtechnologi.htm>
- SEC prior ETF ticker change:
  <https://www.sec.gov/Archives/edgar/data/1719812/000199937126007611/cist-497_040226.htm>

Nasdaq explicitly warns that SPCX was previously used for a different security
and that old market data must not be linked to the new security. The SEC prior-ETF
filing records the change from SPCX to SPCK effective 2026-04-07.

## General Security-Master Repair

The current universe contains overlapping documentation rows for some ticker
symbols. Before repair, downstream code used the first row returned by
`drop_duplicates("ticker")`. For symbols such as NVDA and AAPL, an excluded index
proxy row appeared before the included market-cap-enriched row. This caused valid
long-history securities to be classified as non-investable during USD
normalization.

The canonical resolution rule now prioritizes, in order:

1. included and investable rows;
2. included rows;
3. stronger source methods;
4. later as-of dates;
5. stable original row order as a deterministic tie-break.

This rule is shared by returns, scoring, portfolio metadata, exposure metadata and
report metadata. It does not assert that duplicate rows are duplicate securities;
it selects the one row that governs the current investable security while
preserving the source universe unchanged.

## History Boundary Method

For a verified current-security listing boundary:

```text
effective_history_start =
    max(provider_history_start, current_listing_start_date, first_valid_price_date)
```

Observations before that boundary are removed unless a documented status proves
same-security or predecessor continuity. Splits and dividends are corporate-action
adjustments and do not by themselves establish or break legal-security continuity.

## Feature-History Method

QuantVerse uses trading-day observation requirements:

| Feature | Minimum valid returns |
| --- | ---: |
| 1-month momentum | 21 |
| 3-month momentum and volatility | 63 |
| 6-month momentum | 126 |
| 12-month momentum and volatility | 252 |
| Sharpe-like and Sortino-like standard components | 252 |
| Standard composite score | 252 and identity eligibility |

A shorter available sample is not relabelled as a longer horizon. Ineligible
components are `NaN`, and the security is labelled
`diagnostic_short_history`. It remains visible but cannot enter the standard
ranking.

## Portfolio-Input Enforcement

The history contract is enforced at both portfolio surfaces:

- the v2 equity portfolio league uses only standard-selected securities;
- the legacy global master allocator filters its returns, covariance,
  correlation, candidate-weight and random-portfolio inputs through
  `global_feature_history_eligibility.csv`.

The master allocator also requires the eligibility artifact's `run_id` to match
the active run manifest. A missing, invalid or stale eligibility artifact causes
a fail-safe `not promoted` result instead of a portfolio calculation. In the
current rebuilt evidence, SPCX is the only returned equity labelled
`diagnostic_short_history`; it is absent from master selected assets, candidate
weights, the 10,000 random portfolios and the covariance/correlation universe.

## Cross-Artifact Contract

The following generated artifacts must share one `run_id`, `data_as_of_date`,
`generated_at` and `universe_snapshot_id`:

- security identity audit;
- feature-history eligibility;
- stock scores;
- return forecasts;
- portfolio league weights;
- walk-forward window summary.

`global_cross_artifact_count_reconciliation.csv` separately reconciles scored,
selected, semantic-report, forecast, candidate, final-holding and latest
walk-forward counts. A same-run unexplained mismatch fails validation.

## Methodology Basis

All eight local methodology books were inspected through the existing source
inventory. Their relevant project rules are:

- *Portfolio Optimization*: estimation error, covariance dependence, robust
  constraints and the need for comparable samples.
- *Introduction to Statistical Methods for Financial Models* and *Statistical
  Quantitative Methods in Finance*: sample-size discipline, return construction,
  volatility estimation and uncertainty.
- *Machine Learning for Algorithmic Trading* and *Machine Learning in Finance*:
  point-in-time data, survivorship bias, leakage prevention and chronological
  validation.
- *An Introduction to Statistical Learning*: training/test separation and
  feature comparability.
- *Machine Learning for Economics and Finance in TensorFlow 2* and *Quantitative
  Economics with Python*: time ordering, simulation discipline and
  out-of-sample interpretation.

These sources support the observation-sufficiency and no-look-ahead rules. The
SPCX issuer, listing and symbol-reuse facts come from Nasdaq and SEC primary
evidence, not from the books.

## Remaining Limitations

- The manual override file covers documented conflicts, not every possible
  historical ticker reuse in the global universe.
- Most securities remain `no_known_conflict_provider_only`; this means no known
  conflict was detected, not that institutional security-master reconciliation
  was completed.
- Historical point-in-time constituents, delistings and full corporate-action
  reference data remain unavailable.
- CUSIP and exchange evidence are not fabricated when unavailable; missing stable
  identifiers are recorded as `unavailable`.

Institutional/global master promotion remains `not_promoted`.
