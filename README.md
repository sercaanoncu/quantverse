# QuantVerse

QuantVerse, çok varlıklı portföy araştırması, risk analizi, walk-forward backtest,
downside-risk ML tanısı ve resmi PDF rapor üretimi yapan Python projesidir.

Bu proje yatırım tavsiyesi değildir. Amaç; veri, varsayım, portföy ağırlıkları,
risk ölçüleri ve model sınırlılıklarını denetlenebilir biçimde raporlamaktır.

## Ne Yapar?

- Canonical üretim konfigürasyonunu `configs/base.yaml` dosyasından okur.
- ETF, kripto, emtia, tahvil ve REIT evrenini indirir ve iş günü getiri matrisi üretir.
- `^VIX`, `^TNX`, `^IRX` ve `DX-Y.NYB` gibi serileri portföyden ayırır; bunlar sinyaldir.
- Risk-free oranını mümkün olduğunda `^IRX` piyasa proxy'sinden alır; fallback kullanılırsa metadata'da açıkça yazar.
- Ledoit-Wolf kovaryans, Mean-Variance, HRP, Risk Parity, Inverse Volatility ve Minimum CVaR portföyleri üretir.
- Düşük geçmiş getiri nedeniyle varlık silmez; veri kalitesi nedeniyle dışarıda kalanları `data_quality_report.csv` dosyasında açıklar.
- Her portföy için hangi enstrümandan ne kadar alındığını `portfolio_holdings_long.csv` ve `portfolio_weights_matrix.csv` dosyalarında gösterir.
- Maliyet dahil walk-forward backtest çalıştırır.
- VaR, CVaR, drawdown, Calmar, Ulcer Index ve çeşitlendirme metrikleri üretir.
- Statik optimizasyon ile walk-forward sonuç arasındaki farkı `model_diagnostics.parquet` dosyasında ölçer.
- Downside-risk için zaman sıralı ML tanısı üretir; bu modül al-sat sinyali değildir.
- Resmi, Türkçe, metodoloji ve sınırlılık açıklamalı PDF rapor üretir.

## Kurulum

```powershell
python -m pip install -e ".[dev,notebook]"
```

Sadece üretim pipeline'ı için:

```powershell
python -m pip install -e .
```

## Çalıştırma

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml
```

PDF üretmeden:

```powershell
python scripts/run_full_pipeline.py --config configs/base.yaml --skip-pdf
```

Makefile olan ortamlarda:

```bash
make smoke
make report
```

## Test

```powershell
python -m pytest -q
python -m compileall src scripts
```

## Ana Çıktılar

- `data/processed/run_metadata.json`
- `data/processed/data_quality_report.csv`
- `data/processed/portfolio_holdings_long.csv`
- `data/processed/portfolio_weights_matrix.csv`
- `data/processed/risk_metrics.parquet`
- `data/processed/backtest_summary.parquet`
- `data/processed/model_diagnostics.parquet`
- `data/processed/ml_downside_risk_metrics.csv`
- `reports/run_logs/latest_run.log`
- `output/pdf/quantverse_analysis_report.pdf`

## Metodoloji İlkeleri

Statik optimizasyon sonucu tek başına karar kanıtı değildir. Karar okumasında
walk-forward sonuç, drawdown, maliyet, risk metrikleri ve model tanı farkı önceliklidir.

Black-Litterman ana üretim raporunda kullanılmaz; çünkü tarihli, kaynaklandırılmış
ve güven düzeyi belirtilmiş yatırım görüşleri olmadan bilimsel kanıt üretmez.

XGBoost ve LightGBM çekirdek bağımlılık değildir; üretim pipeline'ında doğrulanmış
bir getiri tahmin sistemi olmadığı sürece projeyi olduğundan büyük göstermek doğru değildir.

## Proje Yapısı

```text
configs/base.yaml                 canonical üretim konfigürasyonu
src/project/config.py             config yükleme ve validasyon
src/project/pipeline.py           uçtan uca üretim pipeline'ı
src/project/data_pipeline/        evren, veri indirme, temizleme
src/project/optimization/         portföy optimizasyonları
src/project/risk/                 VaR, CVaR, drawdown ve risk katkısı
src/project/backtest/             walk-forward backtest
src/project/ml/                   downside-risk tanı modeli
src/project/reporting/            PDF rapor ve dashboard verisi
docs/                             metodoloji, validasyon ve yönetişim
tests/                            kritik invariant testleri
```

## Dokümantasyon

- `docs/architecture.md`
- `docs/data_dictionary.md`
- `docs/methodology.md`
- `docs/model_governance.md`
- `docs/validation/model_validation_checklist.md`
- `docs/validation/market_risk_validation_report.md`
- `docs/model_cards/downside_risk_model_card.md`
- `docs/limitations.md`

## Sınırlılıklar

Veri kaynağı public yfinance'tır. Kurumsal yatırım kararı için bağımsız veri
sağlayıcı mutabakatı gerekir. Backtest geçmiş performansı ölçer, gelecek performansı
garanti etmez. PDF ve tablolar karar destek çıktısıdır; kişisel yatırım tavsiyesi
değildir.
