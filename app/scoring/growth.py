from __future__ import annotations

from .utils import weighted_average, smooth_step
from app.core.metrics import GrowthMetrics, clamp


def score_growth(metrics: GrowthMetrics) -> float:
    """Score a company on long-horizon fundamental growth momentum."""

    components = {
        "revenue_cagr": smooth_step(metrics.revenue_cagr_3y, lower=0.08, upper=0.35),
        "revenue_acceleration": smooth_step(metrics.revenue_acceleration, lower=0.0, upper=0.12),
        "ebit_margin_trend": smooth_step(metrics.ebit_margin_trend, lower=0.0, upper=0.08),
        "fcf_margin": smooth_step(metrics.fcf_margin, lower=0.05, upper=0.2),
        "backlog_growth": smooth_step(metrics.backlog_growth or 0.0, lower=0.0, upper=0.25),
    }
    weights = {
        "revenue_cagr": 0.32,
        "revenue_acceleration": 0.22,
        "ebit_margin_trend": 0.18,
        "fcf_margin": 0.18,
        "backlog_growth": 0.10,
    }
    return clamp(weighted_average(components, weights))
