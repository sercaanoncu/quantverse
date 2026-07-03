# Bank Interview Talk Track

## 60-Second Pitch

QuantVerse v2 is a public-data global equity research engine. It starts with a
sourced current universe, normalizes returns into USD where possible, scores
stocks with transparent risk and momentum diagnostics, builds a portfolio model
league, evaluates risk metrics, runs current-universe walk-forward validation
and generates explainable PDF and Excel outputs.

## Strongest Technical Point

The project does not treat optimization output as truth. Every model has a
status, every candidate is compared with Equal Weight and random portfolios, and
the system keeps data-source, FX, market-cap and point-in-time limitations
visible.

## How To Defend The Model League

Equal Weight is the benchmark. Inverse Volatility, GMV, HRP, Risk Parity and
Min CVaR are risk-allocation candidates. Max Sharpe and Black-Litterman are
diagnostic unless expected-return inputs and priors are defensible.
Forecast-enhanced portfolios are constrained and must be validated
chronologically.

## How To Defend The Final Model Selection

I do not select the final model only because it has the highest in-sample
return. The v2 decision layer checks actual model status, constraints,
walk-forward evidence, transaction-cost-adjusted return, Sharpe, drawdown,
CVaR, turnover, random portfolio percentiles and Equal Weight comparison. If no
active model clears those gates, Equal Weight remains the defensible benchmark
and no active model is promoted.

## What I Would Improve In A Bank Setting

I would replace public-provider data with a licensed vendor feed, add
point-in-time constituents, reconcile delistings and corporate actions, harden FX
calendar alignment, add model approval documentation, and connect monitoring to
production risk controls.
