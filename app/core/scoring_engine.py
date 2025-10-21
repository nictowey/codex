from __future__ import annotations

from typing import Iterable, List, Optional

from .metrics import CompanyIndicators, ScoreBreakdown, WeightConfig
from app.scoring.growth import score_growth
from app.scoring.quality import score_quality
from app.scoring.catalysts import score_catalysts
from app.scoring.valuation import score_valuation
from app.scoring.risk import score_risk


def evaluate_company(
    indicators: CompanyIndicators, *, weight_config: Optional[WeightConfig] = None
) -> ScoreBreakdown:
    """Compute the detailed score breakdown for a single company."""

    return ScoreBreakdown(
        ticker=indicators.ticker,
        name=indicators.name,
        growth=score_growth(indicators.growth),
        quality=score_quality(indicators.quality),
        catalysts=score_catalysts(indicators.catalysts),
        valuation=score_valuation(indicators.valuation),
        risk=score_risk(indicators.risk),
        weights=weight_config,
    )


def rank_companies(
    indicators: Iterable[CompanyIndicators], *, weight_config: Optional[WeightConfig] = None
) -> List[ScoreBreakdown]:
    """Evaluate and rank companies by composite score."""

    scores = [evaluate_company(item, weight_config=weight_config) for item in indicators]
    return sorted(scores, key=lambda item: item.composite, reverse=True)
