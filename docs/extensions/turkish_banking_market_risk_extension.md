# Turkish Banking Market-Risk Extension Design

Tarih: 2026-06-25

## Amaç

Bu doküman, QuantVerse'in Türkiye bankacılık ve piyasa riski analitiğine nasıl
genişletilebileceğini tasarlar. Bu uzantı mevcut doğrulanmış pipeline'ın parçası
değildir; üretime alınmadan önce ayrı veri mutabakatı, test ve model validasyon
süreci gerekir.

## Potansiyel Veri Kaynakları

| Veri Ailesi | Örnek Kaynak | Kullanım Amacı |
|---|---|---|
| TCMB EVDS | Politika faizi, DİBS faizleri, enflasyon, kur sepeti. | TRY faiz rejimi, makro risk ve iskonto oranı bağlamı. |
| BIST / XBANK | Banka endeksi, BIST 100, sektör getirileri. | Türkiye hisse ve banka beta analizi. |
| USDTRY / EURTRY | Kur serileri. | Kur şoku, açık pozisyon ve makro stres. |
| TRY rates | Kısa/uzun vadeli TL faiz eğrisi. | Duration, faiz şoku ve sermaye maliyeti. |
| CDS proxy | Türkiye 5Y CDS veya erişilebilir proxy. | Ülke risk primi ve risk-off rejimi. |
| Enflasyon | TÜFE/ÜFE gerçekleşmeleri ve beklentileri. | Reel getiri, faiz-enflasyon ayrışması ve makro stres. |

## Sisteme Katacağı Analitik Değer

- Türkiye bankalarının faiz, kur, ülke riski ve enflasyon şoklarına duyarlılığı
  daha gerçekçi test edilebilir.
- XBANK ve BIST karşılaştırması, global ETF evrenine yerel piyasa bağlamı ekler.
- USDTRY ve TRY faizleri ile stilize stres senaryoları yerel risk komitesi diliyle
  yazılabilir.
- CDS proxy ve enflasyon rejimi, downside-risk ML tanısına yerel makro sinyal
  katmanı sağlayabilir.

## Üretim Öncesi Zorunlu Validasyon

1. Veri lisansı ve kullanım hakkı kontrol edilmeli.
2. Her veri serisi için kaynak, frekans, revizyon politikası ve eksik veri davranışı
   belgelenmeli.
3. TCMB EVDS, BIST ve kur verileri bağımsız sağlayıcıyla örneklem bazında
   karşılaştırılmalı.
4. Takvim uyumu belirlenmeli: BIST tatilleri, global ETF takvimi ve kripto takvimi
   ayrı ele alınmalı.
5. Stres büyüklükleri tarihsel örnekler ve risk komitesi onayıyla sabitlenmeli.
6. Backtest, look-ahead bias yaratmayacak şekilde gecikmeli makro veri kullanmalı.
7. PDF/HTML raporlarında yerel veri kaynağı ve sınırlılıkları ayrıca gösterilmeli.

## Neden Şu An Opsiyonel?

Mevcut QuantVerse pipeline'ı global çok varlıklı araştırma sistemi olarak doğrulanmıştır.
Türkiye bankacılık uzantısı yeni veri kaynakları, yeni takvim kuralları ve ayrı model
riski getirir. Doğrulanmamış konektörü doğrudan üretim pipeline'a bağlamak kaliteyi
artırmaz; aksine yanlış güven yaratır. Bu nedenle uzantı tasarım seviyesinde tutulmuş,
mevcut final skoruna dahil edilmemiştir.
