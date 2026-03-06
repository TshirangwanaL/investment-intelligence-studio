"""Portfolio analytics — volatility, correlation, concentration, drawdown."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from schemas.portfolio import PortfolioRiskMetrics, PortfolioState


class PortfolioAnalytics:
    @staticmethod
    def compute_risk_metrics(
        portfolio: PortfolioState,
        returns_df: Optional[pd.DataFrame] = None,
    ) -> PortfolioRiskMetrics:
        weights = np.array([p.weight for p in portfolio.positions])
        if weights.sum() == 0:
            return PortfolioRiskMetrics()

        sorted_w = sorted(weights, reverse=True)
        top5 = float(sum(sorted_w[:5]))
        hhi = float(np.sum(weights ** 2))

        sector_weights: dict[str, float] = {}
        for pos in portfolio.positions:
            s = pos.sector or "Unknown"
            sector_weights[s] = sector_weights.get(s, 0.0) + pos.weight

        annual_vol = 0.0
        daily_var_95 = 0.0
        max_dd = 0.0
        sharpe = 0.0
        corr_avg = 0.0

        if returns_df is not None and not returns_df.empty:
            tickers = [p.ticker for p in portfolio.positions]
            available = [t for t in tickers if t in returns_df.columns]
            if available:
                ret = returns_df[available].dropna()
                w_avail = np.array([
                    portfolio.weight_map.get(t, 0.0) for t in available
                ])
                w_sum = w_avail.sum()
                if w_sum > 0:
                    w_avail = w_avail / w_sum

                if len(ret) > 5:
                    cov = ret.cov().values
                    port_var = float(w_avail @ cov @ w_avail)
                    annual_vol = float(np.sqrt(port_var * 252))

                    port_ret = (ret.values @ w_avail)
                    daily_var_95 = float(np.percentile(port_ret, 5))

                    cum = (1 + port_ret).cumprod()
                    peak = np.maximum.accumulate(cum)
                    dd = (cum - peak) / peak
                    max_dd = float(dd.min())

                    if port_ret.std() > 0:
                        sharpe = float(
                            port_ret.mean() / port_ret.std() * np.sqrt(252)
                        )

                    corr_mat = ret.corr().values
                    n = len(available)
                    if n > 1:
                        corr_avg = float(
                            (corr_mat.sum() - n) / (n * (n - 1))
                        )

        return PortfolioRiskMetrics(
            timestamp=datetime.utcnow(),
            annual_vol=annual_vol,
            daily_var_95=daily_var_95,
            max_drawdown_proxy=max_dd,
            sharpe_proxy=sharpe,
            top5_concentration=top5,
            hhi=hhi,
            correlation_avg=corr_avg,
            sector_weights=sector_weights,
        )

    @staticmethod
    def returns_from_prices(prices_df: pd.DataFrame) -> pd.DataFrame:
        return prices_df.pct_change().dropna()
