# Global Master Portfolio

The global master portfolio allocator reads a global returns matrix and universe
metadata, selects holdings through a cluster-aware scoring layer and compares
multiple candidate portfolios against Equal Weight and random portfolio
benchmarks.

Candidate models include Equal Weight, Inverse Volatility, Min Variance, Max
Sharpe, Min CVaR, Black-Litterman where market caps are available and a
cluster-balanced candidate. The global sprint also adds a policy-constrained
candidate that enforces long-only weights, weight sum, single-name cap,
asset-class caps, region caps and cluster caps. HRP, Risk Parity and
forecast-enhanced variants are kept explicit in the comparison layer when
unavailable for a given run.

The final candidate is promoted only if the evidence gate supports it. Otherwise
the output remains `not promoted`.

The current global stock run may produce a fully weighted research candidate
while still returning `not promoted`. This is expected when the input universe
uses current-constituent proxies, market caps are missing, or non-USD local
returns have not been FX-normalized into the USD reporting base currency.
