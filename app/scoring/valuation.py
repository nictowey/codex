from __future__ import annotations

from .utils import weighted_average, smooth_step, inverse_smooth_step
from app.core.metrics import ValuationMetrics, clamp


def score_valuation(metrics: ValuationMetrics) -> float:
    components = {
        "peg": inverse_smooth_step(metrics.peg_ratio, lower=0.5, upper=2.0),
        "ev_ebitda": inverse_smooth_step(metrics.ev_to_ebitda_vs_peers, lower=-2.0, upper=3.0),
        "fcf_yield": smooth_step(metrics.free_cash_flow_yield, lower=0.0, upper=0.06),
        "momentum": smooth_step(metrics.price_momentum, lower=0.0, upper=0.3),
        "consolidation": smooth_step(metrics.consolidation_score, lower=0.2, upper=0.8),
    }
    weights = {
        "peg": 0.25,
        "ev_ebitda": 0.2,
        "fcf_yield": 0.2,
        "momentum": 0.2,
        "consolidation": 0.15,
    }
    return clamp(weighted_average(components, weights))
