from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from app.core.metrics import ScoreBreakdown


@dataclass(slots=True)
class RankingSnapshot:
    created_at: str
    scores: List[dict]


class RankingTracker:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".growth_picker" / "rankings.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, scores: Iterable[ScoreBreakdown]) -> RankingSnapshot:
        snapshot = RankingSnapshot(
            created_at=datetime.utcnow().isoformat(timespec="seconds"),
            scores=[score.to_dict() for score in scores],
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
                    scores=list(entry.get("scores", [])),
                )
            )
        return history
