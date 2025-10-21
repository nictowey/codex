from __future__ import annotations

from typing import Dict

from app.core.metrics import clamp


def weighted_average(values: Dict[str, float], weights: Dict[str, float]) -> float:
    numerator = sum(values[key] * weights.get(key, 0.0) for key in values)
    denominator = sum(weights.get(key, 0.0) for key in values)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def smooth_step(value: float, *, lower: float, upper: float) -> float:
    """Map a metric to a 0–1 score using a smooth transition between bounds."""

    if upper == lower:
        return clamp(1.0 if value >= upper else 0.0)
    if value <= lower:
        return 0.0
    if value >= upper:
        return 1.0
    normalized = (value - lower) / (upper - lower)
    return clamp(normalized)


def inverse_smooth_step(value: float, *, lower: float, upper: float) -> float:
    """Inverse smooth step for ratios where lower is better (e.g., leverage)."""

    if value <= lower:
        return 1.0
    if value >= upper:
        return 0.0
    normalized = 1 - (value - lower) / (upper - lower)
    return clamp(normalized)
