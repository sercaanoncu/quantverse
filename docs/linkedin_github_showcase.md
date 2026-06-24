# QuantVerse GitHub ve LinkedIn Sunum Metni

## GitHub Kısa Açıklama

QuantVerse is a research-grade multi-asset portfolio analytics platform that
combines investable-universe cleaning, covariance shrinkage, constrained portfolio
optimization, walk-forward validation, market-risk analytics, downside-risk ML
diagnostics, VaR exception testing, stress scenarios, benchmark comparison,
transaction-cost sensitivity, bootstrap robustness, and formal PDF/HTML reporting.

## GitHub README Öne Çıkarılacak Maddeler

- Config-driven production pipeline with `configs/base.yaml`.
- Investable assets separated from market-context signals.
- Walk-forward validation used as the primary decision layer.
- Portfolio holdings exported in both matrix and long CSV format.
- VaR/CVaR, drawdown, cost-aware backtest and model diagnostics.
- VaR exception testing, stylized stress scenarios, benchmark comparison,
  transaction-cost sensitivity and moving-block bootstrap robustness.
- Downside-risk ML diagnostic with chronological validation, confusion matrix and
  drift report.
- Formal Turkish PDF research report and static HTML report with methodology and limitations.
- CI, Dockerfile, Makefile, audit and validation documentation.

## LinkedIn Türkçe Paylaşım Taslağı

QuantVerse projemi araştırma düzeyinden üretim disiplinine taşıdım. Proje artık
yalnızca notebook çıktısı üretmiyor; tek konfigürasyon dosyasından çalışan,
yatırım yapılabilir varlıkları piyasa sinyallerinden ayıran, portföy ağırlıklarını
açıkça raporlayan, walk-forward doğrulama yapan, VaR/CVaR ve drawdown metrikleri
üreten, VaR exception testing, stres senaryosu, benchmark karşılaştırması, işlem
maliyeti duyarlılığı ve bootstrap sağlamlık analizi oluşturan; downside-risk için
time-series split ile ML tanısı, confusion matrix ve drift raporu hazırlayan uçtan
uca bir quantitative finance araştırma sistemi.

Özellikle iki ilkeye dikkat ettim: geçmiş getirisi düşük diye varlık silmedim ve
statik optimizasyon sonucunu yatırım kararı gibi göstermedim. Nihai okuma
walk-forward kanıtı, risk, maliyet ve model tanıları üzerinden yapılıyor.

## Uyarı

Paylaşımda “yatırım tavsiyesi değildir” ifadesi mutlaka bulunmalıdır. Proje
akademik ve araştırma amaçlı karar destek sistemidir.
