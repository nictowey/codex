from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import pandas as pd

from .metrics import ScoreBreakdown, WeightConfig
from app.core.backtesting import BacktestResult


@dataclass(slots=True)
class WeightOptimization:
    recommended: WeightConfig
    factor_correlations: Dict[str, float]


def recommend_weights(
    scores: Iterable[ScoreBreakdown],
    backtests: Iterable[BacktestResult],
) -> Optional[WeightOptimization]:
    scores_list = list(scores)
    tests_list = list(backtests)
    if not scores_list or not tests_list:
        return None

    score_df = pd.DataFrame(
        [
            {
                "ticker": score.ticker,
                "growth": score.growth,
                "quality": score.quality,
                "catalysts": score.catalysts,
                "valuation": score.valuation,
                "risk": score.risk,
            }
            for score in scores_list
        ]
    )
    backtest_df = pd.DataFrame(
        [
            {
                "ticker": result.ticker,
                "cagr": result.cagr,
            }
            for result in tests_list
        ]
    )

    merged = score_df.merge(backtest_df, on="ticker", how="inner")
    if merged.empty or merged["cagr"].abs().sum() == 0:
        return None

    correlations: Dict[str, float] = {}
    weights: Dict[str, float] = {}
    for factor in ("growth", "quality", "catalysts", "valuation", "risk"):
        corr = merged[factor].corr(merged["cagr"])
        if pd.isna(corr):
            corr = 0.0
        correlations[factor] = float(corr)
        weights[factor] = max(corr, 0.0)

    proposed = WeightConfig(
        growth=weights["growth"],
        quality=weights["quality"],
        catalysts=weights["catalysts"],
        valuation=weights["valuation"],
        risk=weights["risk"],
    ).normalized()

    return WeightOptimization(recommended=proposed, factor_correlations=correlations)
