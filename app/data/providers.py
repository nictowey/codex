from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import requests


class DataProviderError(RuntimeError):
    """Raised when a data provider returns an error response."""


@dataclass(slots=True)
class ProviderConfig:
    base_url: str
    api_key: str
    session: Optional[requests.Session] = None

    def get_session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session


class BaseProvider(abc.ABC):
    """Shared functionality for HTTP-based data providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        params = {**params, **self._auth_params()}
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = self.config.get_session().get(url, params=params, timeout=30)
        if response.status_code != 200:
            raise DataProviderError(
                f"{self.__class__.__name__} returned {response.status_code}: {response.text}"
            )
        return response.json()

    @abc.abstractmethod
    def _auth_params(self) -> Dict[str, Any]:
        """Return authentication parameters for the provider."""

    @abc.abstractmethod
    def fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Fetch fundamental data for a ticker."""

    @abc.abstractmethod
    def price_series(self, ticker: str, *, interval: str = "1day", limit: int = 365) -> Dict[str, Any]:
        """Fetch historical price series."""


class FinnhubProvider(BaseProvider):
    def _auth_params(self) -> Dict[str, Any]:
        return {"token": self.config.api_key}

    def fundamentals(self, ticker: str) -> Dict[str, Any]:
        return self._get("stock/metric", {"symbol": ticker, "metric": "all"})

    def price_series(self, ticker: str, *, interval: str = "D", limit: int = 365) -> Dict[str, Any]:
        return self._get("stock/candle", {"symbol": ticker, "resolution": interval, "count": limit})


class TwelveDataProvider(BaseProvider):
    def _auth_params(self) -> Dict[str, Any]:
        return {"apikey": self.config.api_key}

    def fundamentals(self, ticker: str) -> Dict[str, Any]:
        return self._get("fundamentals", {"symbol": ticker})

    def price_series(self, ticker: str, *, interval: str = "1day", limit: int = 365) -> Dict[str, Any]:
        return self._get("time_series", {"symbol": ticker, "interval": interval, "outputsize": limit})


class FMPProvider(BaseProvider):
    def _auth_params(self) -> Dict[str, Any]:
        return {"apikey": self.config.api_key}

    def fundamentals(self, ticker: str) -> Dict[str, Any]:
        return self._get("profile/{}".format(ticker))

    def price_series(self, ticker: str, *, interval: str = "1day", limit: int = 365) -> Dict[str, Any]:
        return self._get("historical-price-full/{}".format(ticker), {"serietype": "line", "timeseries": limit})


def close_providers(providers: Iterable[BaseProvider]) -> None:
    for provider in providers:
        session = provider.config.session
        if session is not None:
            session.close()
