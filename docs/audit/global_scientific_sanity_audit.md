# Global Scientific Sanity Audit

The scientific sanity audit is a second validation layer beyond unit tests. It
does not ask whether Python code runs; it asks whether the produced financial
evidence is plausible, correctly labelled and safe to interpret.

Run:

```powershell
python scripts/audit_global_scientific_sanity.py
```

Outputs:

- `data/processed/global_scientific_sanity_summary.csv`
- `data/processed/global_scientific_sanity_issues.csv`
- `data/processed/global_red_flag_dashboard.csv`

The audit flags extreme annualized return/risk metrics, missing market-cap
coverage, incomplete FX normalization, price coverage gaps, outlier returns,
weight-sum errors, dust weights, concentration, unavailable models and weak
forecast diagnostics.

Critical and high issues do not mean the code is useless. They mean the output
must be interpreted as research evidence and must not be promoted as an
institutional global USD master portfolio until the blocker is fixed.
