# Portfolio Logic Audit

This audit checks mathematical portfolio correctness before any user-facing
claim is made. It is intentionally separate from performance reporting: a model
may have attractive historical return and still be rejected if weights,
constraints, data lineage or promotion gates fail.

## Audit Scope

- Complete portfolio weight vectors must sum to 1 within `1e-6`.
- Weights must be finite and non-negative unless shorting is explicitly enabled.
- Max-weight, holding-count, asset-class, region and cluster constraints are
  checked for the global master candidate.
- Signal-only rows must not enter investable portfolio weights.
- Dropped or unavailable assets must be traceable to coverage or investability
  reasons, not to low historical return alone.
- Equal Weight and random portfolios are benchmarks, not proof of superiority.

## Outputs

The local audit command writes:

```powershell
python scripts/audit_quantverse_portfolio_logic.py
```

Expected local artifacts:

- `data/processed/portfolio_logic_audit_summary.csv`
- `data/processed/portfolio_logic_audit_issues.csv`
- `data/processed/portfolio_weight_sum_audit.csv`
- `data/processed/portfolio_constraint_audit.json`

## Global Master Portfolio Checks

The global master run now writes full audit tables for:

- selected assets,
- full model weights,
- asset-class weights,
- region weights,
- cluster weights,
- model comparison,
- Equal Weight comparison,
- random portfolio benchmark,
- constraint audit,
- promotion gate.

Unconstrained candidates may remain in the comparison table for research, but
they cannot become the final user-facing candidate if the policy constraint
audit fails. The policy-constrained candidate is the only global candidate that
is allowed to pass the defined hard allocation caps in this sprint.

## Known Remaining Gaps

The current global equity source files are current-constituent proxies, not
point-in-time historical membership files. Global USD promotion is blocked when
non-USD local return series have not been FX-normalized into the reporting base
currency. A future institutional version must add point-in-time membership,
market caps, delisting handling, corporate-action reconciliation and FX return
normalization.
