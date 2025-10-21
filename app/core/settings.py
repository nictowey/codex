from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .metrics import WeightConfig


@dataclass(slots=True)
class UserPreferences:
    """Persisted UI preferences across sessions."""

    theme: str = "Aurora Dark"
    favorites: List[str] = field(default_factory=list)
    live_tickers: List[str] = field(default_factory=lambda: ["CLS", "NVST", "SMCI"])
    data_mode: str = "Live data (cached)"
    auto_refresh: bool = False

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "favorites": self.favorites,
            "live_tickers": self.live_tickers,
            "data_mode": self.data_mode,
            "auto_refresh": self.auto_refresh,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "UserPreferences":
        if not payload:
            return cls()
        return cls(
            theme=str(payload.get("theme", cls().theme)),
            favorites=[str(item).upper() for item in payload.get("favorites", []) if str(item).strip()],
            live_tickers=[str(item).upper() for item in payload.get("live_tickers", cls().live_tickers)],
            data_mode=str(payload.get("data_mode", cls().data_mode)),
            auto_refresh=bool(payload.get("auto_refresh", False)),
        )


class WeightSettingsStore:
    """Persist user-selected scoring weights on the local filesystem."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or self._default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_path() -> Path:
        app_root = Path.home() / ".growth_picker"
        return app_root / "weights.json"

    def load(self) -> WeightConfig:
        if not self.path.exists():
            return WeightConfig()
        try:
            payload = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return WeightConfig()
        return WeightConfig.from_dict(payload)

    def save(self, config: WeightConfig) -> None:
        normalized = config.normalized()
        self.path.write_text(json.dumps(normalized.to_dict(), indent=2))


class UserPreferencesStore:
    """Persist UI preferences such as theme and favorite tickers."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or self._default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_path() -> Path:
        app_root = Path.home() / ".growth_picker"
        return app_root / "preferences.json"

    def load(self) -> UserPreferences:
        if not self.path.exists():
            return UserPreferences()
        try:
            payload = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return UserPreferences()
        return UserPreferences.from_dict(payload)

    def save(self, preferences: UserPreferences) -> None:
        self.path.write_text(json.dumps(preferences.to_dict(), indent=2))
