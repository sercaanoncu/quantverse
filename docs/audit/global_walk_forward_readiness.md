# Global Walk-Forward Readiness

## Rule

Walk-forward validation requires chronological training and test windows,
point-in-time universe membership, no-look-ahead data preparation and
transaction-cost-aware portfolio evaluation.

## Required Outputs

Before a global stock candidate can be promoted on historical evidence,
QuantVerse should produce:

- `data/processed/global_walk_forward_validation.csv`,
- `data/processed/global_walk_forward_returns.csv`,
- `data/processed/global_walk_forward_weights.csv`,
- train/test window metadata,
- universe membership snapshots,
- turnover and transaction-cost checks,
- benchmark-aligned Equal Weight and random portfolio comparisons.

## Current QuantVerse Status

The current global research layer produces current candidate and projection
evidence. It does not yet provide point-in-time global stock walk-forward
validation.

## Promotion Rule

No global stock candidate may be promoted as historical or out-of-sample
evidence without these walk-forward readiness outputs.
