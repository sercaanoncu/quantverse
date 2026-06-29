# PROJECT_CONTEXT.md - QuantVerse

## Purpose

QuantVerse is a multi-asset quant research and portfolio analytics system for
systematic portfolio construction, risk analysis and reproducible financial
research.

## Core Modules

- universe construction
- market data ingestion
- return calculation
- risk metrics
- portfolio optimization
- backtesting
- stress testing
- projection and simulation
- reporting
- validation

## Asset Coverage

QuantVerse currently supports ETF/multi-asset research and a global quant
research layer for equities, crypto, commodities, defensive assets and benchmark
proxies.

## Standard Assumptions

- Daily returns are the default.
- Annualization uses 252 trading days.
- Adjusted prices should be used when available.
- Long-only allocation is the default.
- Generated outputs are not source code and are not committed by default.

## Critical Risks

Key risks are look-ahead bias, survivorship bias, missing-data bias, unstable
covariance, overfitting, benchmark mismatch, stale universe definitions and
currency mismatch.
