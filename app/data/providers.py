from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING

import requests


if TYPE_CHECKING:  # pragma: no cover - circular import guard
    from app.data.ingestion import ProviderHealthMonitor


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

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self.config = config

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.config is None:
            raise DataProviderError("HTTP provider is missing configuration")
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
        resolution = interval
        if interval.lower() in {"1day", "1d"}:
            resolution = "D"
        return self._get(
            "stock/candle",
            {"symbol": ticker, "resolution": resolution, "count": limit},
        )


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


class FailoverProvider(BaseProvider):
    """Chain multiple providers together with failover semantics."""

    def __init__(
        self,
        providers: Sequence[Tuple[str, BaseProvider]],
        *,
        name: str,
    ) -> None:
        super().__init__(config=None)
        self.providers: List[Tuple[str, BaseProvider]] = [
            (label, provider) for label, provider in providers if provider is not None
        ]
        if not self.providers:
            raise ValueError("FailoverProvider requires at least one provider")
        self.name = name
        self._monitor: Optional["ProviderHealthMonitor"] = None

    def _auth_params(self) -> Dict[str, Any]:  # pragma: no cover - unused
        return {}

    def fundamentals(self, ticker: str) -> Dict[str, Any]:
        errors: List[str] = []
        for label, provider in self.providers:
            try:
                result = provider.fundamentals(ticker)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{label}: {exc}")
                if self._monitor is not None:
                    self._monitor.record_failure(f"{self.name}:{label}", str(exc))
                continue
            if self._monitor is not None:
                self._monitor.record_success(f"{self.name}:{label}")
            return result
        raise DataProviderError(
            f"All {self.name} providers failed for {ticker}: {'; '.join(errors)}"
        )

    def price_series(
        self, ticker: str, *, interval: str = "1day", limit: int = 365
    ) -> Dict[str, Any]:
        errors: List[str] = []
        for label, provider in self.providers:
            try:
                result = provider.price_series(ticker, interval=interval, limit=limit)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{label}: {exc}")
                if self._monitor is not None:
                    self._monitor.record_failure(f"{self.name}:{label}", str(exc))
                continue
            if self._monitor is not None:
                self._monitor.record_success(f"{self.name}:{label}")
            return result
        raise DataProviderError(
            f"All {self.name} providers failed for {ticker}: {'; '.join(errors)}"
        )

    @property
    def provider_labels(self) -> List[str]:
        return [label for label, _ in self.providers]

    def iter_children(self) -> Iterable[BaseProvider]:
        for _, provider in self.providers:
            yield provider

    def attach_monitor(self, monitor: "ProviderHealthMonitor") -> None:
        self._monitor = monitor


def close_providers(providers: Iterable[BaseProvider]) -> None:
    for provider in providers:
        if isinstance(provider, FailoverProvider):
            close_providers(provider.iter_children())
            continue
        session = provider.config.session
        if session is not None:
            session.close()
