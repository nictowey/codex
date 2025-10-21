from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List


def _build_price_series(start: date, values: List[float]) -> List[Dict[str, str | float]]:
    series: List[Dict[str, str | float]] = []
    current = start
    for price in values:
        series.append({"date": current.isoformat(), "close": price})
        current += timedelta(days=30)
    return series


SAMPLE_PRICE_SERIES: Dict[str, List[Dict[str, str | float]]] = {
    "CLS": _build_price_series(
        date(2022, 1, 1),
        [
            8.2,
            8.5,
            9.1,
            9.5,
            9.8,
            10.4,
            11.2,
            12.1,
            14.0,
            16.5,
            18.2,
            21.4,
            24.8,
            27.5,
            29.3,
            31.1,
            35.0,
            40.5,
            46.2,
            52.7,
        ],
    ),
    "NVST": _build_price_series(
        date(2022, 1, 1),
        [
            42.0,
            41.5,
            40.2,
            39.8,
            40.1,
            41.0,
            41.8,
            42.5,
            43.0,
            43.8,
            44.5,
            45.2,
            44.0,
            43.0,
            42.5,
            41.8,
            42.2,
            43.5,
            44.7,
            45.8,
        ],
    ),
    "SMCI": _build_price_series(
        date(2022, 1, 1),
        [
            40.0,
            41.3,
            43.6,
            46.8,
            52.0,
            58.5,
            64.2,
            72.0,
            83.5,
            95.0,
            115.0,
            140.0,
            170.0,
            205.0,
            260.0,
            320.0,
            400.0,
            520.0,
            680.0,
            820.0,
        ],
    ),
}


def load_price_frame(ticker: str):  # pragma: no cover - convenience wrapper
    """Return the sample price history as a pandas DataFrame if pandas is available."""

    try:
        import pandas as pd
    except ModuleNotFoundError:  # pragma: no cover - pandas always installed in app context
        raise RuntimeError("pandas is required for price history visualization") from None

    records = SAMPLE_PRICE_SERIES.get(ticker.upper())
    if records is None:
        raise KeyError(f"No sample price series for {ticker}")
    return pd.DataFrame(records)


def load_fundamental_history(ticker: str):  # pragma: no cover - convenience wrapper
    """Synthetic quarterly fundamentals for charting."""

    try:
        import pandas as pd
    except ModuleNotFoundError:  # pragma: no cover
        raise RuntimeError("pandas is required for fundamental history visualization") from None

    ticker = ticker.upper()
    if ticker == "CLS":
        revenue = [1.4, 1.45, 1.52, 1.60, 1.68, 1.75, 1.9, 2.05]
        margin = [0.035, 0.036, 0.038, 0.039, 0.041, 0.043, 0.045, 0.047]
    elif ticker == "NVST":
        revenue = [0.63, 0.64, 0.65, 0.66, 0.67, 0.68, 0.685, 0.69]
        margin = [0.018, 0.019, 0.02, 0.021, 0.021, 0.022, 0.022, 0.023]
    else:
        revenue = [1.0, 1.05, 1.1, 1.2, 1.35, 1.55, 1.8, 2.1]
        margin = [0.05, 0.052, 0.056, 0.06, 0.065, 0.07, 0.075, 0.08]

    quarters = pd.date_range(end=pd.Timestamp.today(), periods=len(revenue), freq="Q")
    return pd.DataFrame({"revenue": revenue, "ebit_margin": margin}, index=quarters)
