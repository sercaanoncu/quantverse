"""Build the canonical QuantVerse portfolio-analysis workbook payload and XLSX."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output" / "excel" / "quantverse_portfolio_analysis.xlsx"
CANONICAL_SHEET_NAMES = (
    "START_HERE",
    "CURRENT_PORTFOLIO",
    "HOLDING_RATIONALE",
    "REJECTED_CANDIDATES",
    "MODEL_COMPARISON",
    "BALANCED_BENCHMARK_DEFENSIVE",
    "OOS_PERFORMANCE",
    "RISK",
    "TURNOVER_COSTS",
    "EXPOSURE",
    "DATA_QUALITY",
    "LIMITATIONS",
    "FORMULA_DICTIONARY",
    "RAW_WEIGHTS",
    "RAW_OOS_RETURNS",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()
    del args

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = _payload()
    sheet_names = tuple(sheet["name"] for sheet in payload["sheets"])
    if sheet_names != CANONICAL_SHEET_NAMES:
        raise RuntimeError(f"Canonical workbook sheet contract changed: {sheet_names}")
    _write_workbook(payload, OUTPUT)
    print(f"Portfolio workbook written: {OUTPUT}")
    return 0


def _payload() -> dict[str, Any]:
    decision = _csv("global_portfolio_decision_summary.csv")
    roles = _csv("global_portfolio_roles.csv")
    weights = _csv("global_current_portfolio_weights.csv")
    selected = _csv("global_current_selected_securities.csv")
    rejected_source = _csv("global_rejected_candidates.csv")
    league = _csv("global_portfolio_league.csv")
    comparison = _csv("global_walk_forward_model_comparison.csv")
    oos_observations = _common_oos_observations(comparison)
    oos = _csv("global_walk_forward_returns.csv")
    risk = _csv("global_portfolio_risk_report.csv")
    risk_contribution = _csv("global_risk_contribution_report.csv")
    costs = _csv("global_walk_forward_cost_sensitivity.csv")
    sector = _csv("global_sector_exposure.csv")
    country = _csv("global_issuer_country_exposure.csv")
    industry = _csv("global_industry_exposure.csv")
    acceptance = _csv("global_portfolio_core_acceptance.csv")
    rf = _csv("global_risk_free_series.csv")

    balanced = _decision_value(decision, "balanced_research_portfolio")
    benchmark = _decision_value(decision, "transparent_benchmark")
    defensive = _decision_value(decision, "defensive_alternative")
    current = weights[weights["portfolio_role"].eq("balanced_research_portfolio")]
    current = current.merge(
        risk_contribution[risk_contribution["model_name"].eq(balanced)][
            ["ticker", "risk_contribution_pct"]
        ],
        on="ticker",
        how="left",
    )
    selected_rows = selected[selected["selected"].astype(str).str.lower().eq("true")]
    rejected = rejected_source.sort_values(
        "composite_quant_score", ascending=False
    ).head(20)

    current_columns = [
        "ticker",
        "issuer_name",
        "weight",
        "risk_contribution_pct",
        "sector",
        "industry",
        "issuer_country",
    ]
    rationale_columns = [
        "ticker",
        "issuer_name",
        "composite_quant_score",
        "momentum_6m",
        "momentum_12m",
        "volatility_12m",
        "downside_volatility",
        "max_drawdown",
        "correlation_diversification_score",
        "selection_reason",
    ]
    rejected_columns = [
        "ticker",
        "issuer_name",
        "composite_quant_score",
        "selection_status",
        "selection_reason",
        "representative_rejection_reason",
    ]
    model_columns = [
        "model_name",
        "oos_cagr",
        "oos_annualized_return",
        "oos_volatility",
        "oos_sharpe",
        "oos_observations",
        "oos_sortino",
        "oos_max_drawdown",
        "oos_cvar_95",
        "avg_turnover",
        "sharpe_diff_ci_lower",
        "sharpe_diff_ci_upper",
    ]
    summary = comparison[
        comparison["model_name"].isin({balanced, benchmark, defensive})
    ]
    start_rows = [
        ["KANONİK KAPSAM", "US-listed global-issuer equity research"],
        ["KANIT DURUMU", _decision_value(decision, "evidence_status")],
        ["DENGELİ ARAŞTIRMA PORTFÖYÜ", balanced],
        ["ŞEFFAF BENCHMARK", benchmark],
        ["SAVUNMACI ALTERNATİF", defensive],
        [
            "İLK BAKILACAK SAYFA",
            "CURRENT_PORTFOLIO: 20 menkul kıymet ve kesin ağırlıklar",
        ],
        ["KARŞILAŞTIRMA", "MODEL_COMPARISON: aynı OOS tarihlerinde net performans"],
        [
            "TEMEL SINIR",
            "Mevcut evren tarihsel point-in-time bileşenleri ve delistings içermiyor.",
        ],
        [
            "CANLI İŞLEM",
            "Kurumsal/canlı işlem için veri, kapasite, yürütme ve yönetişim eksikleri sürüyor.",
        ],
    ]
    formulas = pd.DataFrame(
        [
            [
                "Simple portfolio return",
                "r_p,t = sum_i(w_i,t-1 * r_i,t)",
                "Portföy toplaması; eksik getiri sıfır değildir.",
            ],
            [
                "Daily risk-free",
                "(1 + annual_rf)^(1/252) - 1",
                "^IRX geçmişe dönük doldurma olmadan hizalanır.",
            ],
            [
                "Annualized arithmetic return",
                "252 * mean(daily net return)",
                "OOS günlük net seriden.",
            ],
            [
                "CAGR",
                "prod(1+r_t)^(252/n) - 1",
                "Bileşik büyüme; yıllık aritmetik getiri değildir.",
            ],
            [
                "Volatility",
                "std(r_t, ddof=1) * sqrt(252)",
                "Örneklem standart sapması.",
            ],
            [
                "Sharpe",
                "mean(r_t-rf_t)/std(r_t-rf_t) * sqrt(252)",
                "Birincil ölçüm zaman hizalı ^IRX kullanır.",
            ],
            [
                "Sortino",
                "annualized excess return / annualized downside deviation",
                "Negatif excess returns aşağı yönlü risk oluşturur.",
            ],
            [
                "Drawdown",
                "wealth/running_max(wealth)-1",
                "Her zaman sıfır veya negatiftir.",
            ],
            [
                "Historical CVaR 95%",
                "mean(r_t | r_t <= empirical VaR_5%)",
                "Dağılım normalliği varsaymaz.",
            ],
            [
                "Turnover cost",
                "turnover * cost_bps / 10000",
                "Her fold başlangıcında test getirisinden düşülür.",
            ],
        ],
        columns=["metric", "formula_or_method", "interpretation_and_limit"],
    )
    data_quality = pd.DataFrame(
        [
            ["target_holdings", len(current), 20, len(current) == 20],
            [
                "duplicate_economic_issuer_count",
                current["issuer_key"].duplicated().sum(),
                0,
                not current["issuer_key"].duplicated().any(),
            ],
            [
                "balanced_weight_sum",
                current["weight"].sum(),
                1.0,
                abs(current["weight"].sum() - 1.0) <= 1e-8,
            ],
            [
                "sector_max",
                current.groupby("sector")["weight"].sum().max(),
                0.25,
                current.groupby("sector")["weight"].sum().max() <= 0.25 + 1e-8,
            ],
            [
                "industry_max",
                current.groupby("industry")["weight"].sum().max(),
                0.15,
                current.groupby("industry")["weight"].sum().max() <= 0.15 + 1e-8,
            ],
            [
                "issuer_country_max",
                current.groupby("issuer_country")["weight"].sum().max(),
                0.60,
                current.groupby("issuer_country")["weight"].sum().max() <= 0.60 + 1e-8,
            ],
            [
                "nonzero_rf_observations",
                (pd.to_numeric(rf["daily_hurdle"], errors="coerce") != 0).sum(),
                "> 0",
                (pd.to_numeric(rf["daily_hurdle"], errors="coerce") != 0).any(),
            ],
            [
                "core_acceptance",
                int(acceptance["passed"].astype(str).str.lower().eq("true").sum()),
                len(acceptance),
                acceptance["passed"].astype(str).str.lower().eq("true").all(),
            ],
        ],
        columns=["check", "observed", "expected", "passed"],
    )
    limitations = pd.DataFrame(
        [
            [
                "scope",
                "Evren US-listed menkul kıymetlerle sınırlıdır; geniş küresel borsa kapsamı iddia edilmez.",
                "research-grade with limitations",
            ],
            [
                "survivorship",
                "Mevcut evren tarihsel point-in-time üyelik değildir.",
                "promotion blocker for historical selection claims",
            ],
            [
                "corporate_actions",
                "Adjusted fiyatlar kullanılır; delisting ve tüm kurumsal işlem uzlaştırması yoktur.",
                "institutional limitation",
            ],
            [
                "execution",
                "Kapasite, bid-ask spread, market impact, vergi ve broker yürütmesi modellenmemiştir.",
                "live-trading blocker",
            ],
            [
                "5_percent_cap",
                "20 holding ile %5 üst sınır matematiksel olarak yalnızca Equal Weight üretir; aktif model karşılaştırması %10 operasyonel cap kullanır.",
                "explicitly disclosed design constraint",
            ],
            [
                "uncertainty",
                "Aktif modellerin bootstrap Sharpe farkı alt güven sınırı sıfırın üstünde değildir.",
                "Equal Weight remains balanced",
            ],
        ],
        columns=["area", "limitation", "decision_effect"],
    )
    exposure = pd.concat(
        [
            sector.assign(exposure_type="sector"),
            country.assign(exposure_type="issuer_country"),
            industry.assign(exposure_type="industry"),
        ],
        ignore_index=True,
    )
    cost_columns = [
        "model_name",
        "transaction_cost_bps",
        "cagr",
        "annualized_return",
        "volatility",
        "sharpe",
        "sortino",
        "max_drawdown",
        "cvar_95",
        "average_turnover",
    ]
    return {
        "sheets": [
            _sheet(
                "START_HERE",
                start_rows,
                "Önce burayı okuyun; kapsam, karar rolleri ve sınırlamalar.",
            ),
            _sheet(
                "CURRENT_PORTFOLIO",
                _rows(current[current_columns]),
                "Dengeli araştırma portföyünün tam 20 ağırlığı ve risk katkısı.",
            ),
            _sheet(
                "HOLDING_RATIONALE",
                _rows(selected_rows[rationale_columns]),
                "Seçim anında kullanılan şeffaf skor bileşenleri; tahmin garantisi değildir.",
            ),
            _sheet(
                "REJECTED_CANDIDATES",
                _rows(rejected[rejected_columns]),
                "En yakın 20 reddedilen aday ve kesin ret nedeni.",
            ),
            _sheet(
                "MODEL_COMPARISON",
                _rows(comparison[model_columns]),
                (
                    f"Aynı {oos_observations} OOS gün, aynı 20 ihraççı "
                    "politikası, ^IRX ve 10 bps maliyet."
                ),
            ),
            _sheet(
                "BALANCED_BENCHMARK_DEFENSIVE",
                _rows(summary[model_columns]),
                "Dengeli, benchmark ve savunmacı karar yüzeyi.",
            ),
            _sheet(
                "OOS_PERFORMANCE",
                _rows(oos[["Date", "model_name", "return"]]),
                "Stitched net OOS günlük getiri; her gün bir kez kullanılır.",
            ),
            _sheet(
                "RISK",
                _rows(risk),
                "Tam örneklem tanısal risk ile model kararında kullanılan OOS risk ayrıdır.",
            ),
            _sheet(
                "TURNOVER_COSTS",
                _rows(costs[cost_columns]),
                "5, 10 ve 25 bps işlem maliyeti duyarlılığı.",
            ),
            _sheet(
                "EXPOSURE",
                _rows(
                    exposure[
                        [
                            "exposure_type",
                            "bucket",
                            "weight",
                            "asset_count",
                            "interpretation",
                        ]
                    ]
                ),
                "Dengeli portföy sektör, ihraççı ülke ve endüstri maruziyeti.",
            ),
            _sheet(
                "DATA_QUALITY",
                _rows(data_quality),
                "Kanonik kabul ve sayısal bütünlük kontrolleri.",
            ),
            _sheet(
                "LIMITATIONS",
                _rows(limitations),
                "Sonuçların geçersizleşebileceği veri ve uygulama koşulları.",
            ),
            _sheet(
                "FORMULA_DICTIONARY",
                _rows(formulas),
                "Ana metriklerin yöntem ve geçersizlik koşulları.",
            ),
            _sheet(
                "RAW_WEIGHTS",
                _rows(weights),
                "Üç rol için yayımlanan tam ağırlık matrisi.",
            ),
            _sheet(
                "RAW_OOS_RETURNS",
                _rows(oos),
                "Bağımsız yeniden hesaplama için net OOS getiri kanıtı.",
            ),
        ],
        "charts": {
            "model_comparison_sheet": "MODEL_COMPARISON",
            "exposure_sheet": "EXPOSURE",
            "cost_sheet": "TURNOVER_COSTS",
        },
    }


def _write_workbook(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pd.DataFrame] = {}
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        title_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#17324D",
                "font_size": 15,
                "align": "left",
                "valign": "vcenter",
            }
        )
        note_format = workbook.add_format(
            {
                "font_color": "#17324D",
                "bg_color": "#EAF2F6",
                "text_wrap": True,
                "valign": "vcenter",
            }
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#2B6F8F",
                "text_wrap": True,
                "border": 1,
                "border_color": "#D7E0E5",
                "valign": "vcenter",
            }
        )
        text_format = workbook.add_format(
            {
                "text_wrap": True,
                "valign": "top",
                "bottom": 1,
                "bottom_color": "#D7E0E5",
            }
        )
        percent_format = workbook.add_format(
            {
                "num_format": "0.00%;[Red](0.00%);-",
                "valign": "top",
                "bottom": 1,
                "bottom_color": "#D7E0E5",
            }
        )

        for spec in payload["sheets"]:
            rows = spec["rows"] or [["status"], ["No rows available"]]
            headers = [str(value) for value in rows[0]]
            frame = pd.DataFrame(rows[1:], columns=headers)
            frames[spec["name"]] = frame
            frame.to_excel(
                writer,
                sheet_name=spec["name"],
                index=False,
                startrow=4,
            )
            worksheet = writer.sheets[spec["name"]]
            last_column = max(len(headers) - 1, 0)
            worksheet.hide_gridlines(2)
            worksheet.freeze_panes(5, 0)
            worksheet.set_row(0, 24)
            worksheet.set_row(1, 24)
            worksheet.set_row(2, 24)
            worksheet.merge_range(0, 0, 0, last_column, spec["name"], title_format)
            worksheet.merge_range(
                1, 0, 2, last_column, spec["explanation"], note_format
            )
            for column_index, header in enumerate(headers):
                worksheet.write(4, column_index, header, header_format)
                width = _column_width(header, frame[header])
                cell_format = (
                    percent_format if _is_percentage_column(header) else text_format
                )
                worksheet.set_column(column_index, column_index, width, cell_format)
            if len(frame):
                worksheet.autofilter(4, 0, 4 + len(frame), last_column)
            if "passed" in headers and len(frame):
                passed_column = headers.index("passed")
                worksheet.conditional_format(
                    5,
                    passed_column,
                    4 + len(frame),
                    passed_column,
                    {
                        "type": "cell",
                        "criteria": "==",
                        "value": False,
                        "format": workbook.add_format(
                            {
                                "bg_color": "#B54747",
                                "font_color": "#FFFFFF",
                                "bold": True,
                            }
                        ),
                    },
                )
                worksheet.conditional_format(
                    5,
                    passed_column,
                    4 + len(frame),
                    passed_column,
                    {
                        "type": "cell",
                        "criteria": "==",
                        "value": True,
                        "format": workbook.add_format(
                            {
                                "bg_color": "#D7EBD9",
                                "font_color": "#215A2A",
                                "bold": True,
                            }
                        ),
                    },
                )

        _add_workbook_charts(workbook, writer.sheets, frames)


def _add_workbook_charts(
    workbook: Any,
    worksheets: dict[str, Any],
    frames: dict[str, pd.DataFrame],
) -> None:
    model = frames["MODEL_COMPARISON"]
    if not model.empty:
        model_sheet = worksheets["MODEL_COMPARISON"]
        model_chart = workbook.add_chart({"type": "column"})
        model_column = model.columns.get_loc("model_name")
        for column_name in ["oos_annualized_return", "oos_volatility"]:
            value_column = model.columns.get_loc(column_name)
            model_chart.add_series(
                {
                    "name": ["MODEL_COMPARISON", 4, value_column],
                    "categories": [
                        "MODEL_COMPARISON",
                        5,
                        model_column,
                        4 + len(model),
                        model_column,
                    ],
                    "values": [
                        "MODEL_COMPARISON",
                        5,
                        value_column,
                        4 + len(model),
                        value_column,
                    ],
                }
            )
        model_chart.set_title({"name": "Common-Sample OOS Return And Risk"})
        model_chart.set_y_axis({"num_format": "0%"})
        model_chart.set_legend({"position": "bottom"})
        model_sheet.insert_chart("N5", model_chart, {"x_scale": 1.25, "y_scale": 1.2})

    exposure = frames["EXPOSURE"]
    sector = exposure.loc[exposure["exposure_type"].astype(str).eq("sector")]
    if not sector.empty:
        exposure_sheet = worksheets["EXPOSURE"]
        exposure_chart = workbook.add_chart({"type": "bar"})
        first_row = 5 + int(sector.index.min())
        last_row = 5 + int(sector.index.max())
        bucket_column = exposure.columns.get_loc("bucket")
        weight_column = exposure.columns.get_loc("weight")
        exposure_chart.add_series(
            {
                "name": "Balanced Portfolio Sector Exposure",
                "categories": [
                    "EXPOSURE",
                    first_row,
                    bucket_column,
                    last_row,
                    bucket_column,
                ],
                "values": [
                    "EXPOSURE",
                    first_row,
                    weight_column,
                    last_row,
                    weight_column,
                ],
            }
        )
        exposure_chart.set_title({"name": "Balanced Portfolio Sector Exposure"})
        exposure_chart.set_x_axis({"num_format": "0%"})
        exposure_chart.set_legend({"none": True})
        exposure_sheet.insert_chart(
            "G5", exposure_chart, {"x_scale": 1.15, "y_scale": 1.2}
        )

    costs = frames["TURNOVER_COSTS"]
    if not costs.empty:
        cost_sheet = worksheets["TURNOVER_COSTS"]
        helper_start_column = 20
        cost_sheet.write_row(
            0, helper_start_column, ["cost_bps", "Equal Weight", "GMV"]
        )
        for row_offset, bps in enumerate([5, 10, 25], 1):
            values: list[object] = [bps]
            for model_name in ["Equal Weight", "GMV"]:
                match = costs.loc[
                    costs["model_name"].astype(str).eq(model_name)
                    & pd.to_numeric(costs["transaction_cost_bps"], errors="coerce").eq(
                        bps
                    ),
                    "sharpe",
                ]
                values.append(float(match.iloc[0]) if len(match) else "")
            cost_sheet.write_row(row_offset, helper_start_column, values)
        cost_sheet.set_column(
            helper_start_column, helper_start_column + 2, None, None, {"hidden": True}
        )
        cost_chart = workbook.add_chart({"type": "line"})
        for series_offset, model_name in enumerate(["Equal Weight", "GMV"], 1):
            cost_chart.add_series(
                {
                    "name": model_name,
                    "categories": [
                        "TURNOVER_COSTS",
                        1,
                        helper_start_column,
                        3,
                        helper_start_column,
                    ],
                    "values": [
                        "TURNOVER_COSTS",
                        1,
                        helper_start_column + series_offset,
                        3,
                        helper_start_column + series_offset,
                    ],
                    "marker": {"type": "circle"},
                }
            )
        cost_chart.set_title({"name": "Transaction-Cost Sensitivity"})
        cost_chart.set_x_axis({"name": "Cost (bps)"})
        cost_chart.set_y_axis({"name": "OOS Sharpe"})
        cost_chart.set_legend({"position": "bottom"})
        cost_sheet.insert_chart("L10", cost_chart, {"x_scale": 1.15, "y_scale": 1.1})


def _column_width(header: str, values: pd.Series) -> int:
    key = header.lower()
    if any(
        token in key for token in ["reason", "limitation", "formula", "interpretation"]
    ):
        return 45
    sampled = values.astype(str).head(200)
    longest = max([len(header), *(len(value) for value in sampled)], default=12)
    return min(max(longest + 2, 11), 24)


def _is_percentage_column(header: str) -> bool:
    key = header.lower()
    return any(
        token in key
        for token in [
            "weight",
            "return",
            "cagr",
            "volatility",
            "drawdown",
            "var_95",
            "cvar_95",
            "turnover",
            "momentum",
            "risk_contribution",
            "ci_lower",
            "ci_upper",
            "probability",
        ]
    )


def _common_oos_observations(comparison: pd.DataFrame) -> int:
    observations = (
        pd.to_numeric(comparison["oos_observations"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
    )
    if len(observations) != 1 or observations[0] <= 0:
        raise RuntimeError(
            "Canonical workbook requires one positive common OOS observation count."
        )
    return int(observations[0])


def _sheet(name: str, rows: list[list[Any]], explanation: str) -> dict[str, Any]:
    return {"name": name, "rows": rows, "explanation": explanation}


def _rows(frame: pd.DataFrame) -> list[list[Any]]:
    clean = frame.replace([np.inf, -np.inf], np.nan).where(pd.notna(frame), "")
    return [list(clean.columns)] + clean.astype(object).values.tolist()


def _csv(name: str) -> pd.DataFrame:
    path = PROCESSED / name
    if not path.exists():
        raise FileNotFoundError(f"Required canonical workbook input missing: {path}")
    return pd.read_csv(path)


def _decision_value(frame: pd.DataFrame, column: str) -> str:
    return str(frame.iloc[0][column])


if __name__ == "__main__":
    raise SystemExit(main())
