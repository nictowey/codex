from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from typing import TYPE_CHECKING

from app.data.providers import BaseProvider
from .metrics import CompanyIndicators
from .transformers import IndicatorTransformer, MetricSource

if TYPE_CHECKING:
    from app.data.ingestion import ProviderHealthMonitor


@dataclass(slots=True)
class PipelineConfig:
    providers: Dict[str, BaseProvider]


class IndicatorPipeline:
    """High-level pipeline for fetching and transforming company data."""

    def __init__(self, config: PipelineConfig, *, monitor: Optional["ProviderHealthMonitor"] = None) -> None:
        self.config = config
        self.monitor = monitor

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
            try:
                response = theme_provider.fundamentals(ticker)
            except Exception as exc:  # noqa: BLE001
                if self.monitor is not None:
                    self.monitor.record_failure("themes", str(exc))
            else:
                metadata.update(
                    {
                        "themeAlignment": response.get("themeAlignment", 0.0),
                        "strategicInvestorScore": response.get("strategicInvestorScore"),
                        "sector": response.get("sector") or response.get("profile", {}).get("sector"),
                        "industry": response.get("industry") or response.get("profile", {}).get("industry"),
                    }
                )
                if self.monitor is not None:
                    self.monitor.record_success("themes")
        return metadata
