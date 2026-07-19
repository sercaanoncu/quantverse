# QuantVerse v2 Report Semantic Terminology Audit

## Decision

The semantic repair remains valid, but the latest corrected evidence now
selects **Equal Weight** as the public-data research model. HRP remains an
actually-run defensive candidate. This document does not select either model;
it governs how their holdings and exposures are described.

Institutional/global master promotion remains `not_promoted`. The canonical
report must keep the public-data v2 decision, legacy global-master candidate,
and institutional promotion as separate scopes.

The canonical user-facing selected-stock view is
`data/processed/global_selected_stocks_report_view.csv`. Its join and coverage
evidence is `data/processed/global_selected_stocks_report_view_quality.csv`.
Raw source evidence remains available separately.

## Methodology Basis

The eight local methodology books support a common governance rule: an input
variable must retain its defined statistical and economic meaning throughout a
transformation. Portfolio theory and risk measurement cannot repair a
misclassified exposure after the fact. Financial-statistics and machine-learning
validation likewise require explicit feature definitions, source lineage, and no
silent proxy substitution. This audit applies those principles without copying
book text or inventing unsupported exposure data.

## Terminology Audit

| Location | Current label | Actual meaning | Methodology risk | Correct label | Evidence source | Fix applied | Status |
|---|---|---|---|---|---|---|---|
| PDF first-page selected-stock preview | `country` | Legacy listing-universe country | A foreign issuer may be presented as a United States issuer | `listing_country` plus separate `issuer_country` and `economic_country` | `global_stock_scores.csv`; `global_top_holdings_explanation.csv` | Replaced raw score preview with canonical semantic view | Fixed |
| PDF first-page selected-stock preview | `currency` | Security trading currency | Trading currency may be mistaken for economic currency risk | `listing_currency` | Same as above | Replaced ambiguous header and added interpretation note | Fixed |
| HTML selected-stock preview | Full raw stock-score table | Research scoring evidence with legacy source fields | Wide raw table hides the distinction between listing and issuer | Canonical semantic selected-stock table | `global_selected_stocks_report_view.csv` | HTML now uses the same semantic view as PDF and Excel | Fixed |
| Excel `SELECTED_STOCKS` | Raw filtered `global_stock_scores.csv` | Selected rows from the scoring engine | User-facing sheet could misstate issuer/economic exposure | Curated semantic view | `global_selected_stocks_report_view.csv` | Added explanatory note and semantic columns | Fixed |
| Excel `SELECTED_STOCKS_RAW` | New explicit raw sheet | Unmodified selected scoring evidence | Legacy `country` and `currency` remain ambiguous if treated as conclusions | Raw/legacy source fields only | `global_stock_scores.csv` | Preserved for auditability and labelled raw | Accepted raw evidence |
| Top holdings explanation | `listing_country`, `issuer_country`, `economic_country` | Listing venue, domicile, and supported business-risk geography | No material ambiguity when all three remain separate | No change | `global_top_holdings_explanation.csv` | Used as primary enriched metadata evidence | Passed |
| Exposure tables | Separate listing, issuer, and economic files | Weight grouped by each defined exposure dimension | A legacy alias can be mistaken for issuer/economic exposure | Explicit exposure dimension in filename and report label | `global_listing_country_exposure.csv`; `global_issuer_country_exposure.csv`; `global_economic_country_exposure.csv` | Explicit tables retained; legacy aliases documented | Passed with legacy alias warning |
| Dashboard exposure wording | `currency` in legacy chart-ready source | Listing/trading currency grouped from final holdings | May be mistaken for revenue or economic currency risk | `listing_currency` in report-facing wording | `quantverse_v2_visual_exposure.csv`; `global_currency_exposure.csv` | Report text documents trading-currency limitation | Passed with terminology note |
| Appendix/raw tables | `country`, `currency`, `region` | Provider/source classification fields | Unsafe if promoted as issuer or economic interpretation | Keep only as explicitly raw/legacy evidence | Raw universe and score artifacts | Not overwritten; separated from curated output | Accepted raw evidence |

## Scientific Review Answers

1. Listing country is not a valid proxy for issuer domicile. A security may be
   listed in the United States while its issuer is domiciled in Switzerland,
   Canada, the United Kingdom, Japan, Taiwan, or another jurisdiction.
2. Issuer domicile is not a valid proxy for economic business exposure. Revenue,
   assets, suppliers, customers, and operating risks can span many countries.
3. Trading currency is not necessarily economic currency risk. A USD-traded ADR
   can retain material non-USD business and cash-flow exposure.
4. Issuer-country coverage can equal 1.0 while economic-country coverage equals
   0.0 because the two variables answer different questions and use different
   evidence requirements.
5. `passed_with_metadata_warning` is appropriate for the current reporting use
   only because listing country, issuer country, sector, and industry are complete,
   while economic-country exposure is shown as unavailable and is explicitly not
   inferred. It would be inappropriate if the report used issuer domicile or
   listing venue as economic exposure.
6. After this repair, PDF, HTML, and Excel present the same semantic selected-stock
   view. Foreign issuers such as UBS and TSM retain distinct listing and issuer
   countries, and unavailable economic exposure is visible rather than imputed.

## Validation And Invalidation

The semantic view is valid when normalized ticker joins are one-to-one, the
selected row count is unchanged, duplicate tickers are absent, metadata coverage
is reported, and unsupported economic country values remain `unavailable`.

The view is invalid if a join duplicates or drops a selected row, if `country` is
shown without a listing/issuer/economic qualifier in a report-facing selected
stock table, or if listing country, issuer domicile, trading currency, or economic
exposure is substituted for another concept.
