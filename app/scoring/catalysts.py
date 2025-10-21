from __future__ import annotations

from .utils import weighted_average, smooth_step
from app.core.metrics import CatalystMetrics, clamp


def score_catalysts(metrics: CatalystMetrics) -> float:
    components = {
        "theme": smooth_step(metrics.theme_alignment, lower=0.2, upper=0.9),
        "earnings": smooth_step(metrics.earnings_revision_trend, lower=0.0, upper=0.25),
        "insider": smooth_step(metrics.insider_activity_score, lower=0.0, upper=0.7),
        "strategic": smooth_step((metrics.strategic_investor_presence or 0.0), lower=0.0, upper=0.5),
    }
    weights = {
        "theme": 0.35,
        "earnings": 0.3,
        "insider": 0.2,
        "strategic": 0.15,
    }
    return clamp(weighted_average(components, weights))
