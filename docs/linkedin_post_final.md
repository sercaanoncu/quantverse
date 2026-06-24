# LinkedIn Paylaşım Taslağı

QuantVerse projemi uçtan uca, config-driven bir quantitative finance araştırma
sistemine dönüştürdüm.

Proje artık yalnızca portföy optimizasyonu yapmıyor. Aynı çalıştırmada:

- yatırım yapılabilir varlıkları VIX/faiz/DXY gibi piyasa sinyallerinden ayırıyor,
- portföy ağırlıklarını uzun ve matris formatında raporluyor,
- walk-forward backtest ile statik optimizasyonu denetliyor,
- VaR/CVaR, drawdown, Calmar ve Ulcer Index üretiyor,
- VaR exception testing, stres senaryosu, benchmark comparison, transaction-cost
  sensitivity ve moving-block bootstrap sağlamlık analizi hazırlıyor,
- downside-risk için time-series split ML tanısı, confusion matrix ve drift raporu
  oluşturuyor,
- resmi Türkçe PDF ve statik HTML rapor üretiyor.

Bu projede özellikle iki ilkeye dikkat ettim:

1. Düşük geçmiş getiri, varlığı silme gerekçesi değildir.
2. Güzel görünen statik optimizasyon sonucu, walk-forward ve risk kanıtı olmadan
   karar kanıtı değildir.

QuantVerse yatırım tavsiyesi değildir. Akademik ve araştırma amaçlı karar destek
sistemidir; canlı yatırım veya kurumsal portföy yönetimi için bağımsız veri
mutabakatı, model approval, limit sistemi ve execution kontrolleri gerekir.
