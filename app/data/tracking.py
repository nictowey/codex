from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from app.core.metrics import ScoreBreakdown
from app.data.ingestion import DataIngestionManager


@dataclass(slots=True)
class RankingSnapshot:
    created_at: str
    entries: List[dict]


@dataclass(slots=True)
class SnapshotPerformance:
    run_timestamp: str
    ticker: str
    name: str
    recorded_price: Optional[float]
    latest_price: Optional[float]
    return_since_capture: Optional[float]
    target_met: bool
    composite: float


class RankingTracker:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".growth_picker" / "rankings.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        scores: Iterable[ScoreBreakdown],
        *,
        price_lookup: Optional[Dict[str, Dict[str, object]]] = None,
    ) -> RankingSnapshot:
        price_lookup = price_lookup or {}
        snapshot = RankingSnapshot(
            created_at=datetime.utcnow().isoformat(timespec="seconds"),
            entries=[
                {
                    **score.to_dict(),
                    "recorded_price": self._latest_close_from_payload(price_lookup.get(score.ticker)),
                    "target_price": self._target_price(price_lookup.get(score.ticker)),
                }
                for score in scores
            ],
        )
        history = self.load_history()
        history.append(snapshot)
        self.path.write_text(
            json.dumps([snapshot.__dict__ for snapshot in history], indent=2)
        )
        return snapshot

    def load_history(self) -> List[RankingSnapshot]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return []
        history: List[RankingSnapshot] = []
        for entry in raw:
            history.append(
                RankingSnapshot(
                    created_at=str(entry.get("created_at", "")),
                    entries=self._normalize_entries(entry),
                )
            )
        return history

    def build_performance(self, manager: DataIngestionManager) -> List[SnapshotPerformance]:
        performances: List[SnapshotPerformance] = []
        for snapshot in self.load_history():
            for entry in snapshot.entries:
                ticker = entry.get("ticker")
                if not ticker:
                    continue
                recorded_price = self._safe_float(entry.get("recorded_price"))
                latest_price = manager.latest_close(ticker) if manager else None
                return_since = None
                target_met = False
                if recorded_price and latest_price:
                    return_since = (latest_price / recorded_price) - 1
                    target_price = self._safe_float(entry.get("target_price"))
                    target_met = bool(target_price and latest_price >= target_price)
                performances.append(
                    SnapshotPerformance(
                        run_timestamp=snapshot.created_at,
                        ticker=ticker,
                        name=str(entry.get("name", "")),
                        recorded_price=recorded_price,
                        latest_price=latest_price,
                        return_since_capture=return_since,
                        target_met=target_met,
                        composite=float(entry.get("composite", 0.0)),
                    )
                )
        return performances

    @staticmethod
    def _normalize_entries(entry: dict) -> List[dict]:
        scores = entry.get("entries")
        if isinstance(scores, list):
            return list(scores)
        legacy_scores = entry.get("scores")
        if isinstance(legacy_scores, list):
            normalized: List[dict] = []
            for item in legacy_scores:
                normalized.append(
                    {
                        **item,
                        "recorded_price": None,
                        "target_price": None,
                    }
                )
            return normalized
        return []

    @staticmethod
    def _latest_close_from_payload(payload: Optional[Dict[str, object]]) -> Optional[float]:
        if not payload:
            return None
        candles = payload.get("candles") if isinstance(payload, dict) else None
        if not candles:
            return None
        last = candles[-1]
        try:
            return float(last.get("close"))
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _target_price(payload: Optional[Dict[str, object]]) -> Optional[float]:
        latest = RankingTracker._latest_close_from_payload(payload)
        if latest is None:
            return None
        return latest * 2

    @staticmethod
    def _safe_float(value: object) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
