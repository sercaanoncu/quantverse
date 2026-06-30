# Current Sprint Problem Diagnosis

## What the user is dissatisfied with

The existing global stock outputs prove that a real current research universe
can be built, but the outputs are still too difficult to understand. The prior
PDF and presentation rely heavily on raw tables, show `Unnamed: 0` columns, use
decimal returns without plain-language interpretation, and bury the most
important blockers behind dense CSV-style text.

## What confused the user

- Which assets are actually in the final candidate.
- Whether the universe is exact top-100 by market cap or merely an index proxy.
- Why a portfolio candidate exists but is still `not promoted`.
- Why some metrics look extreme, especially annual returns, volatility, Sortino
  and total return.
- Whether model names like Black-Litterman, HRP, Risk Parity, ARIMA or GARCH
  were actually run or only listed as unavailable.

## Trustworthy outputs

- Source universe rows are auditable through `data/universe/sources/*.csv`.
- The current global universe has nonzero real stock/proxy rows.
- Full candidate weights are traceable to
  `data/processed/global_master_candidate_weights.csv`.
- Weight sums and hard constraints are auditable through
  `global_master_constraint_audit.csv`.
- FX limitations are explicit in `global_fx_normalization_report.csv`.
- The final global USD master decision remains `not promoted`.

## Outputs not yet fully trustworthy

- Exact top-100 market-cap claims are not supported for most equity sleeves.
- Current constituents are not point-in-time historical constituents.
- Global returns are mixed local-currency returns where FX conversion is not
  implemented.
- Suspicious return and risk metrics require visible warnings.
- Forecast metrics are diagnostic only and do not justify allocation promotion.

## Data-quality blockers

Market-cap and market-cap-rank coverage is missing for most equity proxy rows.
Some price series fail coverage checks. Public yfinance data is useful for
research, but not institutional-grade reconciliation.

## FX blocker

The global portfolio contains non-USD listings. Until local returns are
converted into the USD base currency with appropriate FX series and calendar
alignment, a global USD master portfolio cannot be promoted.

## Market-cap blocker

Crypto rows have market-cap evidence, but most equity sleeves are index proxies
without sourced market cap or rank fields. This blocks exact top-100-by-market-
cap claims and blocks Black-Litterman market-cap priors.

## Point-in-time blocker

Current index constituents cannot be used as historical point-in-time membership
evidence. Historical security-selection claims require dated constituent files,
market caps, delistings and corporate-action reconciliation.

## Scientific correctness for this project

Scientific correctness means that each claim is tied to sourced data, correct
units, appropriate model assumptions, transparent validation metrics, no
look-ahead or survivorship overclaim, audited weights and an honest promotion
gate.

## What this sprint fixes

This sprint adds source/methodology inventory, requirement traceability, a
failure-mode taxonomy, scientific sanity checks, red-flag dashboards, chart-led
Turkish PDF/presentation outputs and an explainable Excel workbook.

## What this sprint does not pretend to fix

This sprint does not create exact market-cap-ranked equity universes, does not
implement FX normalization, does not add point-in-time historical constituents,
does not fabricate performance and does not promote the global USD master
portfolio.
