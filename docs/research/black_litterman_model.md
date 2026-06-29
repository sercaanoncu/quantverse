# Black-Litterman Model

The Black-Litterman implementation uses market-cap weights as the neutral prior,
computes implied equilibrium returns and optionally incorporates investor views
through a P/Q/Omega view system.

If market caps are missing, the model must not pretend to be valid. If no views
are supplied, the model returns a market-implied baseline allocation and records
that no subjective or factor views were applied.

Black-Litterman is a portfolio construction model, not evidence of superiority.
It can become a promoted candidate only after the same Equal Weight, random
portfolio, drawdown, CVaR, transaction-cost and robustness gates are passed.
