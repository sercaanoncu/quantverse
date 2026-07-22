"""Professional QuantVerse v2 PDF and HTML research publications."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Mapping, Sequence

import matplotlib
import numpy as np
import pandas as pd

from project.research.run_identity import validate_registered_artifacts
from project.research.global_model_selection import build_final_model_decision

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

if TYPE_CHECKING:
    from reportlab.platypus import Flowable

INK = "#17252E"
BLUE = "#176B87"
TEAL = "#2A9D8F"
GOLD = "#E9C46A"
RED = "#C8553D"
SOFT_RED = "#FCE8E6"
SOFT_BLUE = "#EAF4F8"
SOFT_GOLD = "#FFF6D8"
LIGHT = "#F4F6F7"
MID = "#68737D"
WHITE = "#FFFFFF"

RUN_IDENTITY_FIELDS = (
    "run_id",
    "execution_id",
    "data_as_of_date",
    "generated_at",
    "universe_snapshot_id",
    "data_snapshot_id",
    "config_hash",
    "input_fingerprint",
)


@dataclass(frozen=True)
class ChartSpec:
    """Reader-facing chart contract."""

    key: str
    title: str
    method: str
    interpretation: str
    limitation: str
    invalidation: str


@dataclass
class PublicationEvidence:
    """One run-consistent publication evidence package."""

    root: Path
    manifest: dict[str, object]
    decision: dict[str, object]
    reference_summary: dict[str, object]
    random_provenance: dict[str, object]
    reference_checks: pd.DataFrame
    visual_validation: pd.DataFrame
    league: pd.DataFrame
    model_selection: pd.DataFrame
    weights: pd.DataFrame
    holdings: pd.DataFrame
    risk: pd.DataFrame
    walk_forward: pd.DataFrame
    leakage_audit: pd.DataFrame
    uncertainty: pd.DataFrame
    stress: pd.DataFrame
    exposure: pd.DataFrame
    equity: pd.DataFrame
    drawdown: pd.DataFrame
    risk_return: pd.DataFrame
    random_benchmark: pd.DataFrame
    forecast_error: pd.DataFrame
    sanity: pd.DataFrame
    identity: pd.DataFrame
    eligibility: pd.DataFrame
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    json_payloads: dict[str, dict[str, object]] = field(default_factory=dict)

    @property
    def final_model(self) -> str:
        return str(self.decision.get("final_selected_model", "not available"))

    @property
    def final_decision(self) -> str:
        return str(self.decision.get("final_decision", "not promoted"))

    @property
    def final_weights(self) -> pd.DataFrame:
        if self.weights.empty or "model_name" not in self.weights:
            return pd.DataFrame()
        return self.weights.loc[
            self.weights["model_name"].astype(str).eq(self.final_model)
        ].copy()

    @property
    def final_risk(self) -> pd.Series:
        if self.risk.empty or "model_name" not in self.risk:
            return pd.Series(dtype=object)
        rows = self.risk.loc[self.risk["model_name"].astype(str).eq(self.final_model)]
        return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)

    def frame_for(self, path: str | Path) -> pd.DataFrame:
        """Return a defensive copy from the immutable publication snapshot."""
        key = _snapshot_key(self.root, path)
        if key not in self.frames:
            raise KeyError(f"CSV was not loaded into the publication snapshot: {key}")
        return self.frames[key].copy(deep=True)

    def json_for(self, path: str | Path) -> dict[str, object]:
        """Return a copy of a JSON payload from the publication snapshot."""
        key = _snapshot_key(self.root, path)
        if key not in self.json_payloads:
            raise KeyError(f"JSON was not loaded into the publication snapshot: {key}")
        return dict(self.json_payloads[key])


def load_publication_evidence(
    root: str | Path,
    *,
    additional_csv_paths: Sequence[str | Path] = (),
    additional_json_paths: Sequence[str | Path] = (),
) -> PublicationEvidence:
    """Load critical report evidence and reject mixed run identities."""
    root_path = Path(root).resolve()
    processed = root_path / "data" / "processed"
    frames: dict[str, pd.DataFrame] = {}
    json_payloads: dict[str, dict[str, object]] = {}

    def csv_snapshot(path: str | Path) -> pd.DataFrame:
        key = _snapshot_key(root_path, path)
        if key not in frames:
            frames[key] = _read_csv(root_path / key)
        return frames[key]

    def json_snapshot(path: str | Path) -> dict[str, object]:
        key = _snapshot_key(root_path, path)
        if key not in json_payloads:
            json_payloads[key] = _read_json(root_path / key)
        return json_payloads[key]

    manifest = json_snapshot(processed / "quantverse_v2_run_manifest.json")
    if not manifest.get("run_id"):
        raise ValueError("A complete QuantVerse v2 run manifest is required.")
    core_csv_paths = [
        processed / "quantverse_v2_reference_math_checks.csv",
        processed / "quantverse_v2_visual_validation.csv",
        processed / "global_portfolio_league.csv",
        processed / "global_model_selection_report.csv",
        processed / "global_portfolio_league_weights.csv",
        processed / "global_top_holdings_explanation.csv",
        processed / "global_portfolio_risk_report.csv",
        processed / "global_walk_forward_model_comparison.csv",
        processed / "global_walk_forward_leakage_audit.csv",
        processed / "global_walk_forward_uncertainty.csv",
        processed / "global_stress_test_results.csv",
        processed / "quantverse_v2_visual_exposure.csv",
        processed / "quantverse_v2_visual_equity_curve.csv",
        processed / "quantverse_v2_visual_drawdown_curve.csv",
        processed / "quantverse_v2_visual_model_risk_return.csv",
        processed / "quantverse_v2_visual_random_benchmark.csv",
        processed / "quantverse_v2_visual_forecast_error.csv",
        processed / "global_risk_metric_sanity_checks.csv",
        processed / "global_security_identity_audit.csv",
        processed / "global_security_history_eligibility.csv",
    ]
    core_json_paths = [
        processed / "global_final_model_decision.json",
        processed / "quantverse_v2_reference_math_summary.json",
        processed / "global_walk_forward_random_benchmark_provenance.json",
    ]
    registry_failures = validate_registered_artifacts(
        processed,
        [
            *core_csv_paths,
            *core_json_paths,
            *additional_csv_paths,
            *additional_json_paths,
        ],
        manifest=manifest,
        root=root_path,
    )
    if registry_failures:
        raise ValueError(
            "Publication evidence mixes runs, is stale, or differs from the "
            "registered source hash: " + "; ".join(registry_failures)
        )
    for path in [*core_csv_paths, *additional_csv_paths]:
        csv_snapshot(path)
    for path in [*core_json_paths, *additional_json_paths]:
        json_snapshot(path)

    decision = json_snapshot(processed / "global_final_model_decision.json")
    evidence = PublicationEvidence(
        root=root_path,
        manifest=manifest,
        decision=decision,
        reference_summary=json_snapshot(
            processed / "quantverse_v2_reference_math_summary.json"
        ),
        random_provenance=json_snapshot(
            processed / "global_walk_forward_random_benchmark_provenance.json"
        ),
        reference_checks=csv_snapshot(
            processed / "quantverse_v2_reference_math_checks.csv"
        ),
        visual_validation=csv_snapshot(
            processed / "quantverse_v2_visual_validation.csv"
        ),
        league=csv_snapshot(processed / "global_portfolio_league.csv"),
        model_selection=csv_snapshot(processed / "global_model_selection_report.csv"),
        weights=csv_snapshot(processed / "global_portfolio_league_weights.csv"),
        holdings=csv_snapshot(processed / "global_top_holdings_explanation.csv"),
        risk=csv_snapshot(processed / "global_portfolio_risk_report.csv"),
        walk_forward=csv_snapshot(
            processed / "global_walk_forward_model_comparison.csv"
        ),
        leakage_audit=csv_snapshot(processed / "global_walk_forward_leakage_audit.csv"),
        uncertainty=csv_snapshot(processed / "global_walk_forward_uncertainty.csv"),
        stress=csv_snapshot(processed / "global_stress_test_results.csv"),
        exposure=csv_snapshot(processed / "quantverse_v2_visual_exposure.csv"),
        equity=csv_snapshot(processed / "quantverse_v2_visual_equity_curve.csv"),
        drawdown=csv_snapshot(processed / "quantverse_v2_visual_drawdown_curve.csv"),
        risk_return=csv_snapshot(
            processed / "quantverse_v2_visual_model_risk_return.csv"
        ),
        random_benchmark=csv_snapshot(
            processed / "quantverse_v2_visual_random_benchmark.csv"
        ),
        forecast_error=csv_snapshot(
            processed / "quantverse_v2_visual_forecast_error.csv"
        ),
        sanity=csv_snapshot(processed / "global_risk_metric_sanity_checks.csv"),
        identity=csv_snapshot(processed / "global_security_identity_audit.csv"),
        eligibility=csv_snapshot(processed / "global_security_history_eligibility.csv"),
        frames=frames,
        json_payloads=json_payloads,
    )
    _validate_evidence_identity(evidence)
    _validate_publication_gates(evidence)
    return evidence


def build_publication_bundle(
    evidence: PublicationEvidence,
    *,
    executive_pdf: str | Path,
    methodology_pdf: str | Path,
    html_report: str | Path,
) -> dict[str, object]:
    """Build the two-PDF and HTML publication package."""
    executive_path = Path(executive_pdf)
    methodology_path = Path(methodology_pdf)
    html_path = Path(html_report)
    for path in (executive_path, methodology_path, html_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    _build_executive_pdf(evidence, executive_path)
    _build_methodology_pdf(evidence, methodology_path)
    _build_html(evidence, html_path)
    return {
        "executive_pdf": executive_path,
        "methodology_pdf": methodology_path,
        "html_report": html_path,
        "chart_count": len(_chart_specs(evidence)),
        "final_model": evidence.final_model,
        "final_decision": evidence.final_decision,
        "run_id": str(evidence.manifest["run_id"]),
    }


def _validate_evidence_identity(evidence: PublicationEvidence) -> None:
    mismatches: list[str] = []
    expected = {
        field: str(evidence.manifest.get(field, "")).strip()
        for field in RUN_IDENTITY_FIELDS
    }
    missing_manifest_fields = [field for field, value in expected.items() if not value]
    if missing_manifest_fields:
        mismatches.append(
            "run_manifest:missing_" + ",".join(sorted(missing_manifest_fields))
        )

    for name, payload in [
        ("global_final_model_decision.json", evidence.decision),
        ("quantverse_v2_reference_math_summary.json", evidence.reference_summary),
        (
            "global_walk_forward_random_benchmark_provenance.json",
            evidence.random_provenance,
        ),
    ]:
        for field, expected_value in expected.items():
            observed = str(payload.get(field, "")).strip()
            if observed != expected_value:
                mismatches.append(f"{name}:{field}={observed!r}")

    for name, frame in [
        ("reference_checks", evidence.reference_checks),
        ("visual_validation", evidence.visual_validation),
        ("league", evidence.league),
        ("model_selection", evidence.model_selection),
        ("weights", evidence.weights),
        ("holdings", evidence.holdings),
        ("risk", evidence.risk),
        ("walk_forward", evidence.walk_forward),
        ("leakage_audit", evidence.leakage_audit),
        ("uncertainty", evidence.uncertainty),
        ("exposure", evidence.exposure),
        ("equity", evidence.equity),
        ("drawdown", evidence.drawdown),
        ("risk_return", evidence.risk_return),
        ("random_benchmark", evidence.random_benchmark),
        ("forecast_error", evidence.forecast_error),
        ("stress", evidence.stress),
        ("sanity", evidence.sanity),
        ("identity", evidence.identity),
        ("eligibility", evidence.eligibility),
    ]:
        if frame.empty:
            mismatches.append(f"{name}:empty")
            continue
        for field, expected_value in expected.items():
            if field not in frame:
                mismatches.append(f"{name}:missing_{field}")
                continue
            observed = set(frame[field].dropna().astype(str).str.strip())
            if observed != {expected_value}:
                mismatches.append(f"{name}:{field}={sorted(observed)}")
    if mismatches:
        raise ValueError(
            "Publication evidence mixes runs or lacks run identity: "
            + "; ".join(mismatches)
        )


def _validate_publication_gates(evidence: PublicationEvidence) -> None:
    failures: list[str] = []
    if (
        str(evidence.reference_summary.get("status", "")).lower() != "passed"
        or _safe_int(evidence.reference_summary.get("failed_check_count"), -1) != 0
    ):
        failures.append("reference_math:not_passed")
    _require_all_passed(
        evidence.reference_checks,
        "reference_math_checks",
        failures,
    )
    _require_all_passed(evidence.sanity, "risk_metric_sanity", failures)
    _require_all_passed(
        evidence.visual_validation,
        "visual_validation",
        failures,
    )
    _require_all_passed(
        evidence.leakage_audit,
        "walk_forward_leakage_audit",
        failures,
    )
    leakage_selection_pass = bool(
        not evidence.model_selection.empty
        and {
            "leakage_gate_pass",
            "leakage_evidence_status",
        }.issubset(evidence.model_selection.columns)
        and evidence.model_selection["leakage_gate_pass"].map(_truthy).all()
        and evidence.model_selection["leakage_evidence_status"]
        .astype(str)
        .eq("verified_current_no_lookahead_with_survivorship_limitation")
        .all()
    )
    if not leakage_selection_pass:
        failures.append("model_selection:leakage_gate_not_verified")

    final_model = evidence.final_model.strip()
    final_decision = evidence.final_decision.strip()
    decision_reason = str(evidence.decision.get("final_decision_reason", "")).strip()
    if not final_model or final_model.lower() in {"missing", "not available", "nan"}:
        failures.append("decision:missing_final_model")
    if not final_decision or final_decision.lower() in {"missing", "nan"}:
        failures.append("decision:missing_final_decision")
    if not decision_reason:
        failures.append("decision:missing_final_decision_reason")
    _validate_model_selection_decision(evidence, failures)

    final_weights = evidence.final_weights
    if final_weights.empty:
        failures.append(f"Final model weights are missing for {final_model!r}.")
    else:
        required = {"ticker", "weight"}
        missing = required.difference(final_weights.columns)
        if missing:
            failures.append("weights:missing_" + ",".join(sorted(missing)))
        else:
            tickers = final_weights["ticker"].astype(str)
            weights = pd.to_numeric(final_weights["weight"], errors="coerce")
            if tickers.duplicated().any():
                failures.append("weights:duplicate_ticker")
            if not np.isfinite(weights.to_numpy(dtype=float)).all():
                failures.append("weights:non_finite")
            elif (weights < -1e-12).any():
                failures.append("weights:negative")
            elif not np.isclose(float(weights.sum()), 1.0, atol=1e-8, rtol=0.0):
                failures.append(f"weights:sum={float(weights.sum()):.12g}")

            league_rows = evidence.league.loc[
                evidence.league["model_name"].astype(str).eq(final_model)
            ]
            if league_rows.empty or "configured_max_weight" not in league_rows:
                failures.append("weights:configured_max_weight_missing")
            else:
                configured_cap = pd.to_numeric(
                    league_rows["configured_max_weight"], errors="coerce"
                ).iloc[0]
                if not np.isfinite(configured_cap):
                    failures.append("weights:configured_max_weight_non_finite")
                elif weights.max() > float(configured_cap) + 1e-10:
                    failures.append(
                        "weights:max_cap_breach="
                        f"{float(weights.max()):.12g}>{float(configured_cap):.12g}"
                    )

    _validate_holdings_reconciliation(evidence, failures)
    if failures:
        raise ValueError("Publication scientific gate failed: " + "; ".join(failures))


def _validate_model_selection_decision(
    evidence: PublicationEvidence,
    failures: list[str],
) -> None:
    selection = evidence.model_selection.copy()
    required = {
        "model_name",
        "eligible_final_model",
        "selection_score",
        "book_grounded_rank",
        "random_sharpe_percentile",
        "promotion_gate_failed_reasons",
        "sharpe_improvement_vs_equal_weight",
        "beats_equal_weight_sharpe",
        "drawdown_not_materially_worse_than_equal_weight",
        "cvar_not_materially_worse_than_equal_weight",
        "turnover_within_limit",
        "random_sharpe_gate_pass",
        "uncertainty_gate_pass",
        "robustness_gate_pass",
        "forecast_validation_gate_pass",
        "extreme_metric_warning",
        "walk_forward_sharpe",
        "walk_forward_annualized_return",
        "walk_forward_max_drawdown",
        "walk_forward_cvar_95",
        "turnover",
    }
    missing = required.difference(selection.columns)
    if missing:
        failures.append(
            "model_selection:decision_evidence_missing=" + ",".join(sorted(missing))
        )
        return

    final_rows = selection.loc[
        selection["model_name"].astype(str).eq(evidence.final_model)
    ]
    if len(final_rows) != 1:
        failures.append(f"model_selection:final_model_rows={len(final_rows)}")
        return
    if not _truthy(final_rows["eligible_final_model"].iloc[0]):
        failures.append("model_selection:final_model_not_eligible")

    boolean_columns = {
        "eligible_final_model",
        "beats_equal_weight_sharpe",
        "drawdown_not_materially_worse_than_equal_weight",
        "cvar_not_materially_worse_than_equal_weight",
        "turnover_within_limit",
        "random_sharpe_gate_pass",
        "uncertainty_gate_pass",
        "robustness_gate_pass",
        "forecast_validation_gate_pass",
    }
    for column in boolean_columns:
        selection[column] = selection[column].map(_truthy)
    try:
        expected = build_final_model_decision(selection)
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(
            "model_selection:decision_rebuild_failed=" f"{type(exc).__name__}"
        )
        return

    compared_fields = (
        "final_selected_model",
        "final_model_selection_method",
        "final_model_selection_score",
        "final_decision",
        "final_decision_reason",
        "equal_weight_comparison",
        "random_portfolio_percentile",
        "final_model_book_grounded_rank",
        "final_model_gate_reasons",
        "publish_readiness_status",
        "hard_limitations",
    )
    mismatches = [
        field
        for field in compared_fields
        if not _decision_values_equal(
            evidence.decision.get(field),
            expected.get(field),
        )
    ]
    if mismatches:
        failures.append("model_selection:decision_mismatch=" + ",".join(mismatches))


def _decision_values_equal(observed: object, expected: object) -> bool:
    if isinstance(expected, Mapping):
        if not isinstance(observed, Mapping) or set(observed) != set(expected):
            return False
        return all(
            _decision_values_equal(observed[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return bool(
            isinstance(observed, list)
            and len(observed) == len(expected)
            and all(
                _decision_values_equal(left, right)
                for left, right in zip(observed, expected, strict=True)
            )
        )
    if expected is None:
        return bool(
            observed is None
            or (
                isinstance(observed, (float, np.floating)) and np.isnan(float(observed))
            )
        )
    if isinstance(expected, bool):
        return _truthy(observed) is expected
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return bool(
                np.isclose(
                    float(str(observed)),
                    float(expected),
                    atol=1e-12,
                    rtol=1e-12,
                    equal_nan=True,
                )
            )
        except (TypeError, ValueError):
            return False
    return str(observed) == str(expected)


def _require_all_passed(
    frame: pd.DataFrame,
    name: str,
    failures: list[str],
) -> None:
    if frame.empty or "passed" not in frame:
        failures.append(f"{name}:missing_passed_evidence")
        return
    passed = frame["passed"].map(_truthy)
    if not bool(passed.all()):
        failures.append(f"{name}:failed_checks={int((~passed).sum())}")


def _validate_holdings_reconciliation(
    evidence: PublicationEvidence,
    failures: list[str],
) -> None:
    holdings = evidence.holdings
    if holdings.empty:
        failures.append("holdings:empty")
        return
    required = {"model_name", "ticker", "weight"}
    missing = required.difference(holdings.columns)
    if missing:
        failures.append("holdings:missing_" + ",".join(sorted(missing)))
        return
    holdings = holdings.loc[
        holdings["model_name"].astype(str).eq(evidence.final_model)
    ].copy()
    if holdings.empty:
        failures.append("holdings:final_model_missing")
        return
    if holdings["ticker"].astype(str).duplicated().any():
        failures.append("holdings:duplicate_ticker")
        return
    expected = evidence.final_weights.set_index(
        evidence.final_weights["ticker"].astype(str)
    )
    observed = holdings.set_index(holdings["ticker"].astype(str))
    unknown = observed.index.difference(expected.index)
    if len(unknown):
        failures.append(f"holdings:unknown_tickers={sorted(unknown)}")
        return
    expected_weights = pd.to_numeric(
        expected.loc[observed.index, "weight"], errors="coerce"
    ).to_numpy(dtype=float)
    observed_weights = pd.to_numeric(observed["weight"], errors="coerce").to_numpy(
        dtype=float
    )
    if not (
        np.isfinite(expected_weights).all()
        and np.isfinite(observed_weights).all()
        and np.allclose(expected_weights, observed_weights, atol=1e-10, rtol=0.0)
    ):
        failures.append("holdings:weight_mismatch")


def _build_executive_pdf(evidence: PublicationEvidence, path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        Flowable,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "QVTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=27,
        leading=31,
        textColor=colors.HexColor(INK),
        alignment=TA_LEFT,
        spaceAfter=12,
    )
    subtitle = ParagraphStyle(
        "QVSubtitle",
        parent=styles["BodyText"],
        fontSize=11,
        leading=16,
        textColor=colors.HexColor(MID),
        spaceAfter=12,
    )
    h1 = ParagraphStyle(
        "QVH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(INK),
        spaceBefore=5,
        spaceAfter=9,
    )
    h2 = ParagraphStyle(
        "QVH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor(BLUE),
        spaceBefore=6,
        spaceAfter=5,
    )
    body = ParagraphStyle(
        "QVBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor(INK),
        spaceAfter=5,
    )
    small = ParagraphStyle(
        "QVSmall",
        parent=body,
        fontSize=7.4,
        leading=10,
        textColor=colors.HexColor(MID),
    )
    center = ParagraphStyle(
        "QVCenter",
        parent=body,
        alignment=TA_CENTER,
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="QuantVerse v2 Executive Quantitative Research Report",
        author="QuantVerse",
    )
    story: list[Flowable] = []
    story.extend(
        _cover_story(evidence, title, subtitle, body, small, Table, TableStyle, colors)
    )
    story.append(PageBreak())

    final_row = _final_model_row(evidence)
    story.append(Paragraph("1. Executive Research Verdict", h1))
    story.append(
        _decision_banner(
            evidence,
            body,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(Spacer(1, 7))
    story.append(
        _metric_cards(
            [
                (
                    "OOS annualized return",
                    _pct(final_row.get("walk_forward_annualized_return")),
                    "Arithmetic annualized mean",
                ),
                (
                    "OOS volatility",
                    _pct(final_row.get("walk_forward_volatility")),
                    "Annualized daily volatility",
                ),
                (
                    "OOS Sharpe",
                    _num(final_row.get("walk_forward_sharpe")),
                    "Daily compounded RF hurdle",
                ),
                (
                    "OOS max drawdown",
                    _pct(final_row.get("walk_forward_max_drawdown")),
                    "Peak-to-trough loss",
                ),
            ],
            body,
            small,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("Decision interpretation", h2))
    story.append(
        Paragraph(
            _escape(str(evidence.decision.get("final_decision_reason", ""))),
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Critical warning:</b> high annualized returns and Sharpe ratios "
            "come from a short 252-observation OOS sample. They are estimates "
            "with material sampling and regime uncertainty, not expected future returns.",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("2. Portfolio Holdings and Concentration", h1))
    story.extend(
        _chart_block(
            evidence,
            "holdings",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    holdings = _final_holdings(evidence).head(12)
    story.append(
        _report_table(
            holdings,
            [
                "ticker",
                "name",
                "weight",
                "listing_country",
                "issuer_country",
                "economic_country",
            ],
            body,
            small,
            Table,
            TableStyle,
            colors,
            formats={"weight": _pct},
        )
    )
    story.append(
        Paragraph(
            f"Full holdings: {len(evidence.final_weights)}; weight sum: "
            f"{_num(_numeric(evidence.final_weights, 'weight').sum(), 8)}. "
            "The complete table is in the Excel workbook, not truncated in this report.",
            small,
        )
    )
    story.append(
        Paragraph(
            "<b>Exposure semantics:</b> Listing exposure identifies where the "
            "security trades. Issuer exposure identifies the issuer domicile. "
            "Economic exposure requires explicit supported business-exposure "
            "metadata and is never inferred from listing venue, trading currency "
            "or issuer domicile. Economic-country exposure is unavailable and is "
            "not inferred from listing venue, trading currency or issuer domicile.",
            small,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("3. Out-of-Sample Path Evidence", h1))
    story.extend(
        _chart_block(
            evidence,
            "equity",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.extend(
        _chart_block(
            evidence,
            "drawdown",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("4. Model Comparison", h1))
    story.extend(
        _chart_block(
            evidence,
            "risk_return",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    comparison = evidence.model_selection.sort_values(
        "book_grounded_rank", na_position="last"
    ).head(8)
    story.append(
        _report_table(
            comparison,
            [
                "model_name",
                "model_status",
                "walk_forward_sharpe",
                "walk_forward_max_drawdown",
                "uncertainty_gate_pass",
                "robustness_gate_pass",
            ],
            body,
            small,
            Table,
            TableStyle,
            colors,
            formats={
                "walk_forward_sharpe": _num,
                "walk_forward_max_drawdown": _pct,
            },
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("5. Uncertainty and Promotion Gates", h1))
    story.extend(
        _chart_block(
            evidence,
            "uncertainty",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(
        Paragraph(
            "Intervals crossing zero do not establish an active model's Sharpe "
            "improvement over Equal Weight. Current robustness is diagnostic "
            "configuration sensitivity, not promotion-grade nested OOS evidence.",
            body,
        )
    )
    story.extend(
        _chart_block(
            evidence,
            "random",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("6. Risk and Stress", h1))
    story.extend(
        _chart_block(
            evidence,
            "risk",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.extend(
        _chart_block(
            evidence,
            "stress",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("7. Exposure and Data Quality", h1))
    story.extend(
        _chart_block(
            evidence,
            "exposure",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(
        Paragraph(
            "<b>Listing exposure:</b> where securities trade. "
            "<b>Issuer exposure:</b> issuer legal domicile. "
            "<b>Economic exposure:</b> supported business-risk geography only. "
            "Economic-country exposure is unavailable and is not inferred from "
            "listing venue, trading currency or issuer domicile.",
            body,
        )
    )
    identity_status = _identity_summary(evidence)
    story.append(
        _metric_cards(
            [
                (
                    "Identity rows",
                    str(identity_status["rows"]),
                    "Security master audit",
                ),
                (
                    "Unresolved identity",
                    str(identity_status["unresolved"]),
                    "Blocks affected securities",
                ),
                (
                    "History ineligible",
                    str(identity_status["ineligible"]),
                    "Excluded from standard research",
                ),
                (
                    "Exact top-100",
                    "Unsupported",
                    "No official dated rank evidence",
                ),
            ],
            body,
            small,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("8. Forecast Diagnostics", h1))
    story.extend(
        _chart_block(
            evidence,
            "forecast",
            body,
            small,
            Image,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(
        Paragraph(
            "Lower MAE than a random-walk comparator is diagnostic evidence only. "
            "It does not establish net portfolio utility, calibration, or a promotable "
            "trading signal; negative R-squared values remain material warnings.",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("9. Limitations and Research Status", h1))
    limitations = [
        "Current-universe public data are not institutional point-in-time membership.",
        "Official dated exact market-cap top-100 support is unavailable.",
        "Complete delisting and institutional corporate-action history is unavailable.",
        "Nested promotion-grade robustness and formal multiple-testing correction are not implemented.",
        "The OOS path has approximately 252 observations and is regime-sensitive.",
        "Transaction costs are simplified; market impact, capacity, taxes and execution are outside scope.",
        "This is quantitative research, not investment advice; no live execution, "
        "order-management, monitoring or trading-system capability is claimed.",
    ]
    for item in limitations:
        story.append(Paragraph(f"- {_escape(item)}", body))
    story.append(Spacer(1, 8))
    story.append(
        _status_table(
            [
                ("Public-data research package", "ready with limitations"),
                ("Active-model promotion", "not supported"),
                ("Institutional/global master promotion", "not promoted"),
                ("Investment recommendation", "not provided"),
            ],
            body,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Read the methodology appendix and analytical Excel workbook before "
            "using any metric or holding outside the declared research context.",
            center,
        )
    )
    doc.build(
        story,
        onFirstPage=lambda canvas, current_doc: _page_frame(
            canvas, current_doc, evidence, executive=True
        ),
        onLaterPages=lambda canvas, current_doc: _page_frame(
            canvas, current_doc, evidence, executive=True
        ),
    )


def _build_methodology_pdf(evidence: PublicationEvidence, path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        Flowable,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "MethodTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor(INK),
        spaceAfter=12,
    )
    h1 = ParagraphStyle(
        "MethodH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor(INK),
        spaceBefore=5,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "MethodH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor(BLUE),
        spaceBefore=7,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "MethodBody",
        parent=styles["BodyText"],
        fontSize=8.2,
        leading=11.5,
        textColor=colors.HexColor(INK),
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "MethodSmall",
        parent=body,
        fontSize=7,
        leading=9.3,
        textColor=colors.HexColor(MID),
    )
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="QuantVerse v2 Scientific Methodology and Validation Appendix",
        author="QuantVerse",
    )
    story: list[Flowable] = [
        Spacer(1, 25 * mm),
        Paragraph("QuantVerse v2", title),
        Paragraph("Scientific Methodology and Validation Appendix", title),
        Paragraph(
            "Theory - formula - code - input - test - independent recomputation "
            "- output - reporting claim",
            body,
        ),
        Spacer(1, 12),
        _status_table(
            [
                ("Run ID", str(evidence.manifest.get("run_id"))),
                ("Data as of", str(evidence.manifest.get("data_as_of_date"))),
                ("Final research model", evidence.final_model),
                ("Portfolio promotion", evidence.final_decision),
            ],
            body,
            Table,
            TableStyle,
            colors,
        ),
        PageBreak(),
        Paragraph("1. Declared Scope and Evidence Boundary", h1),
        Paragraph(
            "QuantVerse is a public-data equity research and portfolio analytics "
            "system. It compares executable allocation methods using common "
            "constraints, chronological walk-forward evidence, transaction costs, "
            "risk metrics, uncertainty and constrained random portfolios.",
            body,
        ),
        Paragraph(
            "It does not claim institutional point-in-time membership, complete "
            "delisting coverage, official exact top-100 ranks, execution capacity, "
            "or future performance. Those limitations block stronger claims.",
            body,
        ),
        Paragraph("Run identity", h2),
        _status_table(
            [
                (field, str(evidence.manifest.get(field, "missing")))
                for field in RUN_IDENTITY_FIELDS
            ],
            small,
            Table,
            TableStyle,
            colors,
        ),
        PageBreak(),
        Paragraph("2. Methodology Source Basis", h1),
    ]
    books = _book_inventory(evidence.root)
    story.append(
        _report_table(
            books,
            ["source", "primary_contribution", "usage_boundary"],
            body,
            small,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(
        Paragraph(
            "No page-specific claim is made unless separately verified. The books "
            "ground method selection and validation rules; they do not prove that "
            "this implementation or empirical result is correct.",
            small,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("3. Formula and Unit Contracts", h1))
    formulas = _formula_rows()
    story.append(
        _report_table(
            formulas,
            ["metric", "implementation", "unit_sign", "validity", "invalidation"],
            body,
            small,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("4. Data Lineage and Missing-Data Policy", h1))
    for line in [
        "Source universe -> security identity/history gate -> adjusted prices -> "
        "simple/log return matrices -> feature eligibility -> stock scores -> "
        "covariance and model weights -> non-overlapping walk-forward returns -> "
        "costs and risk -> uncertainty and random benchmark -> model selection -> reports.",
        "Simple returns are used for linear portfolio aggregation. Log returns are "
        "used for statistical covariance diagnostics where explicitly labeled.",
        "Selected-weight return dates require complete available weight. Missing "
        "selected returns are not silently converted to zero.",
        "Current-universe evidence is not relabeled as historical point-in-time membership.",
    ]:
        story.append(Paragraph(_escape(line), body))
    story.append(
        _status_table(
            [
                ("Return missing policy", "complete_selected_weight_required"),
                ("FX policy", "native/listing USD equity scope in current final run"),
                (
                    "Corporate actions",
                    "provider-adjusted public prices; institutional reconciliation absent",
                ),
                ("Point-in-time membership", "not available"),
            ],
            body,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("5. Portfolio Models and Decision Status", h1))
    models = evidence.model_selection.copy()
    story.append(
        _report_table(
            models,
            [
                "model_name",
                "model_status",
                "selection_label",
                "walk_forward_sharpe",
                "uncertainty_gate_pass",
                "robustness_evidence_status",
                "rejection_reason",
            ],
            body,
            small,
            Table,
            TableStyle,
            colors,
            formats={"walk_forward_sharpe": _num},
            max_rows=20,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("6. Walk-Forward and Random Benchmark Protocol", h1))
    protocol = _protocol_rows(evidence)
    story.append(
        _status_table(
            protocol,
            body,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(Paragraph("Validation meaning", h2))
    story.append(
        Paragraph(
            "Fold test dates are concatenated once to form the stitched OOS net "
            "path. Model and random paths must share dates, selected-universe rules, "
            "constraints, maximum weights, rebalance schedule and transaction costs. "
            "A scope label without raw provenance is rejected.",
            body,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("7. Uncertainty and Multiple Testing", h1))
    story.append(
        Paragraph(
            "Paired circular block bootstrap preserves short-range dependence better "
            "than an IID resample and evaluates model-minus-Equal-Weight differences "
            "on common OOS dates. Confidence intervals crossing zero block claims of "
            "statistically established improvement.",
            body,
        )
    )
    story.append(
        _report_table(
            evidence.uncertainty,
            [
                "model_name",
                "paired_observations",
                "bootstrap_samples",
                "block_length",
                "sharpe_diff_ci_lower",
                "sharpe_diff_ci_upper",
                "probability_sharpe_improvement",
            ],
            body,
            small,
            Table,
            TableStyle,
            colors,
            formats={
                "sharpe_diff_ci_lower": _num,
                "sharpe_diff_ci_upper": _num,
                "probability_sharpe_improvement": _pct,
            },
            max_rows=20,
        )
    )
    story.append(
        Paragraph(
            "Formal Deflated Sharpe, SPA/Reality Check and Probability of Backtest "
            "Overfitting are not presented as completed. The conservative response "
            "to limited OOS history and multiple model comparisons is non-promotion.",
            small,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("8. Risk, Tail and Stress Contracts", h1))
    story.append(
        _report_table(
            evidence.risk,
            [
                "model_name",
                "observations",
                "cagr",
                "annualized_volatility",
                "sharpe",
                "sortino",
                "max_drawdown",
                "cvar_95",
                "extreme_metric_warning",
            ],
            body,
            small,
            Table,
            TableStyle,
            colors,
            formats={
                "cagr": _pct,
                "annualized_volatility": _pct,
                "sharpe": _num,
                "sortino": _num,
                "max_drawdown": _pct,
                "cvar_95": _pct,
            },
            max_rows=15,
        )
    )
    story.append(
        Paragraph(
            "Historical VaR/CVaR are daily simple-return quantiles and tail means. "
            "Negative values represent losses. Stress scenarios are stylized "
            "sensitivity diagnostics, not forecasts or historical replays.",
            small,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("9. Independent Validation and Invalidation", h1))
    reference_count = _safe_int(evidence.reference_summary.get("check_count"), 0)
    validation_rows = [
        (
            "Independent reference arithmetic",
            f"{reference_count} primitive-evidence checks; status=passed",
        ),
        ("Artifact validation", "run/hash/schema/claim and numerical gates"),
        ("Risk-free regression", "5% annual compounded daily hurdle"),
        ("Random provenance", "raw dates, folds, universe and protocol hashes"),
        ("Robustness", "fails closed unless promotion-grade nested OOS evidence"),
        ("Publication", "staged files, rollback and manifest-last hashes"),
    ]
    story.append(
        _status_table(
            validation_rows,
            body,
            Table,
            TableStyle,
            colors,
        )
    )
    invalidations = [
        "Any selected return silently filled with zero.",
        "Overlapping or duplicated stitched OOS test dates.",
        "A random benchmark with different dates, universe rules, caps or costs.",
        "Missing/stale/diagnostic robustness treated as positive evidence.",
        "Weights outside long-only, sum-to-one or configured cap constraints.",
        "Positive drawdown or CVaR sign inconsistent with the declared loss convention.",
        "A report package mixing run IDs, config hashes or input fingerprints.",
    ]
    for item in invalidations:
        story.append(Paragraph(f"- {_escape(item)}", body))
    story.append(PageBreak())
    story.append(Paragraph("10. Decision Register Summary", h1))
    decision_rows = pd.DataFrame(
        [
            {
                "decision_id": "QV2-DEC-001",
                "decision": "Robustness evidence fails closed",
                "status": "implemented",
            },
            {
                "decision_id": "QV2-DEC-002",
                "decision": "Random benchmark requires artifact-bound provenance",
                "status": "implemented",
            },
            {
                "decision_id": "QV2-DEC-003",
                "decision": "Daily compounded risk-free contract",
                "status": "implemented",
            },
            {
                "decision_id": "QV2-DEC-004",
                "decision": "Independent validation uses primitive evidence",
                "status": "implemented",
            },
            {
                "decision_id": "QV2-DEC-005",
                "decision": f"Current final research model: {evidence.final_model}",
                "status": evidence.final_decision,
            },
            {
                "decision_id": "QV2-DEC-006",
                "decision": "Artifacts publish as one verified package",
                "status": "implemented",
            },
        ]
    )
    story.append(
        _report_table(
            decision_rows,
            ["decision_id", "decision", "status"],
            body,
            small,
            Table,
            TableStyle,
            colors,
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("11. Residual Limitations", h1))
    for item in [
        "No institutional point-in-time constituent and delisting database.",
        "No complete institutional security master or corporate-action reconciliation.",
        "No exact dated official market-cap top-100 support.",
        "Short OOS sample and regime dependence.",
        "No promotion-grade nested robustness or formal multiple-testing correction.",
        "Simplified transaction costs; no market impact, borrow, taxes or capacity.",
        "Public-provider metadata and adjusted prices retain provider risk.",
    ]:
        story.append(Paragraph(f"- {_escape(item)}", body))
    story.append(
        Paragraph(
            "<b>Conclusion:</b> the package is suitable for transparent public-data "
            "research with explicit limitations. It is not an institutional production "
            "trading system and does not provide investment advice.",
            body,
        )
    )
    doc.build(
        story,
        onFirstPage=lambda canvas, current_doc: _page_frame(
            canvas, current_doc, evidence, executive=False
        ),
        onLaterPages=lambda canvas, current_doc: _page_frame(
            canvas, current_doc, evidence, executive=False
        ),
    )


def _build_html(evidence: PublicationEvidence, path: Path) -> None:
    final_row = _final_model_row(evidence)
    charts: dict[str, str] = {}
    for spec in _chart_specs(evidence):
        figure = _make_chart(evidence, spec.key)
        svg = _figure_svg(figure)
        charts[spec.key] = f"""
            <article class="chart-card" id="{html.escape(spec.key)}">
              <div class="section-kicker">EVIDENCE VIEW</div>
              <h3>{html.escape(spec.title)}</h3>
              <div class="chart">{svg}</div>
              <dl class="chart-contract">
                <div><dt>Method</dt><dd>{html.escape(spec.method)}</dd></div>
                <div><dt>Interpretation</dt><dd>{html.escape(spec.interpretation)}</dd></div>
                <div><dt>Limitation</dt><dd>{html.escape(spec.limitation)}</dd></div>
                <div><dt>Invalidation</dt><dd>{html.escape(spec.invalidation)}</dd></div>
              </dl>
            </article>
            """
    model_table = _html_table(
        evidence.model_selection,
        [
            "model_name",
            "model_status",
            "walk_forward_annualized_return",
            "walk_forward_sharpe",
            "walk_forward_max_drawdown",
            "uncertainty_gate_pass",
            "robustness_evidence_status",
            "selection_label",
        ],
        max_rows=20,
    )
    holdings_table = _html_table(
        _final_holdings(evidence),
        [
            "ticker",
            "name",
            "weight",
            "sector",
            "industry",
            "listing_country",
            "issuer_country",
            "economic_country",
            "risk_contribution_pct",
        ],
        max_rows=100,
    )
    limitations = "".join(
        f"<li>{html.escape(item)}</li>"
        for item in [
            "No institutional point-in-time membership or complete delisting history.",
            "No official dated exact market-cap top-100 evidence.",
            "Short OOS history and material regime/sampling uncertainty.",
            "Robustness remains diagnostic, not nested promotion-grade evidence.",
            "Transaction costs are simplified; no market impact or capacity model.",
            "Research only; not investment advice; no live execution, order-management, "
            "monitoring or trading-system capability is claimed.",
        ]
    )
    navigation = "".join(
        f'<a href="#{key}">{html.escape(label)}</a>'
        for key, label in [
            ("executive", "Executive verdict"),
            ("portfolio", "Portfolio"),
            ("equity", "OOS path"),
            ("risk_return", "Model comparison"),
            ("uncertainty", "Uncertainty"),
            ("random", "Random benchmark"),
            ("risk", "Risk"),
            ("exposure", "Exposure"),
            ("forecast", "Forecasts"),
            ("methodology", "Methodology"),
            ("limitations", "Limitations"),
        ]
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QuantVerse v2 Research Report</title>
  <style>
    :root {{
      --ink:{INK}; --blue:{BLUE}; --teal:{TEAL}; --gold:{GOLD};
      --red:{RED}; --light:{LIGHT}; --mid:{MID}; --white:{WHITE};
    }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:#eef2f3; color:var(--ink);
      font-family:Inter,Segoe UI,Arial,sans-serif; line-height:1.55; }}
    .layout {{ display:grid; grid-template-columns:240px minmax(0,1fr);
      width:100%; min-width:0; min-height:100vh; }}
    aside {{ position:sticky; top:0; height:100vh; padding:28px 20px;
      min-width:0; background:var(--ink); color:white; overflow:auto; }}
    .brand {{ font-size:22px; font-weight:800; margin-bottom:4px; }}
    .brand-sub {{ color:#b8c6cb; font-size:12px; margin-bottom:24px; }}
    nav {{ display:grid; gap:4px; }}
    nav a {{ color:#dbe6e9; text-decoration:none; padding:7px 8px;
      border-left:2px solid transparent; font-size:13px; }}
    nav a:hover {{ border-color:var(--gold); background:#20343e; }}
    main {{ width:min(1180px,100%); min-width:0; max-width:100%;
      padding:34px 42px 70px; }}
    .hero {{ background:var(--white); border-top:6px solid var(--teal);
      padding:34px; box-shadow:0 10px 30px rgba(23,37,46,.08); }}
    .kicker,.section-kicker {{ color:var(--blue); font-weight:800;
      font-size:11px; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ font-size:38px; line-height:1.1; margin:8px 0 14px; }}
    h2 {{ margin:42px 0 14px; font-size:26px; }}
    h3 {{ margin:5px 0 14px; font-size:19px; }}
    .verdict {{ display:inline-block; margin:12px 0; padding:8px 12px;
      background:{SOFT_GOLD}; color:#6b5300; border-left:4px solid var(--gold);
      font-weight:800; }}
    .meta {{ color:var(--mid); font-size:13px; overflow-wrap:anywhere; }}
    .cards {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr));
      gap:12px; margin:18px 0; }}
    .card {{ background:white; border-top:3px solid var(--blue); padding:16px;
      box-shadow:0 5px 16px rgba(23,37,46,.07); }}
    .card span {{ color:var(--mid); font-size:12px; }}
    .card strong {{ display:block; font-size:24px; margin-top:4px; }}
    .warning {{ background:{SOFT_RED}; border-left:5px solid var(--red);
      padding:16px 18px; margin:18px 0; }}
    .chart-grid {{ display:grid; grid-template-columns:1fr; gap:18px; }}
    .chart-card {{ min-width:0; background:white; padding:22px;
      box-shadow:0 6px 20px rgba(23,37,46,.07); scroll-margin-top:20px; }}
    .chart svg {{ width:100%; height:auto; display:block; }}
    .chart-contract {{ display:grid; grid-template-columns:1fr 1fr; gap:8px;
      margin:14px 0 0; }}
    .chart-contract div {{ background:var(--light); padding:9px 11px; }}
    dt {{ font-size:11px; color:var(--blue); font-weight:800; }}
    dd {{ margin:3px 0 0; font-size:12px; }}
    .table-wrap {{ width:100%; min-width:0; max-width:100%; overflow-x:auto;
      background:white; padding:10px;
      box-shadow:0 5px 16px rgba(23,37,46,.06); }}
    table {{ border-collapse:collapse; width:100%; min-width:900px; font-size:12px; }}
    th {{ position:sticky; top:0; background:var(--ink); color:white;
      text-align:left; padding:9px; }}
    td {{ border-bottom:1px solid #dce3e5; padding:8px 9px; vertical-align:top; }}
    tr:nth-child(even) {{ background:#f7f9fa; }}
    details {{ background:white; margin:10px 0; padding:14px 16px; }}
    summary {{ cursor:pointer; color:var(--blue); font-weight:800; }}
    footer {{ margin-top:45px; color:var(--mid); font-size:12px; }}
    @media (max-width:900px) {{
      .layout {{ grid-template-columns:minmax(0,1fr); }}
      aside {{ position:relative; width:100%; max-width:100%; height:auto; }}
      nav {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      nav a {{ min-width:0; overflow-wrap:anywhere; }}
      main {{ width:100%; padding:20px 14px 50px; }}
      .cards {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      .chart-contract {{ grid-template-columns:1fr; }}
      h1 {{ font-size:31px; }}
    }}
    @media (max-width:520px) {{
      nav {{ grid-template-columns:1fr; }}
      .hero {{ padding:24px 18px; }}
      .cards {{ grid-template-columns:1fr; }}
      .chart-card {{ padding:16px 12px; }}
      h1 {{ font-size:28px; overflow-wrap:anywhere; }}
      h2 {{ font-size:23px; }}
    }}
  </style>
</head>
<body>
<div class="layout">
  <aside>
    <div class="brand">QuantVerse v2</div>
    <div class="brand-sub">Public-data quantitative research</div>
    <nav>{navigation}</nav>
  </aside>
  <main>
    <header class="hero" id="executive">
      <div class="kicker">Executive Summary</div>
      <h1>Evidence before promotion.</h1>
      <div class="verdict">{html.escape(evidence.final_model)} / {html.escape(evidence.final_decision)}</div>
      <p>{html.escape(str(evidence.decision.get("final_decision_reason", "")))}</p>
      <div class="meta">Run {html.escape(str(evidence.manifest.get("run_id")))}
      | Data as of {html.escape(str(evidence.manifest.get("data_as_of_date")))}
      | Current-universe public data, not institutional PIT evidence</div>
    </header>
    <section class="cards">
      <div class="card"><span>OOS annualized return</span><strong>{_pct(final_row.get("walk_forward_annualized_return"))}</strong></div>
      <div class="card"><span>OOS volatility</span><strong>{_pct(final_row.get("walk_forward_volatility"))}</strong></div>
      <div class="card"><span>OOS Sharpe</span><strong>{_num(final_row.get("walk_forward_sharpe"))}</strong></div>
      <div class="card"><span>OOS max drawdown</span><strong>{_pct(final_row.get("walk_forward_max_drawdown"))}</strong></div>
    </section>
    <div class="warning"><b>Metric warning.</b> The OOS path is short and regime-sensitive.
    High annualized metrics are estimates with material uncertainty, not expected future performance.</div>
    <h2 id="portfolio">Portfolio holdings</h2>
    <p>All {len(evidence.final_weights)} holdings are shown below. Weights are research allocations, not buy recommendations.</p>
    <p><b>Listing exposure</b> identifies where the security trades.
    <b>Issuer exposure</b> identifies issuer domicile.
    <b>Economic exposure</b> requires explicit supported business-risk metadata.
    Economic-country exposure is unavailable and is not inferred from listing venue,
    trading currency or issuer domicile.</p>
    <div class="table-wrap">{holdings_table}</div>
    <h2>Visual Portfolio Analytics</h2>
    <h2>Portfolio Holdings</h2>
    <div class="chart-grid">{charts['holdings']}</div>
    <h2>Equity Curve and Drawdown</h2>
    <div class="chart-grid">{charts['equity']}{charts['drawdown']}</div>
    <h2>Model Risk-Return Map</h2>
    <div class="chart-grid">{charts['risk_return']}</div>
    <h2>Uncertainty</h2>
    <div class="chart-grid">{charts['uncertainty']}</div>
    <h2>Random Benchmark Distribution</h2>
    <div class="chart-grid">{charts['random']}</div>
    <h2>Risk and Stress Tests</h2>
    <div class="chart-grid">{charts['risk']}{charts['stress']}</div>
    <h2>Exposure and Concentration</h2>
    <div class="chart-grid">{charts['exposure']}</div>
    <p><b>Listing exposure</b>, <b>issuer exposure</b> and
    <b>economic exposure</b> are separate concepts; one is never silently
    substituted for another.</p>
    <h2>Forecast Error Versus Random Walk</h2>
    <div class="chart-grid">{charts['forecast']}</div>
    <h2 id="methodology">Portfolio Model League and Robust Model Selection</h2>
    <div class="table-wrap">{model_table}</div>
    <details open><summary>Stock Scoring Methodology</summary>
      <p>Trailing features are eligibility-gated and use past information only.
      Securities with insufficient history remain diagnostic and are not silently
      ranked as seasoned securities. Listing, issuer and economic exposure concepts
      remain separate.</p></details>
    <details><summary>Walk-Forward methodology</summary>
      <p>Non-overlapping test folds are concatenated into one net OOS path.
      Costs, universe rules, constraints and dates are bound to the random benchmark
      provenance. Paired block bootstrap intervals assess model-minus-benchmark uncertainty.</p></details>
    <details><summary>Security Identity and History Eligibility</summary>
      <p>Ticker strings are not permanent identifiers. Known listing-history conflicts,
      pre-listing observations and insufficient feature history block standard selection.</p></details>
    <h2 id="limitations">Limitations</h2>
    <ul>{limitations}</ul>
    <footer>QuantVerse v2 | Research only | Not investment advice |
    Run {html.escape(str(evidence.manifest.get("run_id")))}</footer>
  </main>
</div>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def _chart_specs(evidence: PublicationEvidence) -> list[ChartSpec]:
    return [
        _spec_from_frame(
            "holdings",
            "Final portfolio weights",
            evidence.holdings,
            "Weights expose capital concentration and exact holdings.",
        ),
        _spec_from_frame(
            "equity",
            "Stitched OOS cumulative wealth",
            evidence.equity,
            "The path shows realized compounding on non-overlapping OOS dates.",
        ),
        _spec_from_frame(
            "drawdown",
            "Stitched OOS drawdown",
            evidence.drawdown,
            "Drawdown shows path-dependent capital loss relative to the prior peak.",
        ),
        _spec_from_frame(
            "risk_return",
            "Model risk-return map",
            evidence.risk_return,
            "Risk is on the x-axis and return is on the y-axis; no raw-return-only ranking.",
        ),
        ChartSpec(
            key="uncertainty",
            title="Paired Sharpe-difference confidence intervals",
            method="Paired circular block bootstrap on common stitched OOS dates; interval is model Sharpe minus Equal Weight Sharpe.",
            interpretation="An interval crossing zero does not establish a positive Sharpe improvement.",
            limitation="Approximately 252 OOS observations and one public-data regime limit precision.",
            invalidation="Invalid if paths are unpaired, dates differ, blocks are IID relabeled, or test evidence selected the model.",
        ),
        _spec_from_frame(
            "random",
            "Same-protocol random portfolio benchmark",
            evidence.random_benchmark,
            "The final model is contextualized within constrained OOS net random outcomes.",
        ),
        ChartSpec(
            key="risk",
            title="Final-model return and loss metrics",
            method="Arithmetic annualized return, annualized volatility, historical daily VaR/CVaR and maximum drawdown from persisted simple returns.",
            interpretation="Return must be read jointly with volatility, drawdown and tail loss.",
            limitation="Historical tail estimates are sample-dependent and do not cover all future crises.",
            invalidation="Invalid if units or signs are mixed, CVaR is less adverse than VaR, or returns are silently zero-filled.",
        ),
        ChartSpec(
            key="stress",
            title="Stylized stress impacts",
            method="Predefined scenario shocks are applied to the portfolio exposure mapping.",
            interpretation="Negative bars show sensitivity to declared shocks, not forecast probabilities.",
            limitation="Stylized scenarios are not historical replays and omit nonlinear market dynamics.",
            invalidation="Invalid if presented as a probability forecast or if exposure mappings are stale.",
        ),
        _spec_from_frame(
            "exposure",
            "Sector exposure",
            evidence.exposure,
            "Sector aggregation reveals concentration that ticker counts alone can hide.",
        ),
        _spec_from_frame(
            "forecast",
            "Forecast error versus random walk",
            evidence.forecast_error,
            "A model must be compared with a naive time-series baseline on the same target scale.",
        ),
    ]


def _spec_from_frame(
    key: str,
    title: str,
    frame: pd.DataFrame,
    fallback_interpretation: str,
) -> ChartSpec:
    row = frame.iloc[0] if not frame.empty else pd.Series(dtype=object)
    return ChartSpec(
        key=key,
        title=title,
        method=str(row.get("formula_method", "Declared chart calculation.")),
        interpretation=fallback_interpretation,
        limitation=str(
            row.get(
                "limitation", "Public-data research evidence remains sample-dependent."
            )
        ),
        invalidation=str(
            row.get(
                "invalidation_condition",
                "Invalid if source evidence is missing, stale or uses a different run.",
            )
        ),
    )


def _make_chart(evidence: PublicationEvidence, key: str) -> Figure:
    factories: dict[str, Callable[[PublicationEvidence], Figure]] = {
        "holdings": _holdings_figure,
        "equity": _equity_figure,
        "drawdown": _drawdown_figure,
        "risk_return": _risk_return_figure,
        "uncertainty": _uncertainty_figure,
        "random": _random_figure,
        "risk": _risk_figure,
        "stress": _stress_figure,
        "exposure": _exposure_figure,
        "forecast": _forecast_figure,
    }
    return factories[key](evidence)


def _base_figure(figsize: tuple[float, float] = (8.6, 3.5)) -> tuple[Figure, Axes]:
    fig, axis = plt.subplots(figsize=figsize, constrained_layout=True)
    fig.patch.set_facecolor(WHITE)
    axis.set_facecolor(WHITE)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(colors=MID, labelsize=8)
    axis.grid(axis="y", color="#DDE4E7", linewidth=0.7, alpha=0.8)
    return fig, axis


def _holdings_figure(evidence: PublicationEvidence) -> Figure:
    frame = _final_holdings(evidence).sort_values("weight", ascending=False).head(15)
    frame = frame.sort_values("weight")
    fig, axis = _base_figure((8.6, 4.2))
    axis.barh(
        frame.get("ticker", pd.Series(dtype=str)).astype(str),
        _numeric(frame, "weight") * 100,
        color=TEAL,
    )
    axis.set_xlabel("Portfolio weight (%)", color=MID, fontsize=8)
    axis.set_title(
        f"{evidence.final_model}: largest 15 holdings",
        loc="left",
        color=INK,
        fontweight="bold",
    )
    return fig


def _equity_figure(evidence: PublicationEvidence) -> Figure:
    frame = evidence.equity.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    fig, axis = _base_figure()
    axis.plot(frame["date"], _numeric(frame, "equity_curve"), color=BLUE, linewidth=2)
    axis.axhline(1.0, color=MID, linewidth=0.8, linestyle="--")
    axis.set_ylabel("Cumulative wealth", color=MID, fontsize=8)
    axis.set_title(
        "Normalized OOS equity curve (start = 1.0)",
        loc="left",
        color=INK,
        fontweight="bold",
    )
    return fig


def _drawdown_figure(evidence: PublicationEvidence) -> Figure:
    frame = evidence.drawdown.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    values = _numeric(frame, "drawdown") * 100
    fig, axis = _base_figure()
    axis.fill_between(frame["date"], values, 0, color=RED, alpha=0.32)
    axis.plot(frame["date"], values, color=RED, linewidth=1.2)
    axis.set_ylim(min(float(values.min()) * 1.15, -1.0), 0.5)
    axis.set_ylabel("Drawdown (%)", color=MID, fontsize=8)
    axis.set_title(
        "OOS drawdown (non-positive)", loc="left", color=INK, fontweight="bold"
    )
    return fig


def _risk_return_figure(evidence: PublicationEvidence) -> Figure:
    frame = evidence.risk_return.copy()
    x = _numeric(frame, "risk_x") * 100
    y = _numeric(frame, "return_y") * 100
    fig, axis = _base_figure((8.6, 4.4))
    colors = [
        GOLD if _truthy(value) else TEAL
        for value in frame.get("is_final_model", pd.Series(False, index=frame.index))
    ]
    axis.scatter(x, y, c=colors, s=65, edgecolor=INK, linewidth=0.6, zorder=3)
    for position, row in enumerate(frame.to_dict(orient="records")):
        axis.annotate(
            str(row.get("model_name", "")),
            (float(x.iloc[position]), float(y.iloc[position])),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=6.5,
            color=INK,
        )
    axis.set_xlabel("Annualized volatility (%)", color=MID, fontsize=8)
    axis.set_ylabel("Annualized realized return (%)", color=MID, fontsize=8)
    axis.set_title(
        "Risk on x-axis; return on y-axis", loc="left", color=INK, fontweight="bold"
    )
    return fig


def _uncertainty_figure(evidence: PublicationEvidence) -> Figure:
    frame = evidence.uncertainty.copy()
    frame = frame.loc[
        frame["model_name"].astype(str).ne("Equal Weight")
        & pd.to_numeric(frame["sharpe_diff_ci_lower"], errors="coerce").notna()
    ].copy()
    frame = frame.sort_values("sharpe_diff_ci_lower").tail(8)
    lower = _numeric(frame, "sharpe_diff_ci_lower")
    upper = _numeric(frame, "sharpe_diff_ci_upper")
    midpoint = (lower + upper) / 2
    fig, axis = _base_figure((8.6, 4.2))
    positions = np.arange(len(frame))
    axis.errorbar(
        midpoint,
        positions,
        xerr=np.vstack([midpoint - lower, upper - midpoint]),
        fmt="o",
        color=BLUE,
        ecolor=TEAL,
        capsize=3,
    )
    axis.axvline(0, color=RED, linestyle="--", linewidth=1)
    axis.set_yticks(positions, frame["model_name"].astype(str), fontsize=7)
    axis.set_xlabel("Sharpe difference versus Equal Weight", color=MID, fontsize=8)
    axis.set_title(
        "95% paired block-bootstrap intervals", loc="left", color=INK, fontweight="bold"
    )
    return fig


def _random_figure(evidence: PublicationEvidence) -> Figure:
    frame = evidence.random_benchmark.copy()
    left = _numeric(frame, "bucket_left")
    right = _numeric(frame, "bucket_right")
    counts = _numeric(frame, "portfolio_count")
    widths = right - left
    final_value = _first_numeric(frame, "final_model_value")
    percentile = _first_numeric(frame, "final_model_percentile")
    fig, axis = _base_figure((8.6, 4.0))
    axis.bar(left, counts, width=widths, align="edge", color=BLUE, alpha=0.82)
    axis.axvline(final_value, color=GOLD, linewidth=2)
    axis.text(
        final_value,
        max(float(counts.max()), 1.0) * 0.9,
        f"Final model\n{percentile:.1%} percentile",
        fontsize=8,
        color=INK,
        ha="center",
        bbox={"facecolor": SOFT_GOLD, "edgecolor": GOLD, "pad": 4},
    )
    axis.set_xlabel("Same-protocol OOS net Sharpe", color=MID, fontsize=8)
    axis.set_ylabel("Random portfolios", color=MID, fontsize=8)
    axis.set_title(
        "Constrained random benchmark distribution",
        loc="left",
        color=INK,
        fontweight="bold",
    )
    return fig


def _risk_figure(evidence: PublicationEvidence) -> Figure:
    row = evidence.final_risk
    labels = ["Ann. return", "Volatility", "|Max DD|", "|CVaR 95|"]
    values = [
        _safe_float(row.get("annualized_return")) * 100,
        _safe_float(row.get("annualized_volatility")) * 100,
        abs(_safe_float(row.get("max_drawdown"))) * 100,
        abs(_safe_float(row.get("cvar_95"))) * 100,
    ]
    fig, axis = _base_figure()
    axis.bar(labels, values, color=[BLUE, TEAL, RED, GOLD])
    axis.set_ylabel("Percent", color=MID, fontsize=8)
    axis.set_title(
        "Return and risk must be read together",
        loc="left",
        color=INK,
        fontweight="bold",
    )
    return fig


def _stress_figure(evidence: PublicationEvidence) -> Figure:
    frame = _stress_plot_frame(evidence)
    fig, axis = _base_figure()
    axis.barh(
        frame.get("Scenario", pd.Series(dtype=str)).astype(str),
        _numeric(frame, "Portfolio_Impact") * 100,
        color=RED,
        alpha=0.78,
    )
    axis.axvline(0, color=MID, linewidth=0.8)
    axis.set_xlabel("Stylized portfolio impact (%)", color=MID, fontsize=8)
    axis.set_title(
        "Scenario sensitivity, not forecast probability",
        loc="left",
        color=INK,
        fontweight="bold",
    )
    return fig


def _stress_plot_frame(evidence: PublicationEvidence) -> pd.DataFrame:
    """Normalize only declared stress schemas and retain the final model."""
    frame = evidence.stress.copy()
    current = {"model_name", "scenario", "portfolio_loss_estimate"}
    legacy = {"Scenario", "Portfolio_Impact"}
    if current.issubset(frame.columns):
        frame = frame.loc[
            frame["model_name"].astype(str).eq(evidence.final_model)
        ].rename(
            columns={
                "scenario": "Scenario",
                "portfolio_loss_estimate": "Portfolio_Impact",
            }
        )
    elif not legacy.issubset(frame.columns):
        raise ValueError(
            "Stress chart requires current model_name/scenario/"
            "portfolio_loss_estimate columns or the declared legacy schema."
        )
    frame["Scenario"] = frame["Scenario"].astype(str).str.strip()
    frame["Portfolio_Impact"] = pd.to_numeric(
        frame["Portfolio_Impact"], errors="coerce"
    )
    frame = frame.loc[
        frame["Scenario"].ne("") & frame["Portfolio_Impact"].notna(),
        ["Scenario", "Portfolio_Impact"],
    ].copy()
    if frame.empty:
        raise ValueError(
            f"Stress chart has no finite scenarios for final model {evidence.final_model}."
        )
    return frame.sort_values("Portfolio_Impact")


def _exposure_figure(evidence: PublicationEvidence) -> Figure:
    frame = evidence.exposure.loc[
        evidence.exposure["exposure_type"].astype(str).eq("sector")
    ].copy()
    frame = frame.sort_values("weight").tail(12)
    fig, axis = _base_figure((8.6, 4.1))
    axis.barh(frame["bucket"].astype(str), _numeric(frame, "weight") * 100, color=TEAL)
    axis.set_xlabel("Portfolio weight (%)", color=MID, fontsize=8)
    axis.set_title("Sector concentration", loc="left", color=INK, fontweight="bold")
    return fig


def _forecast_figure(evidence: PublicationEvidence) -> Figure:
    frame = evidence.forecast_error.copy().sort_values("horizon_days")
    positions = np.arange(len(frame))
    width = 0.36
    fig, axis = _base_figure((8.6, 3.8))
    axis.bar(
        positions - width / 2,
        _numeric(frame, "model_mae"),
        width,
        label="Model MAE",
        color=BLUE,
    )
    axis.bar(
        positions + width / 2,
        _numeric(frame, "random_walk_mae"),
        width,
        label="Random-walk MAE",
        color=GOLD,
    )
    axis.set_xticks(positions, frame["horizon"].astype(str))
    axis.set_ylabel("Error in target return units", color=MID, fontsize=8)
    axis.legend(frameon=False, fontsize=8)
    axis.set_title(
        "Forecast diagnostic versus naive baseline",
        loc="left",
        color=INK,
        fontweight="bold",
    )
    return fig


def _chart_block(
    evidence: PublicationEvidence,
    key: str,
    body,
    small,
    image_cls,
    table_cls,
    table_style_cls,
    colors,
) -> list[Flowable]:
    from reportlab.platypus import Paragraph, Spacer

    spec = next(item for item in _chart_specs(evidence) if item.key == key)
    figure = _make_chart(evidence, key)
    buffer = _figure_png(figure)
    image = image_cls(buffer, width=175 * 2.8346, height=78 * 2.8346)
    caption = table_cls(
        [
            ["Method", _escape(spec.method)],
            ["Interpretation", _escape(spec.interpretation)],
            ["Limitation", _escape(spec.limitation)],
            ["Invalidation", _escape(spec.invalidation)],
        ],
        colWidths=[76, 420],
    )
    caption.setStyle(
        table_style_cls(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LIGHT)),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(BLUE)),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.6),
                ("LEADING", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D8E0E3")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [Paragraph(spec.title, body), image, Spacer(1, 3), caption, Spacer(1, 8)]


def _cover_story(
    evidence,
    title,
    subtitle,
    body,
    small,
    table_cls,
    table_style_cls,
    colors,
) -> list[Flowable]:
    from reportlab.platypus import Paragraph, Spacer

    return [
        Spacer(1, 34),
        Paragraph("QUANTVERSE v2", title),
        Paragraph("Executive Quantitative Research Report", title),
        Paragraph(
            "Public-data equity research | Portfolio construction | "
            "Walk-forward validation | Risk | Model governance",
            subtitle,
        ),
        Spacer(1, 20),
        _decision_banner(evidence, body, table_cls, table_style_cls, colors),
        Spacer(1, 16),
        _status_table(
            [
                ("Run ID", str(evidence.manifest.get("run_id"))),
                ("Data as of", str(evidence.manifest.get("data_as_of_date"))),
                (
                    "Universe snapshot",
                    str(evidence.manifest.get("universe_snapshot_id")),
                ),
                ("Data snapshot", str(evidence.manifest.get("data_snapshot_id"))),
                ("Final research model", evidence.final_model),
                ("Decision", evidence.final_decision),
            ],
            small,
            table_cls,
            table_style_cls,
            colors,
        ),
        Spacer(1, 24),
        Paragraph(
            "<b>Evidence boundary.</b> Current-universe public-data research; "
            "not institutional point-in-time evidence, not an official exact "
            "top-100 portfolio, not investment advice.",
            body,
        ),
    ]


def _decision_banner(evidence, body, table_cls, table_style_cls, colors):
    from reportlab.platypus import Paragraph

    table = table_cls(
        [
            [
                Paragraph(
                    f"<b>CURRENT RESEARCH MODEL</b><br/>{_escape(evidence.final_model)}",
                    body,
                ),
                Paragraph(
                    "<b>PORTFOLIO PROMOTION</b><br/>"
                    + _escape(evidence.final_decision.upper()),
                    body,
                ),
            ]
        ],
        colWidths=[248, 248],
    )
    table.setStyle(
        table_style_cls(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(SOFT_BLUE)),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(SOFT_GOLD)),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(INK)),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("LEADING", (0, 0), (-1, -1), 16),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CAD7DC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def _metric_cards(items, body, small, table_cls, table_style_cls, colors):
    from reportlab.platypus import Paragraph

    cells = []
    for label, value, note in items:
        cells.append(
            Paragraph(
                f"<font color='{BLUE}'><b>{_escape(label)}</b></font><br/>"
                f"<font size='15'><b>{_escape(value)}</b></font><br/>"
                f"<font color='{MID}' size='6'>{_escape(note)}</font>",
                body,
            )
        )
    table = table_cls([cells], colWidths=[124] * len(cells))
    table.setStyle(
        table_style_cls(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CDD8DC")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CDD8DC")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _status_table(rows, style, table_cls, table_style_cls, colors):
    from reportlab.platypus import Paragraph

    table = table_cls(
        [
            [
                Paragraph(_escape(label), style),
                Paragraph(_escape(value), style),
            ]
            for label, value in rows
        ],
        colWidths=[145, 351],
    )
    table.setStyle(
        table_style_cls(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(LIGHT)),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(BLUE)),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
                ("LEADING", (0, 0), (-1, -1), 9.5),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D7E0E3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _report_table(
    frame: pd.DataFrame,
    columns: Iterable[str],
    body,
    small,
    table_cls,
    table_style_cls,
    colors,
    *,
    formats: dict[str, Callable[[object], str]] | None = None,
    max_rows: int = 12,
):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    selected = [column for column in columns if column in frame]
    limited = frame[selected].head(max_rows).copy() if selected else pd.DataFrame()
    header_style = ParagraphStyle(
        "QVTableHeader",
        parent=small,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        fontSize=6.0,
        leading=7.3,
    )
    cell_style = ParagraphStyle(
        "QVTableCell",
        parent=small,
        textColor=colors.HexColor(INK),
        fontSize=5.8,
        leading=7.2,
    )
    header = [
        Paragraph(_escape(column.replace("_", " ").title()), header_style)
        for column in selected
    ]
    rows = []
    formatters = formats or {}
    for _, row in limited.iterrows():
        rows.append(
            [
                Paragraph(
                    _escape(
                        formatters[column](row[column])
                        if column in formatters
                        else _display_value(row[column])
                    ),
                    cell_style,
                )
                for column in selected
            ]
        )
    if not selected:
        header = [Paragraph("Evidence", header_style)]
        rows = [[Paragraph("Not available", cell_style)]]
    widths = _column_widths(selected or ["evidence"], total=496)
    table = table_cls([header, *rows], repeatRows=1, colWidths=widths)
    table.setStyle(
        table_style_cls(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INK)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.2),
                ("LEADING", (0, 0), (-1, -1), 8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F6F8F9")],
                ),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D3DDE0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _column_widths(columns: list[str], total: float) -> list[float]:
    long_tokens = ("reason", "warning", "status", "name", "decision")
    weights = [
        2.0 if any(token in column.lower() for token in long_tokens) else 1.0
        for column in columns
    ]
    scale = total / sum(weights)
    return [weight * scale for weight in weights]


def _page_frame(canvas, doc, evidence: PublicationEvidence, *, executive: bool) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4

    canvas.saveState()
    width, height = A4
    canvas.setFillColor(HexColor(INK))
    canvas.rect(0, height - 11, width, 11, fill=1, stroke=0)
    canvas.setStrokeColor(HexColor("#D5DEE1"))
    canvas.line(45, 35, width - 45, 35)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(HexColor(MID))
    label = "EXECUTIVE RESEARCH" if executive else "METHODOLOGY AND VALIDATION"
    canvas.drawString(45, 23, f"QuantVerse v2 | {label}")
    canvas.drawRightString(
        width - 45,
        23,
        f"Run {str(evidence.manifest.get('run_id'))[-18:]} | Page {doc.page}",
    )
    canvas.restoreState()


def _final_model_row(evidence: PublicationEvidence) -> pd.Series:
    rows = evidence.model_selection.loc[
        evidence.model_selection["model_name"].astype(str).eq(evidence.final_model)
    ]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)


def _final_holdings(evidence: PublicationEvidence) -> pd.DataFrame:
    if (
        not evidence.holdings.empty
        and "model_name" in evidence.holdings
        and evidence.holdings["model_name"].astype(str).eq(evidence.final_model).any()
    ):
        return evidence.holdings.loc[
            evidence.holdings["model_name"].astype(str).eq(evidence.final_model)
        ].copy()
    return evidence.final_weights.copy()


def _identity_summary(evidence: PublicationEvidence) -> dict[str, int]:
    unresolved = 0
    if "identity_continuity_status" in evidence.identity:
        status = evidence.identity["identity_continuity_status"].astype(str).str.lower()
        unresolved = int(status.str.contains("uncertain|unresolved|blocked").sum())
    ineligible = 0
    if "standard_scoring_eligible" in evidence.eligibility:
        ineligible = int(
            (~evidence.eligibility["standard_scoring_eligible"].map(_truthy)).sum()
        )
    return {
        "rows": int(len(evidence.identity)),
        "unresolved": unresolved,
        "ineligible": ineligible,
    }


def _protocol_rows(evidence: PublicationEvidence) -> list[tuple[str, str]]:
    row = _final_model_row(evidence)
    provenance = evidence.random_provenance
    return [
        ("OOS observations", _display_value(row.get("paired_oos_observations"))),
        ("Random scope", _display_value(row.get("random_benchmark_scope"))),
        (
            "Random provenance",
            _display_value(row.get("random_benchmark_provenance_status")),
        ),
        ("Protocol hash", _display_value(row.get("random_benchmark_protocol_hash"))),
        ("Folds", _display_value(provenance.get("fold_count"))),
        (
            "Transaction cost",
            f"{_display_value(provenance.get('transaction_cost_bps'))} bps",
        ),
        ("Max weight", _pct(provenance.get("max_weight"))),
        ("Risk-free policy", _display_value(provenance.get("risk_free_policy"))),
    ]


def _book_inventory(root: Path) -> pd.DataFrame:
    book_dir = root.parent / "book"
    contributions = {
        "portfolio": (
            "Portfolio optimization, constraints, covariance and risk allocation",
            "Theory source; not empirical proof",
        ),
        "ISLR": (
            "Train/test discipline, regularization, trees, metrics and clustering",
            "General statistical learning; finance adaptations require time ordering",
        ),
        "Algorithmic": (
            "Financial ML, leakage, walk-forward and transaction-aware research",
            "Method principles; no copied trading claim",
        ),
        "finance-matthew": (
            "Financial ML validation, time series and model-risk cautions",
            "Deep methods remain diagnostic without stronger evidence",
        ),
        "Statistical_Quantitative": (
            "Financial statistics, estimation, regression and model discipline",
            "Assumptions are tested, not presumed",
        ),
        "statistical-methods": (
            "Return distributions, covariance, stationarity and inference",
            "Diagnostics do not prove predictability",
        ),
        "Economics_and_Finance": (
            "ML workflow, simulation and economics/finance interpretation",
            "Prediction metrics do not equal portfolio utility",
        ),
        "quantitative_economics": (
            "Econometric reasoning, simulation, MLE and reproducibility",
            "Economic interpretation remains required",
        ),
    }
    rows = []
    for path in sorted(book_dir.glob("*.pdf")):
        contribution = next(
            (
                value
                for token, value in contributions.items()
                if token.lower() in path.name.lower()
            ),
            ("Methodology reference", "No page-specific claim without verification"),
        )
        rows.append(
            {
                "source": path.name,
                "primary_contribution": contribution[0],
                "usage_boundary": contribution[1],
            }
        )
    return pd.DataFrame(rows)


def _formula_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (
                "Simple return",
                "r_t = P_t / P_(t-1) - 1",
                "daily decimal; signed",
                "Portfolio aggregation is linear in simple returns",
                "Unadjusted price or silent missing value",
            ),
            (
                "Portfolio return",
                "r_p,t = sum_i w_i,t-1 r_i,t",
                "daily decimal; signed",
                "Lagged long-only fully invested weights",
                "Future weights, missing selected return or weight sum != 1",
            ),
            (
                "CAGR",
                "prod(1+r_t)^(252/n) - 1",
                "annual decimal",
                "Compounded wealth growth",
                "Any r_t <= -1 or inconsistent frequency",
            ),
            (
                "Annual volatility",
                "sd(r_t, ddof=1) sqrt(252)",
                "annual decimal; non-negative",
                "Sample daily volatility",
                "Wrong frequency or fewer than two valid observations",
            ),
            (
                "Sharpe",
                "mean(r_t-rf_daily) * 252 / annual_volatility",
                "dimensionless",
                "rf_daily = (1+rf_annual)^(1/252)-1",
                "Frequency mismatch or zero volatility",
            ),
            (
                "Sortino",
                "mean(excess)*252 / annualized downside deviation",
                "dimensionless",
                "Downside deviations use the aligned daily hurdle",
                "No downside observations or hurdle mismatch",
            ),
            (
                "Drawdown",
                "wealth_t / running_max(wealth)_t - 1",
                "decimal; <= 0",
                "Path-dependent peak loss",
                "Positive drawdown or non-wealth input",
            ),
            (
                "Historical CVaR 95",
                "mean(r_t | r_t <= empirical VaR_0.05)",
                "daily decimal; loss is negative",
                "Empirical tail mean",
                "Insufficient tail observations or reversed sign",
            ),
            (
                "Turnover",
                "sum_i |w_i,t - w_i,t-1|",
                "gross traded-notional ratio",
                "Includes purchases, sales, exits and first allocation",
                "Dropped assets omitted from alignment",
            ),
            (
                "Transaction cost",
                "turnover_t * bps / 10000",
                "daily decimal drag",
                "Applied to the realized net OOS path",
                "Gross path mislabeled as net",
            ),
            (
                "Paired bootstrap",
                "block-resample common-date model and benchmark return pairs",
                "CI in metric-difference units",
                "Preserves pairing and local dependence",
                "Unpaired samples or test-driven block tuning",
            ),
            (
                "Random percentile",
                "mean(random_metric <= candidate_metric)",
                "0 to 1",
                "Same-protocol constrained reference distribution",
                "Different dates, universe, caps, costs or degenerate sample",
            ),
        ],
        columns=["metric", "implementation", "unit_sign", "validity", "invalidation"],
    )


def _figure_png(figure: Figure) -> BytesIO:
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=155, bbox_inches="tight", facecolor=WHITE)
    plt.close(figure)
    buffer.seek(0)
    return buffer


def _figure_svg(figure: Figure) -> str:
    buffer = BytesIO()
    figure.savefig(buffer, format="svg", bbox_inches="tight", facecolor=WHITE)
    plt.close(figure)
    svg = buffer.getvalue().decode("utf-8")
    return svg[svg.find("<svg") :]


def _html_table(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    max_rows: int,
) -> str:
    selected = [column for column in columns if column in frame]
    if not selected:
        return "<p>Evidence not available.</p>"
    return (
        frame[selected]
        .head(max_rows)
        .to_html(
            index=False,
            border=0,
            classes="evidence-table",
            na_rep="not available",
        )
    )


def _read_csv(path: Path) -> pd.DataFrame:
    # A publication snapshot must retain the exact serialized evidence values.
    return (
        pd.read_csv(path, float_precision="round_trip")
        if path.exists()
        else pd.DataFrame()
    )


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_key(root: Path, path: str | Path) -> str:
    candidate = Path(path)
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    )
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Publication snapshot paths must remain under repository root: {resolved}"
        ) from exc
    return relative.as_posix()


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        raise ValueError(f"Publication evidence is missing numeric column {column!r}.")
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(
            f"Publication evidence column {column!r} contains non-finite values."
        )
    return values.astype(float)


def _first_numeric(frame: pd.DataFrame, column: str) -> float:
    values = _numeric(frame, column)
    if values.empty:
        raise ValueError(f"Publication evidence column {column!r} is empty.")
    return float(values.iloc[0])


def _safe_float(value: object) -> float:
    try:
        numeric = float(str(value))
    except (TypeError, ValueError):
        return 0.0
    return numeric if np.isfinite(numeric) else 0.0


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return int(default)


def _pct(value: object) -> str:
    return f"{_safe_float(value):.1%}"


def _num(value: object, digits: int = 2) -> str:
    return f"{_safe_float(value):.{digits}f}"


def _display_value(value: object) -> str:
    if value is None or value is pd.NA or value is pd.NaT:
        return "not available"
    if isinstance(value, (float, np.floating)) and np.isnan(float(value)):
        return "not available"
    return str(value)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "passed"}


def _escape(value: object) -> str:
    from xml.sax.saxutils import escape

    return escape(str(value))
