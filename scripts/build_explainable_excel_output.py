"""Build an explainable Turkish Excel workbook through artifact-tool."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROCESSED = Path("data/processed")
OUTPUT_XLSX = Path("output/excel/quantverse_explainable_global_stock_output.xlsx")
TMP_DIR = Path("tmp/explainable_excel_build")
FIG_DIR = Path("output/figures/global_audit")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default=str(PROCESSED))
    parser.add_argument("--output", default=str(OUTPUT_XLSX))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed = Path(args.processed_dir)
    output = Path(args.output)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    payload = _workbook_payload(processed)
    payload_path = TMP_DIR / "workbook_payload.json"
    payload_path.write_text(
        json.dumps(payload, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    builder_path = TMP_DIR / "build_workbook.mjs"
    builder_path.write_text(_js_builder(), encoding="utf-8")
    _ensure_artifact_tool_node_modules(TMP_DIR)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "node",
            str(builder_path.resolve()),
            str(payload_path.resolve()),
            str(output.resolve()),
        ],
        check=True,
        cwd=str(TMP_DIR.resolve()),
    )
    print(f"Excel workbook written: {output}")
    return 0


def _workbook_payload(processed: Path) -> dict[str, Any]:
    decision = _read_json(processed / "global_master_decision_summary.json")
    sheets = [
        _sheet(
            "START_HERE",
            _start_here(decision),
            "Bu dosya nasıl okunur? İlk buradan başla.",
        ),
        _sheet(
            "EXECUTIVE_SUMMARY",
            _executive_summary(processed, decision),
            "Kısa hüküm ve kritik sonuçlar.",
        ),
        _sheet(
            "RED_FLAGS",
            _csv(processed / "global_scientific_sanity_issues.csv", 250),
            "Bilimsel kırmızı bayraklar. Critical/high satırlar promotion bloklayabilir.",
        ),
        _sheet(
            "REQUIREMENT_TRACEABILITY",
            _csv(processed / "user_requirement_traceability_matrix.csv", 200),
            "Kullanıcı talepleri ve karşılanma durumu.",
        ),
        _sheet(
            "UNIVERSE",
            _csv(processed / "real_global_universe_population_summary.csv", 100),
            "Kaynak evren satır sayıları.",
        ),
        _sheet(
            "DATA_QUALITY",
            _data_quality(processed),
            "Source, market-cap, FX ve price coverage özeti.",
        ),
        _sheet(
            "MODEL_COMPARISON",
            _csv(processed / "global_master_model_comparison.csv", 50),
            "Model karşılaştırması. Extreme metrikler kırmızı bayrakla okunmalı.",
        ),
        _sheet(
            "CONSTRAINT_AUDIT",
            _csv(processed / "global_master_constraint_audit.csv", 50),
            "Hard constraints geçiş/kalış denetimi.",
        ),
        _sheet(
            "FINAL_WEIGHTS",
            _final_weights(processed, decision),
            "Final modelin full ağırlıkları. Top holdings partial değildir; bu sheet final full listedir.",
        ),
        _sheet(
            "ASSET_CLASS_WEIGHTS",
            _csv(processed / "global_master_asset_class_weights.csv", 100),
            "Final aday sleeve ağırlıkları.",
        ),
        _sheet(
            "REGION_WEIGHTS",
            _csv(processed / "global_master_region_weights.csv", 100),
            "Final aday region ağırlıkları.",
        ),
        _sheet(
            "CLUSTER_WEIGHTS",
            _csv(processed / "global_master_cluster_weights.csv", 100),
            "Final aday correlation cluster ağırlıkları.",
        ),
        _sheet(
            "RANDOM_BENCHMARK",
            _random_summary(processed),
            "10.000 random portfolio benchmark özeti.",
        ),
        _sheet(
            "PROJECTIONS",
            _csv(processed / "global_monte_carlo_projection.csv", 50),
            "Monte Carlo 1/3/6/12 ay projection aralıkları.",
        ),
        _sheet(
            "METHODOLOGY_SOURCE_BASIS",
            _csv(processed / "methodology_source_check.csv", 200),
            "Metodoloji alanı, kaynak ve doğru kullanım.",
        ),
        _sheet(
            "APPENDIX_RAW_TABLES",
            _appendix_paths(),
            "Uzun ham tabloların dosya yolları. Ana yorumlar önceki sheet'lerde.",
        ),
    ]
    return {
        "title": "QuantVerse Explainable Global Stock Output",
        "generated_by": "scripts/build_explainable_excel_output.py",
        "chart_folder": str(FIG_DIR.resolve()),
        "sheets": sheets,
    }


def _sheet(name: str, rows: list[list[Any]], explanation: str) -> dict[str, Any]:
    return {"name": name, "explanation": explanation, "rows": rows}


def _start_here(decision: dict[str, Any]) -> list[list[Any]]:
    return [
        ["Soru", "Kısa cevap"],
        [
            "Bu dosya ne?",
            "QuantVerse global stock/proxy araştırma çıktılarının Türkçe, açıklanabilir Excel özetidir.",
        ],
        [
            "İlk hangi sayfaya bakmalıyım?",
            "START_HERE, EXECUTIVE_SUMMARY, RED_FLAGS, FINAL_WEIGHTS ve PROJECTIONS.",
        ],
        [
            "Hangi sonuç güvenilir?",
            "Ağırlık toplamı, constraint audit, source coverage ve not promoted kararı güvenilir audit çıktılarıdır.",
        ],
        [
            "Hangi sonuç güvenilir değil?",
            "Exact top-100 market-cap ve global USD promoted portfolio iddiası güvenilir değildir; veri blokları var.",
        ],
        ["Neden not promoted?", _decision_reason(decision)],
        [
            "Neden FX blocker var?",
            "Non-USD local returns USD'ye çevrilmediği için global USD portföy terfi edemez.",
        ],
        [
            "Neden exact top-100 claim yok?",
            "Equity sleeves market_cap_usd/market_cap_rank kanıtı taşımıyor; çoğu index_proxy.",
        ],
        [
            "Ağırlıklar nerede?",
            "FINAL_WEIGHTS sheet'i ve data/processed/global_master_candidate_weights.csv.",
        ],
        [
            "Grafikler nerede?",
            "output/figures/global_audit klasörü ve PDF rapor içinde.",
        ],
    ]


def _executive_summary(processed: Path, decision: dict[str, Any]) -> list[list[Any]]:
    sanity = _read_csv(processed / "global_scientific_sanity_summary.csv")
    coverage = _read_csv(processed / "global_returns_coverage_report.csv")
    fx = _read_csv(processed / "global_fx_normalization_report.csv")
    included = (
        int(coverage["included_in_returns"].astype(bool).sum())
        if "included_in_returns" in coverage
        else 0
    )
    excluded = (
        int((~coverage["included_in_returns"].astype(bool)).sum())
        if "included_in_returns" in coverage
        else 0
    )
    fx_blocked = (
        int(fx["fx_normalization_status"].astype(str).eq("not_implemented").sum())
        if "fx_normalization_status" in fx
        else 0
    )
    return [
        ["Metrik", "Değer", "Yorum"],
        ["Final model", decision.get("final_model", ""), "Araştırma adayıdır."],
        [
            "Promotion decision",
            decision.get("promotion_decision", ""),
            "Global USD master portfolio promoted değildir.",
        ],
        [
            "Selected holdings",
            decision.get("selected_holdings", ""),
            "Full ağırlıklar FINAL_WEIGHTS sheet'indedir.",
        ],
        ["Price included assets", included, "Fiyat kapsamı yeterli olan varlıklar."],
        ["Price excluded assets", excluded, "Ticker/provider coverage problemi."],
        ["FX not implemented rows", fx_blocked, "Promotion blocker."],
        [
            "Total red flags",
            _cell(sanity, "total_issues"),
            "Bilimsel sanity audit issue sayısı.",
        ],
        [
            "Promotion blockers",
            _cell(sanity, "promotion_blockers"),
            "Critical/high blocker sayısı değil, promotion blocker flag toplamıdır.",
        ],
    ]


def _data_quality(processed: Path) -> list[list[Any]]:
    rows = [["Area", "Metric", "Value", "Interpretation"]]
    market = _read_csv(processed / "real_global_universe_market_cap_coverage.csv")
    fx = _read_csv(processed / "global_fx_normalization_report.csv")
    coverage = _read_csv(processed / "global_returns_coverage_report.csv")
    source = _read_csv(processed / "real_global_universe_source_coverage.csv")
    if not market.empty and {"sleeve", "market_cap_rows"}.issubset(market.columns):
        equity_zero_cap = market.loc[
            market["sleeve"].astype(str).str.startswith("global_equity")
            & pd.to_numeric(market["market_cap_rows"], errors="coerce").eq(0)
        ]
        rows.append(
            [
                "Market-cap",
                "Equity sleeves with zero cap rows",
                int(equity_zero_cap.shape[0]),
                "Exact top-100 claim blocked.",
            ]
        )
    if not fx.empty:
        rows.append(
            [
                "FX",
                "not_implemented",
                int(
                    fx["fx_normalization_status"]
                    .astype(str)
                    .eq("not_implemented")
                    .sum()
                ),
                "Global USD promotion blocked.",
            ]
        )
    if not coverage.empty:
        rows.append(
            [
                "Price",
                "excluded assets",
                int((~coverage["included_in_returns"].astype(bool)).sum()),
                "Coverage/ticker mapping review needed.",
            ]
        )
    if not source.empty and "source_urls" in source:
        rows.append(
            [
                "Source",
                "rows with source URLs",
                int(pd.to_numeric(source["source_urls"], errors="coerce").sum()),
                "Source path exists; quality still depends on method.",
            ]
        )
    return rows


def _final_weights(processed: Path, decision: dict[str, Any]) -> list[list[Any]]:
    weights = _read_csv(processed / "global_master_candidate_weights.csv")
    final_model = str(decision.get("final_model", ""))
    if weights.empty:
        return [["Message"], ["No final weights found."]]
    final = weights.loc[weights["Model"].astype(str).eq(final_model)].copy()
    final["Weight_Percent"] = pd.to_numeric(final["Weight"], errors="coerce")
    final = final.sort_values("Weight", ascending=False)
    return _frame_to_rows(final[["Model", "Ticker", "Weight", "Weight_Percent"]], 200)


def _random_summary(processed: Path) -> list[list[Any]]:
    randoms = _read_csv(processed / "global_master_random_portfolio_benchmark.csv")
    cols = [
        col
        for col in ["CAGR", "Volatility", "Sharpe", "Max_Drawdown", "CVaR_95"]
        if col in randoms
    ]
    if randoms.empty or not cols:
        return [["Message"], ["Random benchmark missing."]]
    summary = randoms[cols].describe().reset_index()
    return _frame_to_rows(summary, 20)


def _appendix_paths() -> list[list[Any]]:
    files = sorted(PROCESSED.glob("global_*.csv")) + sorted(
        PROCESSED.glob("real_global_*.csv")
    )
    rows = [["File", "Purpose"]]
    rows.extend([str(path), "Raw generated output; not committed."] for path in files)
    return rows


def _csv(path: Path, max_rows: int) -> list[list[Any]]:
    return _frame_to_rows(_read_csv(path), max_rows)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame({"status": [f"missing: {path}"]})
    return pd.read_csv(path).drop(columns=["Unnamed: 0"], errors="ignore")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _frame_to_rows(frame: pd.DataFrame, max_rows: int) -> list[list[Any]]:
    if frame.empty:
        return [["status"], ["No rows available."]]
    clean = (
        frame.head(max_rows)
        .replace([np.inf, -np.inf], np.nan)
        .where(pd.notna(frame.head(max_rows)), "")
    )
    return [list(clean.columns)] + clean.astype(object).values.tolist()


def _cell(frame: pd.DataFrame, column: str) -> Any:
    if frame.empty or column not in frame:
        return ""
    return frame[column].iloc[0]


def _json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return ""
    return str(value)


def _decision_reason(decision: dict[str, Any]) -> str:
    reason = str(
        decision.get("reason", "FX, market-cap ve data quality blocker devam ediyor.")
    )
    return reason.replace(
        "net CAGR greater than Equal Weight",
        "net CAGR is not greater than Equal Weight",
    )


def _ensure_artifact_tool_node_modules(tmp_dir: Path) -> None:
    node_modules = tmp_dir / "node_modules"
    if node_modules.exists():
        return
    provided = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
    )
    if not provided.exists():
        raise RuntimeError(
            "artifact-tool node_modules not found in Codex runtime cache."
        )
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(node_modules), str(provided)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        os.symlink(provided, node_modules, target_is_directory=True)


def _js_builder() -> str:
    return textwrap.dedent(r"""
        import fs from "node:fs/promises";
        import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

        const [payloadPath, outputPath] = process.argv.slice(2);
        const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
        const workbook = Workbook.create();
        workbook.comments.setSelf({displayName: "QuantVerse"});

        function colLetter(n) {
          let s = "";
          while (n >= 0) {
            s = String.fromCharCode((n % 26) + 65) + s;
            n = Math.floor(n / 26) - 1;
          }
          return s;
        }

        for (const spec of payload.sheets) {
          const sheet = workbook.worksheets.add(spec.name);
          sheet.showGridLines = false;
          const rows = spec.rows.length ? spec.rows : [["status"], ["No rows available"]];
          const width = Math.max(...rows.map(r => r.length));
          const normalized = rows.map(r => {
            const copy = [...r];
            while (copy.length < width) copy.push("");
            return copy;
          });
          sheet.getRange("A1:D1").merge();
          sheet.getRange("A1").values = [[spec.name]];
          sheet.getRange("A1").format = {fill: "#102F45", font: {bold: true, color: "#FFFFFF", size: 14}};
          sheet.getRange("A2:D3").merge();
          sheet.getRange("A2").values = [[spec.explanation + " Kaynak grafik klasörü: " + payload.chart_folder]];
          sheet.getRange("A2").format = {fill: "#EAF3F8", wrapText: true, font: {color: "#102F45"}};
          const rowCount = normalized.length;
          const endCol = colLetter(width - 1);
          const tableRange = `A5:${endCol}${4 + rowCount}`;
          sheet.getRangeByIndexes(4, 0, rowCount, width).values = normalized;
          sheet.getRange(`A5:${endCol}5`).format = {fill: "#2F6F8F", font: {bold: true, color: "#FFFFFF"}, wrapText: true};
          sheet.getRange(tableRange).format.borders = {preset: "inside", style: "thin", color: "#D9E2E8"};
          sheet.getRange(tableRange).format.autofitColumns();
          sheet.getRange(tableRange).format.autofitRows();
          sheet.freezePanes.freezeRows(5);
        }

        const errors = await workbook.inspect({
          kind: "match",
          searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
          options: {useRegex: true, maxResults: 300},
          summary: "formula error scan",
        });
        await fs.writeFile(outputPath + ".inspect.ndjson", errors.ndjson);
        const output = await SpreadsheetFile.exportXlsx(workbook);
        await output.save(outputPath);
        """)


if __name__ == "__main__":
    raise SystemExit(main())
