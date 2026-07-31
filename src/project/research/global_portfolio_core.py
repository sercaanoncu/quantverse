"""Canonical security selection and portfolio-constraint contracts.

This module contains the narrow rules shared by the current portfolio, the
model league and every walk-forward fold.  It deliberately separates security
selection from allocation so every model receives the same economic issuers.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp, minimize

from project.data_pipeline.security_identity import resolve_security_master_rows

MISSING = "unavailable"


@dataclass(frozen=True)
class CanonicalPortfolioPolicy:
    """Operational policy for the canonical equity portfolio."""

    target_holdings: int = 20
    diagnostic_history_observations: int = 252
    final_history_observations: int = 504
    requested_max_issuer_weight: float = 0.05
    max_weight: float = 0.10
    min_weight: float = 0.005
    max_sector_weight: float = 0.25
    max_industry_weight: float = 0.15
    max_issuer_country_weight: float = 0.60

    @property
    def requested_cap_is_model_degenerate(self) -> bool:
        """Return whether the requested cap leaves only Equal Weight feasible."""
        product = self.target_holdings * self.requested_max_issuer_weight
        return bool(np.isclose(product, 1.0, atol=1e-12, rtol=0.0))

    def validate(self) -> None:
        if self.target_holdings <= 1:
            raise ValueError("target_holdings must be greater than one.")
        if self.max_weight * self.target_holdings < 1.0 - 1e-12:
            raise ValueError("Operational max_weight is infeasible.")
        if self.min_weight * self.target_holdings > 1.0 + 1e-12:
            raise ValueError("Operational min_weight is infeasible.")
        for name, value in [
            ("max_sector_weight", self.max_sector_weight),
            ("max_industry_weight", self.max_industry_weight),
            ("max_issuer_country_weight", self.max_issuer_country_weight),
        ]:
            if not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be in (0, 1].")


def policy_from_mapping(config: dict[str, object]) -> CanonicalPortfolioPolicy:
    """Build the canonical policy from the reviewed v2 configuration."""
    return CanonicalPortfolioPolicy(
        target_holdings=int(config.get("target_holdings", 20)),
        diagnostic_history_observations=int(
            config.get("minimum_standard_history_observations", 252)
        ),
        final_history_observations=int(
            config.get("minimum_final_portfolio_history_observations", 504)
        ),
        requested_max_issuer_weight=float(
            config.get("requested_max_issuer_weight", 0.05)
        ),
        max_weight=float(config.get("max_weight", 0.10)),
        min_weight=float(config.get("min_weight", 0.005)),
        max_sector_weight=float(config.get("max_sector_weight", 0.25)),
        max_industry_weight=float(config.get("max_industry_weight", 0.15)),
        max_issuer_country_weight=float(config.get("max_issuer_country_weight", 0.60)),
    )


def build_canonical_security_metadata(
    universe: pd.DataFrame,
    identity_audit: pd.DataFrame,
    returns: pd.DataFrame,
    *,
    metadata_cache_dir: str | Path,
    allow_network: bool = False,
) -> pd.DataFrame:
    """Build one constraint-ready metadata row per ticker.

    Public provider profiles are used only for current issuer/sector metadata.
    They do not create point-in-time classifications and that limitation must
    remain visible in reports.
    """
    canonical = resolve_security_master_rows(universe)
    canonical["ticker"] = canonical["ticker"].astype(str)
    identity = (
        identity_audit.drop_duplicates("ticker").set_index("ticker")
        if not identity_audit.empty and "ticker" in identity_audit
        else pd.DataFrame()
    )
    numeric_returns = returns.apply(pd.to_numeric, errors="coerce")
    cache = Path(metadata_cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for row in canonical.to_dict("records"):
        ticker = str(row.get("ticker", "")).strip()
        if not ticker or ticker not in numeric_returns:
            continue
        identity_row = (
            identity.loc[ticker].to_dict()
            if not identity.empty and ticker in identity.index
            else {}
        )
        profile = _load_profile(ticker, cache, allow_network=allow_network)
        issuer_name = _first_text(
            identity_row.get("issuer_name"),
            profile.get("longName"),
            row.get("name"),
            ticker,
        )
        stable_identifier = _first_verified_identifier(
            identity_row.get("stable_identifier")
        )
        verified_issuer_name = _verified_issuer_name(identity_row)
        if stable_identifier is not None:
            issuer_key_source = "verified_stable_identifier"
            issuer_key = stable_identifier
        elif verified_issuer_name is not None:
            issuer_key_source = "verified_issuer_name"
            issuer_key = normalize_issuer_name(verified_issuer_name)
        else:
            issuer_key_source = "normalized_issuer_name_fallback"
            issuer_key = normalize_issuer_name(issuer_name)
        series = numeric_returns[ticker]
        valid = series.dropna()
        observations = int(valid.shape[0])
        rows.append(
            {
                "ticker": ticker,
                "name": _first_text(row.get("name"), profile.get("longName"), ticker),
                "issuer_name": issuer_name,
                "issuer_key": issuer_key,
                "issuer_key_source": issuer_key_source,
                "stable_identifier": stable_identifier or MISSING,
                "primary_listing_verified": _truthy(
                    identity_row.get(
                        "primary_listing_verified",
                        row.get("primary_listing_verified", False),
                    )
                ),
                "listing_country": _first_text(row.get("country"), MISSING),
                "issuer_country": _first_text(profile.get("country"), MISSING),
                "currency": _first_text(
                    profile.get("currency"), row.get("currency"), MISSING
                ),
                "exchange": _first_text(
                    profile.get("exchange"), row.get("exchange"), MISSING
                ),
                "sector": _first_text(
                    profile.get("sector"), row.get("sector"), MISSING
                ),
                "industry": _first_text(
                    profile.get("industry"), row.get("industry"), MISSING
                ),
                "observations": observations,
                "first_return_date": _date(valid.index.min()),
                "last_return_date": _date(valid.index.max()),
                "missing_rate": float(series.isna().mean()),
                "median_dollar_volume": _profile_dollar_volume(profile),
                "metadata_source": (
                    "yfinance_profile_cache_or_current_query"
                    if profile
                    else "current_universe_and_identity_only"
                ),
                "constraint_metadata_complete": bool(
                    all(
                        value != MISSING
                        for value in [
                            _first_text(profile.get("country"), MISSING),
                            _first_text(
                                profile.get("sector"), row.get("sector"), MISSING
                            ),
                            _first_text(
                                profile.get("industry"), row.get("industry"), MISSING
                            ),
                        ]
                    )
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)


def select_canonical_securities(
    scores: pd.DataFrame,
    metadata: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select exactly one representative per issuer under group constraints."""
    policy.validate()
    if scores.empty or metadata.empty:
        raise ValueError("Scores and canonical security metadata are required.")
    required_scores = {
        "ticker",
        "composite_quant_score",
        "standard_composite_score_eligible",
    }
    if not required_scores.issubset(scores.columns):
        raise ValueError("Stock scores are missing canonical selection fields.")
    frame = scores.copy()
    frame["ticker"] = frame["ticker"].astype(str)
    frame = frame.merge(metadata, on="ticker", how="left", validate="one_to_one")
    frame["final_history_eligible"] = (
        pd.to_numeric(
            frame.get("observations_x", frame.get("observations_y")), errors="coerce"
        )
        .fillna(0)
        .ge(policy.final_history_observations)
    )
    frame["score_eligible"] = frame["standard_composite_score_eligible"].map(_truthy)
    frame["constraint_metadata_complete"] = frame["constraint_metadata_complete"].map(
        _truthy
    )
    frame["issuer_representative"] = False
    frame["representative_selection_reason"] = ""
    frame["representative_rejection_reason"] = ""

    eligible_for_rep = frame.loc[
        frame["score_eligible"]
        & frame["final_history_eligible"]
        & frame["constraint_metadata_complete"]
        & frame["issuer_key"].notna()
    ].copy()
    for _, group in eligible_for_rep.groupby("issuer_key", sort=True):
        representative, representative_reason = _choose_representative(group)
        frame.loc[frame["ticker"].eq(representative), "issuer_representative"] = True
        frame.loc[
            frame["ticker"].eq(representative), "representative_selection_reason"
        ] = representative_reason
        rejected = group.loc[~group["ticker"].eq(representative), "ticker"]
        frame.loc[frame["ticker"].isin(rejected), "representative_rejection_reason"] = (
            "duplicate_economic_issuer; selected_representative="
            + representative
            + "; "
            + representative_reason
        )

    candidates = frame.loc[frame["issuer_representative"]].copy()
    selected_tickers = _solve_selection(candidates, policy)
    frame["selected"] = frame["ticker"].isin(selected_tickers)
    frame["selection_status"] = np.where(frame["selected"], "selected", "rejected")
    frame["selection_reason"] = frame.apply(
        lambda row: _selection_reason(row, frame.loc[frame["selected"]], policy),
        axis=1,
    )
    selected = frame.loc[frame["selected"]].sort_values(
        ["composite_quant_score", "ticker"], ascending=[False, True]
    )
    if len(selected) != policy.target_holdings:
        raise ValueError(
            f"Canonical selection requires {policy.target_holdings} holdings; "
            f"observed {len(selected)}."
        )
    _validate_selected_groups(selected, policy)
    audit = frame.sort_values(
        ["selected", "composite_quant_score", "ticker"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return selected.reset_index(drop=True), audit


def project_group_constrained_weights(
    raw_weights: pd.Series,
    metadata: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> pd.Series:
    """Project long-only weights onto the canonical individual/group limits."""
    policy.validate()
    raw = pd.Series(raw_weights, dtype=float)
    if raw.empty or not np.isfinite(raw.to_numpy(dtype=float)).all():
        raise ValueError("Raw model weights must be finite and non-empty.")
    meta = metadata.drop_duplicates("ticker").set_index("ticker").reindex(raw.index)
    required = {"sector", "industry", "issuer_country", "issuer_key"}
    if not required.issubset(meta.columns) or meta[list(required)].isna().any().any():
        raise ValueError("Complete group metadata is required for weight constraints.")
    if meta["issuer_key"].duplicated().any():
        raise ValueError("Portfolio weights contain duplicate economic issuers.")
    target = raw.clip(lower=0.0)
    target = (
        target / target.sum()
        if target.sum() > 0
        else pd.Series(1 / len(raw), index=raw.index)
    )

    if _weight_vector_passes(target, meta, policy):
        return target.rename("weight")

    rows: list[np.ndarray] = []
    upper: list[float] = []
    for column, cap in [
        ("sector", policy.max_sector_weight),
        ("industry", policy.max_industry_weight),
        ("issuer_country", policy.max_issuer_country_weight),
    ]:
        for label in sorted(meta[column].astype(str).unique()):
            mask = meta[column].astype(str).eq(label).to_numpy(dtype=float)
            rows.append(mask)
            upper.append(float(cap))
    result = minimize(
        lambda weights: float(np.square(weights - target.to_numpy(dtype=float)).sum()),
        x0=np.full(len(target), 1.0 / len(target)),
        bounds=Bounds(
            np.full(len(target), policy.min_weight),
            np.full(len(target), policy.max_weight),
        ),
        constraints=[
            LinearConstraint(
                np.ones((1, len(target))), np.array([1.0]), np.array([1.0])
            ),
            LinearConstraint(
                np.vstack(rows),
                np.full(len(rows), -np.inf),
                np.array(upper),
            ),
        ],
        method="SLSQP",
        options={"maxiter": 2000, "ftol": 1e-12},
    )
    if not result.success:
        raise ValueError(
            "Canonical group-constrained projection failed: " + str(result.message)
        )
    weights = pd.Series(result.x, index=target.index, name="weight")
    validate_portfolio_constraints(
        weights,
        meta.rename_axis("ticker").reset_index(),
        policy,
    )
    return weights


def _weight_vector_passes(
    weights: pd.Series,
    metadata: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> bool:
    values = weights.to_numpy(dtype=float)
    if (
        not np.isclose(values.sum(), 1.0, atol=1e-8, rtol=0.0)
        or bool((values < policy.min_weight - 1e-8).any())
        or bool((values > policy.max_weight + 1e-8).any())
    ):
        return False
    for column, cap in [
        ("sector", policy.max_sector_weight),
        ("industry", policy.max_industry_weight),
        ("issuer_country", policy.max_issuer_country_weight),
    ]:
        if (
            float(weights.groupby(metadata[column].astype(str)).sum().max())
            > cap + 1e-8
        ):
            return False
    return True


def validate_portfolio_constraints(
    weights: pd.Series,
    metadata: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> dict[str, object]:
    """Validate the complete canonical portfolio constraint set."""
    series = pd.Series(weights, dtype=float)
    meta = metadata.drop_duplicates("ticker").set_index("ticker").reindex(series.index)
    exposures = {}
    for column in ["sector", "industry", "issuer_country", "issuer_key"]:
        grouped = series.groupby(meta[column].astype(str)).sum()
        exposures[column] = grouped
    result = {
        "holdings_count": int((series > 1e-12).sum()),
        "weight_sum": float(series.sum()),
        "negative_weight_count": int((series < -1e-12).sum()),
        "max_weight": float(series.max()),
        "duplicate_economic_issuer_count": int(meta["issuer_key"].duplicated().sum()),
        "max_sector_weight": float(exposures["sector"].max()),
        "max_industry_weight": float(exposures["industry"].max()),
        "max_issuer_country_weight": float(exposures["issuer_country"].max()),
    }
    passed = bool(
        result["holdings_count"] == policy.target_holdings
        and np.isclose(result["weight_sum"], 1.0, atol=1e-8, rtol=0.0)
        and result["negative_weight_count"] == 0
        and result["max_weight"] <= policy.max_weight + 1e-8
        and result["duplicate_economic_issuer_count"] == 0
        and result["max_sector_weight"] <= policy.max_sector_weight + 1e-8
        and result["max_industry_weight"] <= policy.max_industry_weight + 1e-8
        and result["max_issuer_country_weight"]
        <= policy.max_issuer_country_weight + 1e-8
    )
    result["all_constraints_pass"] = passed
    if not passed:
        raise ValueError(f"Canonical portfolio constraints failed: {result}")
    return result


def portfolio_constraints_satisfied(
    weights: pd.Series,
    metadata: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> bool:
    """Return a non-raising constraint predicate for random sampling."""
    series = pd.Series(weights, dtype=float)
    meta = metadata.drop_duplicates("ticker").set_index("ticker").reindex(series.index)
    if meta[["sector", "industry", "issuer_country", "issuer_key"]].isna().any().any():
        return False
    if meta["issuer_key"].duplicated().any():
        return False
    return _weight_vector_passes(series, meta, policy)


def sample_constraint_feasible_weights(
    metadata: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
    rng: np.random.Generator,
    *,
    steps: int = 10,
) -> pd.Series:
    """Draw a reproducible hit-and-run sample inside the constraint polytope."""
    frame = metadata.drop_duplicates("ticker").set_index("ticker")
    if len(frame) != policy.target_holdings:
        raise ValueError("Random sampling requires the canonical holdings count.")
    tickers = frame.index.astype(str)
    weights = np.full(len(frame), 1.0 / len(frame), dtype=float)
    constraints: list[tuple[np.ndarray, float]] = []
    for column, cap in [
        ("sector", policy.max_sector_weight),
        ("industry", policy.max_industry_weight),
        ("issuer_country", policy.max_issuer_country_weight),
    ]:
        for label in sorted(frame[column].astype(str).unique()):
            constraints.append(
                (frame[column].astype(str).eq(label).to_numpy(dtype=float), float(cap))
            )
    for _ in range(int(steps)):
        direction = rng.normal(size=len(weights))
        direction = direction - direction.mean()
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-15:
            continue
        direction = direction / norm
        lower = -np.inf
        upper = np.inf
        for value, delta in zip(weights, direction, strict=True):
            if delta > 1e-15:
                lower = max(lower, (policy.min_weight - value) / delta)
                upper = min(upper, (policy.max_weight - value) / delta)
            elif delta < -1e-15:
                lower = max(lower, (policy.max_weight - value) / delta)
                upper = min(upper, (policy.min_weight - value) / delta)
        for mask, cap in constraints:
            current = float(mask @ weights)
            delta = float(mask @ direction)
            if delta > 1e-15:
                upper = min(upper, (cap - current) / delta)
            elif delta < -1e-15:
                lower = max(lower, (cap - current) / delta)
        if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper:
            continue
        weights = weights + rng.uniform(lower, upper) * direction
    sample = pd.Series(weights, index=tickers, name="weight")
    if not portfolio_constraints_satisfied(sample, frame.reset_index(), policy):
        raise ValueError("Hit-and-run random portfolio violated canonical constraints.")
    return sample


def normalize_issuer_name(value: object) -> str:
    """Return a deterministic issuer-name key used only as documented fallback."""
    text = str(value or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    suffix = re.compile(
        r"(?:\s+(?:class\s+[a-z]|common\s+stock|ordinary\s+shares?|adr|new))+$"
    )
    text = suffix.sub("", text.strip())
    return " ".join(text.split()) or MISSING


def _solve_selection(
    candidates: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> list[str]:
    if len(candidates) < policy.target_holdings:
        raise ValueError(
            "Not enough issuer-deduplicated, metadata-complete candidates."
        )
    ordered = candidates.sort_values("ticker").reset_index(drop=True)
    score = pd.to_numeric(ordered["composite_quant_score"], errors="coerce")
    if score.isna().any():
        raise ValueError("Candidate composite scores must be finite.")
    score = (score - score.min()) / max(float(score.max() - score.min()), 1e-12)
    objective = -score.to_numpy(dtype=float) + np.arange(len(ordered)) * 1e-10
    rows = [np.ones(len(ordered), dtype=float)]
    lower = [float(policy.target_holdings)]
    upper = [float(policy.target_holdings)]
    for column, cap in [
        ("sector", policy.max_sector_weight),
        ("industry", policy.max_industry_weight),
        ("issuer_country", policy.max_issuer_country_weight),
    ]:
        max_count = int(np.floor(cap * policy.target_holdings + 1e-12))
        for label in sorted(ordered[column].astype(str).unique()):
            rows.append(ordered[column].astype(str).eq(label).to_numpy(dtype=float))
            lower.append(0.0)
            upper.append(float(max_count))
    result = milp(
        c=objective,
        integrality=np.ones(len(ordered), dtype=int),
        bounds=Bounds(np.zeros(len(ordered)), np.ones(len(ordered))),
        constraints=LinearConstraint(np.vstack(rows), np.array(lower), np.array(upper)),
        options={"disp": False},
    )
    if not result.success or result.x is None:
        raise ValueError("Canonical 20-security selection constraints are infeasible.")
    selected = ordered.loc[result.x > 0.5, "ticker"].astype(str).tolist()
    return selected


def _choose_representative(group: pd.DataFrame) -> tuple[str, str]:
    ordered = group.copy()
    primary = ordered.get(
        "primary_listing_verified",
        pd.Series(False, index=ordered.index),
    )
    ordered["_primary_listing"] = primary.map(_truthy)
    ordered["_median_dollar_volume"] = pd.to_numeric(
        ordered.get(
            "median_dollar_volume",
            pd.Series(np.nan, index=ordered.index),
        ),
        errors="coerce",
    ).fillna(-1.0)
    observation_column = next(
        (
            column
            for column in ["observations_x", "observations_y", "observations"]
            if column in ordered
        ),
        None,
    )
    ordered["_observations"] = (
        pd.to_numeric(ordered[observation_column], errors="coerce").fillna(-1.0)
        if observation_column
        else -1.0
    )
    ordered["_missing_rate"] = pd.to_numeric(
        ordered.get("missing_rate", pd.Series(np.nan, index=ordered.index)),
        errors="coerce",
    ).fillna(np.inf)
    ordered = ordered.sort_values(
        [
            "_primary_listing",
            "_median_dollar_volume",
            "_observations",
            "_missing_rate",
            "ticker",
        ],
        ascending=[False, False, False, True, True],
        kind="mergesort",
    )
    selected = ordered.iloc[0]
    if len(ordered) == 1:
        reason = "selected_representative_only_eligible_security_for_issuer"
    elif bool(selected["_primary_listing"]) and not ordered["_primary_listing"].all():
        reason = "selected_representative_by_verified_primary_listing"
    elif (
        float(selected["_median_dollar_volume"]) >= 0.0
        and int(
            np.isclose(
                ordered["_median_dollar_volume"].to_numpy(dtype=float),
                float(selected["_median_dollar_volume"]),
            ).sum()
        )
        == 1
    ):
        reason = "selected_representative_by_highest_reliable_median_dollar_volume"
    elif (
        int(
            np.isclose(
                ordered["_observations"].to_numpy(dtype=float),
                float(selected["_observations"]),
            ).sum()
        )
        == 1
    ):
        reason = "selected_representative_by_longest_valid_continuous_history"
    elif (
        int(
            np.isclose(
                ordered["_missing_rate"].to_numpy(dtype=float),
                float(selected["_missing_rate"]),
            ).sum()
        )
        == 1
    ):
        reason = "selected_representative_by_lowest_missing_data_rate"
    else:
        reason = "selected_representative_by_deterministic_ticker_tiebreak"
    return str(selected["ticker"]), reason


def _selection_reason(
    row: pd.Series,
    selected: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> str:
    if bool(row.get("selected", False)):
        return "selected_by_score_subject_to_issuer_sector_industry_country_constraints"
    if not bool(row.get("score_eligible", False)):
        return "rejected_not_diagnostic_score_eligible"
    if not bool(row.get("final_history_eligible", False)):
        return f"rejected_final_history_below_{policy.final_history_observations}"
    if not bool(row.get("constraint_metadata_complete", False)):
        return "rejected_missing_sector_industry_or_issuer_country_metadata"
    representative_reason = str(row.get("representative_rejection_reason", "")).strip()
    if representative_reason:
        return representative_reason
    for column, cap in [
        ("sector", policy.max_sector_weight),
        ("industry", policy.max_industry_weight),
        ("issuer_country", policy.max_issuer_country_weight),
    ]:
        limit = int(np.floor(cap * policy.target_holdings + 1e-12))
        if int(selected[column].astype(str).eq(str(row.get(column))).sum()) >= limit:
            return f"rejected_{column}_capacity_constraint"
    return "rejected_lower_composite_score_than_selected_feasible_set"


def _validate_selected_groups(
    selected: pd.DataFrame,
    policy: CanonicalPortfolioPolicy,
) -> None:
    if selected["issuer_key"].duplicated().any():
        raise ValueError("Selected securities contain duplicate economic issuers.")
    for column, cap in [
        ("sector", policy.max_sector_weight),
        ("industry", policy.max_industry_weight),
        ("issuer_country", policy.max_issuer_country_weight),
    ]:
        limit = int(np.floor(cap * policy.target_holdings + 1e-12))
        observed = int(selected[column].astype(str).value_counts().max())
        if observed > limit:
            raise ValueError(f"Selected {column} count exceeds Equal Weight cap.")


def _load_profile(
    ticker: str, cache: Path, *, allow_network: bool
) -> dict[str, object]:
    path = cache / f"{re.sub(r'[^A-Za-z0-9_-]', '_', ticker)}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    if not allow_network:
        return {}
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).get_info()
    except Exception:
        return {}
    keys = [
        "country",
        "sector",
        "industry",
        "exchange",
        "currency",
        "quoteType",
        "longName",
        "averageDailyVolume10Day",
        "regularMarketPrice",
    ]
    profile = {key: info.get(key) for key in keys if info.get(key) is not None}
    if profile:
        path.write_text(json.dumps(profile, indent=2, default=str), encoding="utf-8")
    return profile


def _profile_dollar_volume(profile: dict[str, object]) -> float:
    try:
        volume = float(profile.get("averageDailyVolume10Day", np.nan))
        price = float(profile.get("regularMarketPrice", np.nan))
        value = volume * price
        return value if np.isfinite(value) and value > 0 else np.nan
    except (TypeError, ValueError):
        return np.nan


def _first_verified_identifier(value: object) -> str | None:
    text = str(value or "").strip()
    return None if text.lower() in {"", "nan", "none", MISSING} else text


def _verified_issuer_name(identity_row: dict[str, object]) -> str | None:
    confidence = str(identity_row.get("evidence_confidence", "")).strip().lower()
    if confidence not in {"verified", "high", "medium"}:
        return None
    value = _first_text(identity_row.get("issuer_name"))
    return None if value == MISSING else value


def _first_text(*values: object) -> str:
    for value in values:
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() not in {"nan", "none", "null", MISSING}:
            return text
    return MISSING


def _date(value: object) -> str:
    if value is None or pd.isna(value):
        return MISSING
    return pd.Timestamp(value).date().isoformat()


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
