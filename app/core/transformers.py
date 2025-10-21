from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .metrics import (
    CatalystMetrics,
    CompanyIndicators,
    GrowthMetrics,
    QualityMetrics,
    RiskMetrics,
    ValuationMetrics,
)


@dataclass(slots=True)
class MetricSource:
    """Raw data containers extracted from provider responses."""

    fundamentals: Dict[str, Any]
    price_history: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class IndicatorTransformer:
    """Translate provider payloads into normalized indicator objects."""

    def __init__(self, *, ticker: str, name: str | None = None) -> None:
        self.ticker = ticker.upper()
        self.name = name or ticker.upper()

    def build(self, source: MetricSource) -> CompanyIndicators:
        fundamentals = source.fundamentals
        meta = source.metadata or {}

        growth = GrowthMetrics(
            revenue_cagr_3y=self._safe_get(fundamentals, ["growth", "threeYearRevenueCagr"], default=0.0),
            revenue_acceleration=self._safe_get(fundamentals, ["growth", "revenueGrowth"], default=0.0),
            ebit_margin_trend=self._safe_get(fundamentals, ["profitability", "ebitMargin"], default=0.0),
            fcf_margin=self._safe_get(fundamentals, ["profitability", "freeCashFlowMargin"], default=0.0),
            backlog_growth=self._safe_get(fundamentals, ["operational", "backlogGrowth"], default=None),
        )

        quality = QualityMetrics(
            roic=self._safe_get(fundamentals, ["profitability", "roic"], default=0.0),
            roic_trend=self._safe_get(fundamentals, ["trend", "roic"], default=0.0),
            net_debt_to_ebitda=self._safe_get(fundamentals, ["leverage", "netDebtToEbitda"], default=3.0),
            interest_coverage=self._safe_get(fundamentals, ["leverage", "interestCoverage"], default=0.0),
            asset_turnover_trend=self._safe_get(fundamentals, ["trend", "assetTurnover"], default=0.0),
        )

        catalysts = CatalystMetrics(
            theme_alignment=self._safe_get(meta, ["themeAlignment"], default=0.0),
            earnings_revision_trend=self._safe_get(fundamentals, ["sentiment", "earningsRevision"], default=0.0),
            insider_activity_score=self._safe_get(fundamentals, ["sentiment", "insiderActivity"], default=0.0),
            strategic_investor_presence=self._safe_get(meta, ["strategicInvestorScore"], default=None),
        )

        valuation = ValuationMetrics(
            peg_ratio=self._safe_get(fundamentals, ["valuation", "pegRatio"], default=2.0),
            ev_to_ebitda_vs_peers=self._safe_get(meta, ["evToEbitdaVsPeers"], default=0.0),
            free_cash_flow_yield=self._safe_get(fundamentals, ["valuation", "fcfYield"], default=0.0),
            price_momentum=self._safe_get(meta, ["priceMomentum"], default=0.0),
            consolidation_score=self._safe_get(meta, ["consolidationScore"], default=0.0),
        )

        risk = RiskMetrics(
            market_cap=self._safe_get(fundamentals, ["size", "marketCap"], default=0.0),
            avg_daily_dollar_volume=self._safe_get(meta, ["avgDollarVolume"], default=0.0),
            beta=self._safe_get(fundamentals, ["risk", "beta"], default=1.0),
            volatility_3y=self._safe_get(fundamentals, ["risk", "volatility3Y"], default=0.3),
            drawdown_1y=self._safe_get(meta, ["drawdown1Y"], default=0.2),
        )

        return CompanyIndicators(
            ticker=self.ticker,
            name=self.name,
            growth=growth,
            quality=quality,
            catalysts=catalysts,
            valuation=valuation,
            risk=risk,
        )

    @staticmethod
    def _safe_get(payload: Dict[str, Any], keys: list[str], *, default: Any) -> Any:
        node: Any = payload
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node
