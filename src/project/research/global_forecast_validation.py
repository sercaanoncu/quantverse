"""Forecast validation and calibration diagnostics for QuantVerse v2."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BY_HORIZON_COLUMNS = [
    "horizon",
    "horizon_days",
    "forecast_count",
    "mean_rmse",
    "mean_mae",
    "mean_random_walk_mae",
    "mae_improvement_vs_random_walk",
    "fraction_beating_random_walk",
    "mean_r2",
    "mean_forecast_confidence",
    "forecast_validation_status",
    "allocation_signal_status",
    "interpretation",
]

CALIBRATION_COLUMNS = [
    "horizon",
    "confidence_bucket",
    "forecast_count",
    "mean_confidence",
    "mean_mae",
    "mean_interval_width",
    "confidence_error_ratio",
    "calibration_interpretation",
]

RANDOM_WALK_COLUMNS = [
    "horizon",
    "model_mae",
    "random_walk_mae",
    "model_beats_random_walk",
    "mae_improvement",
    "decision",
]

WARNING_COLUMNS = [
    "horizon",
    "warning_type",
    "severity",
    "evidence",
    "allocation_use_allowed",
    "required_next_fix",
]


def build_forecast_validation(
    forecasts: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build validation tables from generated forecast diagnostics."""
    if forecasts.empty:
        return {
            "by_horizon": pd.DataFrame(columns=BY_HORIZON_COLUMNS),
            "calibration": pd.DataFrame(columns=CALIBRATION_COLUMNS),
            "random_walk": pd.DataFrame(columns=RANDOM_WALK_COLUMNS),
            "warnings": pd.DataFrame(columns=WARNING_COLUMNS),
        }
    frame = forecasts.copy()
    frame["horizon"] = frame.get("horizon", "unknown").astype(str)
    for column in [
        "horizon_days",
        "rmse",
        "mae",
        "benchmark_random_walk_error",
        "r2",
        "forecast_confidence",
        "prediction_interval_low",
        "prediction_interval_high",
    ]:
        if column not in frame:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    by_horizon = _by_horizon(frame)
    calibration = _calibration(frame)
    random_walk = _random_walk_comparison(by_horizon)
    warnings = _warnings(by_horizon)
    return {
        "by_horizon": by_horizon,
        "calibration": calibration,
        "random_walk": random_walk,
        "warnings": warnings,
    }


def write_forecast_validation_outputs(
    validation: dict[str, pd.DataFrame],
    output_dir: str | Path,
) -> None:
    """Write forecast validation outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    validation["by_horizon"].to_csv(
        path / "global_forecast_validation_by_horizon.csv", index=False
    )
    validation["calibration"].to_csv(
        path / "global_forecast_calibration_report.csv", index=False
    )
    validation["random_walk"].to_csv(
        path / "global_forecast_random_walk_comparison.csv", index=False
    )
    validation["warnings"].to_csv(
        path / "global_forecast_warning_report.csv", index=False
    )


def _by_horizon(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for horizon, group in frame.groupby("horizon", sort=True):
        mae = group["mae"].dropna()
        random_walk = group["benchmark_random_walk_error"].dropna()
        comparable = group[["mae", "benchmark_random_walk_error"]].dropna()
        mean_mae = float(mae.mean()) if not mae.empty else np.nan
        mean_rw = float(random_walk.mean()) if not random_walk.empty else np.nan
        improvement = (
            mean_rw - mean_mae
            if np.isfinite(mean_rw) and np.isfinite(mean_mae)
            else np.nan
        )
        beat_fraction = (
            float(
                (comparable["mae"] < comparable["benchmark_random_walk_error"]).mean()
            )
            if not comparable.empty
            else 0.0
        )
        scale_failed = _scale_failed(
            mean_mae=mean_mae,
            mean_rmse=(
                float(group["rmse"].mean()) if group["rmse"].notna().any() else np.nan
            ),
            mean_random_walk=mean_rw,
        )
        if scale_failed:
            status = "failed_scale_sanity"
        elif beat_fraction >= 0.55 and np.isfinite(improvement) and improvement > 0:
            status = "validated_diagnostic"
        else:
            status = "diagnostic_only"
        rows.append(
            {
                "horizon": horizon,
                "horizon_days": (
                    int(group["horizon_days"].dropna().iloc[0])
                    if group["horizon_days"].dropna().any()
                    else np.nan
                ),
                "forecast_count": int(len(group)),
                "mean_rmse": (
                    float(group["rmse"].mean())
                    if group["rmse"].notna().any()
                    else np.nan
                ),
                "mean_mae": mean_mae,
                "mean_random_walk_mae": mean_rw,
                "mae_improvement_vs_random_walk": improvement,
                "fraction_beating_random_walk": beat_fraction,
                "mean_r2": (
                    float(group["r2"].mean()) if group["r2"].notna().any() else np.nan
                ),
                "mean_forecast_confidence": (
                    float(group["forecast_confidence"].mean())
                    if group["forecast_confidence"].notna().any()
                    else np.nan
                ),
                "forecast_validation_status": status,
                "allocation_signal_status": (
                    "blocked_failed_scale_sanity" if scale_failed else "diagnostic_only"
                ),
                "interpretation": (
                    "Forecasts are validation diagnostics only; they cannot promote "
                    "a portfolio unless net decision quality improves out of sample."
                ),
            }
        )
    return pd.DataFrame(rows, columns=BY_HORIZON_COLUMNS)


def _calibration(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frame = frame.copy()
    frame["interval_width"] = (
        frame["prediction_interval_high"] - frame["prediction_interval_low"]
    )
    for horizon, group in frame.groupby("horizon", sort=True):
        valid = group.dropna(subset=["forecast_confidence"])
        if valid.empty:
            continue
        ranks = valid["forecast_confidence"].rank(method="first")
        bucket_count = min(4, len(valid))
        valid = valid.assign(
            confidence_bucket=pd.qcut(
                ranks,
                q=bucket_count,
                labels=False,
                duplicates="drop",
            )
            + 1
        )
        for bucket, bucket_frame in valid.groupby("confidence_bucket", sort=True):
            mean_confidence = float(bucket_frame["forecast_confidence"].mean())
            mean_mae = (
                float(bucket_frame["mae"].mean())
                if bucket_frame["mae"].notna().any()
                else np.nan
            )
            ratio = (
                mean_confidence / mean_mae
                if np.isfinite(mean_mae) and mean_mae > 0
                else np.nan
            )
            rows.append(
                {
                    "horizon": horizon,
                    "confidence_bucket": int(bucket),
                    "forecast_count": int(len(bucket_frame)),
                    "mean_confidence": mean_confidence,
                    "mean_mae": mean_mae,
                    "mean_interval_width": (
                        float(bucket_frame["interval_width"].mean())
                        if bucket_frame["interval_width"].notna().any()
                        else np.nan
                    ),
                    "confidence_error_ratio": ratio,
                    "calibration_interpretation": (
                        "Higher confidence should eventually correspond to lower realized error; "
                        "current public-data forecast output remains diagnostic."
                    ),
                }
            )
    return pd.DataFrame(rows, columns=CALIBRATION_COLUMNS)


def _random_walk_comparison(by_horizon: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in by_horizon.iterrows():
        model_mae = float(row["mean_mae"]) if pd.notna(row["mean_mae"]) else np.nan
        random_mae = (
            float(row["mean_random_walk_mae"])
            if pd.notna(row["mean_random_walk_mae"])
            else np.nan
        )
        improvement = (
            random_mae - model_mae
            if np.isfinite(model_mae) and np.isfinite(random_mae)
            else np.nan
        )
        beats = bool(np.isfinite(improvement) and improvement > 0)
        rows.append(
            {
                "horizon": row["horizon"],
                "model_mae": model_mae,
                "random_walk_mae": random_mae,
                "model_beats_random_walk": beats,
                "mae_improvement": improvement,
                "decision": (
                    "forecast remains diagnostic; random-walk comparison is not enough for allocation promotion"
                ),
            }
        )
    return pd.DataFrame(rows, columns=RANDOM_WALK_COLUMNS)


def _warnings(by_horizon: pd.DataFrame) -> pd.DataFrame:
    if by_horizon.empty:
        return pd.DataFrame(
            [
                {
                    "horizon": "all",
                    "warning_type": "missing_forecasts",
                    "severity": "high",
                    "evidence": "No forecast validation rows.",
                    "allocation_use_allowed": False,
                    "required_next_fix": "Generate forecasts and validate against a random-walk baseline.",
                }
            ],
            columns=WARNING_COLUMNS,
        )
    rows = []
    for _, row in by_horizon.iterrows():
        if str(row["forecast_validation_status"]) == "failed_scale_sanity":
            rows.append(
                {
                    "horizon": row["horizon"],
                    "warning_type": "forecast_error_scale_failed",
                    "severity": "high",
                    "evidence": (
                        f"mean_mae={row['mean_mae']}; "
                        f"mean_random_walk_mae={row['mean_random_walk_mae']}"
                    ),
                    "allocation_use_allowed": False,
                    "required_next_fix": (
                        "Inspect forecast target units, outliers and input universe before any allocation use."
                    ),
                }
            )
        elif str(row["forecast_validation_status"]) == "diagnostic_only":
            rows.append(
                {
                    "horizon": row["horizon"],
                    "warning_type": "forecast_not_validated_as_alpha",
                    "severity": "medium",
                    "evidence": (
                        f"fraction_beating_random_walk={row['fraction_beating_random_walk']}"
                    ),
                    "allocation_use_allowed": False,
                    "required_next_fix": (
                        "Run stricter walk-forward portfolio-level validation before using forecasts as signals."
                    ),
                }
            )
    if not rows:
        rows.append(
            {
                "horizon": "all",
                "warning_type": "forecast_validated_but_still_diagnostic",
                "severity": "low",
                "evidence": "Forecast errors improved versus random walk in aggregate.",
                "allocation_use_allowed": False,
                "required_next_fix": "Prove net portfolio decision quality after costs and risk.",
            }
        )
    return pd.DataFrame(rows, columns=WARNING_COLUMNS)


def _scale_failed(
    *,
    mean_mae: float,
    mean_rmse: float,
    mean_random_walk: float,
) -> bool:
    model_error = np.nanmax([mean_mae, mean_rmse])
    if not np.isfinite(model_error):
        return False
    if model_error > 2.0:
        return True
    if np.isfinite(mean_random_walk) and mean_random_walk > 0:
        return bool(model_error > 10.0 * mean_random_walk and model_error > 0.50)
    return False
