# QuantVerse Veri Sözlüğü

Tarih: 2026-06-24

## Temel Çıktılar

| Dosya | Açıklama |
|---|---|
| `data/processed/prices_clean.parquet` | Temizlenmiş, iş günü takvimine uyarlanmış fiyat serileri. |
| `data/processed/returns_daily.parquet` | Basit günlük getiriler. Portföy ve risk hesaplarının ana girdisidir. |
| `data/processed/log_returns_daily.parquet` | Log getiriler. Tanısal ve istatistiksel analizlerde kullanılabilir. |
| `data/processed/market_signals.parquet` | Portföy ağırlığı alamayan piyasa sinyalleri. |
| `data/processed/asset_class_map.json` | Her yatırım yapılabilir ticker için varlık sınıfı eşlemesi. |
| `data/processed/data_quality_report.csv` | Her ticker için veri kapsama ve dışlama nedeni tablosu. |

## Portföy Çıktıları

| Dosya | Açıklama |
|---|---|
| `portfolio_weights.parquet` | Strateji sütunları ve ticker satırları ile ağırlık matrisi. |
| `portfolio_weights_matrix.csv` | Aynı ağırlık matrisinin CSV hali. Değerler 0-1 ölçeğindedir. |
| `portfolio_holdings_long.csv` | Her portföy, ticker ve ağırlık için uzun format tablo. `Weight_Percent` yüzde ölçeğindedir. |
| `portfolio_summary.parquet` | Statik portföy getiri, volatilite, Sharpe ve yoğunlaşma metrikleri. |

## Risk ve Backtest Çıktıları

| Dosya | Açıklama |
|---|---|
| `risk_metrics.parquet` | Günlük VaR/CVaR, 252 günlük empirik VaR/CVaR, drawdown ve çeşitlendirme metrikleri. |
| `backtest_returns.parquet` | Walk-forward strateji getiri serileri. |
| `backtest_summary.parquet` | CAGR, volatilite, Sharpe, drawdown, rebalancing ve maliyet özeti. |
| `model_diagnostics.parquet` | Statik sonuç ile walk-forward sonuç arasındaki farkın tanı tablosu. |
| `decision_summary.json` | Karar okuma kuralı, en iyi OOS strateji ve risk filtresi sonucu. |
| `var_exception_tests.csv` / `.parquet` | Rolling historical VaR ihlal sayısı, beklenen ihlal sayısı, Kupiec POF ve Christoffersen bağımsızlık tanısı. |
| `stress_scenarios.csv` / `.parquet` | Varlık sınıfı bazlı stilize piyasa şoklarının portföy etkileri. |
| `benchmark_comparison.csv` / `.parquet` | Stratejilerin iç 60/40 proxy dahil basit karşılaştırma ölçütleriyle performans karşılaştırması. |
| `transaction_cost_sensitivity.csv` / `.parquet` | 0, 5, 10 ve 25 baz puan maliyet varsayımı altında strateji performansı. |
| `statistical_robustness.csv` / `.parquet` | Moving-block bootstrap ile CAGR ve Sharpe güven aralıkları. |

## ML ve Rejim Çıktıları

| Dosya | Açıklama |
|---|---|
| `regime_labels.parquet` | Volatilite, HMM ve clustering rejim etiketleri. |
| `adaptive_returns.parquet` | Rejim bazlı adaptif tahsis denemelerinin getiri serileri. |
| `ml_downside_risk_metrics.csv` | Downside-risk tanı modelinin time-series split metrikleri. |
| `ml_downside_risk_predictions.parquet` | Downside-risk olay olasılıkları ve gerçekleşen hedef. |
| `ml_downside_risk_feature_importance.csv` | Lojistik model katsayı önemleri. |
| `ml_downside_confusion_matrix.csv` / `.parquet` | 0.50 olasılık eşiğinde confusion matrix, precision, recall ve specificity. |
| `ml_downside_drift_report.csv` / `.parquet` | Tahmin olasılığı dağılım kayması için KS ve PSI tanısı. |

## Run Metadata

`run_metadata.json`, raporun veri son tarihi, risk-free kaynağı, kullanılan
config yolu, işlem maliyeti, train window, rebalancing frekansı, sinyal ayrımı,
drop edilen varlıklar ve ML tanı özeti gibi izlenebilir çalıştırma bilgisini taşır.

## Ölçekler

- `Weight`: 0-1 arası sermaye payı.
- `Weight_Percent`: yüzde ölçeği.
- `CAGR`, `Volatility`, `Max_Drawdown`: 0-1 ölçeğinde oran.
- `VaR_5%`, `CVaR_5%`, `Max_DD_%`: yüzde puanı ölçeği.
- Stres senaryosu `Impact_%` kolonları: yüzde puanı ölçeği.
- `Cost_Bps`: 1 baz puan = %0,01 işlem maliyeti varsayımıdır.
- `Sharpe`: risksiz faiz sonrası getiri / volatilite oranı; birimsizdir.
