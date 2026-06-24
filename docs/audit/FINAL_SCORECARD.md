# QuantVerse Final Scorecard

Tarih: 2026-06-25

## Çalıştırma Özeti

- Config: `configs/base.yaml`
- Veri dönemi: 2017-11-10 - 2026-06-24
- Veri son tarihi: 2026-06-24
- Risk-free kaynak: yfinance `^IRX`
- Risk-free quote date: 2026-06-24
- Yıllık risk-free oran: 3.76%
- Getiri matrisi: 2249 iş günü x 37 yatırım yapılabilir enstrüman
- Portföy sayısı: 7
- Walk-forward strateji sayısı: 5
- Portföy içi sinyal sayısı: 0
- Hafta sonu satırı: 0
- Drop edilen varlıklar: `SOL-USD`, `XLC`
- Drop gerekçesi: veri kapsamı; düşük getiri nedeniyle dışlama yapılmadı.

## Karar Katmanı

| Ölçüt | Sonuç |
|---|---|
| En yüksek walk-forward Sharpe | Equal Weight, 0.79 |
| Risk filtresi sonrası ana araştırma adayı | HRP |
| HRP walk-forward Sharpe | 0.72 |
| HRP walk-forward max drawdown | -19.97% |
| En büyük statik/walk-forward Sharpe farkı | Max Sharpe, 0.70 |
| Max Sharpe sınıfı | Diagnostic only |
| İç 60/40 benchmark Sharpe | 0.36 |

## Yeni Hardening Çıktıları

| Artefakt | Satır | Amaç |
|---|---:|---|
| `var_exception_tests.csv` | 5 | Rolling historical VaR ihlal testi |
| `stress_scenarios.csv` | 7 | Stilize piyasa şok hassasiyeti |
| `benchmark_comparison.csv` | 6 | Strateji ve iç benchmark karşılaştırması |
| `transaction_cost_sensitivity.csv` | 20 | 0/5/10/25 bps maliyet duyarlılığı |
| `statistical_robustness.csv` | 5 | Moving-block bootstrap güven aralığı |
| `ml_downside_confusion_matrix.csv` | 1 | ML 0.50 eşik confusion matrix |
| `ml_downside_drift_report.csv` | 3 | ML tahmin olasılığı drift tanısı |
| `output/html/quantverse_report.html` | 43,718 byte | Statik HTML rapor |

## VaR, Stres ve Bootstrap Bulgusu

- VaR exception frekansı beş stratejide de beklenen yüzde 5 kuyruk oranına yakın.
- Min Variance ve Max Sharpe için Christoffersen bağımsızlık testi ihlal kümelenmesi
  uyarısı veriyor; bu stratejiler risk yönetiminde daha ihtiyatlı okunmalı.
- Equal Weight ve HRP bootstrap Sharpe aralıklarında pozitif alt sınır gösteriyor;
  Inverse Vol, Min Variance ve Max Sharpe için kanıt daha zayıf veya inconclusive.
- Stres senaryolarında Equal Weight çoğu risk-off şokunda en büyük stilize kaybı
  alıyor; HRP faiz/tahvil şoku altında daha hassas hale gelebiliyor.

## ML Downside-Risk Tanısı

| Metrik | Değer | Yorum |
|---|---:|---|
| ROC-AUC | 0.561 | Rastgele 0.50 üzerinde, fakat güçlü değil |
| PR-AUC | 0.116 | Baseline 0.095 üzerinde, sınırlı bilgi |
| Brier | 0.304 | Kalibrasyon iyileştirmeye açık |
| F1 | 0.128 | Nadir olay yakalama zayıf |
| Precision @0.50 | 10.7% | Çok sayıda false positive var |
| Recall @0.50 | 64.5% | Downside event yakalama tarafı daha yüksek |
| PSI drift | 2.553 | Tahmin dağılımı izleme gerektiriyor |

Sonuç: ML bileşeni yatırım sinyali olarak değil, zayıf ama raporlanabilir
downside-risk tanısı olarak okunmalıdır.

## Test ve Doğrulama

- `python -m black src scripts tests`: başarılı
- `python -m compileall src scripts`: başarılı
- `python -m pytest -q`: 19 passed
- `python scripts/run_full_pipeline.py --config configs/base.yaml`: başarılı
- PDF üretimi: `output/pdf/quantverse_analysis_report.pdf`, 15 sayfa, A4
- PDF görsel render: portföy bileşimi, validasyon, hardening ve risk sayfaları
  görsel olarak kontrol edildi
- PDF text checks: VaR Exception Testing, Benchmark Comparison, Transaction Cost
  Sensitivity, Statistical Robustness, ML Confusion ve yatırım tavsiyesi uyarısı mevcut
- HTML rapor: `output/html/quantverse_report.html` üretildi

## Skor

| Alan | Skor | Gerekçe |
|---|---:|---|
| Kod çalışabilirliği | 9.0/10 | Test, compile, tam pipeline, PDF ve HTML çalışıyor |
| Finansal tutarlılık | 8.8/10 | Sinyal ayrımı, risk-free metadata, walk-forward karar kuralı ve benchmark var |
| İstatistiksel savunulabilirlik | 8.5/10 | Shrinkage, walk-forward, VaR exception ve bootstrap var; PSR/DSR yok |
| Risk yönetimi | 8.5/10 | VaR/CVaR, exception, stres, drawdown ve maliyet duyarlılığı var; resmi limit sistemi yok |
| Raporlama | 9.0/10 | PDF holdings, hardening ve ML tanı içeriyor; HTML var |
| GitHub/CV hazır olma | 8.0/10 | Dokümantasyon güçlü; yerel `.git` bozuk olduğu için commit/branch doğrulanamıyor |
| Bank-grade üretim | 6.5/10 | Public veri, bağımsız mutabakat, model approval, limit ve execution katmanı eksik |

Genel araştırma/sunum skoru: 9.0/10.

Kurumsal canlı yatırım sistemi skoru: 6.5/10.

## Kalan Riskler

- Public yfinance verisi resmi yatırım verisi değildir.
- `.git` yerel olarak bozuk; branch, tracking ve commit bu çalışma ağacında doğrulanamıyor.
- ML downside-risk modeli zayıf sinyallidir ve drift izleme gerektirir.
- Transaction cost modeli gerçek emir defteri, vergi, piyasa etkisi ve likidite
  kurumasını tam modellemez.
- VaR exception ve bootstrap geçmiş veri tanısıdır; gelecek performans garantisi değildir.
- Kurumsal kullanım için bağımsız veri sağlayıcı, model validation imzası, limit
  dokümanı, execution ölçümü ve canlı monitoring gerekir.

## Nihai Hüküm

Proje veri bilimi yüksek lisans sunumu ve GitHub/CV vitrini için artık savunulabilir,
ölçülebilir ve profesyonel bir araştırma sistemi seviyesindedir. Buna rağmen kişisel
veya kurumsal yatırım kararını tek başına otomatikleştirecek bank-grade canlı trading
sistemi değildir.
