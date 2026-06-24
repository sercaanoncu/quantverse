# Model Card: Downside-Risk Diagnostic Model

Tarih: 2026-06-24

## Model

Balanced logistic regression with standardized features and chronological
TimeSeriesSplit validation.

## Amaç

Model, bir sonraki iş gününde eşit ağırlıklı portföy getirisinin geçmiş pencereye
göre alt kuyruk olayına düşme olasılığını tanısal olarak ölçer. Bu bir al-sat
sinyali veya getiri tahmini değildir.

## Hedef Değişken

Hedef `1`, bir sonraki gün eşit ağırlıklı portföy getirisinin önceki rolling
pencereye göre alt yüzde 10 eşiğinin altında kalmasıdır. Eşik geçmiş veriden
hesaplanır ve bir gün geciktirilir.

## Özellikler

- 1, 5 ve 21 günlük portföy getirisi.
- 21 ve 63 günlük gerçekleşmiş volatilite.
- Drawdown.
- Kesitsel getiri dağılımı.
- Pozitif getiri üreten varlık oranı.
- VIX, faiz ve DXY gibi sinyal seviyeleri ve 5 günlük değişimleri.

## Validasyon

Zaman sırasını bozmayan TimeSeriesSplit kullanılır. Her fold için:

- ROC-AUC
- PR-AUC
- Baseline PR-AUC
- Brier score
- Balanced accuracy
- F1

raporlanır.

Ek üretim tanıları:

- `ml_downside_confusion_matrix.csv`: 0.50 olasılık eşiğinde TN, FP, FN, TP,
  precision, recall ve specificity.
- `ml_downside_drift_report.csv`: Tahmin olasılığı dağılımı için ilk yarı/ikinci
  yarı KS testi ve PSI drift tanısı.
- `ml_downside_risk_feature_importance.csv`: Standardize edilmiş lojistik model
  katsayılarına göre göreli özellik yönü ve büyüklüğü.

## Kullanım

Uygun kullanım: risk komitesi veya araştırmacının “piyasa koşulları son dönemde
downside event açısından uyarı veriyor mu?” sorusuna yardımcı tanı üretmesi.

Uygun olmayan kullanım: doğrudan hisse/ETF/kripto al-sat sinyali üretmek, kaldıraç
kararı vermek, kişisel yatırım tavsiyesi oluşturmak.

## Sınırlılıklar

- Finansal downside event'ler nadirdir; PR-AUC ve Brier score özellikle önemlidir.
- Public veri kaynağı nedeniyle veri revizyonu ve sağlayıcı hatası mümkündür.
- Model doğrusal bir sınıflandırıcıdır; karmaşık nedensel ilişki iddiası taşımaz.
- Geçmişte ölçülen sinyal gelecekte aynı gücü göstermek zorunda değildir.

## İzleme

Her pipeline çalıştırmasında `ml_downside_risk_metrics.csv`, tahmin tablosu,
feature importance, confusion matrix, drift raporu ve kalibrasyon figürü kontrol
edilmelidir. PR-AUC baseline'a yakınsa model sadece zayıf tanı olarak okunmalıdır.
PSI yüksek veya KS testi anlamlıysa model çıktısı "dağılım kayması incelemesi
gerekir" notuyla kullanılmalıdır.
