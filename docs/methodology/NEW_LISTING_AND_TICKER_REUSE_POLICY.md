# New Listing And Ticker-Reuse Policy

## Purpose

This policy prevents a ticker string, current constituent list or short price
series from being treated as sufficient proof of security identity or comparable
history. It applies before stock scoring, forecasting, covariance estimation,
walk-forward validation and portfolio construction.

## Allowed Eligibility Statuses

Every security-history eligibility decision must use one of:

- `eligible`
- `diagnostic_short_history`
- `blocked_identity_uncertain`
- `blocked_ticker_reuse_contamination`
- `blocked_insufficient_history`
- `manual_review_required`

These are research eligibility states, not buy/sell recommendations.

## Identity Evidence Hierarchy

1. official exchange notice;
2. SEC or other regulatory filing;
3. issuer investor-relations evidence;
4. stable security identifiers;
5. public-provider metadata as secondary evidence.

A ticker is never a permanent identifier. CUSIP, ISIN, CIK or another identifier
is recorded only when supported; otherwise the value is `unavailable`.

## IPO And Direct Listing

An IPO or direct listing begins at its verified first valid trading date. Earlier
observations under the same symbol are excluded unless same-security continuity
is explicitly proven.

The security remains visible as `diagnostic_short_history` until it has the full
history needed by the standard feature set. It may not receive a 12-month label
from fewer than 252 valid daily returns.

## Relisting And Ticker Reuse

Known ticker reuse by an unrelated security creates a hard identity boundary.
Pre-boundary observations must be removed. If the boundary or issuer identity
cannot be verified, the status is `blocked_identity_uncertain` or
`manual_review_required`. If unrelated observations remain, the status is
`blocked_ticker_reuse_contamination`.

## Rename, Merger And Successor Continuity

A simple name or ticker change does not require truncation when official evidence
shows the same legal security continues. A merger, reorganization or successor
security may preserve economic history only through an explicit mapping that
documents:

- predecessor and successor identifiers;
- effective date;
- exchange treatment;
- conversion ratio or corporate-action terms where relevant;
- whether adjusted-price continuity is economically valid.

Without that evidence, histories are not spliced.

## ADR And Listing Changes

An ADR, ordinary share and local listing are distinct securities unless the
analysis explicitly models their conversion and currency relationship. A change
of ADR ratio, depositary, exchange or listing currency requires manual review of
adjusted prices and identity continuity.

## Point-In-Time Inclusion

Current-universe membership cannot be projected backward as historical
eligibility. Walk-forward selection must use only securities and metadata known
at each fold date. Current public-provider universe tests remain labelled
current-universe research until dated constituent and delisting evidence exists.

## Feature-History Eligibility

| Feature or stage | Minimum requirement |
| --- | --- |
| 1M momentum | 21 valid returns |
| 3M momentum / 3M volatility / diversification | 63 valid returns |
| 6M momentum | 126 valid returns |
| 12M momentum / 12M volatility / Sharpe-like / Sortino-like | 252 valid returns |
| Standard composite score | 252 valid returns plus identity eligibility |
| Standard forecast input | 252 valid returns plus standard selection |
| Standard covariance / portfolio input | Current-run standard-history-eligible universe |
| Walk-forward selection | 252 valid training returns inside each fold |

Ineligible feature values are missing, not shortened substitutes.

## Stage Decisions

- **Standard-score eligibility:** `eligible` only when all common 12-month
  requirements and identity checks pass.
- **Forecast eligibility:** standard-selected and at least 252 valid returns.
- **Covariance eligibility:** use the same current-run standard-history-eligible
  universe so score, portfolio-league, global-master and random-benchmark stages
  cannot admit a short-history diagnostic.
- **Walk-forward eligibility:** recompute eligibility inside each chronological
  training fold; future observations cannot repair a past fold.
- **Diagnostic visibility:** short-history rows remain visible with explicit
  reason and may not be mixed into the standard rank.

## Validation And Invalidation

The policy is validated by:

- `global_security_identity_audit.csv`;
- `global_security_history_eligibility.csv`;
- `global_feature_history_eligibility.csv`;
- `global_cross_artifact_count_reconciliation.csv`;
- the v2 artifact validator;
- deterministic synthetic ticker-reuse and short-history tests.

Results are invalidated when:

- known reuse lacks verified continuity;
- current-security returns precede the verified listing boundary;
- a 12-month feature is populated with fewer than 252 observations;
- a short-history row is selected by the standard rank;
- forecasts or portfolio inputs contain an ineligible ticker;
- current report artifacts mix run identifiers.

## Methodology Basis And Limit

The policy operationalizes sample-size, estimation-error, chronological
validation, leakage and survivorship-bias principles from the eight local
methodology books. Security-specific facts must still come from primary
exchange/regulatory evidence. Public-provider metadata is not institutional
security-master proof.
