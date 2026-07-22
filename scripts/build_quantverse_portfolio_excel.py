"""Build the canonical QuantVerse portfolio-analysis workbook payload and XLSX."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output" / "excel" / "quantverse_portfolio_analysis.xlsx"
TMP = ROOT / "tmp" / "portfolio_workbook"
BUILDER = ROOT / "tools" / "workbook" / "build_quantverse_portfolio_analysis.mjs"
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

    TMP.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = _payload()
    sheet_names = tuple(sheet["name"] for sheet in payload["sheets"])
    if sheet_names != CANONICAL_SHEET_NAMES:
        raise RuntimeError(f"Canonical workbook sheet contract changed: {sheet_names}")
    payload_path = TMP / "payload.json"
    payload_path.write_text(
        json.dumps(payload, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    _link_runtime(TMP)
    runtime_builder = TMP / BUILDER.name
    shutil.copy2(BUILDER, runtime_builder)
    subprocess.run(
        [str(_node()), str(runtime_builder), str(payload_path), str(OUTPUT)],
        check=True,
        cwd=TMP,
    )
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
                "Aynı 882 OOS gün, aynı 20 ihraççı politikası, ^IRX ve 10 bps maliyet.",
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


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return ""
    return str(value)


def _node() -> Path | str:
    bundled = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    )
    return bundled if bundled.exists() else "node"


def _link_runtime(directory: Path) -> None:
    node_modules = directory / "node_modules"
    if node_modules.exists():
        return
    runtime = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
    )
    if not runtime.exists():
        raise RuntimeError("Bundled @oai/artifact-tool runtime was not found.")
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(node_modules), str(runtime)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        os.symlink(runtime, node_modules, target_is_directory=True)


if __name__ == "__main__":
    raise SystemExit(main())
