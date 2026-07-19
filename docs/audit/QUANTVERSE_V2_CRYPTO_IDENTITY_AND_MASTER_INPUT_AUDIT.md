# QuantVerse v2 Crypto Identity And Master Input Audit

## Executive Decision

The legacy global master evidence was contaminated by crypto security-identity
and input-policy defects. The observed extreme CAGR and Sharpe values were not
accepted as portfolio performance. They were invalid research evidence.

Until a provider-specific crosswalk proves that a CoinGecko asset ID maps to the
intended price-provider instrument, CoinGecko crypto rows remain visible as
research metadata but are not investable portfolio inputs. Stablecoin and
stable-value rows are also excluded by a separate conservative eligibility gate.

This repair does not claim that crypto is economically undesirable. It states
that an unverified identifier and price history cannot support a portfolio
decision.

## Findings

| ID | Severity | What was wrong | Why it matters | Evidence | Promotion blocker | Repair |
| --- | --- | --- | --- | --- | --- | --- |
| CRYPTO-ID-001 | P0 | `scripts/populate_real_global_universe.py` converted a CoinGecko symbol to a Yahoo-style ticker by appending `-USD` without a verified cross-provider mapping. | Symbols are not stable cross-provider security identifiers. A collision or reused symbol can attach another asset's history to the current CoinGecko row and invalidate every downstream statistic. | `data/universe/sources/crypto_top100_candidates.csv`: `proxy_type=crypto_yfinance_proxy`; `data/processed/global_security_returns.csv`: `CC-USD` maximum absolute daily return `2348.810765`, `JUP-USD` `686.167312`. | Yes | New CoinGecko rows retain the CoinGecko ID and explicit price-mapping fields. An unverified mapping is `signal_only`, non-investable and excluded from price/return/portfolio inputs. |
| CRYPTO-ID-002 | P1 | `scripts/build_current_global_universe.py` overwrote source `investable`, `include`, `signal_only`, `benchmark_only`, `asset_type` and `proxy_type` values. | A source row deliberately excluded as a stablecoin was reintroduced as an investable equity. The canonical universe no longer represented its source evidence. | Before repair: 93/100 source crypto rows were investable, but 100/100 canonical crypto rows became investable and all 100 were labelled `asset_type=equity`. | Yes | Source flags are preserved, crypto rows are labelled `asset_type=crypto`, missing-cap rows are non-investable, and unverified mappings are fail-safe research metadata only. |
| CRYPTO-ID-003 | P1 | Stable-value detection covered only a short token list and missed rows such as `USDS-USD`, `RLUSD-USD`, `USD1-USD` and other dollar-linked products. | Stable-value exposure can dominate a crypto sleeve while being interpreted as a risk-seeking asset. It also violates the stated stablecoin policy. | `data/universe/sources/crypto_top100_candidates.csv`: these rows were marked `stable_like=False` and investable. | Yes | A shared conservative classifier strips the quote suffix, checks exact stable-value symbols, names and source notes, and is enforced in universe, scoring and portfolio-input gates. |
| MASTER-MISSING-001 | P1 | Missing asset returns were filled with `0.0` in the stock-selection and master research path. | A missing market observation is not a zero economic return. Zero imputation creates implicit cash behavior, changes covariance and volatility, and biases portfolio comparisons. | Former `_clean_returns` and `run_master_portfolio_research` implementations used `.fillna(0.0)`. | Yes | Per-asset diagnostics retain missing values. Multivariate optimizers, random portfolios and master comparisons use an explicit complete-case sample and fail if fewer than two common observations remain. |
| MASTER-OPT-001 | P1 | An infeasible Policy Constrained linear program silently returned Equal Weight and was reported as `computed`. | The reported model was not the model named in the output. This hides constraint infeasibility and makes model comparison false. | Former `_policy_constrained_weights` fallback returned `1/n` when `linprog.success=False`. | Yes | Infeasibility now removes the candidate and records `Status=infeasible_constraints`; it is never relabelled as a computed Policy Constrained portfolio. |
| MASTER-OPT-002 | P1 | Max Sharpe, Min CVaR, legacy Min Variance and v2 GMV could silently substitute inverse-volatility or initialization weights after optimizer failure. | A fallback portfolio does not have the objective represented by the model label; reporting it as the failed model invalidates model comparison. | Former optimizer branches returned another weight vector when `result.success=False`. | Yes | Optimizer failures now raise into the model-status layer and are reported as unavailable/failed rather than computed under a false label. |
| MASTER-CAP-001 | P1 | Cluster Balanced capped each cluster allocation and then normalized the total, which could increase capped positions above `max_weight`. | Normalization after clipping does not preserve an upper bound and creates a hard-constraint breach. | Pre-repair `global_master_constraint_audit.csv`: `Cluster Balanced` failed `max_weight_ok`. | Yes | Raw cluster-balanced weights are projected once onto the long-only capped simplex and independently validated before reporting. |
| MASTER-BL-001 | P1 | A prior-only Black-Litterman run on the selected current subset could be shown as an ordinary computed promotion candidate, while the full-universe prerequisite report remained blocked. | Selected-subset current market caps can support a diagnostic equilibrium prior, but they do not cure unsupported exact-universe, point-in-time or view evidence. Scope ambiguity makes the model look more validated than it is. | `global_master_model_comparison.csv` versus `global_black_litterman_prerequisite_report.csv`. | Yes for promotion; no for diagnostic calculation | The selected-subset calculation is labelled `computed_diagnostic_only`, excluded from promotable-candidate ranking, and optimizer failure no longer falls back silently to market weights. |
| PIPELINE-RUN-001 | P1 | The global orchestrator rebuilt the return matrix and run manifest but did not rebuild stock scores and feature-history eligibility before the master allocator. | The master allocator could see a stale eligibility artifact from another run and stop, while the orchestrator had omitted the dependency needed to make the run internally consistent. | `scripts/run_global_quant_research.py` formerly called returns then master directly; `run_global_master_portfolio.py` requires a matching eligibility `run_id`. | Yes | `build_global_stock_scores.py` now runs after returns and before master; a deterministic order test locks the dependency. |

## Before-Repair Forensic Evidence

The pre-repair generated snapshot contained:

- 100 CoinGecko crypto candidate rows;
- 100 canonical crypto rows marked investable;
- all 100 canonical crypto rows incorrectly labelled `equity`;
- 10 crypto rows in the final legacy master selection;
- stable-value rows `USDC-USD`, `USDS-USD`, `RLUSD-USD` and `U-USD` in that
  selection;
- daily simple returns above `10.0` for several selected crypto symbols and a
  maximum of `2348.810765` for `CC-USD`;
- legacy Equal Weight CAGR above `10.0` and Max Sharpe CAGR above `50.0`.

Those figures are retained as forensic evidence only. They are not valid
performance claims.

## Method And Source Basis

CoinGecko's official `/coins/markets` documentation defines separate `id`,
`symbol` and `name` fields. It does not establish a Yahoo Finance symbol
crosswalk. Therefore `CoinGecko symbol + "-USD"` is an unverified inference, not
provider identity evidence:

- <https://docs.coingecko.com/reference/coins-markets>
- <https://docs.coingecko.com/reference/coins-list>

The eight-book methodology inventory supports the governing rules applied here:

- portfolio inputs must represent the intended assets on comparable observations;
- missing observations require an explicit policy and cannot silently become
  zero returns;
- covariance and optimization outputs inherit data-quality and sample-alignment
  errors;
- constraints and optimizer feasibility are part of the model definition;
- attractive backtest metrics do not validate contaminated inputs.

Relevant local methodology families are documented in
`docs/audit/methodology_source_inventory.md` and
`docs/audit/methodology_source_check.md`.

## Post-Repair Contract

For a crypto row to enter portfolio research, all conditions must hold:

1. `include=true`;
2. `investable=true`;
3. `benchmark_only=false`;
4. `signal_only=false`;
5. the row is not classified as stablecoin/stable-value;
6. `price_ticker_verified=true`;
7. the selected price-provider symbol is backed by a reviewed crosswalk;
8. all ordinary history, FX, data-quality and run-identity gates pass.

The current CoinGecko source file has no reviewed cross-provider price map.
Consequently the rebuilt current universe is expected to retain the 100 crypto
rows for coverage while allowing zero of them into portfolio inputs.

## Validation

Deterministic tests cover:

- stable-value classification for USDT, USDS, RLUSD and United Stables;
- non-classification of Bitcoin and Tether Gold;
- unverified crypto mapping exclusion;
- explicit verified mapping admission;
- preservation of source flags and crypto `asset_type`;
- CoinGecko ID lineage and non-investable default;
- missing-return observation counts without zero imputation;
- master exclusion of unverified crypto;
- explicit `infeasible_constraints` optimizer status;
- optimizer failure cannot be relabelled as another model;
- cluster-balanced cap preservation after redistribution;
- Black-Litterman selected-subset output remains diagnostic-only;
- return-matrix -> stock-score/eligibility -> master dependency order.

## Remaining Limitations

- A reviewed CoinGecko-ID-to-price-provider crosswalk is not yet implemented.
- The stable-value taxonomy is an operational conservative rule and requires
  periodic review; it is not a permanent regulatory classification.
- The tracked source snapshot remains useful for market-cap coverage, but it
  cannot by itself prove tradable price identity.
- Historical point-in-time membership, delistings and institutional
  corporate-action reference data remain unavailable.
- Other optimizer fallback behavior and complete missing-data policy consistency
  remain within the wider full-system audit scope.

Current full-system verdict remains `NOT_MERGE_READY` until all P0/P1 findings in
the active scientific red-team audit are resolved or explicitly blocked by
unavailable external data.
