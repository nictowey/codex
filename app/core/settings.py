from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .metrics import WeightConfig


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
