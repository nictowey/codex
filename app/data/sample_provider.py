from __future__ import annotations

from typing import Any, Dict

from app.data.providers import BaseProvider, ProviderConfig

from .sample_data import SAMPLE_FUNDAMENTALS
from .sample_history import SAMPLE_PRICE_SERIES


class SampleProvider(BaseProvider):
    """Offline provider that serves deterministic sample data."""

    def __init__(self) -> None:
        super().__init__(ProviderConfig(base_url="https://sample", api_key="demo"))

    def _auth_params(self) -> Dict[str, Any]:
        return {}

    def fundamentals(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper()
        return SAMPLE_FUNDAMENTALS.get(ticker, SAMPLE_FUNDAMENTALS["CLS"])

    def price_series(self, ticker: str, *, interval: str = "1day", limit: int = 365) -> Dict[str, Any]:
        ticker = ticker.upper()
        series = SAMPLE_PRICE_SERIES.get(ticker, SAMPLE_PRICE_SERIES["CLS"])
        return {"symbol": ticker, "candles": series[:limit], "interval": interval}
