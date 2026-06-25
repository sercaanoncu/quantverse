# QuantVerse Sample Outputs

Tarih: 2026-06-25

Bu dosya son doğrulanan pipeline çalıştırmasının örnek çıktı sözleşmesini özetler.
Rakamlar veri son tarihine bağlıdır; yeniden çalıştırıldığında piyasa verisi
güncellenirse değerler değişebilir.

## Son Doğrulanan Run

- Veri dönemi: 2017-11-10 - 2026-06-24
- Getiri matrisi: 2249 iş günü x 37 yatırım yapılabilir enstrüman
- Risk-free proxy: `^IRX`
- Risk-free kaynak: yfinance
- Risk-free quote date: 2026-06-24
- Yıllık risk-free oran: yaklaşık 3.76%

## Ana Artefaktlar

| Dosya | Beklenen İçerik |
|---|---|
| `data/processed/run_metadata.json` | Veri tarihi, risk-free kaynak, row count, ML tanı özeti. |
| `data/processed/portfolio_holdings_long.csv` | Portföy, ticker, varlık sınıfı, ağırlık ve yüzde ağırlık. |
| `data/processed/portfolio_weights_matrix.csv` | Ticker satırları, strateji sütunları. |
| `data/processed/var_exception_tests.csv` | VaR exception count, expected count, Kupiec ve Christoffersen sonuçları. |
| `data/processed/stress_scenarios.csv` | Stilize şok senaryoları ve portföy etkileri. |
| `data/processed/benchmark_comparison.csv` | Strateji ve iç 60/40 benchmark karşılaştırması. |
| `data/processed/transaction_cost_sensitivity.csv` | 0/5/10/25 bps maliyet duyarlılığı. |
| `data/processed/statistical_robustness.csv` | Moving-block bootstrap CAGR ve Sharpe aralıkları. |
| `data/processed/ml_downside_confusion_matrix.csv` | Diagnostic confusion matrix; trading rule değildir. |
| `data/processed/ml_downside_drift_report.csv` | KS ve PSI drift tanısı. |
| `output/pdf/quantverse_analysis_report.pdf` | Resmi Türkçe araştırma raporu. |
| `output/html/quantverse_report.html` | Statik HTML araştırma raporu. |

## Son Gözlenen Karar Katmanı

- En yüksek walk-forward Sharpe: Equal Weight, yaklaşık 0.79.
- Risk filtresi sonrası ana araştırma adayı: HRP.
- HRP walk-forward Sharpe: yaklaşık 0.72.
- Max Sharpe: diagnostic only; statik/walk-forward farkı yüksek.
- ML downside-risk: diagnostic; PR-AUC baseline üzerinde fakat güçlü al-sat sinyali değil.

## Sunumda Doğru Okuma

Bu çıktılar "kesin en iyi yatırım" cevabı vermez. Doğru okuma sırası: veri kalitesi,
portföy ağırlıkları, walk-forward sonuçlar, VaR exception, stres, benchmark, işlem
maliyeti, bootstrap aralıkları ve sınırlılıklar.
