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
- `var_exception_tests.csv`
- `stress_scenarios.csv`
- `benchmark_comparison.csv`
- `transaction_cost_sensitivity.csv`
- `statistical_robustness.csv`
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

## VaR Exception Testing

`var_exception_tests.csv`, her walk-forward strateji için rolling historical VaR
eşiğini yalnızca geçmiş pencereye bakarak hesaplar. Sonraki gün getiri bu eşiğin
altına düşerse ihlal sayılır. Alpha 0,05 ise uzun dönemde beklenen ihlal oranı
yaklaşık yüzde 5'tir.

Raporlanan iki ana istatistik:

- Kupiec POF testi: İhlal sayısı beklenen ihlal sayısından istatistiksel olarak
  anlamlı biçimde farklı mı?
- Christoffersen bağımsızlık testi: İhlaller kümeleniyor mu, yoksa bağımsız
  sayılabilecek şekilde mi geliyor?

Bu testler VaR modelinin gelecekte doğru çalışacağını ispatlamaz. Sadece geçmiş
walk-forward dönemde ihlal frekansı ve ihlal bağımlılığı açısından açık bir uyarı
olup olmadığını gösterir.

## Stres ve Rejim

Rejim etiketleri piyasa bağlamı sağlar; tek başına alım-satım sinyali değildir.
`stress_scenarios.csv`, COVID benzeri risk-off, 2022 enflasyon/faiz şoku, küresel
risk-off, hisse çöküşü, tahvil faiz şoku, dolar güçlenmesi ve kripto çöküşü gibi
stilize varlık sınıfı şoklarını üretir. Bunlar tarihsel krizin birebir tekrarları
değildir; portföyün sınıf bazlı şoklara hassasiyetini gösteren denetim senaryolarıdır.

## Benchmark, Maliyet ve Bootstrap

`benchmark_comparison.csv`, strateji sonuçlarını basit karşılaştırma ölçütleriyle
yan yana koyar. Basit benchmark, karmaşık optimizasyonun gerçekten ek bilgi sağlayıp
sağlamadığını test etmek için gereklidir.

`transaction_cost_sensitivity.csv`, 0, 5, 10 ve 25 baz puan maliyet varsayımlarında
CAGR, Sharpe, drawdown ve toplam maliyetin nasıl değiştiğini gösterir. Bu çıktı,
sonucun yalnızca düşük maliyet varsayımı altında mı ayakta kaldığını kontrol eder.

`statistical_robustness.csv`, moving-block bootstrap ile zaman serisi bağımlılığını
tamamen yok etmeden Sharpe ve CAGR güven aralıkları üretir. Bu güven aralıkları
geleceği kanıtlamaz; örneklem belirsizliğini görünür kılar.

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
için bağımsız veri sağlayıcı, resmi limit yapısı, yönetim onaylı stres senaryoları,
canlı izleme panosu, emir gerçekleşmesi ölçümü ve model validation imzası gerekir.
