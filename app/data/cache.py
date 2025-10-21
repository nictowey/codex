from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(slots=True)
class CacheRecord:
    """Metadata for cached payloads."""

    key: str
    fetched_at: float


class JsonCache:
    """Lightweight JSON cache stored on disk with TTL semantics."""

    def __init__(
        self,
        namespace: str,
        *,
        ttl_seconds: int = 6 * 60 * 60,
        base_dir: Optional[Path] = None,
    ) -> None:
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds
        self.base_dir = base_dir or Path.home() / ".growth_picker" / "cache"
        self.directory = self.base_dir / namespace
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        sanitized = key.replace("/", "_").upper()
        return self.directory / f"{sanitized}.json"

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

        fetched_at = float(payload.get("_fetched_at", 0))
        if self.ttl_seconds and time.time() - fetched_at > self.ttl_seconds:
            return None
        return payload.get("data")

    def save(self, key: str, data: Dict[str, Any]) -> None:
        path = self._path_for(key)
        wrapped = {"_fetched_at": time.time(), "data": data}
        path.write_text(json.dumps(wrapped))

    def purge_expired(self) -> None:
        if self.ttl_seconds == 0:
            return
        now = time.time()
        for path in self.directory.glob("*.json"):
            try:
                payload = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                path.unlink(missing_ok=True)
                continue
            fetched_at = float(payload.get("_fetched_at", 0))
            if now - fetched_at > self.ttl_seconds:
                path.unlink(missing_ok=True)
