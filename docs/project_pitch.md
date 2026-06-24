# QuantVerse Proje Sunum Metni

QuantVerse, finansal piyasalarda portföy araştırmasını uçtan uca izlenebilir hale
getiren bir Python projesidir. Proje üç soruya cevap verir:

1. Hangi varlıklar yatırım yapılabilir, hangileri yalnızca piyasa sinyalidir?
2. Farklı portföy modelleri aynı veriyle nasıl ağırlık üretir?
3. Bu ağırlıklar geçmişte gerçekten dayanıklı mı, yoksa sadece eğitim döneminde mi iyi görünmüştür?

Sistem önce veri kalitesini kontrol eder. Sonra iş günü getirilerini üretir,
beklenen getiriyi aşırı uçlara karşı shrink eder, kovaryansı Ledoit-Wolf ile
daha kararlı hale getirir ve birden fazla portföy yaklaşımını karşılaştırır.

En kritik bölüm walk-forward doğrulamadır. Model her tarihte sadece o tarihe kadar
bilinen veriyi kullanır. Bu sayede statik optimizasyonun geçmişe aşırı uyum riski
ölçülür.

Son çıktı sadece “en iyi portföy” değildir. Çıktı; portföy bileşimleri, ağırlık
tabloları, risk ölçüleri, VaR exception testi, stres senaryosu, benchmark karşılaştırması,
maliyet duyarlılığı, bootstrap sağlamlık analizi, model tanı farkı, downside-risk
ML tanısı ve yatırım tavsiyesi olmadığı açıkça belirtilmiş resmi PDF/HTML raporudur.
