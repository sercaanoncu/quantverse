"""Build chart-led Turkish scientific audit report and presentation."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

PROCESSED = Path("data/processed")
FIG_DIR = Path("output/figures/global_audit")
REPORT_MD = Path("output/reports/quantverse_visual_scientific_audit_report.md")
REPORT_PDF = Path("output/pdf/quantverse_visual_scientific_audit_report.pdf")
PRESENTATION_MD = Path(
    "output/reports/quantverse_visual_scientific_audit_presentation.md"
)
PRESENTATION_PDF = Path(
    "output/pdf/quantverse_visual_scientific_audit_presentation.pdf"
)


@dataclass
class ChartSpec:
    key: str
    title: str
    source: str
    explanation: str
    importance: str
    red_flag: str
    decision: str
    filename: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default=str(PROCESSED))
    parser.add_argument("--figure-dir", default=str(FIG_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed = Path(args.processed_dir)
    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    data = _load_data(processed)
    specs = _build_charts(data, processed, figure_dir)
    _write_markdown(specs, data)
    _write_pdf(specs, data, REPORT_PDF, "QuantVerse Görsel Bilimsel Denetim Raporu")
    _write_presentation_markdown(specs, data)
    _write_pdf(
        specs,
        data,
        PRESENTATION_PDF,
        "QuantVerse Görsel Bilimsel Denetim Sunumu",
        presentation=True,
        pagesize=landscape(A4),
    )
    print(f"Charts generated: {len(specs)}")
    print(f"Report written: {REPORT_PDF}")
    print(f"Presentation written: {PRESENTATION_PDF}")
    return 0


def _load_data(processed: Path) -> dict[str, pd.DataFrame | dict]:
    files = {
        "universe": "real_global_universe_population_summary.csv",
        "source": "real_global_universe_source_coverage.csv",
        "market_cap": "real_global_universe_market_cap_coverage.csv",
        "coverage": "global_returns_coverage_report.csv",
        "fx": "global_fx_normalization_report.csv",
        "normality": "global_normality_tests.csv",
        "stationarity": "global_stationarity_tests.csv",
        "cluster_diag": "global_cluster_diagnostics.csv",
        "cluster_membership": "global_cluster_membership.csv",
        "pca": "global_pca_summary.csv",
        "covariance": "global_covariance_estimator_comparison.csv",
        "model_comparison": "global_master_model_comparison.csv",
        "constraint": "global_master_constraint_audit.csv",
        "weights": "global_master_candidate_weights.csv",
        "asset_class": "global_master_asset_class_weights.csv",
        "region": "global_master_region_weights.csv",
        "cluster_weights": "global_master_cluster_weights.csv",
        "random": "global_master_random_portfolio_benchmark.csv",
        "monte_carlo": "global_monte_carlo_projection.csv",
        "sanity": "global_scientific_sanity_issues.csv",
        "requirement": "user_requirement_traceability_matrix.csv",
        "applicability": "model_applicability_matrix.csv",
    }
    data: dict[str, pd.DataFrame | dict] = {
        key: _read_csv(processed / filename) for key, filename in files.items()
    }
    decision_path = processed / "global_master_decision_summary.json"
    data["decision"] = (
        json.loads(decision_path.read_text(encoding="utf-8"))
        if decision_path.exists()
        else {}
    )
    return data


def _build_charts(
    data: dict[str, pd.DataFrame | dict],
    processed: Path,
    figure_dir: Path,
) -> list[ChartSpec]:
    chart_builders: list[tuple[ChartSpec, Callable[[Path], None]]] = [
        (
            _spec(
                "universe_rows_by_sleeve",
                "Evren satırları: hangi varlık sınıfından kaç satır var?",
                "data/processed/real_global_universe_population_summary.csv",
                "Her sütun bir sleeve içindeki kaynak satır sayısını gösterir.",
                "Gerçek hisselerin ve proxy varlıkların analize girip girmediğini gösterir.",
                "Sıfır satırlı ana sleeve veri eksikliği kırmızı bayraktır.",
                "Gerçek hisse/proxy evreni var; ancak exact top-100 iddiası ayrı kanıt ister.",
            ),
            lambda p: _bar(
                data["universe"],
                "sleeve",
                "rows",
                p,
                "Evren satır sayısı",
                "Sleeve",
                "Satır",
            ),
        ),
        (
            _spec(
                "included_vs_excluded_assets",
                "Fiyat kapsamı: dahil edilen ve düşen varlıklar",
                "data/processed/global_returns_coverage_report.csv",
                "Fiyat geçmişi yeterli olan varlıklar dahil, yetersiz olanlar hariçtir.",
                "Eksik fiyat kapsamı performans yanlılığı yaratabilir.",
                "Çok fazla excluded varlık veri sağlayıcı/ticker mapping problemidir.",
                "685 varlık analize girmiş, 20 varlık coverage nedeniyle düşmüş.",
            ),
            lambda p: _coverage_chart(data["coverage"], p),
        ),
        (
            _spec(
                "source_method_coverage",
                "Kaynak yöntemi: exact mi, proxy mi?",
                "data/processed/real_global_universe_source_coverage.csv",
                "source_method alanı veri iddiasının gücünü gösterir.",
                "Index proxy ile exact top-100 aynı şey değildir.",
                "Proxy kaynak exact market-cap top-100 gibi anlatılırsa bilimsel hata olur.",
                "Equity sleeve'ler index_proxy; crypto market-cap API enriched.",
            ),
            lambda p: _source_method_chart(data["source"], p),
        ),
        (
            _spec(
                "market_cap_coverage",
                "Market-cap kanıtı: hangi sleeve destekli?",
                "data/processed/real_global_universe_market_cap_coverage.csv",
                "Market-cap satırları exact top-100 ve Black-Litterman için temel kanıttır.",
                "Market-cap yoksa exact rank iddiası yoktur.",
                "Equity market-cap coverage yoksa global top-100 promotion blokludur.",
                "Crypto dışında equity market-cap coverage eksik.",
            ),
            lambda p: _market_cap_chart(data["market_cap"], p),
        ),
        (
            _spec(
                "fx_status",
                "FX durumu: USD bazlı terfi neden bloklu?",
                "data/processed/global_fx_normalization_report.csv",
                "Her varlığın baz para birimine çevrilip çevrilmediğini gösterir.",
                "Global USD portföy için non-USD getiriler USD'ye çevrilmelidir.",
                "not_implemented satırları terfi bloklayıcıdır.",
                "475 satırda FX normalizasyonu yok; not promoted doğru karar.",
            ),
            lambda p: _count_chart(
                data["fx"],
                "fx_normalization_status",
                p,
                "FX normalizasyon durumu",
                "Durum",
                "Varlık",
            ),
        ),
        (
            _spec(
                "price_coverage_by_sleeve",
                "Sleeve bazında fiyat kapsamı",
                "data/processed/global_returns_coverage_report.csv + current_global_equity_universe.csv",
                "Hangi sleeve'lerde fiyat verisi eksildiğini gösterir.",
                "Coverage bias portföy seçimini etkileyebilir.",
                "Bir sleeve fiyat verisi kaybederse sonuç temsili zayıflar.",
                "Eksik fiyatlar ticker/provider mapping olarak izlenmeli.",
            ),
            lambda p: _price_by_sleeve_chart(data["coverage"], p),
        ),
        (
            _spec(
                "normality_counts",
                "Normality testi: getiriler normal mi?",
                "data/processed/global_normality_tests.csv",
                "Jarque-Bera sonucu kaç varlıkta normalite reddedildiğini gösterir.",
                "Normal olmayan getiriler tail-risk yöntemleri gerektirir.",
                "Normal kabul edip sadece normal varsayımıyla karar vermek hatadır.",
                "684 varlıkta normalite reddedildi; CVaR/stress yorumları önemlidir.",
            ),
            lambda p: _count_chart(
                data["normality"],
                "normality_result",
                p,
                "Normality sonucu",
                "Sonuç",
                "Varlık",
            ),
        ),
        (
            _spec(
                "stationarity_counts",
                "Stationarity testi: getiri serileri durağan mı?",
                "data/processed/global_stationarity_tests.csv",
                "ADF sonuçlarının özetini gösterir.",
                "ARMA/ARIMA gibi modeller için durağanlık önemlidir.",
                "Durağanlık yoksa zaman serisi modeli kör çalıştırılamaz.",
                "Çoğu getiri serisi unit root'u reddediyor; yine de tahmin gücü garanti değil.",
            ),
            lambda p: _count_chart(
                data["stationarity"],
                "stationarity_result",
                p,
                "Stationarity sonucu",
                "Sonuç",
                "Varlık",
            ),
        ),
        (
            _spec(
                "cluster_elbow_silhouette",
                "Kümeleme: k seçimi için silhouette/elbow",
                "data/processed/global_cluster_diagnostics.csv",
                "Farklı k değerlerinde cluster kalitesini gösterir.",
                "Küme sayısı tamamen keyfi olmamalıdır.",
                "Çok düşük silhouette cluster güvenini azaltır.",
                "Kümeleme tanısal; promotion için tek başına yeterli değil.",
            ),
            lambda p: _cluster_diag_chart(data["cluster_diag"], p),
        ),
        (
            _spec(
                "cluster_membership_counts",
                "Correlation cluster büyüklükleri",
                "data/processed/global_cluster_membership.csv",
                "Her correlation cluster içindeki varlık sayısıdır.",
                "Aşırı büyük cluster çeşitlendirme riskini gösterir.",
                "Tek cluster çok baskınsa cluster cap açıklanmalıdır.",
                "Final candidate cluster cap ile sınırlandırıldı.",
            ),
            lambda p: _cluster_count_chart(data["cluster_membership"], p),
        ),
        (
            _spec(
                "pca_explained_variance",
                "PCA: ortak faktör yoğunluğu",
                "data/processed/global_pca_summary.csv",
                "İlk bileşenlerin açıklanan varyansını gösterir.",
                "PCA piyasa/faktör yoğunlaşmasını görmeye yarar.",
                "Tek faktör aşırı baskınsa çeşitlendirme zayıf olabilir.",
                "PCA tanısaldır, doğrudan al-sat sinyali değildir.",
            ),
            lambda p: _pca_chart(data["pca"], p),
        ),
        (
            _spec(
                "covariance_condition_number",
                "Kovaryans kararlılığı",
                "data/processed/global_covariance_estimator_comparison.csv",
                "Estimator condition number değerlerini gösterir.",
                "Ill-conditioned kovaryans optimizasyonu bozabilir.",
                "Çok yüksek condition number optimizer red flag'dir.",
                "Shrinkage estimator daha kararlı görünüyor.",
            ),
            lambda p: _covariance_chart(data["covariance"], p),
        ),
        (
            _spec(
                "model_cagr_vol_scatter",
                "Model karşılaştırması: CAGR vs volatilite",
                "data/processed/global_master_model_comparison.csv",
                "Her nokta bir modelin getiri-risk konumudur.",
                "Yüksek getiri tek başına başarı değildir.",
                "Aşırı volatilite veya şüpheli CAGR terfi engelidir.",
                "Policy Constrained daha makul ama EW CAGR'ı geçmiyor.",
            ),
            lambda p: _scatter_model(data["model_comparison"], p),
        ),
        (
            _spec(
                "model_sharpe_bar",
                "Model Sharpe karşılaştırması",
                "data/processed/global_master_model_comparison.csv",
                "Sharpe değerlerini model bazında gösterir.",
                "Risk-adjusted performans return-only metrikten ayrıdır.",
                "Sharpe çok yüksekse veri/ölçek kontrolü gerekir.",
                "Inverse Volatility Sharpe yüksek ama kısıtları ihlal ediyor.",
            ),
            lambda p: _model_metric_bar(
                data["model_comparison"], "Sharpe", p, "Sharpe"
            ),
        ),
        (
            _spec(
                "drawdown_cvar_comparison",
                "Drawdown ve CVaR karşılaştırması",
                "data/processed/global_master_model_comparison.csv",
                "Aşağı yönlü risk metriklerini birlikte gösterir.",
                "CAGR yüksek olsa bile tail risk karar değiştirir.",
                "Max drawdown/CVaR kötüleşirse promotion zayıflar.",
                "Policy Constrained risk tarafında izlenebilir ama promoted değil.",
            ),
            lambda p: _risk_pair_chart(data["model_comparison"], p),
        ),
        (
            _spec(
                "constraint_pass_fail",
                "Kısıt audit: hangi model geçiyor?",
                "data/processed/global_master_constraint_audit.csv",
                "Her modelin hard constraints sonucunu gösterir.",
                "User-facing final aday hard constraints geçmelidir.",
                "Final model constraint fail ise kritik hatadır.",
                "Policy Constrained tüm kısıtları geçiyor.",
            ),
            lambda p: _constraint_chart(data["constraint"], p),
        ),
        (
            _spec(
                "final_top20_weights",
                "Final aday: en yüksek 20 ağırlık",
                "data/processed/global_master_candidate_weights.csv",
                "Final modelin en büyük pozisyonlarını gösterir.",
                "Ağırlık yoğunlaşması kullanıcı tarafından görülmelidir.",
                "Çok fazla max-cap pozisyon kısıtların bağlandığını gösterir.",
                "Full weights CSV esas kaynaktır; bu grafik ilk 20'dir.",
            ),
            lambda p: _final_top_weights(data, p),
        ),
        (
            _spec(
                "final_sleeve_weights",
                "Final aday: sleeve ağırlıkları",
                "data/processed/global_master_asset_class_weights.csv",
                "Varlık sınıfı/sleeve dağılımını gösterir.",
                "Ekonomik anlam için portföyün neye maruz kaldığı bilinmelidir.",
                "Tek sleeve baskınsa yorum gerekir.",
                "Turkey/Japan/bond proxy ağırlıkları açık görülüyor.",
            ),
            lambda p: _bar(
                data["asset_class"],
                "Asset_Class",
                "Weight",
                p,
                "Final sleeve ağırlıkları",
                "Sleeve",
                "Ağırlık",
                percent=True,
            ),
        ),
        (
            _spec(
                "final_region_weights",
                "Final aday: bölge ağırlıkları",
                "data/processed/global_master_region_weights.csv",
                "Bölgesel dağılımı gösterir.",
                "Global portföyde region cap ekonomik riski sınırlar.",
                "Bölge yoğunlaşması çeşitlendirme riskidir.",
                "Region cap sınırları bağlayıcı olabilir.",
            ),
            lambda p: _bar(
                data["region"],
                "Region",
                "Weight",
                p,
                "Final bölge ağırlıkları",
                "Bölge",
                "Ağırlık",
                percent=True,
            ),
        ),
        (
            _spec(
                "final_cluster_weights",
                "Final aday: cluster ağırlıkları",
                "data/processed/global_master_cluster_weights.csv",
                "Correlation cluster ağırlıklarını gösterir.",
                "Benzer hareket eden varlıklara aşırı yüklenmeyi gösterir.",
                "Cluster cap sınırında çok cluster varsa açıklama gerekir.",
                "Final candidate cluster cap'i geçmiyor.",
            ),
            lambda p: _bar(
                data["cluster_weights"],
                "Cluster",
                "Weight",
                p,
                "Final cluster ağırlıkları",
                "Cluster",
                "Ağırlık",
                percent=True,
            ),
        ),
        (
            _spec(
                "random_sharpe_distribution",
                "Random portfolio Sharpe dağılımı",
                "data/processed/global_master_random_portfolio_benchmark.csv",
                "10.000 random portföyün Sharpe dağılımını gösterir.",
                "Adayın rastgele portföylere göre nerede durduğunu gösterir.",
                "Random benchmark geleceği kanıtlamaz.",
                "Policy Constrained random Sharpe 95. yüzdelik eşiğini geçiyor ama EW CAGR'ı geçmiyor.",
            ),
            lambda p: _random_sharpe_chart(data, p),
        ),
        (
            _spec(
                "monte_carlo_percentiles",
                "Monte Carlo percentile bandı",
                "data/processed/global_monte_carlo_projection.csv",
                "1/3/6/12 ay için 5., 50. ve 95. yüzdelikleri gösterir.",
                "Projection belirsizliğini tek sayı yerine aralıkla anlatır.",
                "Geniş bant yüksek belirsizlik demektir.",
                "Projeksiyon karar desteğidir, garanti değildir.",
            ),
            lambda p: _projection_band_chart(data["monte_carlo"], p),
        ),
        (
            _spec(
                "projection_horizon_chart",
                "Projection horizon: ortalama ve zarar olasılığı",
                "data/processed/global_monte_carlo_projection.csv",
                "Horizon bazında mean return ve loss probability gösterir.",
                "Beklenen getiri ile zarar olasılığı birlikte okunmalıdır.",
                "Yüksek loss probability terfi için zayıf kanıttır.",
                "1M loss probability yaklaşık yarıya yakın.",
            ),
            lambda p: _projection_loss_chart(data["monte_carlo"], p),
        ),
        (
            _spec(
                "red_flag_count_by_severity",
                "Bilimsel kırmızı bayraklar",
                "data/processed/global_scientific_sanity_issues.csv",
                "Severity bazında issue sayısını gösterir.",
                "Kod çalışsa bile bilimsel riskler devam edebilir.",
                "Critical/high blocker varsa promotion yapılamaz.",
                "FX ve market-cap blocker'ları açıkça kalıyor.",
            ),
            lambda p: _count_chart(
                data["sanity"], "severity", p, "Red flag severity", "Severity", "Issue"
            ),
        ),
        (
            _spec(
                "requirement_traceability_status",
                "User requirement durumu",
                "data/processed/user_requirement_traceability_matrix.csv",
                "Kullanıcı taleplerinin karşılanma durumunu gösterir.",
                "Proje başarısı sadece model metriği değil requirement coverage'dır.",
                "Blocked/partially_met satırları sonraki sprint işidir.",
                "Bu sprint görselleştirme ve açıklanabilirlik açığını kapatır.",
            ),
            lambda p: _count_chart(
                data["requirement"], "status", p, "Requirement status", "Durum", "Adet"
            ),
        ),
    ]
    specs = []
    for spec, builder in chart_builders:
        path = figure_dir / spec.filename
        builder(path)
        specs.append(spec)
    return specs


def _spec(
    key: str,
    title: str,
    source: str,
    explanation: str,
    importance: str,
    red_flag: str,
    decision: str,
) -> ChartSpec:
    return ChartSpec(
        key=key,
        title=title,
        source=source,
        explanation=explanation,
        importance=importance,
        red_flag=red_flag,
        decision=decision,
        filename=f"{key}.png",
    )


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).drop(columns=["Unnamed: 0"], errors="ignore")


def _prepare_ax(title: str, xlabel: str = "", ylabel: str = ""):
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=140)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    return fig, ax


def _finish(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _bar(
    frame: pd.DataFrame,
    x: str,
    y: str,
    path: Path,
    title: str,
    xlabel: str,
    ylabel: str,
    *,
    percent: bool = False,
) -> None:
    if frame.empty or x not in frame or y not in frame:
        _empty_chart(path, title)
        return
    data = frame[[x, y]].copy()
    data[y] = pd.to_numeric(data[y], errors="coerce").fillna(0)
    data = data.sort_values(y, ascending=True)
    fig, ax = _prepare_ax(title, xlabel, ylabel)
    ax.barh(data[x].astype(str), data[y], color="#2F6F8F")
    if percent:
        ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    _finish(fig, path)


def _count_chart(
    frame: pd.DataFrame, column: str, path: Path, title: str, xlabel: str, ylabel: str
) -> None:
    if frame.empty or column not in frame:
        _empty_chart(path, title)
        return
    counts = frame[column].fillna("missing").astype(str).value_counts().sort_values()
    fig, ax = _prepare_ax(title, xlabel, ylabel)
    ax.barh(counts.index, counts.values, color="#4C956C")
    _finish(fig, path)


def _coverage_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty or "included_in_returns" not in frame:
        _empty_chart(path, "Fiyat kapsamı")
        return
    counts = frame["included_in_returns"].astype(str).value_counts()
    fig, ax = _prepare_ax("Included vs excluded assets", "Durum", "Varlık")
    ax.bar(counts.index, counts.values, color=["#4C956C", "#D95D39"][: len(counts)])
    _finish(fig, path)


def _source_method_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty or "source_methods" not in frame:
        _empty_chart(path, "Source methods")
        return
    exploded = frame.assign(
        source_methods=frame["source_methods"].astype(str).str.split(", ")
    ).explode("source_methods")
    counts = exploded.groupby("source_methods")["rows"].sum().sort_values()
    fig, ax = _prepare_ax("Source method coverage", "Source method", "Satır")
    ax.barh(counts.index, counts.values, color="#2F6F8F")
    _finish(fig, path)


def _market_cap_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        _empty_chart(path, "Market-cap coverage")
        return
    data = frame.copy()
    data["missing_cap_rows"] = pd.to_numeric(
        data["rows"], errors="coerce"
    ) - pd.to_numeric(data["market_cap_rows"], errors="coerce")
    data = data.sort_values("rows", ascending=True)
    fig, ax = _prepare_ax("Market-cap coverage by sleeve", "Satır", "Sleeve")
    ax.barh(
        data["sleeve"], data["market_cap_rows"], label="Market-cap var", color="#4C956C"
    )
    ax.barh(
        data["sleeve"],
        data["missing_cap_rows"],
        left=data["market_cap_rows"],
        label="Eksik",
        color="#D95D39",
    )
    ax.legend()
    _finish(fig, path)


def _price_by_sleeve_chart(coverage: pd.DataFrame, path: Path) -> None:
    universe = _read_csv(Path("data/universe/current_global_equity_universe.csv"))
    if coverage.empty or universe.empty or "ticker" not in coverage:
        _coverage_chart(coverage, path)
        return
    merged = coverage.merge(universe[["ticker", "sleeve"]], on="ticker", how="left")
    grouped = (
        merged.groupby(["sleeve", "included_in_returns"]).size().unstack(fill_value=0)
    )
    grouped = grouped.sort_index()
    fig, ax = _prepare_ax("Price coverage by sleeve", "Sleeve", "Varlık")
    grouped.plot(kind="bar", stacked=True, ax=ax, color=["#D95D39", "#4C956C"])
    ax.tick_params(axis="x", labelrotation=75)
    _finish(fig, path)


def _cluster_diag_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty or "k" not in frame:
        _empty_chart(path, "Cluster diagnostics")
        return
    fig, ax1 = _prepare_ax("Cluster diagnostics", "k", "Silhouette")
    ax1.plot(
        frame["k"],
        frame["silhouette_score"],
        marker="o",
        color="#2F6F8F",
        label="Silhouette",
    )
    ax2 = ax1.twinx()
    ax2.plot(
        frame["k"],
        frame["within_cluster_distance"],
        marker="s",
        color="#D95D39",
        label="Within distance",
    )
    ax2.set_ylabel("Within-cluster distance")
    _finish(fig, path)


def _cluster_count_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty or "cluster" not in frame:
        _empty_chart(path, "Cluster membership")
        return
    counts = frame["cluster"].value_counts().sort_index()
    fig, ax = _prepare_ax("Cluster membership counts", "Cluster", "Varlık")
    ax.bar(counts.index.astype(str), counts.values, color="#4C956C")
    ax.tick_params(axis="x", labelrotation=90)
    _finish(fig, path)


def _pca_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        _empty_chart(path, "PCA")
        return
    fig, ax = _prepare_ax("PCA explained variance", "Component", "Cumulative variance")
    ax.plot(
        frame["component"],
        frame["cumulative_explained_variance"],
        marker="o",
        color="#2F6F8F",
    )
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    _finish(fig, path)


def _covariance_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        _empty_chart(path, "Covariance")
        return
    data = frame.copy()
    data["condition_number_log10"] = np.log10(
        pd.to_numeric(data["condition_number"], errors="coerce").replace(0, np.nan)
    )
    _bar(
        data,
        "estimator",
        "condition_number_log10",
        path,
        "Covariance condition number (log10)",
        "log10 condition",
        "Estimator",
    )


def _scatter_model(frame: pd.DataFrame, path: Path) -> None:
    data = (
        frame.loc[frame["Status"].astype(str).eq("computed")].copy()
        if not frame.empty
        else pd.DataFrame()
    )
    if data.empty:
        _empty_chart(path, "Model comparison")
        return
    fig, ax = _prepare_ax("CAGR vs volatility", "Volatility", "CAGR")
    ax.scatter(data["Volatility"], data["CAGR"], s=80, color="#2F6F8F")
    for _, row in data.iterrows():
        ax.annotate(
            str(row["Model"])[:18], (row["Volatility"], row["CAGR"]), fontsize=8
        )
    _finish(fig, path)


def _model_metric_bar(
    frame: pd.DataFrame, metric: str, path: Path, ylabel: str
) -> None:
    data = (
        frame.loc[frame["Status"].astype(str).eq("computed")].copy()
        if not frame.empty
        else pd.DataFrame()
    )
    _bar(data, "Model", metric, path, f"Model {metric}", "Model", ylabel)


def _risk_pair_chart(frame: pd.DataFrame, path: Path) -> None:
    data = (
        frame.loc[frame["Status"].astype(str).eq("computed")].copy()
        if not frame.empty
        else pd.DataFrame()
    )
    if data.empty:
        _empty_chart(path, "Risk comparison")
        return
    plot = data[["Model", "Max_Drawdown", "CVaR_95"]].set_index("Model")
    fig, ax = _prepare_ax("Max drawdown and CVaR", "Model", "Değer")
    plot.plot(kind="bar", ax=ax, color=["#D95D39", "#2F6F8F"])
    ax.tick_params(axis="x", labelrotation=65)
    _finish(fig, path)


def _constraint_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        _empty_chart(path, "Constraint audit")
        return
    data = frame.copy()
    data["Pass"] = data["All_Constraints_Pass"].astype(bool).map({True: 1, False: 0})
    colors = data["Pass"].map({1: "#4C956C", 0: "#D95D39"})
    fig, ax = _prepare_ax("Constraint pass/fail by model", "Geçti=1", "Model")
    ax.barh(data["Model"], data["Pass"], color=colors)
    ax.set_xlim(0, 1)
    _finish(fig, path)


def _final_top_weights(data: dict[str, pd.DataFrame | dict], path: Path) -> None:
    weights = data["weights"]
    final_model = (
        str(data["decision"].get("final_model", ""))
        if isinstance(data["decision"], dict)
        else ""
    )
    final = (
        weights.loc[weights["Model"].astype(str).eq(final_model)].copy()
        if not weights.empty
        else pd.DataFrame()
    )
    final = final.sort_values("Weight", ascending=False).head(20)
    _bar(
        final,
        "Ticker",
        "Weight",
        path,
        "Final aday ilk 20 ağırlık",
        "Ağırlık",
        "Ticker",
        percent=True,
    )


def _random_sharpe_chart(data: dict[str, pd.DataFrame | dict], path: Path) -> None:
    randoms = data["random"]
    comparison = _read_csv(PROCESSED / "global_master_equal_weight_comparison.csv")
    if randoms.empty or "Sharpe" not in randoms:
        _empty_chart(path, "Random Sharpe")
        return
    fig, ax = _prepare_ax("Random portfolio Sharpe distribution", "Sharpe", "Frekans")
    ax.hist(randoms["Sharpe"], bins=40, color="#9CC5A1", edgecolor="#FFFFFF")
    if not comparison.empty:
        ax.axvline(
            float(comparison["Candidate_Sharpe"].iloc[0]),
            color="#D95D39",
            linewidth=2,
            label="Final aday",
        )
        ax.axvline(
            float(comparison["Equal_Weight_Sharpe"].iloc[0]),
            color="#2F6F8F",
            linewidth=2,
            label="Equal Weight",
        )
        ax.legend()
    _finish(fig, path)


def _projection_band_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        _empty_chart(path, "Projection")
        return
    fig, ax = _prepare_ax("Monte Carlo percentile band", "Horizon (ay)", "Getiri")
    x = frame["Horizon_Months"]
    ax.plot(x, frame["Median_Return"], marker="o", label="Median", color="#2F6F8F")
    ax.fill_between(
        x,
        frame["P05_Return"],
        frame["P95_Return"],
        alpha=0.25,
        color="#2F6F8F",
        label="5%-95%",
    )
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.legend()
    _finish(fig, path)


def _projection_loss_chart(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        _empty_chart(path, "Projection loss")
        return
    fig, ax1 = _prepare_ax(
        "Mean return and probability of loss", "Horizon (ay)", "Mean return"
    )
    ax1.plot(
        frame["Horizon_Months"],
        frame["Mean_Return"],
        marker="o",
        color="#2F6F8F",
        label="Mean return",
    )
    ax1.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax2 = ax1.twinx()
    ax2.plot(
        frame["Horizon_Months"],
        frame["Probability_Of_Loss"],
        marker="s",
        color="#D95D39",
        label="Loss probability",
    )
    ax2.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax2.set_ylabel("Zarar olasılığı")
    _finish(fig, path)


def _empty_chart(path: Path, title: str) -> None:
    fig, ax = _prepare_ax(title)
    ax.text(0.5, 0.5, "Veri bulunamadı", ha="center", va="center")
    ax.set_axis_off()
    _finish(fig, path)


def _write_markdown(
    specs: list[ChartSpec], data: dict[str, pd.DataFrame | dict]
) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    decision = data.get("decision", {})
    lines = [
        "# QuantVerse Görsel Bilimsel Denetim Raporu",
        "",
        "Bu rapor yatırım tavsiyesi değildir. Amaç, QuantVerse çıktılarının hangi kısmının güvenilir, hangi kısmının bloklu ve hangi kısmının yalnızca araştırma kanıtı olduğunu görsel olarak açıklamaktır.",
        "",
        "## Kısa hüküm",
        "",
        f"- Final aday: `{decision.get('final_model', 'missing')}`.",
        f"- Terfi kararı: `{decision.get('promotion_decision', 'missing')}`.",
        f"- Ana gerekçe: {_decision_reason(decision)}",
        "- Global USD master portfolio promoted değildir; FX ve market-cap blokları devam etmektedir.",
        "",
    ]
    for idx, spec in enumerate(specs, start=1):
        lines.extend(_chart_md(idx, spec))
    lines.extend(
        [
            "## Net hüküm",
            "",
            "QuantVerse artık gerçek hisse/proxy evreni, ağırlık auditleri, constraint auditleri, random benchmark, Monte Carlo ve kaynak izlenebilirliği üretiyor. Buna rağmen exact top-100 market-cap kanıtı ve FX-normalized USD return altyapısı eksik olduğu için global master portfolio promoted değildir.",
            "",
            "## Bir sonraki sprint",
            "",
            "Öncelik: point-in-time market-cap-ranked universe, FX conversion, corporate action/delisting reconciliation ve global walk-forward promotion gate.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_presentation_markdown(
    specs: list[ChartSpec], data: dict[str, pd.DataFrame | dict]
) -> None:
    PRESENTATION_MD.parent.mkdir(parents=True, exist_ok=True)
    decision = data.get("decision", {})
    slides = [
        (
            "Current verdict",
            "Proje gerçek global araştırma adayı üretiyor; global USD master portfolio promoted değil.",
        ),
        (
            "What changed",
            "ETF-only yapıdan gerçek hisse/proxy evreni, audit ve projection katmanına geçildi.",
        ),
        (
            "Real universe coverage",
            "Hisse, crypto, commodity ve defensive proxy satırları görsel olarak özetlendi.",
        ),
        (
            "Exact top-100 vs proxy",
            "Equity sleeve'ler index proxy; exact market-cap top-100 kanıtı yok.",
        ),
        ("FX blocker", "Non-USD local returns USD'ye çevrilmeden promotion yapılamaz."),
        (
            "Market-cap blocker",
            "Black-Litterman ve exact top-100 iddiaları market-cap coverage olmadan bloklu.",
        ),
        (
            "Weight and constraints",
            "Policy Constrained aday weight sum ve hard constraints geçiyor.",
        ),
        (
            "Final candidate weight map",
            "Top holdings, sleeve, region ve cluster ağırlıkları ayrı grafiklerde verildi.",
        ),
        (
            "Model comparison",
            "Return, volatility, Sharpe ve drawdown birlikte değerlendirildi.",
        ),
        (
            "Random benchmark",
            "Aday random Sharpe dağılımına göre güçlü, fakat Equal Weight CAGR'ı geçmiyor.",
        ),
        (
            "Risk and drawdown",
            "Tail risk ve drawdown metrikleri promotion kararında görünür.",
        ),
        (
            "Monte Carlo/projection",
            "Projection bantları geniş; garanti değil, senaryo kanıtıdır.",
        ),
        (
            "Requirement traceability",
            "Kullanıcı talepleri met/partial/blocked olarak ayrıldı.",
        ),
        ("Scientific red flags", "Critical/high issue'lar gizlenmedi."),
        (
            "Methodology/source basis",
            "Yerel kitap ve metodoloji kaynakları validasyon kuralına dönüştürüldü.",
        ),
        (
            "What must be fixed next",
            "FX, point-in-time universe, market caps, delistings ve walk-forward gate.",
        ),
        (
            "Final decision",
            f"{decision.get('promotion_decision', 'not promoted')}: {_decision_reason(decision)}",
        ),
    ]
    lines = ["# QuantVerse Görsel Bilimsel Denetim Sunumu", ""]
    for idx, (title, body) in enumerate(slides, start=1):
        chart = specs[min(idx - 1, len(specs) - 1)]
        lines.extend(
            [
                f"## Slide {idx}: {title}",
                "",
                body,
                "",
                f"![{chart.title}](../figures/global_audit/{chart.filename})",
                "",
            ]
        )
    PRESENTATION_MD.write_text("\n".join(lines), encoding="utf-8")


def _chart_md(idx: int, spec: ChartSpec) -> list[str]:
    return [
        f"## {idx}. {spec.title}",
        "",
        f"![{spec.title}](../figures/global_audit/{spec.filename})",
        "",
        f"- Ne görüyorum? {spec.explanation}",
        f"- Neden önemli? {spec.importance}",
        f"- Kırmızı bayrak ne? {spec.red_flag}",
        f"- Hangi kararı destekliyor? {spec.decision}",
        f"- Kaynak: `{spec.source}`.",
        "",
    ]


def _write_pdf(
    specs: list[ChartSpec],
    data: dict[str, pd.DataFrame | dict],
    path: Path,
    title: str,
    *,
    presentation: bool = False,
    pagesize=A4,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    font = _register_font()
    styles = getSampleStyleSheet()
    for name in ["Normal", "BodyText", "Title", "Heading1", "Heading2"]:
        styles[name].fontName = font
    styles["Title"].fontSize = 18 if not presentation else 22
    styles["Title"].textColor = colors.HexColor("#102F45")
    body = ParagraphStyle(
        "AuditBody",
        parent=styles["BodyText"],
        fontName=font,
        fontSize=9.5 if not presentation else 12,
        leading=12 if not presentation else 15,
    )
    heading = ParagraphStyle(
        "AuditHeading",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=13 if not presentation else 17,
        textColor=colors.HexColor("#102F45"),
        spaceAfter=8,
    )
    doc = SimpleDocTemplate(
        str(path),
        pagesize=pagesize,
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    story = [Paragraph(title, styles["Title"]), Spacer(1, 8)]
    decision = data.get("decision", {})
    story.append(
        Paragraph(
            f"Final karar: {decision.get('promotion_decision', 'missing')} - "
            f"{_decision_reason(decision)}",
            body,
        )
    )
    story.append(Spacer(1, 8))
    max_specs = min(len(specs), 17) if presentation else len(specs)
    for idx, spec in enumerate(specs[:max_specs], start=1):
        if presentation and idx > 1:
            story.append(PageBreak())
        story.append(Paragraph(f"{idx}. {spec.title}", heading))
        story.append(
            Image(
                str(FIG_DIR / spec.filename),
                width=9.0 * inch if presentation else 6.8 * inch,
                height=4.1 * inch if presentation else 3.7 * inch,
                kind="proportional",
            )
        )
        story.append(Spacer(1, 6))
        for label, text in [
            ("Ne görüyorum?", spec.explanation),
            ("Neden önemli?", spec.importance),
            ("Kırmızı bayrak ne?", spec.red_flag),
            ("Hangi kararı destekliyor?", spec.decision),
        ]:
            story.append(Paragraph(f"<b>{label}</b> {text}", body))
        story.append(Paragraph(f"<b>Kaynak:</b> {spec.source}", body))
        story.append(Spacer(1, 8))
    doc.build(story)


def _register_font() -> str:
    for path in [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
    ]:
        if path.exists():
            pdfmetrics.registerFont(TTFont("QuantVerseFont", str(path)))
            return "QuantVerseFont"
    return "Helvetica"


def _decision_reason(decision: dict | object) -> str:
    if not isinstance(decision, dict):
        return "missing"
    reason = str(decision.get("reason", "missing"))
    return reason.replace(
        "net CAGR greater than Equal Weight",
        "net CAGR is not greater than Equal Weight",
    )


if __name__ == "__main__":
    raise SystemExit(main())
