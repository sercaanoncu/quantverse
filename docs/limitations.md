# QuantVerse Sınırlılıklar

Tarih: 2026-06-24

## Yatırım Tavsiyesi Değildir

QuantVerse çıktıları kişisel yatırım tavsiyesi, getiri vaadi veya kesin al-sat
talimatı değildir. Kullanıcının risk profili, yatırım ufku, vergi durumu, likidite
ihtiyacı ve uygunluk değerlendirmesi ayrıca yapılmalıdır.

## Veri Sınırı

Veri kaynağı public yfinance'tır. Bu kaynak araştırma ve prototip için uygundur;
kurumsal yatırım kararı için Bloomberg, Refinitiv, ICE, FactSet veya benzeri
bağımsız sağlayıcıyla mutabakat gerekir.

## Model Sınırı

Geçmiş veride iyi çalışan bir portföy gelecekte iyi çalışmak zorunda değildir.
Beklenen getiri tahmini finansal zaman serilerinde yüksek hata içerir. Bu nedenle
pipeline statik sonucu değil walk-forward tanıyı önceliklendirir.

## Backtest Sınırı

Backtest gerçek emir defteri, piyasa etkisi, vergi, fon kapanması, short borrow,
limit emir davranışı ve kriz dönemindeki likidite kurumasını tam modellemez.

## ML Sınırı

Downside-risk modeli tanısaldır. Modelin ROC-AUC veya PR-AUC değerleri zayıfsa bu
durum modelin sınırlı bilgi taşıdığı anlamına gelir; sonuç saklanmaz.

## Git Sınırı

Mevcut yerel çalışma ağacında `.git` klasörü bozuk görünmektedir. GitHub'a sunum
için temiz bir repository başlatılmalı veya gerçek uzak repo yeniden clone edilip
bu dosyalar oraya taşınmalıdır.
