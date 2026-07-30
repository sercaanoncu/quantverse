"""Build the single canonical QuantVerse portfolio PDF and HTML reports."""

from __future__ import annotations

import argparse
import base64
import html
import json
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "output" / "figures" / "portfolio_analysis"
PDF_PATH = ROOT / "output" / "pdf" / "quantverse_portfolio_analysis.pdf"
HTML_PATH = ROOT / "output" / "html" / "quantverse_portfolio_analysis.html"
PRIMARY_MODELS = [
    "Equal Weight",
    "Inverse Volatility",
    "HRP",
    "Risk Parity",
    "GMV",
    "Min CVaR",
]
INK = "#17202A"
BLUE = "#21618C"
GOLD = "#B7950B"
ORANGE = "#CA6F1E"
GREY = "#7B7D7D"
LIGHT = "#EEF2F3"
PDF_FONT = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8")) or {}
    acceptance = _read_json(PROCESSED / "global_portfolio_core_acceptance.json")
    if acceptance.get("overall_status") != "passed":
        raise RuntimeError("Portfolio reports require a passed core acceptance gate.")
    data = _load_data(config, acceptance)
    FIGURES.mkdir(parents=True, exist_ok=True)
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    charts = _build_charts(data)
    _build_pdf(data, charts)
    _build_html(data, charts)
    print(f"Portfolio PDF written: {PDF_PATH}")
    print(f"Portfolio HTML written: {HTML_PATH}")
    return 0


def _load_data(config: dict, acceptance: dict) -> dict[str, object]:
    decision = _read_json(PROCESSED / "global_final_model_decision.json")
    roles = _read_csv(PROCESSED / "global_current_portfolio_weights.csv")
    comparison = _read_csv(PROCESSED / "global_walk_forward_model_comparison.csv")
    oos = _read_csv(PROCESSED / "global_walk_forward_returns.csv")
    rejected = _read_csv(PROCESSED / "global_rejected_candidates.csv")
    contributions = _read_csv(PROCESSED / "global_risk_contribution_report.csv")
    cost = _read_csv(PROCESSED / "global_walk_forward_cost_sensitivity.csv")
    metadata = _read_csv(PROCESSED / "global_canonical_security_metadata.csv")
    sensitivity = _read_csv(PROCESSED / "global_holdings_count_sensitivity.csv")
    rf = _read_csv(PROCESSED / "global_risk_free_series.csv")
    windows = _read_csv(PROCESSED / "global_walk_forward_window_summary.csv")
    run = _read_json(PROCESSED / "quantverse_v2_run_manifest.json")
    oos["Date"] = pd.to_datetime(oos["Date"], errors="coerce")
    balanced = str(decision["balanced_research_portfolio"])
    benchmark = str(decision["transparent_benchmark"])
    defensive = str(decision["defensive_alternative"])
    current = roles.loc[
        roles["portfolio_role"].astype(str).eq("balanced_research_portfolio")
    ].copy()
    risk_contribution = contributions.loc[
        contributions["model_name"].astype(str).eq(balanced),
        ["ticker", "risk_contribution_pct"],
    ]
    current = current.merge(risk_contribution, on="ticker", how="left")
    v2 = config.get("v2", {})
    return {
        "config": v2,
        "acceptance": acceptance,
        "decision": decision,
        "roles": roles,
        "current": current.sort_values("weight", ascending=False),
        "comparison": comparison.loc[
            comparison["model_name"].astype(str).isin(PRIMARY_MODELS)
        ].copy(),
        "oos": oos.loc[oos["model_name"].astype(str).isin(PRIMARY_MODELS)].copy(),
        "rejected": rejected.head(20).copy(),
        "cost": cost.loc[cost["model_name"].astype(str).isin(PRIMARY_MODELS)].copy(),
        "metadata": metadata,
        "sensitivity": sensitivity,
        "rf": rf,
        "windows": windows,
        "run": run,
        "balanced": balanced,
        "benchmark": benchmark,
        "defensive": defensive,
    }


def _build_charts(data: dict[str, object]) -> dict[str, Path]:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": GREY,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "axes.titleweight": "bold",
        }
    )
    oos = data["oos"]
    comparison = data["comparison"].set_index("model_name")
    balanced = data["balanced"]
    defensive = data["defensive"]
    palette = {balanced: BLUE, defensive: ORANGE}
    paths: dict[str, Path] = {}

    pivot = oos.pivot(index="Date", columns="model_name", values="return").sort_index()
    wealth = (1.0 + pivot).cumprod()
    wealth = pd.concat(
        [
            pd.DataFrame(
                1.0,
                index=[wealth.index.min() - pd.Timedelta(days=1)],
                columns=wealth.columns,
            ),
            wealth,
        ]
    )
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for model in [balanced, defensive]:
        ax.plot(
            wealth.index,
            wealth[model],
            label=model,
            color=palette[model],
            linewidth=2.1,
        )
    ax.set_title("Stitched net OOS cumulative wealth")
    ax.set_ylabel("Starting wealth = 1.0")
    ax.grid(axis="y", color="#D5D8DC", linewidth=0.7)
    ax.legend(frameon=False)
    paths["cumulative"] = _save(fig, "oos_cumulative.png")

    drawdown = wealth / wealth.cummax() - 1.0
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for model in [balanced, defensive]:
        ax.plot(
            drawdown.index,
            drawdown[model],
            label=model,
            color=palette[model],
            linewidth=2.0,
        )
    ax.axhline(0.0, color=GREY, linewidth=0.8)
    ax.set_title("OOS drawdown paths")
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.grid(axis="y", color="#D5D8DC", linewidth=0.7)
    ax.legend(frameon=False)
    paths["drawdown"] = _save(fig, "oos_drawdown.png")

    rolling = pivot[[balanced, defensive]].rolling(126)
    rolling_return = rolling.mean() * 252
    rolling_vol = rolling.std(ddof=1) * np.sqrt(252)
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True)
    for model in [balanced, defensive]:
        axes[0].plot(
            rolling_return.index,
            rolling_return[model],
            label=model,
            color=palette[model],
        )
        axes[1].plot(
            rolling_vol.index, rolling_vol[model], label=model, color=palette[model]
        )
    axes[0].set_title("Rolling 126-day annualized return")
    axes[1].set_title("Rolling 126-day annualized volatility")
    for ax in axes:
        ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
        ax.grid(axis="y", color="#D5D8DC", linewidth=0.7)
    axes[0].legend(frameon=False, ncol=2)
    paths["rolling"] = _save(fig, "oos_rolling_stability.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for model, row in comparison.iterrows():
        color = BLUE if model == balanced else ORANGE if model == defensive else GREY
        ax.scatter(
            row["oos_volatility"], row["oos_annualized_return"], s=65, color=color
        )
        ax.annotate(
            model,
            (row["oos_volatility"], row["oos_annualized_return"]),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_title("Common-sample OOS risk and return")
    ax.set_xlabel("Annualized volatility")
    ax.set_ylabel("Annualized arithmetic return")
    ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.grid(color="#D5D8DC", linewidth=0.7)
    paths["risk_return"] = _save(fig, "model_risk_return.png")

    current = data["current"]
    sector = current.groupby("sector")["weight"].sum().sort_values()
    country = current.groupby("issuer_country")["weight"].sum().sort_values()
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.8))
    axes[0].barh(sector.index, sector.values, color=BLUE)
    axes[0].set_title("Sector exposure")
    axes[1].barh(country.index, country.values, color=GOLD)
    axes[1].set_title("Issuer-country exposure")
    for ax in axes:
        ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
        ax.grid(axis="x", color="#D5D8DC", linewidth=0.7)
    paths["exposure"] = _save(fig, "portfolio_exposure.png")

    intervals = data["comparison"].dropna(
        subset=["sharpe_diff_ci_lower", "sharpe_diff_ci_upper"]
    )
    intervals = intervals.sort_values("sharpe_diff_ci_lower")
    fig, ax = plt.subplots(figsize=(8.7, 4.3))
    centers = (
        intervals["sharpe_diff_ci_lower"] + intervals["sharpe_diff_ci_upper"]
    ) / 2
    errors = np.vstack(
        [
            centers - intervals["sharpe_diff_ci_lower"],
            intervals["sharpe_diff_ci_upper"] - centers,
        ]
    )
    ax.errorbar(
        centers,
        intervals["model_name"],
        xerr=errors,
        fmt="o",
        color=BLUE,
        ecolor=GREY,
        capsize=4,
    )
    ax.axvline(0.0, color=ORANGE, linewidth=1.2)
    ax.set_title("Paired bootstrap Sharpe difference vs Equal Weight")
    ax.set_xlabel("95% confidence interval")
    ax.grid(axis="x", color="#D5D8DC", linewidth=0.7)
    paths["uncertainty"] = _save(fig, "model_uncertainty.png")

    cost = data["cost"]
    fig, ax = plt.subplots(figsize=(8.7, 4.2))
    for model in [balanced, defensive]:
        group = cost.loc[cost["model_name"].astype(str).eq(model)].sort_values(
            "transaction_cost_bps"
        )
        ax.plot(
            group["transaction_cost_bps"],
            group["sharpe"],
            marker="o",
            label=model,
            color=palette[model],
        )
    ax.set_title("Transaction-cost sensitivity")
    ax.set_xlabel("Cost per traded notional (bps)")
    ax.set_ylabel("OOS Sharpe")
    ax.grid(color="#D5D8DC", linewidth=0.7)
    ax.legend(frameon=False)
    paths["cost"] = _save(fig, "cost_sensitivity.png")
    return paths


def _build_pdf(data: dict[str, object], charts: dict[str, Path]) -> None:
    _register_fonts()
    c = canvas.Canvas(str(PDF_PATH), pagesize=A4)
    width, height = A4
    current = data["current"]
    comparison = data["comparison"].set_index("model_name")
    decision = data["decision"]
    balanced = data["balanced"]
    defensive = data["defensive"]
    run = data["run"]
    oos_observations = _common_oos_observations(data["comparison"])

    _page(
        c, 1, "QuantVerse Current Portfolio", "US-listed global-issuer equity research"
    )
    _callout(
        c,
        48,
        height - 150,
        "Evidence status",
        "Research-grade with stated limitations",
        BLUE,
        width=487,
    )
    _callout(c, 48, height - 225, "Balanced allocation", balanced, BLUE)
    _callout(c, 300, height - 225, "Defensive alternative", defensive, ORANGE)
    _paragraph(c, 48, height - 295, decision["final_decision_reason"], 90)
    _paragraph(
        c,
        48,
        height - 380,
        f"As-of date: {run.get('data_as_of_date', 'unavailable')}. Investable scope: 100 current US-listed equities with usable USD returns; 20 economic issuers are selected. This is current-universe public-data research, not a point-in-time institutional backtest.",
        100,
    )
    _paragraph(
        c,
        48,
        height - 485,
        "Operational policy: long-only, 20 holdings, 10 bps primary cost, sector <=25%, industry <=15%, issuer-country <=60%, individual weight <=10%. The requested 5% cap with exactly 20 holdings mathematically forces Equal Weight, so 10% is the disclosed non-degenerate model-comparison cap.",
        105,
    )
    c.showPage()

    _page(
        c,
        2,
        "Exact Current Holdings And Weights",
        f"Balanced model: {balanced}; weights sum to {current['weight'].sum():.6f}",
    )
    table = current[
        [
            "ticker",
            "issuer_name",
            "weight",
            "sector",
            "issuer_country",
            "risk_contribution_pct",
        ]
    ].copy()
    _draw_table(
        c,
        table,
        38,
        height - 105,
        [45, 150, 55, 110, 85, 70],
        20,
        percent_columns={"weight", "risk_contribution_pct"},
    )
    _paragraph(
        c,
        42,
        62,
        "Method: current model weights are applied to the exact selected issuer representatives; component risk contribution uses sample covariance on complete common USD simple returns. Limitation/invalidation: current issuer classifications and current-universe membership are not historical PIT evidence.",
        115,
        size=7.5,
    )
    c.showPage()

    _page(
        c,
        3,
        "Why Selected; Why Near-Candidates Were Rejected",
        "Selection occurs after 504-day eligibility and issuer deduplication",
    )
    selected_table = current[
        [
            "ticker",
            "composite_quant_score",
            "momentum_12m",
            "volatility_12m",
            "max_drawdown",
            "selection_reason",
        ]
    ].copy()
    _draw_table(
        c,
        selected_table,
        35,
        height - 105,
        [42, 68, 65, 65, 65, 225],
        20,
        percent_columns={"momentum_12m", "volatility_12m", "max_drawdown"},
        size=6.5,
    )
    rejected = data["rejected"][
        ["ticker", "composite_quant_score", "selection_reason"]
    ].head(8)
    _draw_table(c, rejected, 45, 345, [50, 90, 380], 8, size=7)
    _paragraph(
        c,
        45,
        155,
        "Method: maximize the transparent composite score subject to exact holdings and issuer/sector/industry/country count feasibility. Rejections are not claims that a security is bad; they state why it did not enter this constrained research portfolio. Invalid if metadata or history eligibility is wrong.",
        115,
        size=7.5,
    )
    c.showPage()

    _page(
        c,
        4,
        "Balanced vs Benchmark vs Defensive",
        (
            f"All metrics use the same {oos_observations} net OOS days "
            "and time-aligned ^IRX hurdle"
        ),
    )
    c.drawImage(
        str(charts["risk_return"]),
        45,
        285,
        width=505,
        height=270,
        preserveAspectRatio=True,
    )
    role_models = [
        ("Balanced", balanced),
        ("Benchmark", data["benchmark"]),
        ("Defensive", defensive),
    ]
    rows = []
    for role, model in role_models:
        row = comparison.loc[model]
        rows.append(
            {
                "Role": role,
                "Model": model,
                "CAGR": row["oos_cagr"],
                "Vol": row["oos_volatility"],
                "Sharpe": row["oos_sharpe"],
                "Max DD": row["oos_max_drawdown"],
                "CVaR": row["oos_cvar_95"],
            }
        )
    _draw_table(
        c,
        pd.DataFrame(rows),
        45,
        255,
        [70, 100, 65, 65, 65, 65, 65],
        3,
        percent_columns={"CAGR", "Vol", "Max DD", "CVaR"},
    )
    _chart_note(
        c,
        45,
        80,
        "Risk is x-axis; annualized arithmetic return is y-axis. Equal Weight is balanced because no active Sharpe-difference lower bound exceeded zero. GMV is defensive because it has the least severe OOS drawdown and CVaR among positive-return valid models. Invalid if common dates, costs or RF alignment diverge.",
    )
    c.showPage()

    _page(
        c,
        5,
        "Stitched OOS Cumulative Return",
        "42 chronological 21-day folds; each net return appears once",
    )
    c.drawImage(
        str(charts["cumulative"]),
        45,
        250,
        width=505,
        height=300,
        preserveAspectRatio=True,
    )
    _chart_note(
        c,
        45,
        110,
        "Formula: cumulative wealth = product(1 + net daily simple return), initialized at 1.0. Interpretation: Equal Weight accumulated more wealth in this current-universe OOS path; GMV traded return for lower risk. Limitation: current constituents create survivorship risk; invalid if any test day is duplicated, omitted or selected with future data.",
    )
    c.showPage()

    _page(
        c,
        6,
        "Drawdown And Tail Risk",
        "Drawdown is always <= 0; CVaR is the mean daily loss beyond historical 95% VaR",
    )
    c.drawImage(
        str(charts["drawdown"]),
        45,
        250,
        width=505,
        height=300,
        preserveAspectRatio=True,
    )
    _chart_note(
        c,
        45,
        105,
        f"Observed OOS max drawdown: {balanced} {comparison.loc[balanced, 'oos_max_drawdown']:.1%}; {defensive} {comparison.loc[defensive, 'oos_max_drawdown']:.1%}. The defensive alternative materially reduced drawdown and tail loss but also reduced CAGR. Invalid if simple returns below -100%, missing weighted returns, or tail sign conventions are mishandled.",
    )
    c.showPage()

    _page(
        c,
        7,
        "Rolling Risk And Return Stability",
        "126-day windows show regime dependence; they are diagnostics, not separate backtests",
    )
    c.drawImage(
        str(charts["rolling"]), 45, 225, width=505, height=330, preserveAspectRatio=True
    )
    _chart_note(
        c,
        45,
        88,
        "Formula: rolling mean x 252 and rolling sample standard deviation x sqrt(252). Interpretation: relative performance and risk are not constant through time. Limitation: overlapping rolling windows are autocorrelated and are not independent evidence; invalid if presented as additional OOS observations.",
    )
    c.showPage()

    _page(
        c,
        8,
        "Sector And Issuer-Country Exposure",
        "Current 20-issuer balanced allocation; listing country is not issuer domicile",
    )
    c.drawImage(
        str(charts["exposure"]),
        40,
        230,
        width=515,
        height=330,
        preserveAspectRatio=True,
    )
    _chart_note(
        c,
        45,
        88,
        "Formula: sum current holding weights by current provider sector and issuer country. Exposures sum to 1.0; sector <=25% and issuer-country <=60%. Limitation: classifications are current and can change; USD listing currency does not eliminate foreign issuer economic exposure. Invalid if metadata coverage or weight reconciliation fails.",
    )
    c.showPage()

    _page(
        c,
        9,
        "Model Evidence, Uncertainty And Costs",
        "A higher point Sharpe is insufficient without a positive paired confidence bound",
    )
    c.drawImage(
        str(charts["uncertainty"]),
        35,
        365,
        width=525,
        height=220,
        preserveAspectRatio=True,
    )
    c.drawImage(
        str(charts["cost"]), 35, 130, width=525, height=220, preserveAspectRatio=True
    )
    _chart_note(
        c,
        42,
        55,
        "Methods: paired circular block bootstrap (21-day blocks, 95% CI) and turnover cost repricing at 5/10/25 bps. Every active-model Sharpe interval crosses zero, so none replaces Equal Weight. Limitation: bootstrap inference depends on block length and current-universe data; invalid if costs are not charged on each rebalance or pairing dates differ.",
        size=7.2,
    )
    c.showPage()

    _page(
        c,
        10,
        "Limitations And Invalidation Conditions",
        "Useful research allocation; not investment advice or live-trading approval",
    )
    limitations = [
        "Current universe is US-listed global-issuer equity research, not broad global exchange coverage.",
        "Current constituents are not historical point-in-time constituents; survivorship bias remains.",
        "Delistings, full corporate-action reconciliation and execution/capacity evidence are incomplete.",
        "Public yfinance prices and current issuer metadata are research-grade inputs, not institutional feeds.",
        "The 20-holding policy and constraints are operational research choices, not universal optima.",
        "The 5% requested cap with 20 holdings is a singleton Equal Weight solution; 10% is used for meaningful model comparison.",
        "Equal Weight wins this corrected sample; this does not guarantee future superiority.",
        "GMV is a defensive alternative, not a forecast of loss avoidance.",
        "Institutional/live trading remains blocked by PIT data, approval, monitoring, limits, tax, slippage and access controls.",
    ]
    y = height - 125
    for number, item in enumerate(limitations, 1):
        _paragraph(c, 55, y, f"{number}. {item}", 100, size=9)
        y -= 58
    _paragraph(
        c,
        48,
        85,
        "Invalidate and rebuild whenever the universe, identity mapping, metadata, price history, FX/listing semantics, risk-free source, transaction costs, selected issuers, model code or as-of date changes.",
        105,
        size=8,
        bold=True,
    )
    c.save()


def _build_html(data: dict[str, object], charts: dict[str, Path]) -> None:
    current = data["current"]
    comparison = data["comparison"]
    rejected = data["rejected"].head(20)
    decision = data["decision"]
    images = {key: _data_uri(path) for key, path in charts.items()}
    html_text = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuantVerse Portfolio Analysis</title><style>
:root{{--ink:#17202a;--blue:#21618c;--gold:#b7950b;--orange:#ca6f1e;--line:#d5d8dc;--soft:#f4f6f7}}
*{{box-sizing:border-box}} body{{margin:0;font:15px/1.55 Arial,sans-serif;color:var(--ink);background:white}}
header{{padding:40px max(24px,calc((100% - 1120px)/2));border-bottom:4px solid var(--blue)}}
main{{max-width:1120px;margin:auto;padding:24px}} h1{{font-size:34px;margin:0 0 8px}} h2{{margin-top:42px;border-bottom:1px solid var(--line);padding-bottom:8px}}
.status{{font-size:18px;color:var(--blue);font-weight:700}} .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.kpi{{border:1px solid var(--line);padding:14px;border-radius:4px}} .kpi b{{display:block;font-size:20px}}
figure{{margin:26px 0}} figure img{{width:100%;max-height:540px;object-fit:contain}} figcaption{{background:var(--soft);padding:12px;border-left:4px solid var(--gold)}}
.table-wrap{{overflow:auto}} table{{border-collapse:collapse;width:100%;font-size:12px}} th,td{{padding:7px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}} th{{background:var(--ink);color:white;position:sticky;top:0}}
.warning{{border-left:5px solid var(--orange);background:#fdf2e9;padding:14px}} @media(max-width:720px){{.grid{{grid-template-columns:1fr}}h1{{font-size:27px}}main{{padding:16px}}}}
</style></head><body><header><h1>QuantVerse Current Portfolio Analysis</h1><div class="status">Evidence status: Research-grade with stated limitations</div><p>{html.escape(str(data['config'].get('declared_scope')))}</p></header><main>
<section class="grid"><div class="kpi">balanced_research_portfolio<b>{html.escape(str(data['balanced']))}</b></div><div class="kpi">transparent_benchmark<b>{html.escape(str(data['benchmark']))}</b></div><div class="kpi">defensive_alternative<b>{html.escape(str(data['defensive']))}</b></div></section>
<p>{html.escape(str(decision['final_decision_reason']))}</p>
<h2>Current holdings and exact weights</h2><div class="table-wrap">{_html_table(current[['ticker','issuer_name','weight','sector','issuer_country','risk_contribution_pct']], {'weight','risk_contribution_pct'})}</div>
<h2>Model comparison</h2><div class="table-wrap">{_html_table(comparison[['model_name','oos_cagr','oos_annualized_return','oos_volatility','oos_sharpe','oos_sortino','oos_max_drawdown','oos_cvar_95','avg_turnover']], {'oos_cagr','oos_annualized_return','oos_volatility','oos_max_drawdown','oos_cvar_95'})}</div>
{_html_figure(images['risk_return'],'Common-sample OOS risk and return','Risk is on x-axis and return on y-axis. Same dates, costs and ^IRX hurdle. Invalid if evidence samples diverge.')}
{_html_figure(images['cumulative'],'Stitched OOS cumulative wealth','product(1 + net daily return), initialized at 1.0. Current-universe survivorship remains.')}
{_html_figure(images['drawdown'],'OOS drawdown','Drawdown <= 0. GMV reduces observed loss depth but also return. Historical evidence is not a guarantee.')}
{_html_figure(images['rolling'],'Rolling stability','126-day annualized diagnostics; overlapping windows are not independent evidence.')}
{_html_figure(images['exposure'],'Sector and issuer-country exposure','Weights sum to 1.0; current classifications are not PIT historical classifications.')}
{_html_figure(images['uncertainty'],'Paired bootstrap uncertainty','All active-model 95% Sharpe-difference intervals cross zero; no active model replaces Equal Weight.')}
{_html_figure(images['cost'],'Cost sensitivity','Stitched OOS returns repriced at 5, 10 and 25 bps per traded notional.')}
<h2>Near-candidate rejection reasons</h2><div class="table-wrap">{_html_table(rejected[['ticker','composite_quant_score','selection_reason']], set())}</div>
<h2>Limitations</h2><div class="warning">US-listed current-universe research only; no historical PIT constituents, complete delisting/corporate-action evidence, institutional execution model or live-trading approval. The requested 5% cap with 20 holdings forces Equal Weight; the disclosed 10% operational cap preserves a meaningful model comparison. Not investment advice.</div>
</main></body></html>"""
    HTML_PATH.write_text(html_text, encoding="utf-8")


def _page(c: canvas.Canvas, number: int, title: str, subtitle: str) -> None:
    width, height = A4
    c.setFillColor(colors.HexColor(INK))
    c.setFont(PDF_FONT_BOLD, 19)
    c.drawString(42, height - 48, title)
    c.setFont(PDF_FONT, 8.5)
    c.setFillColor(colors.HexColor(GREY))
    c.drawString(42, height - 66, subtitle)
    c.setStrokeColor(colors.HexColor(BLUE))
    c.setLineWidth(2)
    c.line(42, height - 76, width - 42, height - 76)
    c.setFont(PDF_FONT, 7)
    c.drawRightString(width - 42, 24, f"QuantVerse | {number}/10")


def _callout(
    c: canvas.Canvas,
    x: float,
    y: float,
    label: str,
    value: str,
    color: str,
    *,
    width: float = 235,
) -> None:
    c.setFillColor(colors.HexColor(LIGHT))
    c.roundRect(x, y, width, 58, 4, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(color))
    c.setFont(PDF_FONT_BOLD, 8)
    c.drawString(x + 12, y + 39, label.upper())
    c.setFillColor(colors.HexColor(INK))
    c.setFont(PDF_FONT_BOLD, 12)
    max_characters = max(12, int(width / 7.0))
    c.drawString(x + 12, y + 17, str(value)[:max_characters])


def _paragraph(
    c: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    width_chars: int,
    *,
    size: float = 9,
    bold: bool = False,
) -> None:
    c.setFillColor(colors.HexColor(INK))
    c.setFont(PDF_FONT_BOLD if bold else PDF_FONT, size)
    for line in textwrap.wrap(str(text), width=width_chars):
        c.drawString(x, y, line)
        y -= size * 1.45


def _draw_table(
    c: canvas.Canvas,
    frame: pd.DataFrame,
    x: float,
    y: float,
    widths: list[float],
    max_rows: int,
    *,
    percent_columns: set[str] | None = None,
    size: float = 7,
) -> None:
    percent_columns = percent_columns or set()
    row_height = 17
    c.setFont(PDF_FONT_BOLD, size)
    c.setFillColor(colors.HexColor(INK))
    c.rect(x, y - row_height, sum(widths), row_height, fill=1, stroke=0)
    cursor = x
    for column, width in zip(frame.columns, widths, strict=True):
        c.setFillColor(colors.white)
        c.drawString(cursor + 3, y - 12, str(column)[:24])
        cursor += width
    c.setFont(PDF_FONT, size)
    for row_number, (_, row) in enumerate(frame.head(max_rows).iterrows(), 1):
        top = y - row_height * row_number
        if row_number % 2 == 0:
            c.setFillColor(colors.HexColor("#F8F9F9"))
            c.rect(x, top - row_height, sum(widths), row_height, fill=1, stroke=0)
        cursor = x
        for column, width in zip(frame.columns, widths, strict=True):
            value = row[column]
            if column in percent_columns and pd.notna(value):
                display = f"{float(value):.1%}"
            elif isinstance(value, (float, np.floating)) and pd.notna(value):
                display = f"{float(value):.3f}"
            else:
                display = str(value)
            c.setFillColor(colors.HexColor(INK))
            c.drawString(
                cursor + 3, top - 12, display[: max(4, int(width / (size * 0.53)))]
            )
            cursor += width


def _chart_note(
    c: canvas.Canvas, x: float, y: float, text: str, *, size: float = 7.8
) -> None:
    c.setFillColor(colors.HexColor(LIGHT))
    c.roundRect(x, y, 505, 90, 3, fill=1, stroke=0)
    _paragraph(c, x + 10, y + 72, text, 118, size=size)


def _register_fonts() -> None:
    global PDF_FONT, PDF_FONT_BOLD

    PDF_FONT = "Helvetica"
    PDF_FONT_BOLD = "Helvetica-Bold"
    try:
        regular = Path(
            font_manager.findfont(
                font_manager.FontProperties(family="DejaVu Sans", weight="normal")
            )
        )
        bold = Path(
            font_manager.findfont(
                font_manager.FontProperties(family="DejaVu Sans", weight="bold")
            )
        )
        if not regular.is_file() or not bold.is_file():
            return
        pdfmetrics.registerFont(TTFont("QuantVerseSans", str(regular)))
        pdfmetrics.registerFont(TTFont("QuantVerseSans-Bold", str(bold)))
        PDF_FONT = "QuantVerseSans"
        PDF_FONT_BOLD = "QuantVerseSans-Bold"
    except (OSError, RuntimeError):
        # Built-in Helvetica keeps generation available if font discovery fails.
        return


def _common_oos_observations(comparison: pd.DataFrame) -> int:
    observations = (
        pd.to_numeric(comparison["oos_observations"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
    )
    if len(observations) != 1 or observations[0] <= 0:
        raise RuntimeError(
            "Canonical report requires one positive common OOS observation count."
        )
    return int(observations[0])


def _save(fig: plt.Figure, filename: str) -> Path:
    path = FIGURES / filename
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode(
        "ascii"
    )


def _html_figure(src: str, title: str, note: str) -> str:
    return f'<figure><h2>{html.escape(title)}</h2><img src="{src}" alt="{html.escape(title)}"><figcaption>{html.escape(note)}</figcaption></figure>'


def _html_table(frame: pd.DataFrame, percent_columns: set[str]) -> str:
    copy = frame.copy()
    for column in copy.columns:
        if column in percent_columns:
            copy[column] = pd.to_numeric(copy[column], errors="coerce").map(
                lambda value: f"{value:.2%}" if pd.notna(value) else ""
            )
        elif pd.api.types.is_numeric_dtype(copy[column]):
            copy[column] = copy[column].map(
                lambda value: f"{value:.4f}" if pd.notna(value) else ""
            )
    return copy.to_html(index=False, escape=True, border=0)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


if __name__ == "__main__":
    sys.exit(main())
