# QuantVerse Piyasa Riski Validasyon Raporu

Tarih: 2026-06-24

## Yönetici Özeti

QuantVerse piyasa riski modülü günlük ve yıllık kuyruk kaybı ölçülerini,
drawdown ölçülerini, çeşitlendirme göstergelerini ve walk-forward performansını
birlikte üretir. Sistem araştırma ve karar destek amaçlıdır; regülasyon kapsamındaki
sermaye hesaplaması, resmi risk limiti veya kişisel yatırım tavsiyesi değildir.

## Kapsam

Validasyon kapsamındaki çıktılar:

- `risk_metrics.parquet`
- `backtest_summary.parquet`
- `model_diagnostics.parquet`
- `data_quality_report.csv`
- `run_metadata.json`

## VaR ve CVaR Yaklaşımı

Günlük VaR, belirli bir güven seviyesinde beklenen kayıp eşiğini ifade eder.
CVaR, bu eşiğin ötesindeki ortalama kaybı ölçer. Finansal getiriler normal
dağılmak zorunda olmadığı için tarihsel CVaR özellikle önemlidir.

Yıllık tarihsel VaR/CVaR için günlük kaybı doğrudan `sqrt(252)` ile büyütmek
yerine, gerçekleşmiş 252 günlük bileşik getiri dağılımı kullanılır. Bu tercih,
seri korelasyon, volatilite kümelenmesi ve bileşik getiri etkisini daha dürüst
yansıtır.

## Backtesting ve Model Riski

Walk-forward backtest, modelin her karar tarihinde yalnızca geçmiş veriye bakmasını
sağlar. Bu, look-ahead bias riskini azaltır. Bununla birlikte backtest geçmiş piyasa
rejimlerinin gelecekte tekrarlanacağını garanti etmez.

`model_diagnostics.parquet`, statik optimizasyon Sharpe değeri ile walk-forward
Sharpe değerini karşılaştırır. Büyük fark, overfit veya tahmin hatası uyarısıdır.

## Stres ve Rejim

Rejim etiketleri piyasa bağlamı sağlar; tek başına alım-satım sinyali değildir.
Stres testleri ve Monte Carlo modülleri projede mevcuttur, fakat tam kurumsal
limit sistemi için senaryo tanımlarının, şok büyüklüklerinin ve yönetim onayının
ayrı bir dokümanda sabitlenmesi gerekir.

## Başlıca Riskler

- Veri sağlayıcı riski: yfinance araştırma için uygundur, resmi mutabakat kaynağı değildir.
- Likidite riski: ETF ve kripto varlıklar aynı likidite profiline sahip değildir.
- Model riski: beklenen getiri tahmini gürültülüdür.
- Regime riski: geçmiş rejim tanımı gelecekteki rejimi garanti etmez.
- Execution riski: gerçek emir gerçekleşmesi, spread ve vergi etkileri modele tam
  yansımayabilir.

## Validasyon Görüşü

Araştırma ve akademik sunum için sistem savunulabilir seviyededir; çünkü veri
kalitesi, sinyal ayrımı, portföy ağırlıkları, walk-forward kanıtı ve risk ölçüleri
izlenebilir dosyalarla raporlanmaktadır. Kurumsal yatırım sistemi olarak kullanmak
için bağımsız veri sağlayıcı, resmi limit yapısı, exception backtesting, stres
senaryosu onayı ve üretim izleme panosu eklenmelidir.
