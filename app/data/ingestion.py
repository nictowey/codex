from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.core.metrics import CompanyIndicators
from app.core.pipeline import IndicatorPipeline, PipelineConfig
from app.data.providers import (
    BaseProvider,
    FMPProvider,
    FinnhubProvider,
    ProviderConfig,
    TwelveDataProvider,
)

from .cache import JsonCache
from .sample_provider import SampleProvider


@dataclass(slots=True)
class IngestionResult:
    ticker: str
    indicators: CompanyIndicators
    price_history: Optional[Dict[str, Any]]


class DataIngestionManager:
    """Coordinate fetching and caching of indicators and price history."""

    def __init__(
        self,
        pipeline: IndicatorPipeline,
        *,
        indicator_cache: Optional[JsonCache] = None,
        price_cache: Optional[JsonCache] = None,
    ) -> None:
        self.pipeline = pipeline
        self.indicator_cache = indicator_cache or JsonCache("indicators")
        self.price_cache = price_cache or JsonCache("prices")

    def get_company(
        self, ticker: str, *, name: Optional[str] = None, force_refresh: bool = False
    ) -> IngestionResult:
        ticker = ticker.upper()
        cached_indicators = None if force_refresh else self.indicator_cache.load(ticker)
        if cached_indicators is not None:
            indicators = CompanyIndicators.from_dict(cached_indicators)
        else:
            indicators = self.pipeline.build_company(ticker, name=name)
            self.indicator_cache.save(ticker, indicators.to_dict())

        cached_prices = None if force_refresh else self.price_cache.load(ticker)
        if cached_prices is None:
            provider = self.pipeline.config.providers.get("primary")
            price_history: Optional[Dict[str, float]] = None
            if provider is not None:
                try:
                    response = provider.price_series(ticker, interval="1day", limit=365 * 3)
                    price_history = self._normalize_price_response(response)
                except Exception:  # noqa: BLE001 - propagate silent fallback for UI
                    price_history = None
            else:
                price_history = None
            if price_history is not None:
                self.price_cache.save(ticker, price_history)
        else:
            price_history = cached_prices

        return IngestionResult(ticker=ticker, indicators=indicators, price_history=price_history)

    def refresh_many(self, tickers: Iterable[str]) -> List[IngestionResult]:
        results: List[IngestionResult] = []
        for ticker in tickers:
            results.append(self.get_company(ticker, force_refresh=True))
        return results

    @staticmethod
    def _normalize_price_response(response: Dict[str, Any]) -> Dict[str, Any]:
        if "candles" in response:
            return response

        if {"c", "t"}.issubset(response.keys()):  # Finnhub style arrays
            candles = []
            closes = response.get("c", [])
            timestamps = response.get("t", [])
            for ts, close in zip(timestamps, closes):
                dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                candles.append({"date": dt.date().isoformat(), "close": float(close)})
            return {"candles": candles, "symbol": response.get("symbol")}

        if "values" in response:  # Twelve Data time series
            candles = []
            for entry in response.get("values", []):
                candles.append({"date": entry.get("datetime"), "close": float(entry.get("close", 0.0))})
            return {"candles": candles, "symbol": response.get("symbol")}

        if "historical" in response:  # FMP historical series
            candles = []
            for entry in response.get("historical", []):
                candles.append({"date": entry.get("date"), "close": float(entry.get("close", 0.0))})
            return {"candles": list(reversed(candles)), "symbol": response.get("symbol")}

        return response


def build_default_manager() -> DataIngestionManager:
    providers: Dict[str, BaseProvider] = {}

    finnhub_key = os.getenv("FINNHUB_TOKEN")
    if finnhub_key:
        providers["primary"] = FinnhubProvider(
            ProviderConfig(base_url="https://finnhub.io/api/v1", api_key=finnhub_key)
        )

    twelve_data_key = os.getenv("TWELVE_DATA_TOKEN")
    if twelve_data_key:
        providers.setdefault(
            "primary",
            TwelveDataProvider(
                ProviderConfig(base_url="https://api.twelvedata.com", api_key=twelve_data_key)
            ),
        )

    fmp_key = os.getenv("FMP_TOKEN")
    if fmp_key:
        providers.setdefault(
            "themes",
            FMPProvider(ProviderConfig(base_url="https://financialmodelingprep.com/api/v3", api_key=fmp_key)),
        )

    if not providers:
        sample_provider = SampleProvider()
        providers = {"primary": sample_provider, "themes": sample_provider}

    pipeline = IndicatorPipeline(PipelineConfig(providers=providers))
    return DataIngestionManager(pipeline)
