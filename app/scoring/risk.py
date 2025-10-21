from __future__ import annotations

from .utils import weighted_average, smooth_step, inverse_smooth_step
from app.core.metrics import RiskMetrics, clamp


def score_risk(metrics: RiskMetrics) -> float:
    components = {
        "market_cap": smooth_step(metrics.market_cap, lower=3e8, upper=1e10),
        "liquidity": smooth_step(metrics.avg_daily_dollar_volume, lower=5e6, upper=5e7),
        "beta": inverse_smooth_step(metrics.beta, lower=0.8, upper=1.6),
        "volatility": inverse_smooth_step(metrics.volatility_3y, lower=0.2, upper=0.6),
        "drawdown": inverse_smooth_step(metrics.drawdown_1y, lower=0.15, upper=0.45),
    }
    weights = {
        "market_cap": 0.25,
        "liquidity": 0.25,
        "beta": 0.2,
        "volatility": 0.2,
        "drawdown": 0.1,
    }
    return clamp(weighted_average(components, weights))
