"""Validate generated QuantVerse v2 release-candidate artifacts.

The validator checks generated evidence files after a local v2 demo run. It
does not download data, modify portfolio logic or commit generated artifacts.
It writes a machine-readable validation summary under data/processed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_numerical_integrity import (
    validate_v2_numerical_integrity,
)  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
VALIDATION_PATH = PROCESSED / "quantverse_v2_artifact_validation.json"

REQUIRED_JSON_FIELDS = {
    "quantverse_v2_demo_summary.json": [
        "run_status",
        "final_selected_model",
        "final_model_selection_method",
        "final_model_selection_score",
        "final_model_selection_decision",
        "promotion_decision",
        "weight_sum",
        "final_selected_holdings",
    ],
    "global_final_model_decision.json": [
        "final_selected_model",
        "final_model_selection_method",
        "final_model_selection_score",
        "final_decision",
        "final_decision_reason",
        "publish_readiness_status",
    ],
}

REQUIRED_CSVS = [
    "global_model_selection_report.csv",
    "global_portfolio_league.csv",
    "global_portfolio_league_weights.csv",
    "global_portfolio_risk_report.csv",
    "global_walk_forward_model_comparison.csv",
    "global_random_portfolio_percentile_report.csv",
    "global_robustness_sensitivity.csv",
    "global_top_holdings_explanation.csv",
    "global_forecast_validation_by_horizon.csv",
]

REQUIRED_HTML_SECTIONS = [
    "Executive Summary",
    "Stock Scoring",
    "Portfolio Model League",
    "Robust Model Selection",
    "Walk-Forward",
    "Exposure",
    "Limitations",
]

REQUIRED_EXCEL_SHEETS = [
    "PORTFOLIO_DASHBOARD",
    "START_HERE",
    "EXECUTIVE_SUMMARY",
    "SELECTED_STOCKS",
    "STOCK_SCORES",
    "RETURN_FORECASTS",
    "MODEL_LEAGUE",
    "MODEL_SELECTION",
    "FINAL_WEIGHTS",
    "RISK_METRICS",
    "RISK_CONTRIBUTIONS",
    "WALK_FORWARD",
    "RANDOM_PERCENTILES",
    "ROBUSTNESS",
    "EXPOSURE_REGION",
    "EXPOSURE_COUNTRY",
    "EXPOSURE_CURRENCY",
    "TOP_HOLDINGS_EXPLANATION",
    "FORECAST_VALIDATION",
    "WARNINGS",
    "CLAIM_CONTROL",
]

FORBIDDEN_REPORT_PATTERNS = [
    r"\bguaranteed alpha\b",
    r"\bguaranteed outperformance\b",
    r"\bofficial exact top-100 is supported\b",
    r"\bofficial exact top-100 supported\b",
    r"\binstitutional point-in-time backtest completed\b",
    r"\binstitutional pit backtest completed\b",
    r"\bis investment advice\b",
    r"\bprovides investment advice\b",
    r"\bproduction trading system\b",
    r"\blive trading system\b",
    r"\bbuy recommendation\b",
    r"\bsell recommendation\b",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = validate_artifacts(root)
    processed = root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    output_path = processed / "quantverse_v2_artifact_validation.json"
    output_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"artifact_validation_status={result['overall_status']}")
    print(f"artifact_validation_path={output_path}")
    return 0 if result["overall_status"] == "passed" else 1


def validate_artifacts(root: Path) -> dict[str, object]:
    """Validate generated v2 artifacts below ``root``."""
    processed = root / "data" / "processed"
    checks: list[dict[str, object]] = []
    summary = _read_json(processed / "quantverse_v2_demo_summary.json")
    decision = _read_json(processed / "global_final_model_decision.json")
    league = _read_csv(processed / "global_portfolio_league.csv")
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")

    _check_required_json_fields(processed, checks)
    _check_required_csvs(processed, checks)
    _check_final_model_consistency(summary, decision, league, checks)
    _check_final_weights(summary, weights, checks)
    _check_pdf(root / "output" / "pdf" / "quantverse_v2_research_report.pdf", checks)
    _check_pdf(
        root / "output" / "thesis" / "quantverse_doctoral_dissertation_full.pdf",
        checks,
        label="thesis_full_pdf",
    )
    _check_pdf(
        root
        / "output"
        / "thesis"
        / "quantverse_doctoral_defense_presentation_full.pdf",
        checks,
        label="defense_full_pdf",
    )
    _check_html(root / "output" / "html" / "quantverse_v2_research_report.html", checks)
    _check_excel(
        root / "output" / "excel" / "quantverse_v2_research_output.xlsx", checks
    )
    _check_report_claim_language(root, checks)
    _check_numerical_integrity(root, checks)

    failed = [check for check in checks if not check["passed"]]
    return {
        "overall_status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "checks": checks,
        "summary": {
            "final_selected_model": summary.get("final_selected_model"),
            "final_model_decision": decision.get("final_decision"),
            "promotion_decision": summary.get("promotion_decision"),
            "publish_readiness_status": decision.get("publish_readiness_status"),
        },
    }


def _check_required_json_fields(
    processed: Path, checks: list[dict[str, object]]
) -> None:
    for filename, fields in REQUIRED_JSON_FIELDS.items():
        path = processed / filename
        payload = _read_json(path)
        missing = [field for field in fields if field not in payload]
        checks.append(
            _check(
                f"json_schema_{filename}",
                path.exists() and not missing,
                f"missing_fields={missing}",
            )
        )


def _check_required_csvs(processed: Path, checks: list[dict[str, object]]) -> None:
    for filename in REQUIRED_CSVS:
        path = processed / filename
        frame = _read_csv(path)
        checks.append(
            _check(
                f"csv_non_empty_{filename}",
                path.exists() and not frame.empty,
                f"rows={len(frame)}",
            )
        )


def _check_final_model_consistency(
    summary: dict[str, object],
    decision: dict[str, object],
    league: pd.DataFrame,
    checks: list[dict[str, object]],
) -> None:
    summary_model = str(summary.get("final_selected_model", "")).strip()
    decision_model = str(decision.get("final_selected_model", "")).strip()
    league_models = (
        set(league["model_name"].astype(str)) if "model_name" in league else set()
    )
    checks.append(
        _check(
            "summary_matches_final_model_decision",
            bool(summary_model and summary_model == decision_model),
            f"summary={summary_model}; decision={decision_model}",
        )
    )
    checks.append(
        _check(
            "final_model_appears_in_model_league",
            bool(summary_model and summary_model in league_models),
            f"final_model={summary_model}",
        )
    )


def _check_final_weights(
    summary: dict[str, object],
    weights: pd.DataFrame,
    checks: list[dict[str, object]],
) -> None:
    model = str(summary.get("final_selected_model", "")).strip()
    selected = (
        weights.loc[weights["model_name"].astype(str).eq(model)]
        if not weights.empty and "model_name" in weights
        else pd.DataFrame()
    )
    weight_sum = (
        float(pd.to_numeric(selected["weight"], errors="coerce").sum())
        if "weight" in selected
        else 0.0
    )
    selected_count = int(
        (
            pd.to_numeric(
                selected.get("weight", pd.Series(dtype=float)), errors="coerce"
            ).abs()
            > 1e-8
        ).sum()
    )
    checks.append(
        _check(
            "final_weights_sum_to_one",
            abs(weight_sum - 1.0) <= 1e-6,
            f"model={model}; weight_sum={weight_sum}",
        )
    )
    checks.append(
        _check(
            "selected_holdings_count_plausible",
            1 <= selected_count <= 100,
            f"selected_count={selected_count}",
        )
    )


def _check_pdf(
    path: Path, checks: list[dict[str, object]], label: str = "report_pdf"
) -> None:
    try:
        reader = PdfReader(str(path))
        pages = len(reader.pages)
        first_text = reader.pages[0].extract_text() if pages else ""
        passed = path.exists() and pages > 0 and bool(first_text)
        details = f"pages={pages}; first_text_chars={len(first_text or '')}"
    except Exception as exc:
        passed = False
        details = f"error={exc}"
    checks.append(_check(label, passed, details))


def _check_html(path: Path, checks: list[dict[str, object]]) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    missing = [section for section in REQUIRED_HTML_SECTIONS if section not in text]
    checks.append(
        _check(
            "html_required_sections",
            path.exists() and not missing,
            f"missing_sections={missing}",
        )
    )


def _check_excel(path: Path, checks: list[dict[str, object]]) -> None:
    try:
        sheets = _excel_sheet_names(path)
        missing = [sheet for sheet in REQUIRED_EXCEL_SHEETS if sheet not in sheets]
        passed = path.exists() and not missing
        details = f"missing_sheets={missing}; sheet_count={len(sheets)}"
    except Exception as exc:
        passed = False
        details = f"error={exc}"
    checks.append(_check("excel_required_sheets", passed, details))


def _check_report_claim_language(root: Path, checks: list[dict[str, object]]) -> None:
    paths = [
        root / "output" / "pdf" / "quantverse_v2_research_report.pdf",
        root / "output" / "html" / "quantverse_v2_research_report.html",
        root / "output" / "thesis" / "quantverse_doctoral_dissertation_full.pdf",
        root
        / "output"
        / "thesis"
        / "quantverse_doctoral_defense_presentation_full.pdf",
    ]
    text = "\n".join(_extract_text(path) for path in paths)
    hits = []
    for pattern in FORBIDDEN_REPORT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    checks.append(
        _check(
            "generated_reports_no_forbidden_claims",
            not hits,
            f"forbidden_hits={hits}",
        )
    )


def _check_numerical_integrity(root: Path, checks: list[dict[str, object]]) -> None:
    result = validate_v2_numerical_integrity(root)
    for check in result["checks"]:
        checks.append(
            _check(
                f"numerical_integrity_{check['check']}",
                bool(check["passed"]),
                str(check["details"]),
            )
        )


def _excel_sheet_names(path: Path) -> list[str]:
    try:
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        return list(workbook.sheetnames)
    except ImportError:
        return _excel_sheet_names_from_zip(path)


def _excel_sheet_names_from_zip(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        workbook_xml = archive.read("xl/workbook.xml")
    root = ElementTree.fromstring(workbook_xml)
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [
        sheet.attrib["name"]
        for sheet in root.findall("main:sheets/main:sheet", namespace)
    ]


def _extract_text(path: Path) -> str:
    if not path.exists():
        return ""
    if path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages[:5])
        except Exception:
            return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _check(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "details": details}


if __name__ == "__main__":
    sys.exit(main())
