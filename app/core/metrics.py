from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional, Type


@dataclass(slots=True)
class GrowthMetrics:
    """Key indicators for long-horizon fundamental growth momentum."""

    revenue_cagr_3y: float
    revenue_acceleration: float
    ebit_margin_trend: float
    fcf_margin: float
    backlog_growth: Optional[float]


@dataclass(slots=True)
class QualityMetrics:
    """Operational quality, efficiency, and balance-sheet health."""

    roic: float
    roic_trend: float
    net_debt_to_ebitda: float
    interest_coverage: float
    asset_turnover_trend: float


@dataclass(slots=True)
class CatalystMetrics:
    """Narrative and sentiment catalysts supporting upside."""

    theme_alignment: float
    earnings_revision_trend: float
    insider_activity_score: float
    strategic_investor_presence: Optional[float]


@dataclass(slots=True)
class ValuationMetrics:
    """Valuation sanity checks relative to growth prospects."""

    peg_ratio: float
    ev_to_ebitda_vs_peers: float
    free_cash_flow_yield: float
    price_momentum: float
    consolidation_score: float


@dataclass(slots=True)
class RiskMetrics:
    """Guardrails ensuring candidates remain investable."""

    market_cap: float
    avg_daily_dollar_volume: float
    beta: float
    volatility_3y: float
    drawdown_1y: float


@dataclass(slots=True)
class CompanyIndicators:
    """Full set of indicators used by the scoring engine."""

    ticker: str
    name: str
    growth: GrowthMetrics
    quality: QualityMetrics
    catalysts: CatalystMetrics
    valuation: ValuationMetrics
    risk: RiskMetrics

    def to_dict(self) -> Dict[str, object]:
        """Serialize indicators so they can be cached on disk."""

        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "CompanyIndicators":
        """Recreate a :class:`CompanyIndicators` instance from cached data."""

        return cls(
            ticker=str(payload["ticker"]),
            name=str(payload["name"]),
            growth=GrowthMetrics(**payload["growth"]),
            quality=QualityMetrics(**payload["quality"]),
            catalysts=CatalystMetrics(**payload["catalysts"]),
            valuation=ValuationMetrics(**payload["valuation"]),
            risk=RiskMetrics(**payload["risk"]),
        )


@dataclass(slots=True)
class WeightConfig:
    """Configurable factor weights for composite scoring."""

    growth: float = 0.32
    quality: float = 0.22
    catalysts: float = 0.18
    valuation: float = 0.18
    risk: float = 0.10

    def normalized(self) -> "WeightConfig":
        total = self.growth + self.quality + self.catalysts + self.valuation + self.risk
        if total <= 0:
            # Fallback to evenly distributed weights when the user zeroes everything.
            equal_weight = 1 / 5
            return WeightConfig(
                growth=equal_weight,
                quality=equal_weight,
                catalysts=equal_weight,
                valuation=equal_weight,
                risk=equal_weight,
            )
        scale = 1 / total
        return WeightConfig(
            growth=self.growth * scale,
            quality=self.quality * scale,
            catalysts=self.catalysts * scale,
            valuation=self.valuation * scale,
            risk=self.risk * scale,
        )

    def to_dict(self) -> Dict[str, float]:
        normalized = self.normalized()
        return {
            "growth": normalized.growth,
            "quality": normalized.quality,
            "catalysts": normalized.catalysts,
            "valuation": normalized.valuation,
            "risk": normalized.risk,
        }

    @classmethod
    def from_dict(cls: Type["WeightConfig"], payload: Dict[str, float]) -> "WeightConfig":
        return cls(
            growth=float(payload.get("growth", cls().growth)),
            quality=float(payload.get("quality", cls().quality)),
            catalysts=float(payload.get("catalysts", cls().catalysts)),
            valuation=float(payload.get("valuation", cls().valuation)),
            risk=float(payload.get("risk", cls().risk)),
        )


@dataclass(slots=True)
class ScoreBreakdown:
    ticker: str
    name: str
    growth: float
    quality: float
    catalysts: float
    valuation: float
    risk: float
    weights: Optional[WeightConfig] = None

    @property
    def composite(self) -> float:
        """Weighted composite score."""

        weights = (self.weights or WeightConfig()).normalized().to_dict()
        return (
            self.growth * weights["growth"]
            + self.quality * weights["quality"]
            + self.catalysts * weights["catalysts"]
            + self.valuation * weights["valuation"]
            + self.risk * weights["risk"]
        )

    def to_dict(self) -> Dict[str, float]:
        data = {
            "ticker": self.ticker,
            "name": self.name,
            "growth": self.growth,
            "quality": self.quality,
            "catalysts": self.catalysts,
            "valuation": self.valuation,
            "risk": self.risk,
            "composite": self.composite,
        }
        if self.weights is not None:
            data["weights"] = self.weights.to_dict()
        return data


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Ensure a score stays within the 0–1 range."""

    return max(min_value, min(max_value, value))
