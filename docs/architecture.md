# QuantVerse Mimari Dokümanı

Tarih: 2026-06-24

## Amaç

QuantVerse, çok varlıklı finansal zaman serilerinden portföy araştırması, risk
ölçümü, walk-forward doğrulama ve resmi rapor üretimi yapan bir karar destek
sistemidir. Sistem yatırım tavsiyesi üretmez; model varsayımlarını, veri
kapsamını, portföy ağırlıklarını, risk ölçülerini ve sınırlılıkları denetlenebilir
biçimde raporlar.

## Ana Akış

1. `configs/base.yaml` üretim için tek konfigürasyon kaynağıdır.
2. `scripts/run_full_pipeline.py` config'i okur, log dosyasını başlatır ve
   `project.pipeline.run_full_pipeline` fonksiyonunu çalıştırır.
3. `data_pipeline` modülü yatırım yapılabilir enstrümanları piyasa sinyallerinden
   ayırır, fiyatları indirir, temizler ve iş günü getiri matrisini üretir.
4. `covariance`, `optimization`, `risk`, `backtest`, `regime` ve `ml` modülleri
   sırasıyla kovaryans, portföy, risk, walk-forward, rejim ve downside-risk
   tanı çıktılarını üretir.
5. `reporting/pdf_report.py` üretilmiş artefaktlardan resmi PDF raporunu oluşturur.

## Veri ve Karar Katmanları

- Ham fiyat verisi: `data/cache/` içinde geçici olarak saklanır.
- Üretim artefaktları: `data/processed/` altında parquet, csv ve json olarak yazılır.
- Sunum tabloları: `reports/tables/` altında yazılır.
- Görseller: `reports/figures/` altında yazılır.
- PDF: `output/pdf/quantverse_analysis_report.pdf` altında yazılır.
- Run log: `reports/run_logs/latest_run.log` altında yazılır.

## Kritik Tasarım İlkeleri

- Sinyaller portföy ağırlığı alamaz. `^VIX`, `^TNX`, `^IRX` ve `DX-Y.NYB`
  yalnızca piyasa bağlamı ve risk-free proxy kaynağı olarak kullanılır.
- Düşük gerçekleşmiş getiri, varlığı dışarı atma gerekçesi değildir. Dışlama
  yalnızca veri sağlayıcı hatası, yetersiz tarihsel kapsam veya temizleme kuralı
  nedeniyle yapılır.
- Statik optimizasyon sonucu karar kanıtı değildir. Nihai okuma walk-forward
  kanıtı, drawdown, maliyet ve model tanı farkları üzerinden yapılır.
- Black-Litterman ana üretim sonucunda kullanılmaz; tarihli, kaynaklandırılmış
  ve güven düzeyi verilmiş yatırım görüşleri olmadan yalnızca varsayımsal senaryo
  olarak kalabilir.

## Çalıştırma

```bash
python scripts/run_full_pipeline.py --config configs/base.yaml
python -m pytest -q
```

## Bilinen Mimari Sınırlar

- `.git` dizini yerelde bozuk olduğu için commit geçmişi bu çalışma ağacında
  doğrulanamamaktadır.
- `Lib/`, `Scripts/`, `etc/`, `share/` klasörleri yerel sanal ortam kalıntısı
  gibi görünmektedir; kullanıcı onayı olmadan silinmemiştir.
- Veriler public `yfinance` kaynağına dayalıdır. Kurumsal kullanımda bağımsız
  veri sağlayıcı mutabakatı gerekir.
