# QuantVerse Model League System

QuantVerse does not use one single "best model" label for every objective. A
portfolio rule can have the highest CAGR while still being too unstable to be
the broad default. Another rule can reduce drawdown while sacrificing return.
The league system keeps those claims separate.

## 1. Broad Default Champion

The broad default champion is the model a cautious research project would use as
the primary reference allocation. It must be stable, simple, low-overfit and
defensible.

Promotion rule:

- Same universe, dates, costs and rebalance calendar as Equal Weight.
- Beats Equal Weight on OOS CAGR.
- Bootstrap CAGR and Sharpe differences are positive.
- Survives 25 bps and 50 bps cost sensitivity.
- Wins across enough subperiod and rolling windows.
- Does not introduce an unacceptable drawdown penalty.

Current interpretation: Equal Weight remains the broad default champion unless a
challenger passes all promotion gates.

## 2. Annual Return Challenger

This league identifies the highest out-of-sample CAGR model after costs. It is
allowed to be more active than Equal Weight, but it must still use only
information available at each rebalance date.

Current highest-CAGR candidate: Asset-Class Momentum Rotation. It keeps the best
point-estimate OOS CAGR and survives the 25 bps and 50 bps cost checks, but the
current bootstrap and subperiod evidence are not strong enough to promote it
beyond research-candidate status.

This label does not automatically replace Equal Weight as the broad default
champion.

## 3. Risk-Adjusted Champion

This league focuses on Sharpe, Sortino and Calmar, not raw return alone. A point
estimate is not enough. Promotion requires:

- Sharpe or blended risk-adjusted edge versus Equal Weight.
- Bootstrap support.
- Cost robustness.
- No severe subperiod instability.
- No hidden concentration or turnover problem.

The pipeline reports the best Sharpe point estimate, but it does not overclaim
the model unless the promotion gate supports it.

## 4. Defensive / Drawdown Champion

This league is for risk reduction and crisis behavior. The winner may have lower
CAGR than Equal Weight. That is acceptable if the purpose is drawdown control,
tail risk, capital preservation or risk-budget stability.

Candidate families:

- HRP / Signal-Aware HRP Lite.
- Risk Parity.
- Risk-Managed Equal Weight.
- Min CVaR or other tail-risk allocation.

The defensive league is not ranked by CAGR alone.

## 5. Research Candidate

Research candidates show some useful evidence, but they do not pass enough
promotion checks. They remain useful for investigation, interviews and future
extensions.

Examples:

- Momentum variants with positive point estimates but weak bootstrap support.
- Regime-aware rules that work in one subperiod but not another.
- Risk overlays that need more live unseen validation.

## 6. Diagnostic Only

Diagnostic-only models explain behavior but are not direct allocation
recommendations. This can include unstable Max Sharpe variants, ML downside-risk
classifiers or regime labels.

Diagnostic models are still valuable because they answer "why" questions without
pretending to be trading signals.

## 7. Rejected

Rejected models fail the implemented promotion logic because of leakage,
instability, cost sensitivity or overfit risk. Rejected does not mean useless; it
means unsuitable for allocation in the current evidence layer.

Rejected models should remain visible in audit outputs when they help explain
what was tested and why it was not promoted.

## Pipeline Outputs

The pipeline writes the league system to:

- `data/processed/model_league_summary.csv`
- `data/processed/model_league_summary.json`
- `data/processed/research_alpha_leaderboard.csv`
- `data/processed/model_promotion_gate.csv`
- `data/processed/model_overfit_diagnostics.csv`

These files are designed for report, PDF and interview defense use.
