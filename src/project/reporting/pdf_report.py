"""Formal PDF research report for QuantVerse analysis outputs."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd


class InvestmentPDFReport:
    """Generate a formal Turkish research report from processed artifacts."""

    def __init__(
        self,
        data_dir: str = "data/processed",
        output_path: str = "output/pdf/quantverse_analysis_report.pdf",
    ):
        self.data_dir = Path(data_dir)
        self.output_path = Path(output_path)
        self.asset_dir = self.output_path.parent / "assets"

    def generate(self) -> Path:
        """Build the PDF and return the output path."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import (
                Image,
                ListFlowable,
                ListItem,
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "PDF generation requires reportlab. Install with "
                "`python -m pip install reportlab pypdf pdfplumber`."
            ) from exc

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.asset_dir.mkdir(parents=True, exist_ok=True)

        data = self._load_data()
        charts = self._build_charts(data)

        font_name, bold_font = self._register_fonts(pdfmetrics, TTFont)
        styles = self._styles(
            getSampleStyleSheet(),
            ParagraphStyle,
            font_name,
            bold_font,
            TA_CENTER,
            TA_LEFT,
            TA_JUSTIFY,
        )
        self._font_name = font_name
        self._bold_font = bold_font
        self._table_header_style = styles["table_header"]
        self._table_cell_style = styles["table_cell"]

        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            rightMargin=1.35 * cm,
            leftMargin=1.35 * cm,
            topMargin=1.25 * cm,
            bottomMargin=1.20 * cm,
            title="QuantVerse Resmi Araştırma Raporu",
            author="QuantVerse",
        )

        story: List = []
        story.extend(self._cover(data, styles, Paragraph, Spacer))
        story.append(PageBreak())
        story.extend(
            self._executive_section(
                data, styles, Paragraph, Spacer, ListFlowable, ListItem
            )
        )
        story.append(PageBreak())
        story.extend(
            self._primer_section(styles, Paragraph, Spacer, ListFlowable, ListItem)
        )
        story.append(PageBreak())
        story.extend(
            self._data_section(
                data, styles, Paragraph, Spacer, Table, TableStyle, colors
            )
        )
        story.append(PageBreak())
        story.extend(
            self._math_section(styles, Paragraph, Spacer, Table, TableStyle, colors)
        )
        story.append(PageBreak())
        story.extend(
            self._methodology_section(
                styles, Paragraph, Spacer, Table, TableStyle, colors
            )
        )
        story.append(PageBreak())
        story.extend(
            self._results_section(
                data,
                charts,
                styles,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                Image,
                colors,
            )
        )
        story.append(PageBreak())
        story.extend(
            self._holdings_section(
                data, styles, Paragraph, Spacer, Table, TableStyle, colors, PageBreak
            )
        )
        story.append(PageBreak())
        story.extend(
            self._validation_section(
                data,
                charts,
                styles,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                Image,
                colors,
            )
        )
        story.append(PageBreak())
        story.extend(
            self._risk_section(
                data,
                charts,
                styles,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                Image,
                colors,
            )
        )
        story.append(PageBreak())
        story.extend(
            self._governance_section(
                data, styles, Paragraph, Spacer, ListFlowable, ListItem
            )
        )
        story.append(PageBreak())
        story.extend(
            self._references_section(styles, Paragraph, Spacer, ListFlowable, ListItem)
        )

        doc.build(story, onFirstPage=self._page_footer, onLaterPages=self._page_footer)
        return self.output_path

    def _load_data(self) -> Dict:
        files = {
            "returns": "returns_daily.parquet",
            "prices": "prices_clean.parquet",
            "class_map": "asset_class_map.json",
            "portfolio_weights": "portfolio_weights.parquet",
            "portfolio_holdings_long": "portfolio_holdings_long.parquet",
            "portfolio_summary": "portfolio_summary.parquet",
            "risk_metrics": "risk_metrics.parquet",
            "backtest_returns": "backtest_returns.parquet",
            "backtest_summary": "backtest_summary.parquet",
            "model_diagnostics": "model_diagnostics.parquet",
            "decision_summary": "decision_summary.json",
            "expected_returns": "expected_returns.parquet",
            "market_signals": "market_signals.parquet",
            "data_quality": "data_quality_report.parquet",
            "ml_downside_risk_metrics": "ml_downside_risk_metrics.parquet",
            "ml_downside_risk_feature_importance": "ml_downside_risk_feature_importance.parquet",
            "regime_labels": "regime_labels.parquet",
            "adaptive_returns": "adaptive_returns.parquet",
            "run_metadata": "run_metadata.json",
        }
        data = {}
        for key, filename in files.items():
            path = self.data_dir / filename
            if not path.exists():
                continue
            if filename.endswith(".json"):
                data[key] = json.loads(path.read_text(encoding="utf-8"))
            else:
                data[key] = pd.read_parquet(path)

        required = [
            "returns",
            "portfolio_summary",
            "risk_metrics",
            "backtest_summary",
            "model_diagnostics",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise FileNotFoundError(f"Missing report inputs: {missing}")
        return data

    def _register_fonts(self, pdfmetrics, TTFont) -> tuple[str, str]:
        arial = Path("C:/Windows/Fonts/arial.ttf")
        arial_bold = Path("C:/Windows/Fonts/arialbd.ttf")
        if arial.exists() and arial_bold.exists():
            pdfmetrics.registerFont(TTFont("ArialTR", str(arial)))
            pdfmetrics.registerFont(TTFont("ArialTR-Bold", str(arial_bold)))
            return "ArialTR", "ArialTR-Bold"
        return "Helvetica", "Helvetica-Bold"

    def _styles(
        self,
        stylesheet,
        ParagraphStyle,
        font_name: str,
        bold_font: str,
        TA_CENTER,
        TA_LEFT,
        TA_JUSTIFY,
    ) -> Dict:
        return {
            "title": ParagraphStyle(
                "QVTitle",
                parent=stylesheet["Title"],
                fontName=bold_font,
                fontSize=22,
                leading=28,
                alignment=TA_CENTER,
                textColor="#142f46",
                spaceAfter=12,
            ),
            "subtitle": ParagraphStyle(
                "QVSubtitle",
                parent=stylesheet["Normal"],
                fontName=font_name,
                fontSize=10.5,
                leading=14,
                alignment=TA_CENTER,
                textColor="#3f5364",
                spaceAfter=8,
            ),
            "h1": ParagraphStyle(
                "QVHeading1",
                parent=stylesheet["Heading1"],
                fontName=bold_font,
                fontSize=15,
                leading=18.5,
                textColor="#142f46",
                spaceBefore=4,
                spaceAfter=7,
            ),
            "h2": ParagraphStyle(
                "QVHeading2",
                parent=stylesheet["Heading2"],
                fontName=bold_font,
                fontSize=11.2,
                leading=14,
                textColor="#24445f",
                spaceBefore=6,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "QVBody",
                parent=stylesheet["BodyText"],
                fontName=font_name,
                fontSize=8.8,
                leading=12.2,
                alignment=TA_JUSTIFY,
                spaceAfter=5,
            ),
            "small": ParagraphStyle(
                "QVSmall",
                parent=stylesheet["BodyText"],
                fontName=font_name,
                fontSize=7.5,
                leading=9.5,
                alignment=TA_LEFT,
                textColor="#4d5963",
            ),
            "note": ParagraphStyle(
                "QVNote",
                parent=stylesheet["BodyText"],
                fontName=bold_font,
                fontSize=8.5,
                leading=11.5,
                textColor="#24415b",
                backColor="#eef5fa",
                borderColor="#9bb7cc",
                borderWidth=0.45,
                borderPadding=6,
                spaceAfter=7,
            ),
            "warning": ParagraphStyle(
                "QVWarning",
                parent=stylesheet["BodyText"],
                fontName=bold_font,
                fontSize=8.5,
                leading=11.5,
                textColor="#7a2f00",
                backColor="#fff2df",
                borderColor="#e1aa62",
                borderWidth=0.45,
                borderPadding=6,
                spaceAfter=7,
            ),
            "table_header": ParagraphStyle(
                "QVTableHeader",
                parent=stylesheet["BodyText"],
                fontName=bold_font,
                fontSize=6.8,
                leading=8.2,
                textColor="#ffffff",
                wordWrap="CJK",
            ),
            "table_cell": ParagraphStyle(
                "QVTableCell",
                parent=stylesheet["BodyText"],
                fontName=font_name,
                fontSize=6.8,
                leading=8.2,
                textColor="#1f2a33",
                wordWrap="CJK",
            ),
        }

    def _cover(self, data, styles, Paragraph, Spacer) -> List:
        returns = data["returns"]
        metadata = data.get("run_metadata", {})
        rf_meta = metadata.get("risk_free_metadata", {})
        return [
            Spacer(1, 2.8 * cm_to_pt()),
            Paragraph("QuantVerse Resmi Araştırma Raporu", styles["title"]),
            Paragraph(
                "Çok varlıklı portföy araştırması, istatistiksel risk ölçümü, "
                "walk-forward doğrulama ve karar destek çerçevesi",
                styles["subtitle"],
            ),
            Spacer(1, 0.7 * cm_to_pt()),
            Paragraph(
                f"Veri dönemi: {returns.index[0].date()} - {returns.index[-1].date()}",
                styles["subtitle"],
            ),
            Paragraph(
                f"Varlık sayısı: {returns.shape[1]} | İş günü getirisi: {returns.shape[0]} | "
                f"Veri son tarihi: {metadata.get('data_as_of', returns.index[-1].date())}",
                styles["subtitle"],
            ),
            Paragraph(
                f"Risksiz faiz proxy'si: {rf_meta.get('proxy', 'N/A')} | "
                f"Son yıllık oran: {metadata.get('risk_free_rate', 0) * 100:.2f}% | "
                f"Kaynak: {rf_meta.get('source', 'N/A')}",
                styles["subtitle"],
            ),
            Spacer(1, 0.4 * cm_to_pt()),
            Paragraph(
                "Bu belge kişisel yatırım tavsiyesi değildir. Belge, geçmiş piyasa "
                "verilerinden üretilmiş araştırma bulgularını, varsayımlarını, model "
                "risklerini ve kullanım sınırlarını resmi bir karar destek formatında "
                "açıklamak amacıyla hazırlanmıştır.",
                styles["warning"],
            ),
            Spacer(1, 1.5 * cm_to_pt()),
            Paragraph(
                f"Oluşturulma zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                styles["small"],
            ),
        ]

    def _executive_section(
        self, data, styles, Paragraph, Spacer, ListFlowable, ListItem
    ):
        diagnostics = data["model_diagnostics"]
        decision = data.get("decision_summary", {})
        best_oos = decision.get("best_oos_strategy", diagnostics["OOS_Sharpe"].idxmax())
        screened = decision.get("risk_screened_candidate", best_oos)
        largest_gap = decision.get(
            "largest_in_sample_gap_strategy", diagnostics["Sharpe_Gap"].idxmax()
        )
        regime = "N/A"
        if "regime_labels" in data and "Vol_Regime" in data["regime_labels"]:
            regime = str(data["regime_labels"]["Vol_Regime"].dropna().iloc[-1])

        bullets = [
            (
                f"Walk-forward Sharpe'a göre en yüksek sonuç: {best_oos} "
                f"({diagnostics.loc[best_oos, 'OOS_Sharpe']:.2f})."
            ),
            (
                f"Risk filtresinden sonra ana araştırma adayı: {screened} "
                f"({diagnostics.loc[screened, 'Evidence_Tier']})."
            ),
            (
                f"En büyük in-sample / walk-forward Sharpe farkı: {largest_gap} "
                f"({diagnostics.loc[largest_gap, 'Sharpe_Gap']:.2f})."
            ),
            f"Son volatilite rejimi: {regime}.",
        ]
        return [
            Paragraph("1. Yönetici Özeti ve Nihai Okuma Kuralı", styles["h1"]),
            Paragraph(
                "Bu raporun ana ilkesi şudur: Eğitim dönemi içinde iyi görünen bir "
                "portföy, gerçek karar kanıtı sayılmaz. Karar açısından daha yüksek "
                "ağırlık, walk-forward yani geçmişte her tarihte yalnızca o tarihe "
                "kadar bilinen veriyi kullanan out-of-sample teste verilir.",
                styles["body"],
            ),
            self._bullet_list(ListFlowable, ListItem, Paragraph, styles, bullets),
            Spacer(1, 6),
            Paragraph("Sonuç Cümlesi", styles["h2"]),
            Paragraph(
                "Proje artık yalnızca portföy üreten bir kod parçası değildir. Veri "
                "evrenini yatırım yapılabilirlik ilkesine göre ayıran, risksiz faizi "
                "güncel proxy ile alan, beklenen getiriyi aşırı uçlardan shrink eden, "
                "statik sonuç ile walk-forward kanıt arasındaki farkı ölçen ve bu farkı "
                "raporun merkezine koyan bir araştırma sistemidir.",
                styles["note"],
            ),
            Paragraph("Neden iki sonuç arasında fark olabilir?", styles["h2"]),
            Paragraph(
                "Bir optimizasyon modeli geçmiş veriye bakarak ağırlık seçtiğinde, "
                "geçmişte tesadüfen iyi çalışan desenleri gerçek bir ekonomik ilişki "
                "zannedebilir. Buna istatistikte tahmin hatası, finans uygulamasında "
                "aşırı uyum veya model riski denir. Bu rapor bu farkı saklamaz; "
                "ölçer, sınıflandırır ve karar katmanında cezalandırır.",
                styles["body"],
            ),
        ]

    def _primer_section(self, styles, Paragraph, Spacer, ListFlowable, ListItem):
        bullets = [
            "1 + 1 = 2 ifadesi iki adet birimin bir araya geldiğinde iki birim oluşturduğunu söyler. Portföyde de iki ayrı ağırlık toplandığında toplam sermaye payını verir.",
            "Yüzde, bir büyüklüğün 100 eşit parçaya bölünmüş halidir. %25 ağırlık, her 100 TL'nin 25 TL'sinin ilgili varlığa ayrılmasıdır.",
            "Getiri, bugün sahip olunan değerin önceki değere göre ne kadar arttığını veya azaldığını ölçer.",
            "Risk, tek başına kaybetme ihtimali değildir; sonucun beklenenden ne kadar sapabileceğini ve kötü senaryoda kaybın ne kadar büyüyebileceğini kapsar.",
            "Portföy, birden fazla varlığın aynı sermaye içinde birlikte tutulmasıdır. Amaç tek varlığın hatasına bağımlılığı azaltmaktır.",
        ]
        return [
            Paragraph("2. Temel Kavramlar: En Baştan Başlayarak", styles["h1"]),
            Paragraph(
                "Bu bölüm bilerek en basit seviyeden başlar. Okuyucu finans, matematik "
                "ve istatistik biliyor olsa bile raporun terminolojisinin aynı anlamda "
                "okunması için kavramlar resmi biçimde tanımlanır.",
                styles["body"],
            ),
            self._bullet_list(ListFlowable, ListItem, Paragraph, styles, bullets),
            Spacer(1, 6),
            Paragraph("Portföy Ağırlığı Ne Demektir?", styles["h2"]),
            Paragraph(
                "Bir portföyde her varlığın bir ağırlığı vardır. Ağırlıklar toplandığında "
                "1 olmalıdır. 1 burada sermayenin tamamıdır. Örneğin 0,25 + 0,25 + "
                "0,50 = 1 ise sermayenin %25'i birinci varlıkta, %25'i ikinci varlıkta, "
                "%50'si üçüncü varlıktadır. Bu projede uzun yönlü portföyler kullanılır; "
                "yani negatif ağırlık veya kaldıraç üretim raporunun ana varsayımı değildir.",
                styles["body"],
            ),
            Paragraph("Bilimsel Okuma Kuralı", styles["h2"]),
            Paragraph(
                "Bir sayı tek başına sonuç değildir. Sayının nasıl üretildiği, hangi "
                "varsayımı kullandığı, hangi veri döneminde hesaplandığı ve başka bir "
                "testte aynı davranışı gösterip göstermediği birlikte değerlendirilir. "
                "Bu nedenle raporda hem statik sonuç hem de walk-forward doğrulama vardır.",
                styles["body"],
            ),
        ]

    def _data_section(self, data, styles, Paragraph, Spacer, Table, TableStyle, colors):
        metadata = data.get("run_metadata", {})
        returns = data["returns"]
        data_rows = [
            ["Konu", "Değer", "Yorum"],
            [
                "Veri dönemi",
                f"{returns.index[0].date()} - {returns.index[-1].date()}",
                "Analizde kullanılan iş günü aralığı",
            ],
            [
                "Varlık sayısı",
                str(returns.shape[1]),
                "Yatırım yapılabilir fiyat serileri",
            ],
            [
                "Hafta sonu satırı",
                str(metadata.get("weekend_rows", 0)),
                "İş günü yıllıklaştırmasıyla uyumlu olmalı",
            ],
            [
                "Portföy içi sinyal",
                str(len(metadata.get("signals_in_returns", []))),
                "Sinyaller ağırlık almaz",
            ],
            [
                "Risksiz faiz",
                f"{metadata.get('risk_free_rate', 0) * 100:.2f}%",
                "Sharpe hesaplarında kullanılan yıllık oran",
            ],
            [
                "Beklenen getiri shrinkage",
                f"{metadata.get('expected_return_shrinkage', 0):.2f}",
                "Tarihsel ortalama hatasını azaltır",
            ],
        ]
        dropped = metadata.get("dropped_assets", [])
        signal_rows = self._signal_rows(data)
        quality_rows = self._data_quality_rows(data)
        return [
            Paragraph("3. Veri Evreni, Güncellik ve Temizlik", styles["h1"]),
            Paragraph(
                "Finansal modelin kalitesi veri kalitesinden ayrı düşünülemez. Bu nedenle "
                "proje önce hangi serilerin portföyde ağırlık alabileceğini, hangi serilerin "
                "sadece piyasa sinyali olduğunu ayırır. VIX, faiz endeksleri ve dolar endeksi "
                "piyasa bağlamı sağlar; üretim portföyünde yatırım yapılabilir varlık gibi "
                "ağırlık almaz.",
                styles["body"],
            ),
            self._table(Table, TableStyle, colors, data_rows, [3.4, 4.0, 8.0]),
            Spacer(1, 8),
            Paragraph("Veri Kapsamı Nedeniyle Çıkarılanlar", styles["h2"]),
            Paragraph(
                (
                    (
                        f"Minimum veri kapsamı kuralını geçemeyen seriler: {', '.join(dropped)}. "
                        "Bu çıkarma performansa göre yapılmamıştır; sadece veri geçmişi "
                        "yetersiz olduğu için yapılmıştır."
                    )
                    if dropped
                    else "Minimum veri kapsamı nedeniyle çıkarılan seri yoktur."
                ),
                styles["body"],
            ),
            Paragraph("Veri Kalitesi Özeti", styles["h2"]),
            self._table(
                Table, TableStyle, colors, quality_rows, [2.4, 3.2, 2.8, 2.8, 4.2]
            ),
            Spacer(1, 6),
            Paragraph("Piyasa Sinyalleri", styles["h2"]),
            self._table(Table, TableStyle, colors, signal_rows, [3.4, 3.2, 3.2, 5.6]),
            Spacer(1, 6),
            Paragraph(
                "Sinyaller raporda bağlam için saklanır; portföy getirisi matrisine "
                "karıştırılmaz. Böylece VIX veya faiz endeksi gibi doğrudan alınıp "
                "satılmayan serilerin yanlışlıkla portföy ağırlığı alması engellenir.",
                styles["note"],
            ),
        ]

    def _math_section(self, styles, Paragraph, Spacer, Table, TableStyle, colors):
        rows = [
            ["Kavram", "Basit tanım", "Projede kullanım"],
            [
                "Getiri",
                "(Bugünkü fiyat / önceki fiyat) - 1",
                "Her iş günü varlık getirisi hesaplanır",
            ],
            [
                "Bileşik getiri",
                "Getirilerin çarpılarak büyümesi",
                "Backtest sermaye eğrileri için kullanılır",
            ],
            [
                "Aritmetik ortalama",
                "Gözlem değerleri toplamı / gözlem sayısı",
                "Tarihsel getiri eğilimini özetler",
            ],
            [
                "Varyans",
                "Getirilerin ortalamadan sapma büyüklüğü",
                "Risk matrisinin temelidir",
            ],
            [
                "Kovaryans",
                "İki varlığın birlikte hareket derecesi",
                "Portföy riskini belirler",
            ],
            [
                "Korelasyon",
                "Kovaryansın -1 ile +1 arasına ölçeklenmiş hali",
                "Çeşitlendirme gücünü gösterir",
            ],
            [
                "Sharpe",
                "(Getiri - risksiz faiz) / volatilite",
                "Birim risk başına fazla getiriyi ölçer",
            ],
            ["VaR", "Belirli güven düzeyinde kayıp eşiği", "Kötü gün eşiğini gösterir"],
            [
                "CVaR",
                "VaR eşiğinin ötesindeki ortalama kayıp",
                "Kuyruk riskini VaR'dan daha açık ölçer",
            ],
            [
                "Max drawdown",
                "Zirveden dibe en büyük düşüş",
                "Yatırımcının yaşayabileceği en sert tarihsel düşüş",
            ],
            ["HHI", "Ağırlık karelerinin toplamı", "Yoğunlaşma arttıkça yükselir"],
        ]
        return [
            Paragraph("4. Matematiksel ve İstatistiksel Çerçeve", styles["h1"]),
            Paragraph(
                "Bu bölümde kullanılan formüller karmaşık görünse de temel fikir aynıdır: "
                "önce değişim ölçülür, sonra bu değişimin ortalaması, oynaklığı, birlikte "
                "hareketi ve kötü senaryo davranışı hesaplanır. Portföy kararı bu ölçümlerin "
                "birleşiminden oluşur.",
                styles["body"],
            ),
            self._table(Table, TableStyle, colors, rows, [3.0, 5.1, 7.3]),
            Spacer(1, 8),
            Paragraph("Yıllıklaştırma", styles["h2"]),
            Paragraph(
                "Bu projede iş günü frekansı kullanıldığı için yıllıklaştırmada 252 işlem "
                "günü varsayılır. Volatilite, günlük standart sapmanın karekök 252 ile "
                "çarpılmasıyla yıllıklaştırılır. Tarihsel yıllık VaR/CVaR ise günlük VaR'ı "
                "mekanik olarak büyütmek yerine 252 günlük bileşik gerçekleşmiş getirilerden "
                "hesaplanır; bu tercih kuyruk riskinde daha doğrudan tarihsel kanıt kullanır.",
                styles["body"],
            ),
            Paragraph("Beklenen Getiri Neden Shrink Edildi?", styles["h2"]),
            Paragraph(
                "Tarihsel ortalama getiri finansal veride gürültülüdür. Bir varlığın geçmişte "
                "çok yüksek getiri üretmesi, gelecekte aynı oranda getiri üreteceğini kanıtlamaz. "
                "Bu nedenle üretim tahmini, ham tarihsel ortalamayı kesitsel medyana doğru "
                "kısmen yaklaştırır. Bu işlem yüksek getirili varlığı silmez; yalnızca tahmin "
                "hatasının portföy optimizasyonunu aşırı uçlara taşımasını engeller.",
                styles["note"],
            ),
        ]

    def _methodology_section(
        self, styles, Paragraph, Spacer, Table, TableStyle, colors
    ):
        rows = [
            ["Yöntem", "Ne yapar?", "Neden kullanılır?", "Nasıl yorumlanır?"],
            [
                "Equal Weight",
                "Her varlığa eşit pay verir",
                "Basit, şeffaf ve güçlü bir benchmark sağlar",
                "Karmaşık modelin gerçekten değer ekleyip eklemediğini gösterir",
            ],
            [
                "Min Variance",
                "Toplam volatiliteyi azaltır",
                "Risk azaltma odaklıdır",
                "Getiri hedeflemez; düşük riskli ama düşük getirili olabilir",
            ],
            [
                "Max Sharpe",
                "Risk başına fazla getiriyi maksimize eder",
                "Teorik olarak verimli portföy arar",
                "Beklenen getiri hatasına çok duyarlıdır; out-of-sample kontrol zorunludur",
            ],
            [
                "HRP",
                "Korelasyon hiyerarşisine göre ağırlık dağıtır",
                "Kovaryans tersleme hatasını azaltır",
                "Model riski düşük, çeşitlendirme odaklı adaydır",
            ],
            [
                "Risk Parity",
                "Risk katkılarını dengelemeye çalışır",
                "Ağırlık değil risk dağılımını dengeler",
                "Getiri tahmininden çok risk yapısına dayanır",
            ],
            [
                "Inverse Volatility",
                "Düşük oynaklığa daha yüksek ağırlık verir",
                "Basit ve açıklanabilir risk tabanlı kuraldır",
                "Korelasyonları tam hesaba katmaz",
            ],
            [
                "Min CVaR",
                "Kuyruk kaybını azaltır",
                "Aşırı kötü senaryolara odaklanır",
                "Ortalama getiriyi feda edebilir",
            ],
        ]
        removed_bl = (
            "Black-Litterman üretim raporundan çıkarıldı. Gerekçe: model, açık ve "
            "tarihli yatırım görüşleri gerektirir. Kaynaklandırılmış görüş seti olmadan "
            "kullanılması bilimsel sonuç değil senaryo üretir."
        )
        return [
            Paragraph("5. Yöntemler: Ne, Neden, Nasıl?", styles["h1"]),
            Paragraph(
                "Projede tek bir yöntemin mutlak doğru olduğu varsayılmaz. Her yöntem "
                "farklı bir hata türüne karşı farklı savunma sağlar. Bilimsel yaklaşım, "
                "yöntemleri aynı veri üzerinde karşılaştırmak ve eğitim dönemi ile "
                "walk-forward dönemindeki davranış farkını ölçmektir.",
                styles["body"],
            ),
            self._table(Table, TableStyle, colors, rows, [3.1, 4.1, 4.3, 4.1]),
            Spacer(1, 8),
            Paragraph("Üretim Kapsamından Çıkarılan Model", styles["h2"]),
            Paragraph(removed_bl, styles["warning"]),
        ]

    def _results_section(
        self,
        data,
        charts,
        styles,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
        colors,
    ):
        ps = data["portfolio_summary"]
        rows = [
            [
                "Strateji",
                "In-sample getiri",
                "Volatilite",
                "Sharpe",
                "Maks. ağırlık",
                "HHI",
            ]
        ]
        for idx, row in (
            ps[["Return (%)", "Volatility (%)", "Sharpe", "Max Weight (%)", "HHI"]]
            .round(2)
            .iterrows()
        ):
            rows.append(
                [
                    idx,
                    f"{row['Return (%)']:.2f}%",
                    f"{row['Volatility (%)']:.2f}%",
                    f"{row['Sharpe']:.2f}",
                    f"{row['Max Weight (%)']:.2f}%",
                    f"{row['HHI']:.2f}",
                ]
            )
        return [
            Paragraph(
                "6. Statik Portföy Sonuçları: Eğitim Dönemi Görünümü", styles["h1"]
            ),
            Paragraph(
                "Aşağıdaki tablo, tüm veri dönemi kullanılarak oluşturulan statik portföy "
                "sonuçlarını gösterir. Bu tablo nihai yatırım kararı değildir; eğitim "
                "döneminde modelin ne öğrendiğini gösteren tanı tablosudur.",
                styles["warning"],
            ),
            self._table(
                Table, TableStyle, colors, rows, [3.2, 2.6, 2.3, 1.8, 2.5, 1.6]
            ),
            Spacer(1, 7),
            Image(
                str(charts["risk_return"]),
                width=15.5 * cm_to_pt(),
                height=7.2 * cm_to_pt(),
            ),
            Spacer(1, 7),
            Image(
                str(charts["weights"]), width=15.5 * cm_to_pt(), height=7.4 * cm_to_pt()
            ),
        ]

    def _holdings_section(
        self,
        data,
        styles,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        colors,
        PageBreak,
    ):
        weights = data["portfolio_weights"].copy() * 100
        class_map = data.get("class_map", {})
        columns = list(weights.columns)
        display_names = {
            "Equal Weight": "EW",
            "Min Variance": "MinVar",
            "Max Sharpe": "MaxSh",
            "HRP": "HRP",
            "Risk Parity": "RiskPar",
            "Inv Volatility": "InvVol",
            "Min CVaR": "MinCVaR",
        }

        rows = [["Varlık", "Sınıf", *[display_names.get(col, col) for col in columns]]]
        for ticker, row in weights.iterrows():
            rows.append(
                [
                    ticker,
                    self._asset_class_label(class_map.get(ticker, "unknown")),
                    *[
                        f"{row[col]:.2f}%" if abs(row[col]) >= 0.005 else "0.00%"
                        for col in columns
                    ],
                ]
            )

        first_half = rows[:1] + rows[1:20]
        second_half = rows[:1] + rows[20:]
        col_widths = [1.8, 2.1, *([1.55] * len(columns))]
        legend = (
            "Kısaltmalar: EW = Equal Weight, MinVar = Min Variance, "
            "MaxSh = Max Sharpe, RiskPar = Risk Parity, InvVol = Inverse Volatility, "
            "MinCVaR = Minimum CVaR."
        )

        story = [
            Paragraph(
                "7. Portföy Bileşimleri: Hangi Varlıktan Ne Kadar Alındı?", styles["h1"]
            ),
            Paragraph(
                "Bu bölüm, raporun karar açısından en somut tablosudur. Satırlarda "
                "portföye girebilecek varlıklar, sütunlarda stratejiler, hücrelerde ise "
                "ilgili stratejinin o varlığa ayırdığı sermaye yüzdesi yer alır. 0.00% "
                "görünen hücre, ilgili portföyün o varlığı fiilen almadığı anlamına gelir.",
                styles["body"],
            ),
            Paragraph(
                "Önemli ayrım: Kullanıcı gündelik dilde bunlara 'hisse' diyebilir; ancak "
                "bu evrende hisse senedi ETF'leri, tahvil ETF'leri, emtia ETF'leri, REIT "
                "ETF'leri ve kripto varlıklar birlikte bulunur. Bu nedenle raporda daha "
                "doğru terim olarak 'varlık' veya 'enstrüman' kullanılır.",
                styles["note"],
            ),
            Paragraph(legend, styles["small"]),
            Spacer(1, 4),
            self._table(Table, TableStyle, colors, first_half, col_widths),
        ]
        if len(second_half) > 1:
            story.extend(
                [
                    PageBreak(),
                    Paragraph("7. Portföy Bileşimleri: Devam", styles["h1"]),
                    Paragraph(legend, styles["small"]),
                    Spacer(1, 4),
                    self._table(Table, TableStyle, colors, second_half, col_widths),
                ]
            )

        story.extend(
            [
                Spacer(1, 7),
                Paragraph("Tablonun Okunması", styles["h2"]),
                Paragraph(
                    "Örneğin bir hücrede 25.00% yazıyorsa, 100 TL sermayenin 25 TL'si "
                    "o varlığa ayrılmıştır. 2.70% yazıyorsa, 100 TL sermayenin yaklaşık "
                    "2,70 TL'si o varlığa ayrılmıştır. Ağırlıkların toplamı her portföy "
                    "sütununda yaklaşık 100%'dür.",
                    styles["body"],
                ),
            ]
        )
        return story

    def _validation_section(
        self,
        data,
        charts,
        styles,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
        colors,
    ):
        diag = data["model_diagnostics"]
        ml_rows = self._ml_diagnostic_rows(data)
        rows = [
            [
                "Strateji",
                "Statik Sharpe",
                "WF Sharpe",
                "Fark",
                "WF max DD",
                "Kanıt sınıfı",
            ]
        ]
        for idx, row in diag[
            [
                "Static_Sharpe",
                "OOS_Sharpe",
                "Sharpe_Gap",
                "OOS_Max_Drawdown",
                "Evidence_Tier",
            ]
        ].iterrows():
            rows.append(
                [
                    idx,
                    f"{row['Static_Sharpe']:.2f}",
                    f"{row['OOS_Sharpe']:.2f}",
                    f"{row['Sharpe_Gap']:.2f}",
                    f"{row['OOS_Max_Drawdown']:.2%}",
                    row["Evidence_Tier"],
                ]
            )
        return [
            Paragraph(
                "8. Doğrulama: Statik Sonuç ile Walk-Forward Kanıtı", styles["h1"]
            ),
            Paragraph(
                "Bu bölüm raporun en kritik bölümüdür. İki sonuç arasında büyük fark "
                "olması, çoğu zaman modelin geçmiş veriye fazla uyduğunu veya beklenen "
                "getiri tahmininin gürültülü olduğunu gösterir. Bu nedenle karar "
                "katmanında walk-forward sonuçları statik sonuçlardan üstündür.",
                styles["body"],
            ),
            self._table(
                Table, TableStyle, colors, rows, [3.0, 2.1, 2.1, 1.8, 2.2, 4.2]
            ),
            Spacer(1, 8),
            Image(
                str(charts["diagnostics"]),
                width=15.5 * cm_to_pt(),
                height=6.8 * cm_to_pt(),
            ),
            Spacer(1, 8),
            Paragraph("Yorum", styles["h2"]),
            Paragraph(self._diagnostic_interpretation(data), styles["note"]),
            Spacer(1, 8),
            Paragraph("ML Downside-Risk Tanısı", styles["h2"]),
            self._table(Table, TableStyle, colors, ml_rows, [3.4, 3.0, 3.0, 3.0, 3.0]),
            Spacer(1, 6),
            Paragraph(
                "Bu ML bileşeni getiri tahmini veya al-sat talimatı değildir. Amaç, "
                "son piyasa durumunun bir sonraki gün alt kuyruk olayı hakkında sınırlı "
                "bilgi taşıyıp taşımadığını zaman sırası bozulmadan test etmektir.",
                styles["body"],
            ),
        ]

    def _risk_section(
        self,
        data,
        charts,
        styles,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
        colors,
    ):
        risk = data["risk_metrics"]
        bt = data["backtest_summary"]
        risk_rows = [
            ["Strateji", "VaR 5% günlük", "CVaR 5% günlük", "Max DD", "Calmar", "Ulcer"]
        ]
        for idx, row in (
            risk[["VaR_5%", "CVaR_5%", "Max_DD_%", "Calmar", "Ulcer_Index"]]
            .round(2)
            .iterrows()
        ):
            risk_rows.append(
                [
                    idx,
                    f"{row['VaR_5%']:.2f}%",
                    f"{row['CVaR_5%']:.2f}%",
                    f"{row['Max_DD_%']:.2f}%",
                    f"{row['Calmar']:.2f}",
                    f"{row['Ulcer_Index']:.2f}",
                ]
            )
        bt_rows = [["Strateji", "CAGR", "Vol", "Sharpe", "Max DD", "Maliyet/yıl"]]
        for idx, row in bt[
            ["CAGR", "Volatility", "Sharpe", "Max_Drawdown", "Annualized_Cost_Drag_%"]
        ].iterrows():
            bt_rows.append(
                [
                    idx,
                    f"{row['CAGR']:.2%}",
                    f"{row['Volatility']:.2%}",
                    f"{row['Sharpe']:.2f}",
                    f"{row['Max_Drawdown']:.2%}",
                    f"{row['Annualized_Cost_Drag_%']:.2f}%",
                ]
            )
        return [
            Paragraph("9. Risk, Geriye Dönük Test ve Sermaye Eğrileri", styles["h1"]),
            Paragraph(
                "Getiri tek başına yeterli değildir. Aynı getiriye sahip iki stratejiden "
                "biri daha düşük düşüş, daha düşük kuyruk kaybı ve daha düşük işlem maliyeti "
                "üretiyorsa ekonomik açıdan daha savunulabilir olabilir.",
                styles["body"],
            ),
            self._table(
                Table, TableStyle, colors, risk_rows, [3.0, 2.4, 2.6, 2.0, 1.7, 1.7]
            ),
            Spacer(1, 8),
            self._table(
                Table, TableStyle, colors, bt_rows, [3.0, 2.1, 2.1, 1.8, 2.1, 2.4]
            ),
            Spacer(1, 8),
            Image(
                str(charts["backtest"]),
                width=15.5 * cm_to_pt(),
                height=6.6 * cm_to_pt(),
            ),
            Spacer(1, 7),
            Image(
                str(charts["drawdown"]),
                width=15.5 * cm_to_pt(),
                height=6.3 * cm_to_pt(),
            ),
        ]

    def _governance_section(
        self, data, styles, Paragraph, Spacer, ListFlowable, ListItem
    ):
        metadata = data.get("run_metadata", {})
        removed = [
            "Portföy ağırlıklarından VIX, 10Y Treasury yield, 13 haftalık T-bill ve DXY çıkarıldı; bunlar raporda sinyal olarak saklanır, yatırım yapılabilir varlık gibi ağırlık almaz.",
            "Black-Litterman üretim sonucundan çıkarıldı; çünkü kaynaklı ve tarihli yatırım görüşleri olmadan kullanılması bilimsel sonuç değil varsayımsal senaryo olur.",
            "Kullanılmayan ağır bağımlılıklar çekirdek kurulumdan çıkarıldı; proje artık var olmayan dashboard veya supervised ML tahmini varmış gibi görünmez.",
            "Eski notebook çıktıları temizlendi; geçmiş çalıştırma kalıntılarının yeni araştırma raporuyla karışması engellendi.",
        ]
        retained = [
            "Düşük geçmiş getirili varlıklar otomatik atılmadı; çünkü düşük geçmiş getiri, gelecekte düşük getiri olacağını ispatlamaz.",
            "Birden fazla risk tabanlı optimizasyon korundu; çünkü her biri farklı hata türünü ve farklı ekonomik varsayımı test eder.",
            "Rejim analizi korundu; çünkü finansal piyasa dağılımları zaman içinde sabit değildir.",
            "Equal Weight benchmark korundu; çünkü karmaşık modelin gerçekten değer ekleyip eklemediğini ölçmek için basit benchmark gerekir.",
        ]
        limitations = [
            f"Veri son tarihi {metadata.get('data_as_of', 'N/A')}; daha yeni piyasa hareketleri rapora dahil değildir.",
            "Yfinance verisi araştırma ve prototip için uygundur; kurumsal yatırım kararı için bağımsız veri sağlayıcı ile mutabakat yapılmalıdır.",
            "Vergi, kişisel risk profili, likidite, emir defteri derinliği ve ürün erişimi kullanıcı bazında ayrıca değerlendirilmelidir.",
            "Bu rapor karar destek çıktısıdır; kişisel yatırım tavsiyesi, getiri vaadi veya kesin al-sat talimatı değildir.",
        ]
        return [
            Paragraph(
                "10. Model Yönetişimi: Çıkarılanlar, Korunanlar ve Sınırlar",
                styles["h1"],
            ),
            Paragraph("Çıkarılan veya devre dışı bırakılanlar", styles["h2"]),
            self._bullet_list(ListFlowable, ListItem, Paragraph, styles, removed),
            Spacer(1, 6),
            Paragraph("Bilinçli olarak korunanlar", styles["h2"]),
            self._bullet_list(ListFlowable, ListItem, Paragraph, styles, retained),
            Spacer(1, 6),
            Paragraph("Sınırlar", styles["h2"]),
            self._bullet_list(ListFlowable, ListItem, Paragraph, styles, limitations),
            Spacer(1, 8),
            Paragraph(
                "Uygulama protokolü: önce veri tarihini kontrol et, sonra risk-free oranını "
                "ve sinyalleri kontrol et, ardından statik tabloyu yalnızca tanı olarak oku, "
                "son kararı walk-forward tablo ve model tanı tablosuyla değerlendir.",
                styles["note"],
            ),
        ]

    def _references_section(self, styles, Paragraph, Spacer, ListFlowable, ListItem):
        refs = [
            "Markowitz, H. (1952). Portfolio Selection. Journal of Finance.",
            "Sharpe, W. F. (1966, 1994). Mutual Fund Performance; The Sharpe Ratio.",
            "Ledoit, O. ve Wolf, M. (2004). A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices.",
            "López de Prado, M. (2016). Building Diversified Portfolios that Outperform Out-of-Sample.",
            "Jorion, P. Value at Risk çalışmaları; VaR ve risk yönetimi literatürü.",
            "Engle, R. (1982). Autoregressive Conditional Heteroscedasticity; zamanla değişen volatilite literatürü.",
        ]
        return [
            Paragraph("11. Kaynak Niteliğindeki Yöntemsel Dayanaklar", styles["h1"]),
            Paragraph(
                "Aşağıdaki liste raporda kullanılan yöntem ailelerinin akademik dayanaklarını "
                "gösterir. Bu liste, piyasa verisinin geleceği kesin olarak tahmin edebileceği "
                "anlamına gelmez; yalnızca kullanılan yöntemlerin finans ve istatistik "
                "literatüründeki yerini belirtir.",
                styles["body"],
            ),
            self._bullet_list(ListFlowable, ListItem, Paragraph, styles, refs),
            Spacer(1, 8),
            Paragraph(
                "Nihai hüküm: Proje bilimsel araştırma disipliniyle karar desteği sağlar; "
                "ancak yatırım kararının kendisi kullanıcıya özgü risk, zaman ufku, maliyet, "
                "vergi ve uygunluk değerlendirmesi gerektirir.",
                styles["warning"],
            ),
        ]

    def _build_charts(self, data: Dict) -> Dict[str, Path]:
        import matplotlib.pyplot as plt

        plt.style.use("seaborn-v0_8-whitegrid")
        charts = {}

        ps = data["portfolio_summary"]
        fig, ax = plt.subplots(figsize=(8.5, 4.0))
        ax.scatter(ps["Volatility (%)"], ps["Return (%)"], s=80, color="#2f6f8f")
        for name, row in ps.iterrows():
            ax.annotate(name, (row["Volatility (%)"], row["Return (%)"]), fontsize=7)
        ax.set_xlabel("Yıllık volatilite (%)")
        ax.set_ylabel("Shrink edilmiş in-sample getiri (%)")
        ax.set_title("Statik Risk - Getiri Haritası")
        charts["risk_return"] = self._save_fig(fig, "risk_return.png")

        weights = data["portfolio_weights"]
        fig, ax = plt.subplots(figsize=(8.5, 4.3))
        top = weights.abs().max(axis=1).sort_values(ascending=False).head(18).index
        (weights.loc[top] * 100).plot(kind="bar", ax=ax, width=0.85)
        ax.set_ylabel("Ağırlık (%)")
        ax.set_title("En Yüksek Ağırlık Alan Varlıklar")
        ax.legend(fontsize=6, ncol=2)
        fig.tight_layout()
        charts["weights"] = self._save_fig(fig, "weights.png")

        diag = data["model_diagnostics"]
        fig, ax = plt.subplots(figsize=(8.5, 3.8))
        diag[["Static_Sharpe", "OOS_Sharpe"]].rename(
            columns={"Static_Sharpe": "Statik", "OOS_Sharpe": "Walk-forward"}
        ).plot(kind="bar", ax=ax, width=0.78)
        ax.set_ylabel("Sharpe")
        ax.set_title("Statik Sharpe ile Walk-Forward Sharpe Karşılaştırması")
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.legend(fontsize=7)
        fig.tight_layout()
        charts["diagnostics"] = self._save_fig(fig, "diagnostics.png")

        bt_returns = data.get("backtest_returns")
        if bt_returns is not None:
            fig, ax = plt.subplots(figsize=(8.5, 4.0))
            ((1 + bt_returns).cumprod()).plot(ax=ax, linewidth=1.35)
            ax.set_ylabel("Birikimli değer")
            ax.set_title("Walk-Forward Sermaye Eğrileri")
            ax.legend(fontsize=7)
            charts["backtest"] = self._save_fig(fig, "backtest.png")

            fig, ax = plt.subplots(figsize=(8.5, 3.8))
            curves = (1 + bt_returns).cumprod()
            drawdowns = curves / curves.cummax() - 1
            (drawdowns * 100).plot(ax=ax, linewidth=1.15)
            ax.set_ylabel("Düşüş (%)")
            ax.set_title("Walk-Forward Drawdown")
            ax.legend(fontsize=7)
            charts["drawdown"] = self._save_fig(fig, "drawdown.png")

        return charts

    def _signal_rows(self, data: Dict) -> List[List[str]]:
        rows = [["Sinyal", "Son tarih", "Son değer", "Yorum"]]
        signals = data.get("market_signals")
        if signals is None or signals.empty:
            rows.append(["N/A", "N/A", "N/A", "Sinyal verisi üretilemedi"])
            return rows

        labels = {
            "^VIX": "Beklenen volatilite bağlamı",
            "^TNX": "ABD 10Y faiz bağlamı",
            "^IRX": "Risksiz faiz proxy bağlamı",
            "DX-Y.NYB": "ABD doları endeksi bağlamı",
        }
        for col in signals.columns:
            series = signals[col].dropna()
            if series.empty:
                continue
            rows.append(
                [
                    col,
                    str(series.index[-1].date()),
                    f"{float(series.iloc[-1]):.2f}",
                    labels.get(col, "Piyasa bağlam sinyali"),
                ]
            )
        return rows

    def _data_quality_rows(self, data: Dict) -> List[List[str]]:
        rows = [["Varlık", "Sınıf", "Kapsam", "Durum", "Gerekçe"]]
        quality = data.get("data_quality")
        if quality is None or quality.empty:
            rows.append(["N/A", "N/A", "N/A", "N/A", "Veri kalite tablosu yok"])
            return rows

        display = quality.sort_values(
            ["Included_In_Returns", "Raw_Coverage_Pct"], ascending=[True, True]
        ).head(8)
        for _, row in display.iterrows():
            status = (
                "Dahil" if bool(row.get("Included_In_Returns", False)) else "Dışarıda"
            )
            rows.append(
                [
                    row.get("Ticker", "N/A"),
                    self._asset_class_label(row.get("Asset_Class", "unknown")),
                    f"{float(row.get('Raw_Coverage_Pct', 0)):.1f}%",
                    status,
                    row.get("Decision_Reason", "N/A"),
                ]
            )
        return rows

    def _ml_diagnostic_rows(self, data: Dict) -> List[List[str]]:
        rows = [["Metrik", "Değer", "Karşılaştırma", "Yorum", "Durum"]]
        metrics = data.get("ml_downside_risk_metrics")
        metadata = data.get("run_metadata", {}).get("ml_downside_risk", {})
        if metrics is None or metrics.empty:
            rows.append(["ML", "N/A", "N/A", "ML tablosu yok", "N/A"])
            return rows

        if "Fold" in metrics:
            mean_rows = metrics[metrics["Fold"].astype(str).eq("mean")]
            row = mean_rows.iloc[0] if not mean_rows.empty else metrics.iloc[-1]
        else:
            row = metrics.iloc[-1]

        status = metadata.get("status", row.get("Status", "N/A"))
        baseline = row.get("Baseline_PR_AUC", metadata.get("baseline_pr_auc", np.nan))
        metric_defs = [
            (
                "ROC-AUC",
                row.get("ROC_AUC", metadata.get("roc_auc", np.nan)),
                "0.50 rastgele",
                "Sıralama gücü",
            ),
            (
                "PR-AUC",
                row.get("PR_AUC", metadata.get("pr_auc", np.nan)),
                f"Baseline {baseline:.3f}" if pd.notna(baseline) else "N/A",
                "Nadir olay yakalama",
            ),
            (
                "Brier",
                row.get("Brier", metadata.get("brier", np.nan)),
                "Düşük daha iyi",
                "Olasılık kalibrasyonu",
            ),
            (
                "F1",
                row.get("F1", metadata.get("f1", np.nan)),
                "0-1 aralığı",
                "Pozitif olay dengesi",
            ),
        ]
        for name, value, comparison, comment in metric_defs:
            value_text = f"{float(value):.3f}" if pd.notna(value) else "N/A"
            rows.append([name, value_text, comparison, comment, status])
        return rows

    def _asset_class_label(self, asset_class: str) -> str:
        labels = {
            "us_equity_sectors": "ABD sektör ETF",
            "international_equity": "Ulus. hisse ETF",
            "crypto": "Kripto",
            "commodities": "Emtia ETF",
            "fixed_income": "Tahvil ETF",
            "reits": "GYO ETF",
            "unknown": "Bilinmiyor",
        }
        return labels.get(asset_class, asset_class)

    def _diagnostic_interpretation(self, data: Dict) -> str:
        diag = data["model_diagnostics"]
        decision = data.get("decision_summary", {})
        largest = decision.get(
            "largest_in_sample_gap_strategy", diag["Sharpe_Gap"].idxmax()
        )
        candidate = decision.get("risk_screened_candidate", diag["OOS_Sharpe"].idxmax())
        return (
            f"En büyük statik/walk-forward Sharpe farkı {largest} stratejisinde "
            f"{diag.loc[largest, 'Sharpe_Gap']:.2f} olarak ölçülmüştür. Bu nedenle "
            f"{largest} sonucu tek başına karar sonucu değildir. Risk filtresinden "
            f"sonra raporun ana araştırma adayı {candidate} olarak okunmalıdır. Bu "
            "ifade yatırım tavsiyesi değil, model kanıtının sınıflandırılmasıdır."
        )

    def _bullet_list(
        self, ListFlowable, ListItem, Paragraph, styles, items: Iterable[str]
    ):
        return ListFlowable(
            [ListItem(Paragraph(escape(str(item)), styles["body"])) for item in items],
            bulletType="bullet",
            leftIndent=12,
            bulletFontName=(
                self._font_name if hasattr(self, "_font_name") else "Helvetica"
            ),
            bulletFontSize=7.5,
        )

    def _table(self, Table, TableStyle, colors, rows, widths_cm):
        from reportlab.platypus import Paragraph

        wrapped_rows = []
        for row_idx, row in enumerate(rows):
            style = self._table_header_style if row_idx == 0 else self._table_cell_style
            wrapped_rows.append([Paragraph(escape(str(cell)), style) for cell in row])

        table = Table(
            wrapped_rows,
            colWidths=[width * cm_to_pt() for width in widths_cm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#142f46")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), self._bold_font),
                    ("FONTNAME", (0, 1), (-1, -1), self._font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 6.8),
                    ("LEADING", (0, 0), (-1, -1), 8.2),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d6dde3")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f6f8fa")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.0),
                ]
            )
        )
        return table

    def _save_fig(self, fig, filename: str) -> Path:
        path = self.asset_dir / filename
        fig.savefig(path, dpi=170, bbox_inches="tight")
        fig.clf()
        return path

    def _page_footer(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(getattr(self, "_font_name", "Helvetica"), 7)
        canvas.setFillColorRGB(0.35, 0.39, 0.43)
        canvas.drawString(
            1.35 * cm_to_pt(),
            0.70 * cm_to_pt(),
            "QuantVerse - resmi araştırma raporu; kişisel yatırım tavsiyesi değildir",
        )
        canvas.drawRightString(
            19.65 * cm_to_pt(), 0.70 * cm_to_pt(), f"Sayfa {doc.page}"
        )
        canvas.restoreState()


def cm_to_pt() -> float:
    return 28.3464566929


def generate_pdf_report(
    data_dir: str = "data/processed",
    output_path: str = "output/pdf/quantverse_analysis_report.pdf",
) -> Path:
    """Convenience wrapper for PDF report generation."""
    return InvestmentPDFReport(data_dir=data_dir, output_path=output_path).generate()
