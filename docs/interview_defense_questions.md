# QuantVerse Savunma Soruları ve Cevapları

Tarih: 2026-06-24

## 1. Proje tek cümlede ne yapıyor?

QuantVerse, çok varlıklı piyasa verisini temizleyip portföy ağırlıkları, walk-forward
performans, piyasa riski, ML downside-risk tanısı ve resmi rapor üreten araştırma
amaçlı bir quantitative finance karar destek sistemidir.

## 2. Bu proje yatırım tavsiyesi mi?

Hayır. Proje geçmiş veriye dayalı araştırma ve risk tanısı üretir. Kişisel risk
profili, vergi, likidite, yatırım ufku ve uygunluk değerlendirmesi olmadan al-sat
talimatı vermez.

## 3. Neden düşük getirili varlıkları otomatik silmediniz?

Düşük geçmiş getiri, gelecekte düşük getiri olacağını ispatlamaz. Bu nedenle varlık
dışlama gerekçesi getiri değil, veri kalitesi ve kapsama yeterliliğidir.

## 4. VIX, faiz ve DXY neden portföy ağırlığı almıyor?

Bu seriler yatırım yapılabilir ETF gibi doğrudan portföy enstrümanı değildir; piyasa
bağlamı ve risk-free proxy için sinyal olarak kullanılır. Sinyalin portföy varlığı
gibi ağırlık alması metodolojik hata olurdu.

## 5. Statik optimizasyon neden ana karar değil?

Statik optimizasyon aynı veride hem öğrenir hem değerlendirilirse geçmişe aşırı
uyum riski doğar. Bu nedenle ana karar katmanı walk-forward sonuç, drawdown, maliyet
ve model diagnostics farkıdır.

## 6. Neden Ledoit-Wolf kovaryans kullandınız?

Finansal zaman serilerinde örnek kovaryans gürültülü ve kararsız olabilir. Ledoit-Wolf
shrinkage, kovaryans matrisini daha iyi koşullu hale getirerek optimizasyonun uç
ağırlıklara savrulmasını azaltır.

## 7. VaR ve CVaR neyi ölçüyor?

VaR belirli güven seviyesinde kayıp eşiğini, CVaR ise bu eşiğin ötesindeki ortalama
kaybı ölçer. CVaR, kuyruk kaybının büyüklüğünü gösterdiği için tek başına VaR'dan
daha açıklayıcıdır.

## 8. VaR exception testing neden eklendi?

VaR eşiği çizmek tek başına yeterli değildir. Exception testing, gerçekleşen ihlal
sayısının beklenen ihlal sayısına yakın olup olmadığını ve ihlallerin kümelenip
kümelenmediğini test eder.

## 9. Stres senaryoları tarihsel krizleri birebir mi tekrar ediyor?

Hayır. Bu sprintteki stresler stilize varlık sınıfı şoklarıdır. Amaç krizi birebir
yeniden oynatmak değil, portföylerin COVID benzeri risk-off, faiz şoku, USD şoku
ve kripto çöküşü gibi sınıf bazlı şoklara hassasiyetini görmektir.

## 10. Benchmark comparison neden gerekli?

Karmaşık modelin değeri basit benchmark'a karşı ölçülmezse modelin gerçekten bilgi
ekleyip eklemediği anlaşılamaz. Equal Weight ve iç 60/40 proxy bu nedenle korunur.

## 11. Transaction-cost sensitivity neyi gösteriyor?

Sonucun yalnızca düşük işlem maliyeti varsayımı altında mı ayakta kaldığını test
eder. 0, 5, 10 ve 25 baz puan maliyet seviyelerinde CAGR, Sharpe ve drawdown yeniden
hesaplanır.

## 12. Bootstrap güven aralığı neyi kanıtlar?

Geleceği kanıtlamaz. Moving-block bootstrap, gözlenen CAGR ve Sharpe değerlerinin
örneklem oynaklığına ne kadar duyarlı olduğunu gösterir ve zaman serisi bağımlılığını
tamamen yok etmemek için blok yapısı kullanır.

## 13. ML modeli neden zayıf olsa bile raporlanıyor?

Model bir al-sat sinyali değil, downside-risk tanısıdır. PR-AUC baseline'a yakınsa
bu zayıflık saklanmaz; raporda modelin sınırlı bilgi taşıdığı açıkça belirtilir.

## 14. Proje yüksek lisans sunumu için yeterli mi, kurumsal canlı yatırım için yeterli mi?

Yüksek lisans sunumu için savunulabilir düzeydedir; çünkü veri kalitesi, portföy
ağırlıkları, walk-forward kanıt, risk, stres, maliyet, bootstrap, ML tanı ve rapor
izlenebilir biçimde üretilir. Kurumsal canlı yatırım için yeterli değildir; bağımsız
veri mutabakatı, model approval, limit yönetimi, execution ölçümü ve canlı izleme
gerekir.
