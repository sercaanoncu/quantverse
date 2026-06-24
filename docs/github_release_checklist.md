# QuantVerse GitHub Release Checklist

Tarih: 2026-06-24

## Yayın Öncesi Zorunlu Kontroller

- [ ] Çalışma ağacı geçerli bir Git repository içinde mi?
- [ ] Branch adı `hardening-sprint` mi?
- [ ] Büyük tekrar üretilebilir dosyalar izlenmiyor mu? Özellikle parquet, pickle,
  PDF, HTML ve cache çıktıları `.gitignore` altında mı?
- [ ] `configs/base.yaml` tek üretim konfigürasyonu olarak korunuyor mu?
- [ ] `python -m pytest -q` hatasız geçiyor mu?
- [ ] `python -m compileall src scripts` hatasız geçiyor mu?
- [ ] `python scripts/run_full_pipeline.py --config configs/base.yaml` PDF ve HTML
  dahil tamamlanıyor mu?
- [ ] `data/processed/run_metadata.json` veri son tarihi, risk-free kaynak ve row
  count bilgilerini içeriyor mu?
- [ ] `portfolio_holdings_long.csv` ve `portfolio_weights_matrix.csv` hangi
  portföyde hangi hisse/ETF/varlık ne kadar var sorusunu cevaplıyor mu?
- [ ] `var_exception_tests.csv`, `stress_scenarios.csv`, `benchmark_comparison.csv`,
  `transaction_cost_sensitivity.csv` ve `statistical_robustness.csv` üretiliyor mu?
- [ ] `ml_downside_confusion_matrix.csv` ve `ml_downside_drift_report.csv` üretiliyor mu?
- [ ] PDF görsel olarak render edilip taşma, boş sayfa, bozuk karakter ve okunamaz
  tablo açısından kontrol edildi mi?
- [ ] README yatırım tavsiyesi iddiası taşımıyor mu?

## Yayın Notu

Bu proje araştırma ve akademik sunum amaçlıdır. Public yfinance verisi kullanır.
Canlı yatırım, portföy yönetimi veya regülasyon kapsamındaki kurumsal karar için
bağımsız veri mutabakatı, model validation imzası, limit dokümanı ve execution
kontrolleri gerekir.
