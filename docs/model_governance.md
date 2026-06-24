# QuantVerse Model Yönetişimi

Tarih: 2026-06-24

## Kapsam

Bu doküman QuantVerse üretim pipeline'ında yer alan veri, optimizasyon, risk,
backtest, rejim ve ML tanı bileşenlerinin yönetişim çerçevesini tanımlar.

## Model Sahipliği

| Bileşen | Sahiplik | Ana risk |
|---|---|---|
| Veri pipeline'ı | Proje sahibi | Eksik, hatalı veya gecikmeli piyasa verisi |
| Optimizasyon | Quant araştırma | Tahmin hatasına aşırı duyarlılık |
| Risk ölçümü | Market risk | Kuyruk riskini eksik ölçme |
| Walk-forward backtest | Model validation | Look-ahead ve overfit riski |
| ML downside-risk | Data science | Zayıf sinyal, kalibrasyon hatası |
| PDF rapor | Araştırma/raporlama | Sonuçların yanlış yorumlanması |

## Onaylanmış Üretim Kaynağı

Tek onaylanmış üretim konfigürasyonu `configs/base.yaml` dosyasıdır. Eski
`config/settings.yaml` yalnızca uyumluluk dosyasıdır ve canonical kaynak değildir.

## Model Risk Kontrolleri

- Her çalıştırmada `run_metadata.json` üretilir.
- Sinyal serileri portföy ağırlığı alamaz.
- Portföy ağırlıkları toplamı 1 olmalıdır.
- Maksimum ağırlık config tarafından belirlenir.
- Risk-free oranının kaynağı metadata'da `yfinance`, `manual_config` veya
  `fallback` olarak açıkça yazılır.
- Walk-forward sonuçlar statik sonuçlardan üstün karar kanıtı sayılır.
- ML çıktısı yatırım sinyali değil, downside-risk tanısıdır.

## Değişiklik Yönetimi

Her metodoloji değişikliği için şu sorular cevaplanmalıdır:

1. Değişiklik hangi varsayımı etkiliyor?
2. Backtest ve risk çıktılarında ne değişti?
3. Veri son tarihi aynı mı?
4. Model, geçmiş veriye daha fazla mı uyum sağladı?
5. Sinyal ve yatırım yapılabilir varlık ayrımı korunuyor mu?
6. PDF ve veri sözlüğü güncellendi mi?

## İzleme

Her üretim çalıştırmasından sonra şu dosyalar kontrol edilmelidir:

- `reports/run_logs/latest_run.log`
- `data/processed/run_metadata.json`
- `data/processed/data_quality_report.csv`
- `data/processed/model_diagnostics.parquet`
- `data/processed/backtest_summary.parquet`
- `data/processed/ml_downside_risk_metrics.csv`

## Sınırlama

Bu yönetişim çerçevesi araştırma sistemi içindir. Regülasyon kapsamındaki kurumsal
kullanım için bağımsız veri mutabakatı, model validasyon imzası, erişim kontrolü,
versiyonlu veri deposu ve ayrı change approval süreci gerekir.
