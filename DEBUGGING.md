# DEBUGGING.md

## Debugging Protocol

1. Summarize the symptom.
2. List the three most likely causes.
3. Identify the smallest command or test that confirms each cause.
4. Change one variable at a time.
5. Re-run the focused test, then the broader validation gate.

## Quant-Specific Checks

- schema mismatch
- date misalignment
- look-ahead leakage
- survivorship bias
- missing data interpreted incorrectly
- frequency mismatch
- unstable covariance matrix
- optimizer infeasibility
- dependency or Python-version differences
