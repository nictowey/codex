from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd


@dataclass(slots=True)
class BacktestResult:
    ticker: str
    cumulative_return: float
    cagr: float
    max_drawdown: float


def _prepare_series(price_payload: Dict[str, object]) -> pd.Series:
    candles = price_payload.get("candles")
    if not candles:
        raise ValueError("Price payload missing 'candles' data")
    df = pd.DataFrame(candles)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df = df.set_index("date")
    return df["close"].astype(float)


def _calculate_cagr(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    start_value = series.iloc[0]
    end_value = series.iloc[-1]
    years = max((series.index[-1] - series.index[0]).days / 365.25, 1 / 12)
    return (end_value / start_value) ** (1 / years) - 1


def _calculate_max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    running_max = series.cummax()
    drawdowns = (series / running_max) - 1
    return float(drawdowns.min())


def run_backtest(ticker: str, price_payload: Dict[str, object]) -> BacktestResult:
    series = _prepare_series(price_payload)
    cumulative_return = float(series.iloc[-1] / series.iloc[0] - 1) if len(series) > 1 else 0.0
    cagr = float(_calculate_cagr(series))
    max_drawdown = float(_calculate_max_drawdown(series))
    return BacktestResult(ticker=ticker, cumulative_return=cumulative_return, cagr=cagr, max_drawdown=max_drawdown)


def run_backtests(price_payloads: Dict[str, Dict[str, object]]) -> List[BacktestResult]:
    results: List[BacktestResult] = []
    for ticker, payload in price_payloads.items():
        try:
            results.append(run_backtest(ticker, payload))
        except ValueError:
            continue
    return results
