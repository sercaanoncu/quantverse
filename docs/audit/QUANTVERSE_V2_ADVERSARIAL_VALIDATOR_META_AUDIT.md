# QuantVerse v2 Adversarial Validator Meta-Audit

## Purpose

This audit asks whether deliberately incorrect evidence can pass the QuantVerse
validators. Passing code, a valid schema or a plausible label is not sufficient.
Each attack below changes a material economic, mathematical or provenance
contract and must be rejected deterministically.

## Attack Matrix

| Attack ID | Injected defect | Required rejection | Executable evidence | Result |
|---|---|---|---|---|
| ADV-001 | Wrong non-native FX direction | Independent replay of quote inversion and simple-return compounding fails | `tests/test_reference_math_validator.py`; `tests/test_fx_normalization.py` | rejected |
| ADV-002 | Static full-sample random portfolio distribution labelled OOS | Random Sharpe promotion gate remains false | `tests/test_book_grounded_model_selection.py::test_full_sample_random_distribution_cannot_pass_oos_random_gate` | rejected |
| ADV-003 | Missing robustness evidence treated as stable | Robustness gate fails closed | `tests/test_book_grounded_model_selection.py::test_missing_robustness_fails_closed` | rejected |
| ADV-004 | Future winner appears only in the test window | Training-window selection cannot use the future return | `tests/test_walk_forward_no_leakage.py::test_walk_forward_recomputes_scores_inside_train_window_without_future_winner` | rejected |
| ADV-005 | Stale run identifier | Robustness/publication evidence fails run reconciliation | `tests/test_book_grounded_model_selection.py::test_stale_robustness_fails_closed`; `tests/test_quantverse_v2_governance_and_publication.py` | rejected |
| ADV-006 | Mismatched config hash with the same apparent model result | Random and robustness gates fail identity reconciliation | `tests/test_book_grounded_model_selection.py::test_mismatched_config_hash_fails_robustness_and_random_gates` | rejected |
| ADV-007 | Annual risk-free rate applied with the wrong frequency | Non-zero 5% fixture fails independent Sharpe/Sortino replay | `tests/test_reference_math_validator.py`; `tests/test_global_portfolio_risk.py` | rejected |
| ADV-008 | Selected asset return is missing or changed to zero | Native-base and final-portfolio metric replays fail | `tests/test_reference_math_validator.py`; `tests/test_portfolio_weight_contract.py` | rejected |
| ADV-009 | Long-only optimizer weights are nonfinite, negative or do not sum to one | Shared weight contract and reference checks fail | `tests/test_portfolio_weight_contract.py`; `tests/test_reference_math_validator.py` | rejected |
| ADV-010 | CVaR sign is reversed | Historical-tail replay and `CVaR <= VaR <= 0` convention fail | `tests/test_quant_math_correctness.py`; `tests/test_reference_math_validator.py` | rejected |
| ADV-011 | OOS model-date rows overlap or are duplicated | Stitched OOS and paired-bootstrap checks fail without crashing | `tests/test_reference_math_validator.py` | rejected |
| ADV-012 | Report package mixes current and stale run artifacts | Publication loader and package-manifest validator fail | `tests/test_quantverse_v2_governance_and_publication.py`; `tests/test_quantverse_v2_artifact_validator.py` | rejected |
| ADV-013 | Additional Excel CSV is absent from the artifact registry or mutated after registration | Publication loading fails before workbook construction | `tests/test_quantverse_v2_governance_and_publication.py` | rejected |
| ADV-014 | Final-decision JSON says `promoted` while model-selection rows imply Equal Weight / not promoted | Independent decision replay fails | `tests/test_quantverse_v2_artifact_validator.py`; `tests/test_quantverse_v2_governance_and_publication.py` | rejected |
| ADV-015 | Effective current-universe, source-universe or master-portfolio policy changes without an identity change | Composite config hash, fingerprint and run ID must change | `tests/test_run_identity.py`; `tests/test_quantverse_v2_demo.py` | rejected |
| ADV-016 | Publication turnover uses half-L1 while the cost path uses gross traded-notional L1 | Formula reconciliation test fails | `tests/test_quantverse_v2_governance_and_publication.py` | rejected |
| ADV-017 | One or more required pairwise correlations are missing but the asset receives diversification credit | Standard score receives zero correlation-diversification credit | `tests/test_global_stock_scoring.py` | rejected |
| ADV-018 | `ffill(limit=None)`, nonpositive bounds or arbitrary `reindex(fill_value=0)` appear in active source | Missing-data AST audit fails unless an exact valid reviewed rule exists | `tests/test_missing_data_operation_audit.py` | rejected |
| ADV-019 | Forecast/risk chart has one finite value and one NaN, or random flags are strings | Complete visual-domain validation fails | `tests/test_visual_analytics_outputs.py` | rejected |
| ADV-020 | Exposure chart contains negative/nonfinite weights even if the aggregate sum appears valid | Visual exposure contract fails | `tests/test_visual_analytics_outputs.py` | rejected |
| ADV-021 | Dynamic or computed forward-fill limit appears outside an exact reviewed call site | AST audit rejects the call even when a variable or function name looks bounded | `tests/test_missing_data_operation_audit.py::test_dynamic_forward_fill_limit_requires_exact_reviewed_callsite`; exact forward-fill allowlist | rejected |
| ADV-022 | The same OOS date is removed from model and random paths and both stored date hashes are rewritten | Primitive return-index replay rejects both shortened paths | `tests/test_global_walk_forward.py::test_walk_forward_comparison_rejects_shortened_or_nonfinite_oos_path`; `tests/test_reference_math_validator.py` | rejected |
| ADV-023 | Publication manifest has the wrong package type, omits a required member, duplicates a member or lies about byte size | Exact type, identity, membership, uniqueness, size and SHA-256 validation fails | `tests/test_quantverse_v2_governance_and_publication.py::test_publication_validator_rejects_inexact_or_mutated_package` | rejected |
| ADV-024 | Global-master cost or promotion threshold configuration is ignored or contains an invalid percentile | Executable gate uses the configured values and rejects invalid thresholds | `tests/test_global_master_portfolio.py::test_master_promotion_gate_uses_configured_cost_and_threshold_contract`; `tests/test_global_master_portfolio.py::test_master_promotion_gate_rejects_invalid_configured_threshold` | rejected |

## Defect Found By The Meta-Audit

The initial overlapping-date attack correctly failed the stitched OOS uniqueness
check, but a later bootstrap `pivot` raised an exception before the validator
could return a controlled failed result. The validator now detects duplicate
`(model_name, Date)` pairs before pivoting, records a failed bootstrap
reconciliation check and completes the audit. Invalid evidence is rejected
without converting a scientific failure into an infrastructure crash.

The closing independent re-reviews found further partial-contract bypasses in
publication source binding, decision reconstruction, run identity,
missing-data syntax, visual domains, dynamic forward-fill controls, OOS path
completeness, publication package completeness and legacy master-gate config
plumbing. ADV-013 through ADV-024 encode those failures directly. Final
validator counts are recorded in the execution ledger after the source-only
rebuild rather than hard-coded here.

## Scientific Boundary

- These tests establish that the listed known error classes are rejected.
- They do not prove that every possible implementation error has been modeled.
- A validator may not call the production formula it claims to independently
  verify.
- A not-applicable check must describe its scope; for example, a native-USD-only
  run does not establish empirical non-native FX coverage.
- Any newly discovered bypass requires a deterministic regression fixture and a
  new row in this matrix.
