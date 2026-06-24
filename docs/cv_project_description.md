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
- TimeSeriesSplit ile downside-risk ML tanısı.
- Config-driven pipeline, pytest, Dockerfile, GitHub Actions ve resmi PDF rapor.

Finansal metodoloji açısından statik optimizasyon çıktısını tek başına karar
kanıtı kabul etmedim; walk-forward sonuçları, risk metrikleri ve model tanı farkı
ile birlikte değerlendirdim.
