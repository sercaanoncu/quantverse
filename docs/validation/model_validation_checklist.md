# QuantVerse Model Validasyon Checklist

Tarih: 2026-06-24

## Veri Kontrolleri

- [ ] `configs/base.yaml` yükleniyor mu?
- [ ] Duplicate ticker yok mu?
- [ ] `^VIX`, `^TNX`, `^IRX`, `DX-Y.NYB` yalnızca sinyal olarak mı duruyor?
- [ ] `data_quality_report.csv` üretilmiş mi?
- [ ] Drop edilen varlıkların gerekçesi veri kalitesi mi, gerçekleşmiş getiri değil mi?
- [ ] Hafta sonu satırı üretim getiri matrisinde sıfır mı?

## Portföy Kontrolleri

- [ ] Her portföy ağırlık toplamı 1 mi?
- [ ] Her varlık ağırlığı config'teki maksimum ağırlığı aşıyor mu?
- [ ] Negatif ağırlık veya kaldıraç oluşmuyor mu?
- [ ] Sinyaller portföy ağırlığı almıyor mu?
- [ ] `portfolio_holdings_long.csv` hangi portföyde hangi enstrüman ne kadar var sorusunu cevaplıyor mu?

## Backtest Kontrolleri

- [ ] Train window config'ten mi geliyor?
- [ ] Rebalancing frekansı config'ten mi geliyor?
- [ ] İşlem maliyeti net getiriye yansıyor mu?
- [ ] Walk-forward her tarihte yalnızca geçmiş veriyi mi kullanıyor?
- [ ] Statik sonuçlar karar kanıtı olarak değil tanı olarak mı etiketleniyor?

## Risk Kontrolleri

- [ ] Günlük VaR ve CVaR raporlanıyor mu?
- [ ] 252 günlük empirik VaR/CVaR raporlanıyor mu?
- [ ] Max drawdown, Calmar ve Ulcer Index raporlanıyor mu?
- [ ] Risk-free oranının kaynağı metadata'da açık mı?
- [ ] `var_exception_tests.csv` ihlal sayısı, beklenen ihlal sayısı, Kupiec ve Christoffersen sonuçlarını içeriyor mu?
- [ ] `stress_scenarios.csv` stilize senaryoların portföy etkilerini gösteriyor mu?
- [ ] `benchmark_comparison.csv` stratejileri basit benchmark ile karşılaştırıyor mu?
- [ ] `transaction_cost_sensitivity.csv` 0/5/10/25 baz puan maliyet varsayımlarını içeriyor mu?
- [ ] `statistical_robustness.csv` bootstrap güven aralıklarını raporluyor mu?

## ML Kontrolleri

- [ ] Downside-risk hedefi ileriye dönük gün için mi tanımlanmış?
- [ ] Target threshold geçmiş pencere ile mi hesaplanıyor?
- [ ] TimeSeriesSplit kullanılıyor mu?
- [ ] ROC-AUC, PR-AUC, Brier ve F1 raporlanıyor mu?
- [ ] Confusion matrix ve drift raporu üretiliyor mu?
- [ ] Model zayıfsa çıktı saklanmadan “diagnostic” olarak mı gösteriliyor?

## Raporlama Kontrolleri

- [ ] PDF yeniden üretildi mi?
- [ ] PDF'de portföy bileşim tablosu okunabilir mi?
- [ ] PDF'de VaR exception, stres, benchmark, maliyet duyarlılığı ve bootstrap bölümü var mı?
- [ ] Veri son tarihi PDF'de görünüyor mu?
- [ ] Yatırım tavsiyesi olmadığı açıkça yazıyor mu?
- [ ] “Neyi neden kullandık, neyi neden kullanmadık” sorusu cevaplanıyor mu?
- [ ] `output/html/quantverse_report.html` yeniden üretildi mi?

## Geçiş Kriteri

Model validasyonu koşullu geçer sayılabilir; çünkü public veri sağlayıcı ve bozuk
yerel `.git` metadata'sı kurumsal tam geçişi engeller. Araştırma ve yüksek lisans
sunumu için geçiş, testlerin tamamının geçmesi, PDF'in okunabilir olması ve
metadata'nın güncel olması şartıyla savunulabilir.
