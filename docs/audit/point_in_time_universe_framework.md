# Point-in-Time Universe Framework

## Rule

Current sourced equity CSV files are current research inputs only. They cannot
support historical stock-selection, historical top-100 or walk-forward
promotion claims.

## Required Evidence For Historical Claims

Each historical membership row must include:

- ticker,
- company name,
- sleeve,
- exchange,
- country,
- currency,
- membership effective start date,
- membership effective end date or active flag,
- source provider,
- source URL,
- source retrieval date,
- market cap or rank as of the membership date,
- delisting/corporate-action status,
- no-look-ahead validation metadata.

## Current QuantVerse Status

The current global universe is useful for current research and pipeline
testing. It is not point-in-time historical evidence.

## Promotion Rule

No global stock strategy may be promoted as historical or out-of-sample
evidence while point-in-time membership fields are missing.
