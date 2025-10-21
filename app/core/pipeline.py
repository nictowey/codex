from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from app.data.providers import BaseProvider
from .metrics import CompanyIndicators
from .transformers import IndicatorTransformer, MetricSource


@dataclass(slots=True)
class PipelineConfig:
    providers: Dict[str, BaseProvider]


class IndicatorPipeline:
    """High-level pipeline for fetching and transforming company data."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    def build_company(self, ticker: str, *, name: Optional[str] = None) -> CompanyIndicators:
        provider = self.config.providers["primary"]
        fundamentals = provider.fundamentals(ticker)
        metadata = self._aggregate_metadata(ticker)
        transformer = IndicatorTransformer(ticker=ticker, name=name)
        return transformer.build(
            MetricSource(
                fundamentals=fundamentals,
                metadata=metadata,
            )
        )

    def build_many(self, tickers: Iterable[str]) -> List[CompanyIndicators]:
        return [self.build_company(ticker) for ticker in tickers]

    def _aggregate_metadata(self, ticker: str) -> Dict[str, float]:
        """Combine auxiliary signals that may live outside the primary provider."""

        metadata: Dict[str, float] = {}
        theme_provider = self.config.providers.get("themes")
        if theme_provider is not None:
            response = theme_provider.fundamentals(ticker)
            metadata.update(
                {
                    "themeAlignment": response.get("themeAlignment", 0.0),
                    "strategicInvestorScore": response.get("strategicInvestorScore"),
                }
            )
        return metadata
