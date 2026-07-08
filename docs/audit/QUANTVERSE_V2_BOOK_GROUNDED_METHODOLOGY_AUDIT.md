# QuantVerse v2 Book-Grounded Methodology Audit

Branch: `fix/v2-numerical-integrity-equity-scope`

This audit translates the local quantitative finance, statistics,
econometrics, machine-learning and portfolio-optimization books into practical
QuantVerse v2 validation rules. It does not quote long copyrighted passages and
does not claim investment advice, guaranteed outperformance or institutional
point-in-time backtest completion.

## 1. Portfolio Theory Principles From Books

Palomar's portfolio optimization text is the primary basis for separating
objective functions: mean-variance, global minimum variance, risk parity, CVaR,
drawdown-aware and robust portfolios are different problems. They should not be
collapsed into one "best return" score. A model that minimizes risk can be a
valid final research model when the decision objective is risk-adjusted utility.

Severini and Ahlawat support strict statistical labeling: realized sample
return is evidence from the historical sample, not an expected-return promise.
Jansen, Dixon/Halperin/Bilokon, Hull and ISLR support chronological validation,
random-walk baselines, train/test discipline and explicit treatment of
overfitting. Quantitative Economics with Python supports simulation, dynamic
systems and economic interpretation rather than mechanical metric chasing.

## 2. Expected Return Versus Realized Return

QuantVerse must distinguish:

- realized annualized return: arithmetic annualized mean from historical daily
  simple returns;
- CAGR: compounded historical growth over the available sample;
- forecast expected return: diagnostic horizon return estimate;
- optimizer expected return: an input to an optimization problem, not a
  guaranteed future outcome.

## 3. Excess Return Versus Raw Return

Sharpe is theoretically excess return divided by volatility. If a risk-free
series is unavailable, QuantVerse must state the zero risk-free assumption. Raw
return can be shown, but it must not silently replace excess return in
risk-adjusted interpretation.

## 4. Return/Risk Versus Risk/Return

Risk-adjusted performance should be return per unit risk, e.g. Sharpe = excess
return / volatility. If risk/return is used, it must be labelled as risk per
unit return and lower is better.

## 5. Sharpe, Sortino, Calmar And CVaR Interpretation

Sharpe measures return per unit total volatility. Sortino focuses on downside
variation. Calmar compares compounded growth to drawdown. CVaR estimates mean
tail loss beyond VaR. These metrics are not interchangeable. A model may have
lower raw return but superior risk-adjusted evidence if it materially improves
Sharpe, drawdown and CVaR.

## 6. Equal Weight As Benchmark

Equal Weight is a necessary benchmark because expected-return estimation error
and optimizer instability often make active allocation hard to justify
out-of-sample. It is not automatically the winner. It remains final only when
active models fail transparent gates.

## 7. Estimation Error And Optimizer Fragility

Max Sharpe and mean-variance optimizers are fragile when expected returns are
noisy. Risk estimators are usually more defensible than direct return forecasts.
Therefore Max Sharpe remains diagnostic unless walk-forward evidence clears
risk, turnover, robustness and random benchmark gates.

## 8. In-Sample Versus Walk-Forward Evidence

In-sample league metrics explain model behavior but cannot dominate final model
selection. Walk-forward metrics are primary evidence because each test window
follows a training window chronologically.

## 9. Forecast Validation And Random Walk Baseline

Forecast models are diagnostic unless they beat the random-walk baseline
out-of-sample and improve portfolio decisions after costs and risk. A forecast
failure blocks forecast-enhanced model promotion.

## 10. Transaction Costs And Turnover

Turnover is a cost and implementation risk proxy. Active models with strong
paper Sharpe but excessive turnover should not be selected without cost-adjusted
evidence.

## 11. Promotion Gate Logic

The book-grounded public-data final model gate now requires:

- executable status: `actually_run` or `benchmark_only`;
- constraints pass;
- walk-forward Sharpe improvement over Equal Weight at or above the configured
  threshold;
- max drawdown not materially worse;
- CVaR not materially worse;
- turnover within the configured maximum;
- random Sharpe percentile above the configured threshold;
- robustness not fragile;
- forecast validation not failed for forecast-driven models.

Institutional/global USD master portfolio promotion remains a separate gate and
stays blocked while exact top-100, point-in-time, delisting and full
institutional data evidence remain unavailable.

## 12. Current QuantVerse Violations

Before this sprint, active models with materially better walk-forward Sharpe and
tail-risk behavior could be rejected solely because raw return was lower than
Equal Weight. That made Equal Weight behave like an automatic winner rather than
a benchmark. The previous `selection_score` also mixed raw return and penalties
without a documented methodology table.

## 13. Required Code Fixes

QuantVerse must:

- expose model-selection diagnostics;
- rank models by a documented book-grounded score;
- allow active risk-managed models to beat Equal Weight when risk-adjusted
  walk-forward gates pass;
- keep diagnostic models out of final selection;
- keep forecast models blocked when forecast validation fails;
- add explicit threshold configuration and tests.

| Principle | Book/source basis | Current implementation | Problem | Required correction | Status |
| --- | --- | --- | --- | --- | --- |
| Return per unit risk is higher-is-better | Palomar; Severini; Ahlawat | Sharpe/Sortino/Calmar shown, but raw return gate dominated active model selection | Active risk-managed models could be rejected despite better Sharpe and tail risk | Use walk-forward Sharpe improvement, drawdown, CVaR, turnover and random benchmark gates | Implemented |
| Equal Weight is benchmark, not automatic winner | Palomar; Jansen | Equal Weight remained final whenever active raw return was lower | Benchmark became a hard winner rule | Allow active model final selection when book-grounded gates pass | Implemented |
| In-sample results are secondary | Jansen; ISLR; Dixon/Halperin/Bilokon | League metrics and walk-forward metrics were both present | Final reasoning did not clearly prioritize walk-forward | Use walk-forward as primary evidence and in-sample as diagnostics | Implemented |
| Forecasts require random-walk validation | Jansen; Hull; ISLR | Forecast models were diagnostic but gate wording was not explicit | A forecast-enhanced model could look stronger than its validation status | Forecast failed validation blocks forecast-driven final selection | Implemented |
| CVaR and drawdown are tail-risk gates | Palomar; financial statistics texts | CVaR/drawdown were checked but raw return still dominated | Tail-risk improvements were underweighted | Treat drawdown and CVaR as explicit active-model gates | Implemented |
| Turnover is implementation cost evidence | Jansen; portfolio optimization practice | Turnover was penalized in score | Gate threshold was not explicit in config | Add `max_turnover` threshold and failure reason | Implemented |
| Risk/return inverse must be labelled | Severini; Ahlawat | No explicit helper or wording discipline | Direction could be misread | Add `return_per_unit_risk` and `risk_per_unit_return` direction helpers/tests | Implemented |
| Diagnostic models cannot override weak OOS evidence | ML finance and ISLR validation texts | Diagnostic models were excluded | Needs regression tests | Add tests preventing diagnostic promotion and in-sample Max Sharpe override | Implemented |
