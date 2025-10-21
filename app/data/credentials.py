"""Helpers for resolving API credentials with sensible defaults."""
from __future__ import annotations

import os
from typing import Optional

__all__ = ["resolve_api_key", "DEFAULT_API_KEYS"]

DEFAULT_API_KEYS = {
    "FINNHUB_TOKEN": "d3relupr01qopgh888bgd3relupr01qopgh888c0",
    "FMP_TOKEN": "GbFN7jfzZrBf88tNIlFyPOWXlKgBsDML",
    "TWELVE_DATA_TOKEN": "8f63a603b23d4b65b8c7cde2d207ce8c",
}


def resolve_api_key(name: str) -> Optional[str]:
    """Return the API key from the environment or bundled defaults."""
    value = os.getenv(name)
    if value:
        value = value.strip()
        if value:
            return value
    default = DEFAULT_API_KEYS.get(name)
    return default
