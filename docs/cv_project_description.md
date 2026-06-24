# CV Proje Açıklaması

## QuantVerse - Multi-Asset Quantitative Portfolio Analytics

Python tabanlı çok varlıklı quantitative finance araştırma sistemi geliştirdim.
Sistem ETF, kripto, emtia, tahvil ve REIT evrenini yatırım yapılabilirlik ilkesine
göre temizler; VIX, faiz ve DXY gibi serileri portföy ağırlığı alamayan sinyal
verisi olarak ayırır.

Başlıca teknikler:

- Pandas, NumPy, SciPy, scikit-learn, statsmodels, yfinance, ReportLab.
- Ledoit-Wolf kovaryans shrinkage.
- Mean-Variance, HRP, Risk Parity, Inverse Volatility ve Minimum CVaR portföyleri.
- Maliyet dahil walk-forward backtest.
- VaR/CVaR, drawdown, Calmar, Ulcer Index ve çeşitlendirme metrikleri.
- VaR exception testing, stres senaryosu, benchmark comparison, transaction-cost
  sensitivity ve moving-block bootstrap sağlamlık analizi.
- TimeSeriesSplit ile downside-risk ML tanısı.
- ML confusion matrix, drift raporu ve feature importance.
- Config-driven pipeline, pytest, Dockerfile, GitHub Actions, statik HTML ve resmi PDF rapor.

Finansal metodoloji açısından statik optimizasyon çıktısını tek başına karar
kanıtı kabul etmedim; walk-forward sonuçları, risk metrikleri ve model tanı farkı
ile birlikte değerlendirdim. Sonuçları kişisel yatırım tavsiyesi değil, araştırma
ve karar destek çıktısı olarak konumlandırdım.
