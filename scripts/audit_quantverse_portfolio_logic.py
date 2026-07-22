"""Audit QuantVerse portfolio math, constraints and evidence traceability."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path("data/processed")
TOLERANCE = 1e-6


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    weight_rows, issues = _audit_weights()
    issues.extend(_audit_universe())
    issues.extend(_audit_returns_and_risk())
    weight_sum = pd.DataFrame(weight_rows)
    issue_frame = pd.DataFrame(
        issues,
        columns=["check_group", "portfolio", "issue", "severity", "detail"],
    )
    summary = _summary(weight_sum, issue_frame)
    constraints = {
        "weight_tolerance": TOLERANCE,
        "critical_issues": (
            int(issue_frame["severity"].eq("critical").sum())
            if not issue_frame.empty
            else 0
        ),
        "error_issues": (
            int(issue_frame["severity"].eq("error").sum())
            if not issue_frame.empty
            else 0
        ),
        "status": "completed",
    }
    weight_sum.to_csv(OUTPUT_DIR / "portfolio_weight_sum_audit.csv", index=False)
    issue_frame.to_csv(OUTPUT_DIR / "portfolio_logic_audit_issues.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "portfolio_logic_audit_summary.csv", index=False)
    (OUTPUT_DIR / "portfolio_constraint_audit.json").write_text(
        json.dumps(constraints, indent=2),
        encoding="utf-8",
    )
    print(f"Portfolio logic audit issues: {len(issue_frame)}")
    return 0


def _audit_weights() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []
    weights_path = OUTPUT_DIR / "portfolio_holdings_long.csv"
    if weights_path.exists():
        weights = pd.read_csv(weights_path)
        rows.extend(
            _weight_rows(
                weights,
                portfolio_col="Portfolio",
                ticker_col="Ticker",
                weight_col="Weight",
                source_file=str(weights_path),
            )
        )
    else:
        issues.append(
            _issue(
                "weights",
                "",
                "portfolio_holdings_long_missing",
                "warning",
                str(weights_path),
            )
        )
    global_path = OUTPUT_DIR / "global_master_candidate_weights.csv"
    if global_path.exists():
        global_weights = pd.read_csv(global_path)
        rows.extend(
            _weight_rows(
                global_weights,
                portfolio_col="Model",
                ticker_col="Ticker",
                weight_col="Weight",
                source_file=str(global_path),
            )
        )
    return rows, issues + _weight_issues(rows)


def _weight_rows(
    weights: pd.DataFrame,
    portfolio_col: str,
    ticker_col: str,
    weight_col: str,
    source_file: str,
) -> list[dict[str, object]]:
    rows = []
    for portfolio, frame in weights.groupby(portfolio_col):
        numeric = pd.to_numeric(frame[weight_col], errors="coerce")
        rows.append(
            {
                "source_file": source_file,
                "portfolio": portfolio,
                "weight_sum": float(numeric.sum()),
                "max_weight": float(numeric.max()) if not numeric.empty else np.nan,
                "min_weight": float(numeric.min()) if not numeric.empty else np.nan,
                "nan_or_inf_weights": bool(
                    numeric.isna().any()
                    or np.isinf(numeric.to_numpy(dtype=float)).any()
                ),
                "negative_weights": int((numeric < -TOLERANCE).sum()),
                "holdings_count": int((numeric > TOLERANCE).sum()),
                "tickers": int(frame[ticker_col].nunique()),
            }
        )
    return rows


def _weight_issues(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    issues = []
    for row in rows:
        portfolio = str(row["portfolio"])
        if abs(float(row["weight_sum"]) - 1.0) > TOLERANCE:
            issues.append(
                _issue(
                    "weights",
                    portfolio,
                    "weight_sum_not_one",
                    "error",
                    str(row["weight_sum"]),
                )
            )
        if bool(row["nan_or_inf_weights"]):
            issues.append(
                _issue(
                    "weights",
                    portfolio,
                    "nan_or_inf_weight",
                    "error",
                    "non-finite weight found",
                )
            )
        if int(row["negative_weights"]) > 0:
            issues.append(
                _issue(
                    "weights",
                    portfolio,
                    "negative_weight_without_shorting",
                    "error",
                    str(row["negative_weights"]),
                )
            )
    return issues


def _audit_universe() -> list[dict[str, object]]:
    issues = []
    data_quality = OUTPUT_DIR / "data_quality_report.csv"
    if data_quality.exists():
        quality = pd.read_csv(data_quality)
        dropped = quality.loc[quality.get("Included_In_Returns", True) != True]
        if not dropped.empty and "Decision_Reason" not in dropped:
            issues.append(
                _issue(
                    "universe",
                    "",
                    "dropped_assets_missing_reasons",
                    "error",
                    "Decision_Reason missing",
                )
            )
        low_return_reasons = (
            dropped.get("Decision_Reason", pd.Series(dtype=str))
            .astype(str)
            .str.contains("low return", case=False, na=False)
        )
        if bool(low_return_reasons.any()):
            issues.append(
                _issue(
                    "universe",
                    "",
                    "low_return_used_as_drop_reason",
                    "error",
                    "low return cannot be a deletion reason",
                )
            )
    current = Path("data/universe/current_global_equity_universe.csv")
    if current.exists():
        frame = pd.read_csv(current)
        equity = (
            frame.get("sleeve", pd.Series(dtype=str))
            .astype(str)
            .str.startswith("global_equity")
        )
        flags = _bool(frame, "include") & _bool(frame, "investable")
        if not bool((equity & flags).any()):
            issues.append(
                _issue(
                    "universe",
                    "",
                    "global_equity_universe_zero_rows",
                    "critical",
                    "global master cannot be promoted",
                )
            )
    return issues


def _audit_returns_and_risk() -> list[dict[str, object]]:
    issues = []
    returns_path = OUTPUT_DIR / "global_security_returns.csv"
    if returns_path.exists():
        returns = pd.read_csv(returns_path)
        first = returns.columns[0]
        if str(first).lower() in {"date", "datetime", "timestamp"}:
            returns = returns.set_index(first)
        numeric = returns.apply(pd.to_numeric, errors="coerce")
        if np.isinf(numeric.to_numpy(dtype=float)).any():
            issues.append(
                _issue("returns", "", "infinite_returns", "error", str(returns_path))
            )
        corr = numeric.corr()
        if not corr.empty and not np.allclose(np.diag(corr.fillna(1.0)), 1.0):
            issues.append(
                _issue(
                    "returns",
                    "",
                    "correlation_diagonal_not_one",
                    "error",
                    "correlation matrix invalid",
                )
            )
    return issues


def _summary(weights: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "audit_area": "portfolio_logic",
                "portfolios_checked": (
                    int(weights["portfolio"].nunique()) if not weights.empty else 0
                ),
                "issues": int(len(issues)),
                "errors": (
                    int(issues["severity"].isin(["error", "critical"]).sum())
                    if not issues.empty
                    else 0
                ),
                "status": "completed",
            }
        ]
    )


def _bool(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].map(
        lambda value: str(value).strip().lower() in {"1", "true", "yes", "y"}
    )


def _issue(
    group: str, portfolio: str, issue: str, severity: str, detail: str
) -> dict[str, object]:
    return {
        "check_group": group,
        "portfolio": portfolio,
        "issue": issue,
        "severity": severity,
        "detail": detail,
    }


if __name__ == "__main__":
    sys.exit(main())
