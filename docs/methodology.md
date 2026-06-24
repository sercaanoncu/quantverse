# QuantVerse Metodoloji Notu

Tarih: 2026-06-24

## 1. Temel Matematik

Bir portföy, varlık ağırlıklarının toplamıdır. Ağırlıkların toplamı 1 olmalıdır.
Örneğin 0,25 + 0,25 + 0,50 = 1 ise sermayenin yüzde 25'i birinci varlığa,
yüzde 25'i ikinci varlığa ve yüzde 50'si üçüncü varlığa ayrılmıştır.

Günlük basit getiri:

```text
R_t = P_t / P_{t-1} - 1
```

Burada `P_t` bugünkü fiyat, `P_{t-1}` önceki iş günü fiyatıdır. Getiri pozitifse
değer artmış, negatifse değer azalmıştır.

## 2. Veri Takvimi

ETF'ler hafta sonu işlem görmezken kripto varlıklar işlem görebilir. Üretim
pipeline'ı iş günü takvimi kullanır. Bu nedenle hafta sonu kripto hareketleri
pazartesi getirisine yansır. Bu tercih, 252 iş günü yıllıklaştırmasıyla tutarlıdır
ve veri frekansının aynı portföy matrisinde karşılaştırılmasını sağlar.

## 3. Beklenen Getiri

Tarihsel ortalama getiri gürültülüdür. Az sayıda aşırı iyi gün, geleceğe ilişkin
beklentiyi olduğundan yüksek gösterebilir. Bu nedenle üretim pipeline'ı ham yıllık
ortalamayı kesitsel medyana doğru shrink eder:

```text
mu_production = (1 - lambda) * mu_historical + lambda * median(mu_historical)
```

Bu işlem düşük getirili varlıkları otomatik olarak silmez. Sadece tahmin hatasının
optimizasyonu aşırı uç portföylere itmesini azaltır.

## 4. Kovaryans

Portföy riski yalnızca tek varlık volatilitesi değildir; varlıkların birlikte
hareket etme derecesi de önemlidir. Üretim pipeline'ında Ledoit-Wolf shrinkage
kovaryansı kullanılır. Gerekçe, yüksek boyutlu ve gürültülü finansal veride örnek
kovaryans matrisinin kararsızlaşabilmesidir.

## 5. Portföy Modelleri

- Equal Weight: Basit ve denetlenebilir karşılaştırma ölçütüdür.
- Minimum Variance: Beklenen getiriye güvenmeden varyansı azaltmayı hedefler.
- Maximum Sharpe: Beklenen getiri ve kovaryans tahminine duyarlıdır; bu nedenle
  walk-forward doğrulama olmadan ana karar sayılmaz.
- HRP: Hiyerarşik korelasyon yapısını kullanır ve kovaryans tersleme hatasına daha
  az bağımlı olabilir.
- Risk Parity: Toplam riske katkıyı dengelemeyi hedefler.
- Inverse Volatility: Daha düşük volatiliteye daha yüksek ağırlık verir; basit
  risk tabanlı benchmark olarak tutulur.
- Minimum CVaR: Kötü kuyruk günlerindeki ortalama kaybı azaltmayı hedefler.

## 6. Walk-Forward Doğrulama

Her rebalancing tarihinde model yalnızca o tarihe kadar bilinen veriyi kullanır.
Sonraki dönem getirisi out-of-sample kabul edilir. Bu yapı, geleceği yanlışlıkla
eğitim verisine sokmayı engeller.

Statik optimizasyon sonucu eğitim dönemi tanısıdır. Karar katmanı walk-forward
Sharpe, drawdown, işlem maliyeti ve tanı farkı üzerinden okunur.

## 7. Risk Ölçümü

VaR, belirli güven seviyesinde beklenen eşiği; CVaR ise bu eşiğin ötesindeki ortalama
kaybı ölçer. Günlük VaR/CVaR kısa vadeli kayıp büyüklüğünü gösterir. Yıllık tarihsel
VaR/CVaR ise günlük kaybı mekanik olarak `sqrt(252)` ile büyütmek yerine 252 günlük
bileşik gerçekleşmiş getirilerden empirik hesaplanır.

## 8. Hardening ve Sağlamlık Testleri

VaR exception testing, modelin yüzde 5 kuyruk eşiği çizdiği günlerde gerçekleşen
ihlal oranının gerçekten yaklaşık yüzde 5'e yakın olup olmadığını kontrol eder.
Kupiec testi ihlal sayısına, Christoffersen testi ihlallerin kümelenip
kümelenmediğine bakar.

Stres senaryoları, "geçmiş ortalama iyi" sonucunun ani piyasa şokunda ne kadar
kırılgan olduğunu gösterir. Benchmark comparison, karmaşık optimizasyonun basit
bir karşılaştırma ölçütüne göre değer ekleyip eklemediğini denetler. Transaction
cost sensitivity, performansın işlem maliyeti varsayımına ne kadar bağımlı
olduğunu gösterir. Moving-block bootstrap, finansal zaman serilerinde ardışık
bağımlılığı tamamen bozmadan Sharpe ve CAGR için örneklem belirsizliği üretir.

## 9. ML Downside-Risk Tanısı

ML modülü getiri tahmini iddiası taşımaz. Amaç, son piyasa durumunun bir sonraki
gün downside event olasılığı hakkında bilgi taşıyıp taşımadığını time-series split
ile test etmektir. Kullanılan hedef, bir sonraki gün eşit ağırlıklı portföy
getirisinin geçmiş pencereye göre alt yüzde 10'luk eşik altında kalmasıdır.

Metrikler:

- ROC-AUC: Olay ve olay olmayan günleri sıralama gücü.
- PR-AUC: Nadir olaylarda pozitif sınıf yakalama kalitesi.
- Brier: Olasılık kalibrasyon hatası.
- F1: Pozitif sınıf yakalama dengesi.

## 10. Kullanılmayan veya Sınırlandırılan Yöntemler

Black-Litterman ana üretimden çıkarılmıştır. Gerekçe: bu modelin bilimsel biçimde
kullanılması için tarihli, kaynaklandırılmış, büyüklüğü ve güven düzeyi belirtilmiş
views gerekir. Bu bilgiler yoksa çıktı, kanıt değil varsayım olur.

XGBoost ve LightGBM çekirdek bağımlılık değildir. Gerekçe: üretim pipeline'ında bu
modellerle eğitilmiş, validasyonu yapılmış ve raporlanan bir tahmin sistemi yoksa
bağımlılık taşımak projeyi olduğundan fazla gösterir.

## 11. Nihai Okuma

QuantVerse çıktıları yatırım kararını otomatikleştirmez. Bilimsel okuma sırası:

1. Veri son tarihini ve data quality tablosunu kontrol et.
2. Risk-free kaynağını ve sinyal ayrımını kontrol et.
3. Statik portföyleri sadece eğitim dönemi tanısı olarak oku.
4. Walk-forward tabloyu ve model diagnostics farkını önceliklendir.
5. VaR exception, stres, benchmark, maliyet duyarlılığı ve bootstrap tablolarını
   birlikte değerlendir.
6. Risk ölçülerini, drawdown'u ve maliyetleri birlikte değerlendir.
7. Kişisel risk profili, vergi, likidite ve uygunluk değerlendirmesini ayrıca yap.
