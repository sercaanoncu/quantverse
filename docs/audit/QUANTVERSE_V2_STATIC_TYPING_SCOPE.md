# QuantVerse v2 Static Typing Scope

## Gate

Run:

```powershell
python -m pyright
```

The gate uses `pyrightconfig.json`, `typeCheckingMode=basic` and Python 3.10 as
the repository's minimum supported Python version. `pandas-stubs` is a
development dependency so dataframe contracts are checked rather than treated
as untyped `Any`.

## Included Critical Modules

- `src/project/research/global_model_selection.py`
- `src/project/research/global_walk_forward.py`
- `src/project/research/global_portfolio_league.py`
- `src/project/research/global_portfolio_risk.py`
- `src/project/research/global_numerical_integrity.py`
- `src/project/data_pipeline/security_identity.py`
- `src/project/data_pipeline/global_returns.py`
- `src/project/data_pipeline/processor.py`
- `src/project/portfolio_contract.py`
- `src/project/reporting/artifact_publication.py`
- `src/project/reporting/quantverse_v2_publication.py`
- `scripts/audit_quantverse_v2_missing_data_operations.py`

This scope covers model promotion, OOS construction, portfolio construction,
risk mathematics, numerical gates, security identity, local/base-currency
returns, price cleaning, the shared weight contract, manifest-last publication,
strict one-run report loading and repository-wide missing-data classification.

## Design

- No file is excluded through `ignore`.
- No diagnostic category is globally disabled.
- Nullable dataframe state is resolved explicitly before arithmetic.
- Walk-forward outputs use a `TypedDict` package contract.
- Values read from heterogeneous rows use scalar conversion helpers that reject
  array-like values.
- The staged initial gate found 127 diagnostics across the eventual critical
  scope. All were repaired without changing the declared financial formulas or
  model-selection gates.

## Boundary

This is an incremental critical-path gate, not a claim that every repository
module is fully typed. New high-risk modules should enter the `include` list
after their current diagnostics are repaired. Expanding the scope must not be
achieved by broad suppressions.
