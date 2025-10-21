from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from .metrics import CompanyIndicators, ScoreBreakdown


@dataclass(slots=True)
class PositionSuggestion:
    ticker: str
    name: str
    weight: float
    composite: float
    notes: List[str]


@dataclass(slots=True)
class PortfolioPlan:
    suggestions: List[PositionSuggestion]
    expected_return: float
    volatility_proxy: float


def _raw_weight(score: ScoreBreakdown, indicators: CompanyIndicators) -> float:
    risk = indicators.risk
    liquidity_penalty = 1.0
    if risk.avg_daily_dollar_volume < 1e7:
        liquidity_penalty *= 0.7
    if risk.market_cap < 1e9:
        liquidity_penalty *= 0.5
    volatility_penalty = max(risk.volatility_3y, 0.15)
    return max(score.composite, 0.0) * liquidity_penalty / volatility_penalty


def build_portfolio_plan(
    scores: Iterable[ScoreBreakdown],
    indicators: Dict[str, CompanyIndicators],
) -> PortfolioPlan:
    scored = [(score, indicators[score.ticker]) for score in scores if score.ticker in indicators]
    if not scored:
        return PortfolioPlan(suggestions=[], expected_return=0.0, volatility_proxy=0.0)

    raw_weights = [max(_raw_weight(score, data), 0.0) for score, data in scored]
    total = sum(raw_weights)
    if total <= 0:
        total = len(raw_weights)
        raw_weights = [1.0 for _ in raw_weights]

    normalized_weights = [weight / total for weight in raw_weights]

    suggestions: List[PositionSuggestion] = []
    expected_return = 0.0
    volatility_proxy = 0.0
    for (score, data), weight in zip(scored, normalized_weights):
        notes: List[str] = []
        if data.risk.avg_daily_dollar_volume < 2e7:
            notes.append("Thin liquidity — size carefully")
        if data.risk.drawdown_1y > 0.35:
            notes.append("High recent drawdown")
        if data.risk.beta > 1.3:
            notes.append("Elevated beta vs. market")

        suggestions.append(
            PositionSuggestion(
                ticker=score.ticker,
                name=score.name,
                weight=weight,
                composite=score.composite,
                notes=notes,
            )
        )
        expected_return += weight * (score.growth + score.catalysts)
        volatility_proxy += weight * data.risk.volatility_3y

    return PortfolioPlan(
        suggestions=suggestions,
        expected_return=expected_return,
        volatility_proxy=volatility_proxy,
    )
