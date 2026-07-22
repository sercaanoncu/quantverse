from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from reportlab.pdfgen import canvas

from project.reporting.selected_stock_report_view import (
    build_selected_stock_report_view,
    build_selected_stock_report_view_quality,
)
from scripts.build_quantverse_v2_excel_output import _write_selected_stocks_sheet
from scripts.build_quantverse_v2_research_report import _stock_scoring_section
from scripts.validate_quantverse_v2_artifacts import (
    _read_excel_sheet_table,
    validate_selected_stock_report_semantics,
)


def _scores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["UBS", "TSM", "LOCAL"],
            "name": ["UBS Group", "Taiwan Semiconductor", "Local Company"],
            "rank_global": [1, 2, 3],
            "composite_quant_score": [0.9, 0.8, 0.7],
            "country": ["United States"] * 3,
            "currency": ["USD"] * 3,
            "selection_flag": [True, True, True],
            "warning_flags": ["none", "none", "none"],
            "selection_reason": ["fixture selection"] * 3,
        }
    )


def _metadata() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["UBS", "TSM"],
            "name": ["UBS Group", "Taiwan Semiconductor"],
            "listing_country": ["United States", "United States"],
            "issuer_country": ["Switzerland", "Taiwan"],
            "economic_country": ["missing", "missing"],
            "listing_currency": ["USD", "USD"],
            "exchange": ["NYQ", "NYQ"],
            "sector": ["Financial Services", "Technology"],
            "industry": ["Banks - Diversified", "Semiconductors"],
            "metadata_source": ["provider_cache", "provider_cache"],
            "metadata_confidence": ["medium", "medium"],
            "metadata_as_of_date": ["2026-07-09", "2026-07-09"],
            "adr_or_foreign_issuer_flag": [True, True],
        }
    )


def test_ubs_and_tsm_listing_issuer_and_economic_meanings_remain_distinct():
    view = build_selected_stock_report_view(_scores(), _metadata())

    ubs = view.loc[view["ticker"].eq("UBS")].iloc[0]
    assert ubs["listing_country"] == "United States"
    assert ubs["issuer_country"] == "Switzerland"
    assert ubs["economic_country"] == "unavailable"

    tsm = view.loc[view["ticker"].eq("TSM")].iloc[0]
    assert tsm["listing_country"] == "United States"
    assert tsm["issuer_country"] == "Taiwan"
    assert tsm["economic_country"] == "unavailable"


def test_legacy_country_and_currency_only_supply_listing_fields():
    view = build_selected_stock_report_view(_scores().iloc[[2]], pd.DataFrame())
    row = view.iloc[0]

    assert row["listing_country"] == "United States"
    assert row["listing_currency"] == "USD"
    assert row["issuer_country"] == "unavailable"
    assert row["economic_country"] == "unavailable"


def test_duplicate_metadata_ticker_is_rejected_explicitly():
    duplicate = pd.concat([_metadata(), _metadata().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate normalized tickers"):
        build_selected_stock_report_view(_scores(), duplicate)


def test_missing_metadata_preserves_selected_rows_and_reports_quality():
    scores = _scores()
    scores_before = scores.copy(deep=True)
    metadata = _metadata()
    metadata_before = metadata.copy(deep=True)

    view = build_selected_stock_report_view(scores, metadata)
    quality = build_selected_stock_report_view_quality(view).iloc[0]

    assert len(view) == 3
    assert quality["selected_stock_count"] == 3
    assert quality["matched_metadata_count"] == 2
    assert quality["unmatched_metadata_count"] == 1
    assert quality["duplicate_ticker_count"] == 0
    assert quality["semantic_view_status"] == "diagnostic_metadata_incomplete"
    assert_frame_equal(scores, scores_before)
    assert_frame_equal(metadata, metadata_before)


def test_pdf_and_html_section_contract_uses_semantic_view():
    view = build_selected_stock_report_view(_scores(), _metadata())
    quality = build_selected_stock_report_view_quality(view)

    section = _stock_scoring_section(view, quality)

    assert section["table_id"] == "selected-stock-semantic-view"
    assert "listing_country" in section["table"].columns
    assert "issuer_country" in section["table"].columns
    assert "economic_country" in section["table"].columns
    assert "country" not in section["table"].columns
    assert "currency" not in section["table"].columns
    assert any(
        "Economic-country exposure is unavailable and is not inferred" in bullet
        for bullet in section["bullets"]
    )


def test_excel_selected_stocks_sheet_uses_semantic_columns(tmp_path):
    view = build_selected_stock_report_view(_scores(), _metadata())
    path = tmp_path / "semantic.xlsx"

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        _write_selected_stocks_sheet(writer, view)

    selected = _read_excel_sheet_table(path, "SELECTED_STOCKS", header_row=3)
    assert {"listing_country", "issuer_country", "economic_country"}.issubset(
        selected.columns
    )
    assert "country" not in selected.columns
    assert "currency" not in selected.columns
    assert set(selected["economic_country"]) == {"unavailable"}


@pytest.mark.parametrize("semantic", [False, True])
def test_validator_rejects_ambiguous_and_accepts_separated_fixture(tmp_path, semantic):
    _write_semantic_validator_fixture(tmp_path, semantic=semantic)

    result = validate_selected_stock_report_semantics(tmp_path)

    assert (result["overall_status"] == "passed") is semantic
    country_check = next(
        check
        for check in result["checks"]
        if check["check"] == "report_no_ambiguous_country_header"
    )
    assert bool(country_check["passed"]) is semantic


def _write_semantic_validator_fixture(root: Path, *, semantic: bool) -> None:
    processed = root / "data" / "processed"
    pdf_dir = root / "output" / "pdf"
    html_dir = root / "output" / "html"
    excel_dir = root / "output" / "excel"
    for path in [processed, pdf_dir, html_dir, excel_dir]:
        path.mkdir(parents=True, exist_ok=True)

    score = _scores().iloc[[0]]
    score.to_csv(processed / "global_stock_scores.csv", index=False)
    if semantic:
        view = build_selected_stock_report_view(score, _metadata().iloc[[0]])
        quality = build_selected_stock_report_view_quality(view)
        table = view
        headers = [
            "Ticker",
            "Listing Country",
            "Issuer Country",
            "Economic Country",
        ]
    else:
        view = pd.DataFrame(
            {"ticker": ["UBS"], "country": ["United States"], "currency": ["USD"]}
        )
        quality = pd.DataFrame(
            {
                "selected_stock_count": [1],
                "matched_metadata_count": [1],
                "unmatched_metadata_count": [0],
                "duplicate_ticker_count": [0],
                "economic_country_coverage_ratio": [0.0],
                "semantic_view_status": ["passed_with_metadata_warning"],
            }
        )
        table = view
        headers = ["Ticker", "Country", "Currency"]
    view.to_csv(processed / "global_selected_stocks_report_view.csv", index=False)
    quality.to_csv(
        processed / "global_selected_stocks_report_view_quality.csv", index=False
    )
    pd.DataFrame({"economic_country_coverage_ratio": [0.0]}).to_csv(
        processed / "global_exposure_metadata_quality.csv", index=False
    )

    disclosure = (
        "Economic-country exposure is unavailable and is not inferred from listing "
        "venue, trading currency or issuer domicile."
    )
    html = (
        '<h2 id="portfolio">Portfolio holdings</h2>'
        + disclosure
        + table.to_html(index=False, table_id="selected-stock-semantic-view")
        + "<h2>Visual Portfolio Analytics</h2>"
    )
    (html_dir / "quantverse_v2_research_report.html").write_text(html, encoding="utf-8")

    pdf_path = pdf_dir / "quantverse_v2_executive_research_report.pdf"
    pdf = canvas.Canvas(str(pdf_path))
    lines = [
        "2. Portfolio Holdings and Concentration",
        disclosure,
        *headers,
        "3. Out-of-Sample Path Evidence",
    ]
    for index, line in enumerate(lines):
        pdf.drawString(40, 780 - index * 18, line)
    pdf.showPage()
    pdf.save()

    excel_path = excel_dir / "quantverse_v2_research_output.xlsx"
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        if semantic:
            _write_selected_stocks_sheet(writer, table)
        else:
            table.to_excel(
                writer, sheet_name="SELECTED_STOCKS", startrow=2, index=False
            )
