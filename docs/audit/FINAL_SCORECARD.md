# QuantVerse Final Scorecard

Tarih: 2026-06-24

## Çalıştırma Özeti

- Config: `configs/base.yaml`
- Veri dönemi: 2017-11-10 - 2026-06-23
- Veri son tarihi: 2026-06-23
- Risk-free kaynak: yfinance `^IRX`
- Risk-free quote date: 2026-06-18
- Yıllık risk-free oran: 3.73%
- Getiri matrisi: 2248 iş günü x 37 yatırım yapılabilir enstrüman
- Portföy sayısı: 7
- Walk-forward strateji sayısı: 5
- Portföy içi sinyal sayısı: 0
- Hafta sonu satırı: 0
- Drop edilen varlıklar: `SOL-USD`, `XLC`
- Drop gerekçesi: veri kapsamı; düşük getiri nedeniyle dışlama yapılmadı.

## Karar Katmanı

| Ölçüt | Sonuç |
|---|---|
| En yüksek walk-forward Sharpe | Equal Weight, 0.80 |
| Risk filtresi sonrası ana araştırma adayı | HRP |
| HRP walk-forward Sharpe | 0.73 |
| HRP walk-forward max drawdown | -19.97% |
| En büyük statik/walk-forward Sharpe farkı | Max Sharpe, 0.70 |
| Max Sharpe sınıfı | Diagnostic only |

## Ağırlık Kontrolleri

Tüm portföylerde ağırlık toplamı 1.00 olarak doğrulandı. Maksimum ağırlıklar config
ile uyumludur:

- Equal Weight: 2.70%
- Min Variance: 25.00%
- Max Sharpe: 25.00%
- HRP: 25.00%
- Risk Parity: 17.21%
- Inverse Volatility: 8.39%
- Minimum CVaR: 25.00%

## ML Downside-Risk Tanısı

| Metrik | Değer | Yorum |
|---|---:|---|
| ROC-AUC | 0.562 | Rastgele 0.50 üzerinde, fakat güçlü değil |
| PR-AUC | 0.116 | Baseline 0.095 üzerinde, sınırlı bilgi |
| Brier | 0.304 | Kalibrasyon iyileştirmeye açık |
| F1 | 0.128 | Nadir olay yakalama zayıf |

Sonuç: ML bileşeni yatırım sinyali olarak değil, zayıf ama raporlanabilir downside-risk
tanısı olarak okunmalıdır.

## Test ve Doğrulama

- `pytest -q`: 17 passed
- `python -m compileall src scripts`: başarılı
- `python -W error::FutureWarning scripts/run_full_pipeline.py --config configs/base.yaml`: başarılı
- PDF text checks: portfolio holdings, data quality, ML downside-risk, yatırım tavsiyesi uyarısı ve aritmetik ortalama tanımı mevcut
- PDF visual render: sayfa 4, 8 ve 10 görsel olarak kontrol edildi

## Skor

| Alan | Skor | Gerekçe |
|---|---:|---|
| Kod çalışabilirliği | 9/10 | Pipeline, test ve PDF üretimi çalışıyor |
| Finansal tutarlılık | 8/10 | Sinyal ayrımı, risk-free metadata, walk-forward karar kuralı mevcut |
| İstatistiksel savunulabilirlik | 7/10 | Shrinkage ve walk-forward mevcut; bootstrap/PSR/DSR henüz yok |
| Risk yönetimi | 7/10 | VaR/CVaR, drawdown, data quality var; exception backtesting ve limit yapısı eksik |
| Raporlama | 8/10 | PDF kapsamlı ve holdings görünür; HTML/dashboard yok |
| GitHub/CV hazır olma | 8/10 | README, docs, CI, Dockerfile, Makefile var; yerel `.git` bozuk |
| Bank-grade üretim | 6/10 | Public veri, bağımsız veri mutabakatı ve kurumsal model approval eksik |

Genel araştırma/sunum skoru: 8/10.

Kurumsal canlı yatırım sistemi skoru: 6/10.

## Kalan Riskler

- Public yfinance verisi resmi yatırım verisi değildir.
- `.git` yerel olarak bozuk; commit ve branch geçmişi doğrulanamıyor.
- VaR exception testing, stress scenario output ve benchmark-relative hypothesis tests üretim pipeline'ına tam entegre edilmedi.
- Downside-risk ML sinyali zayıf; model sinyal değil tanı katmanıdır.
- Streamlit/HTML dashboard henüz yok.
- Kilitlenmiş dependency lock dosyası yok.

## Nihai Hüküm

Proje artık veri bilimi yüksek lisans sunumu için savunulabilir, ölçülebilir ve
raporlanabilir bir araştırma sistemi seviyesine gelmiştir. Ancak kişisel veya
kurumsal yatırım kararını tek başına otomatikleştirecek “tam bank-grade canlı
trading sistemi” değildir. Kurumsal kullanım için bağımsız veri sağlayıcı, resmi
model validasyon imzası, exception testing, stres limitleri, dashboard ve deployment
izleme katmanı gerekir.
