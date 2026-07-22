# Canonical Working Portfolio Protocol

## Scope And Decision Surface

The active QuantVerse analysis is **US-listed global-issuer equity research**.
The label reflects the usable return, listing and currency evidence; it does not
claim broad global-exchange or institutional point-in-time coverage.

The output has three distinct roles:

1. `balanced_research_portfolio`: the allocation selected by corrected stitched
   OOS evidence.
2. `transparent_benchmark`: Equal Weight over the same selected issuers.
3. `defensive_alternative`: the valid positive-return model with the strongest
   OOS max-drawdown and historical CVaR profile.

These are research allocations, not personal investment advice or live-trading
approval.

## Canonical Specification

- Target holdings: 20 unique economic issuers.
- Diagnostic history eligibility: at least 252 daily returns.
- Final eligibility: at least 504 daily returns.
- Share-class rule: one representative security per economic issuer.
- Long-only and fully invested: weights are non-negative and sum to one.
- Selection caps: sector 25%, industry 15%, issuer country 60% where feasible.
- Active allocation cap: 10% per issuer, with 0.5% minimum holding weight.
- Primary transaction cost: 10 bps; sensitivity at 5 and 25 bps.
- Walk-forward: 504 train days, 21 test days, 21-day step, all valid folds.
- Primary risk-free source: time-aligned `^IRX`; daily hurdle is
  `(1 + annual_rf) ** (1 / 252) - 1` with bounded past-only filling.

Exactly 20 holdings under a 5% maximum issuer weight has only one feasible
solution: every holding must equal 5%. The requested 5% policy is therefore
reported as model-degenerate. A disclosed 10% operational cap is required to
compare active risk allocations without relabeling Equal Weight as another
model.

## Selection And Construction

History and data-quality eligibility are applied before ranking. Economic issuer
deduplication is applied before final selection. Where multiple valid securities
represent one issuer, the representative is chosen by verified listing evidence,
then reliable dollar volume, continuous history, missing-data rate and finally a
deterministic ticker tie-break.

The score uses only existing transparent components: momentum, volatility,
downside risk, drawdown and correlation diversification contribution. Sector,
industry and issuer-country constraints are enforced during final selection.
Every selected and near-rejected security receives an explicit reason.

Primary model comparison is limited to Equal Weight, Inverse Volatility, HRP,
Risk Parity, GMV and Min CVaR. Max Sharpe and Black-Litterman remain diagnostic
unless their expected-return or prior requirements are satisfied. Optimizers may
not silently substitute a fallback model.

## OOS Evidence And Metrics

Every fold independently recomputes eligibility, issuer representation, scores,
selected securities, covariance, weights and costs using only information known
at the decision date. Every primary model uses identical test dates. Fold net
returns are concatenated once into one stitched daily OOS series; CAGR, Sharpe,
Sortino, drawdown, VaR and CVaR are calculated from that series rather than by
averaging fold metrics.

Simple returns are used for portfolio aggregation. Annualized arithmetic return
is `252 * mean(r)`, CAGR is `prod(1+r) ** (252/n) - 1`, volatility is sample
standard deviation times `sqrt(252)`, drawdown is wealth divided by its running
maximum minus one, and historical CVaR is the mean return below the empirical 5%
VaR threshold. Missing weighted returns are never replaced with zero.

An active model can replace Equal Weight as balanced only when the lower bound of
its paired circular block-bootstrap Sharpe difference is above zero and its
drawdown, CVaR, turnover, cost, constraint and provenance gates also pass.
Otherwise Equal Weight remains balanced. Full-sample metrics are diagnostic and
cannot select the final model.

## Invalidation Conditions

Rebuild and revalidate whenever the universe, issuer mapping, metadata, adjusted
price history, risk-free source, cost assumption, selected issuers, model code or
as-of date changes. The evidence does not resolve current-universe survivorship,
historical point-in-time membership, complete delisting/corporate-action
reconciliation, market impact, taxes, execution capacity or live monitoring.
