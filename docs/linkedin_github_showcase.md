# QuantVerse GitHub ve LinkedIn Sunum Metni

## GitHub Kısa Açıklama

QuantVerse is a research-grade multi-asset portfolio analytics platform that
combines investable-universe cleaning, covariance shrinkage, constrained portfolio
optimization, walk-forward validation, market-risk analytics, downside-risk ML
diagnostics, and formal PDF reporting.

## GitHub README Öne Çıkarılacak Maddeler

- Config-driven production pipeline with `configs/base.yaml`.
- Investable assets separated from market-context signals.
- Walk-forward validation used as the primary decision layer.
- Portfolio holdings exported in both matrix and long CSV format.
- VaR/CVaR, drawdown, cost-aware backtest and model diagnostics.
- Downside-risk ML diagnostic with chronological validation.
- Formal Turkish PDF research report with methodology and limitations.
- CI, Dockerfile, Makefile, audit and validation documentation.

## LinkedIn Türkçe Paylaşım Taslağı

QuantVerse projemi araştırma düzeyinden üretim disiplinine taşıdım. Proje artık
yalnızca notebook çıktısı üretmiyor; tek konfigürasyon dosyasından çalışan,
yatırım yapılabilir varlıkları piyasa sinyallerinden ayıran, portföy ağırlıklarını
açıkça raporlayan, walk-forward doğrulama yapan, VaR/CVaR ve drawdown metrikleri
üreten, downside-risk için time-series split ile ML tanısı oluşturan ve resmi PDF
rapor hazırlayan uçtan uca bir quantitative finance araştırma sistemi.

Özellikle iki ilkeye dikkat ettim: geçmiş getirisi düşük diye varlık silmedim ve
statik optimizasyon sonucunu yatırım kararı gibi göstermedim. Nihai okuma
walk-forward kanıtı, risk, maliyet ve model tanıları üzerinden yapılıyor.

## Uyarı

Paylaşımda “yatırım tavsiyesi değildir” ifadesi mutlaka bulunmalıdır. Proje
akademik ve araştırma amaçlı karar destek sistemidir.
