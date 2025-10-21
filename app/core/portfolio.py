from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np

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
    diversification_index: float
    sector_allocations: Dict[str, float]
    scenarios: List["StressScenarioResult"]


@dataclass(slots=True)
class StressScenarioResult:
    name: str
    expected_return: float
    volatility: float
    value_at_risk: float
    notes: List[str]


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
        return PortfolioPlan(
            suggestions=[],
            expected_return=0.0,
            volatility_proxy=0.0,
            diversification_index=0.0,
            sector_allocations={},
            scenarios=[],
        )

    raw_weights = [max(_raw_weight(score, data), 0.0) for score, data in scored]
    total = sum(raw_weights)
    if total <= 0:
        total = len(raw_weights)
        raw_weights = [1.0 for _ in raw_weights]

    normalized_weights = [weight / total for weight in raw_weights]

    suggestions: List[PositionSuggestion] = []
    expected_return = 0.0
    volatility_proxy = 0.0
    sector_totals: Dict[str, float] = {}
    for (score, data), weight in zip(scored, normalized_weights):
        notes: List[str] = []
        if data.risk.avg_daily_dollar_volume < 2e7:
            notes.append("Thin liquidity — size carefully")
        if data.risk.drawdown_1y > 0.35:
            notes.append("High recent drawdown")
        if data.risk.beta > 1.3:
            notes.append("Elevated beta vs. market")

        sector_name = data.sector or data.metadata.get("sector") if data.metadata else None
        if not sector_name:
            sector_name = "Unclassified"
        sector_totals[sector_name] = sector_totals.get(sector_name, 0.0) + weight

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

    diversification_index = 1 - float(sum(weight ** 2 for weight in normalized_weights))

    scenarios = _simulate_scenarios(scored, normalized_weights)

    return PortfolioPlan(
        suggestions=suggestions,
        expected_return=expected_return,
        volatility_proxy=volatility_proxy,
        diversification_index=diversification_index,
        sector_allocations=sector_totals,
        scenarios=scenarios,
    )


def _simulate_scenarios(
    scored: List[tuple[ScoreBreakdown, CompanyIndicators]], weights: List[float]
) -> List[StressScenarioResult]:
    if not scored:
        return []
    rng = np.random.default_rng(42)
    weights_arr = np.array(weights)
    factor_returns = np.array([max(score.growth + score.catalysts, 0.0) for score, _ in scored])
    volatilities = np.array([max(data.risk.volatility_3y, 0.05) for _, data in scored])

    scenarios: List[StressScenarioResult] = []

    def run(label: str, return_shift: float, vol_multiplier: float, notes: List[str]) -> StressScenarioResult:
        mean = factor_returns * return_shift
        sigma = volatilities * vol_multiplier
        draws = rng.normal(loc=mean, scale=sigma, size=(2000, len(scored)))
        portfolio_paths = draws @ weights_arr
        expected = float(np.mean(portfolio_paths))
        volatility = float(np.std(portfolio_paths))
        var = float(np.percentile(portfolio_paths, 5))
        return StressScenarioResult(
            name=label,
            expected_return=expected,
            volatility=volatility,
            value_at_risk=var,
            notes=notes,
        )

    scenarios.append(
        run(
            "Base case",
            return_shift=1.0,
            vol_multiplier=1.0,
            notes=["Assumes current growth cadence persists."],
        )
    )
    scenarios.append(
        run(
            "Growth slowdown",
            return_shift=0.6,
            vol_multiplier=1.2,
            notes=["Moderates upside while volatility expands modestly."],
        )
    )
    scenarios.append(
        run(
            "Hyper-growth",
            return_shift=1.4,
            vol_multiplier=0.9,
            notes=["Captures upside if catalysts compound faster than modeled."],
        )
    )
    return scenarios
