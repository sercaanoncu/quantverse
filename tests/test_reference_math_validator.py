import json

import numpy as np
import pandas as pd

from scripts.qa.verify_quantverse_reference_math import verify_reference_math


def test_reference_math_validator_recalculates_and_detects_metric_tampering(
    tmp_path,
):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    dates = pd.bdate_range("2024-01-02", periods=260)
    steps = np.arange(len(dates), dtype=float)
    prices = pd.DataFrame(
        {
            "Date": dates,
            "AAA": 100.0 * np.cumprod(1.0 + 0.0005 + 0.002 * np.sin(steps)),
            "BBB": 80.0 * np.cumprod(1.0 + 0.0003 + 0.001 * np.cos(steps)),
        }
    )
    price_indexed = prices.set_index("Date")
    simple = price_indexed.pct_change(fill_method=None).dropna()
    log_returns = np.log(price_indexed / price_indexed.shift(1)).dropna()
    _write_matrix(prices, processed / "global_security_prices.csv")
    _write_matrix(
        simple.reset_index(),
        processed / "global_security_simple_returns_local.csv",
    )
    _write_matrix(
        log_returns.reset_index(),
        processed / "global_security_log_returns_local.csv",
    )
    _write_matrix(
        simple.reset_index(),
        processed / "global_security_simple_returns_usd.csv",
    )
    pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "currency": ["USD", "USD"],
            "fx_normalization_status": ["native_base", "native_base"],
        }
    ).to_csv(processed / "global_fx_normalization_report.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["AAA", "BBB"],
            "weight": [0.6, 0.4],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)

    portfolio = simple.mul(pd.Series({"AAA": 0.6, "BBB": 0.4}), axis=1).sum(axis=1)
    risk = _risk_metrics(portfolio)
    pd.DataFrame([{"model_name": "Equal Weight", **risk}]).to_csv(
        processed / "global_portfolio_risk_report.csv", index=False
    )
    _risk_contributions(simple, pd.Series({"AAA": 0.6, "BBB": 0.4})).to_csv(
        processed / "global_risk_contribution_report.csv", index=False
    )
    (processed / "global_final_model_decision.json").write_text(
        json.dumps({"final_selected_model": "Equal Weight"}), encoding="utf-8"
    )
    (processed / "quantverse_v2_run_manifest.json").write_text(
        json.dumps({"run_id": "unit-run"}), encoding="utf-8"
    )

    checks = verify_reference_math(tmp_path)

    assert checks["passed"].all()
    risk_path = processed / "global_portfolio_risk_report.csv"
    tampered = pd.read_csv(risk_path)
    tampered.loc[0, "cagr"] += 0.10
    tampered.to_csv(risk_path, index=False)

    tampered_checks = verify_reference_math(tmp_path)

    cagr_check = tampered_checks.loc[
        tampered_checks["check"].eq("final_portfolio_cagr")
    ].iloc[0]
    assert not bool(cagr_check["passed"])


def _write_matrix(frame: pd.DataFrame, path) -> None:
    output = frame.copy()
    output.columns = ["Date", *output.columns[1:]]
    output.to_csv(path, index=False)


def _risk_metrics(returns: pd.Series) -> dict[str, float]:
    wealth = (1.0 + returns).cumprod()
    total_return = float(wealth.iloc[-1] - 1.0)
    annualized_return = float(returns.mean() * 252)
    volatility = float(returns.std(ddof=1) * np.sqrt(252))
    var_95 = float(returns.quantile(0.05))
    return {
        "cagr": float((1.0 + total_return) ** (252 / len(returns)) - 1.0),
        "annualized_return": annualized_return,
        "annualized_volatility": volatility,
        "sharpe": annualized_return / volatility,
        "max_drawdown": float((wealth / wealth.cummax() - 1.0).min()),
        "var_95": var_95,
        "cvar_95": float(returns.loc[returns <= var_95].mean()),
        "total_return": total_return,
    }


def _risk_contributions(returns: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    covariance = returns.cov().to_numpy(dtype=float) * 252
    vector = weights.to_numpy(dtype=float)
    volatility = float(np.sqrt(vector @ covariance @ vector))
    marginal = covariance @ vector / volatility
    component = vector * marginal
    return pd.DataFrame(
        {
            "model_name": "Equal Weight",
            "ticker": weights.index,
            "marginal_risk_contribution": marginal,
            "component_risk_contribution": component,
            "risk_contribution_pct": component / component.sum(),
        }
    )
