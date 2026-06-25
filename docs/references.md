# QuantVerse Methodology References

Tarih: 2026-06-25

Bu doküman, QuantVerse içinde kullanılan yöntem ailelerinin literatürdeki temel
dayanaklarını listeler. Canlı akademik yayın, tez veya makale teslimi öncesinde
sayfa, cilt, DOI ve baskı bilgileri ayrıca doğrulanmalıdır.

## Methodology References To Verify Before Publication

| Yöntem Ailesi | Referans Niteliği | QuantVerse İçindeki Rol |
|---|---|---|
| Mean-Variance Optimization | Markowitz, H. Portfolio Selection, Journal of Finance, 1952. | Portföy beklenen getiri-varyans dengesinin temel çerçevesi. |
| Sharpe Ratio | Sharpe, W. F. Mutual Fund Performance, 1966; The Sharpe Ratio, 1994. | Risk-adjusted performans karşılaştırması. |
| Ledoit-Wolf Shrinkage | Ledoit, O. ve Wolf, M. A well-conditioned estimator for large-dimensional covariance matrices, 2004. | Gürültülü kovaryans matrisini stabilize etmek. |
| HRP | López de Prado, M. Building Diversified Portfolios that Outperform Out-of-Sample, 2016. | Hiyerarşik korelasyon yapısıyla portföy ağırlığı üretmek. |
| VaR | Jorion, P. Value at Risk literatürü; Basel market risk çerçevesi. | Kayıp eşiği ve piyasa riski raporlaması. |
| CVaR / Expected Shortfall | Rockafellar ve Uryasev expected shortfall/CVaR optimizasyon literatürü. | Kuyruk kaybı büyüklüğünü VaR ötesinde ölçmek. |
| Kupiec POF | Kupiec, P. Techniques for Verifying the Accuracy of Risk Measurement Models, 1995. | VaR exception sayısının beklenen ihlal frekansına yakınlığını test etmek. |
| Christoffersen Independence | Christoffersen, P. Evaluating Interval Forecasts, 1998. | VaR ihlallerinin kümelenip kümelenmediğini test etmek. |
| Moving-Block Bootstrap | Künsch ve Lahiri çizgisindeki block bootstrap zaman serisi literatürü. | Zaman bağımlılığını tamamen bozmadan Sharpe/CAGR belirsizliği üretmek. |
| Walk-Forward Validation | Finansal backtesting ve out-of-sample validation literatürü. | Look-ahead bias riskini azaltmak ve statik sonucu tanı katmanında tutmak. |

## Kullanım Sınırı

Bu referans listesi, yöntemlerin akademik kökenini gösterir. Listelenen bir yöntemin
literatürde bulunması, QuantVerse çıktılarının gelecekteki piyasayı doğru tahmin
edeceği anlamına gelmez. Her yöntem veri kalitesi, örneklem dönemi, işlem maliyeti,
likidite ve model varsayımı sınırları içinde okunmalıdır.
