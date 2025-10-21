from __future__ import annotations

from .utils import weighted_average, smooth_step, inverse_smooth_step
from app.core.metrics import QualityMetrics, clamp


def score_quality(metrics: QualityMetrics) -> float:
    components = {
        "roic": smooth_step(metrics.roic, lower=0.08, upper=0.25),
        "roic_trend": smooth_step(metrics.roic_trend, lower=0.0, upper=0.06),
        "leverage": inverse_smooth_step(metrics.net_debt_to_ebitda, lower=0.0, upper=2.5),
        "coverage": smooth_step(metrics.interest_coverage, lower=4.0, upper=15.0),
        "asset_turnover": smooth_step(metrics.asset_turnover_trend, lower=0.0, upper=0.15),
    }
    weights = {
        "roic": 0.3,
        "roic_trend": 0.2,
        "leverage": 0.2,
        "coverage": 0.2,
        "asset_turnover": 0.1,
    }
    return clamp(weighted_average(components, weights))
