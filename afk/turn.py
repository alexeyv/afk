from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, FrozenSet

from afk.turn_result import TurnResult


@dataclass(frozen=True)
class Turn:
    ALLOWED_TRANSITION_TYPES: ClassVar[FrozenSet[str]] = frozenset({"init", "coding"})
    MAX_TURN_NUMBER: ClassVar[int] = 100_000

    turn_number: int
    transition_type: str
    result: TurnResult | None
    log_file: Path
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.turn_number < 1:
            raise ValueError("turn_number must be >= 1")
        if self.turn_number >= self.MAX_TURN_NUMBER:
            raise ValueError(f"turn_number must be < {self.MAX_TURN_NUMBER}")

        transition_type = self.transition_type.strip().lower()
        if not transition_type:
            raise ValueError("transition_type must be non-empty")
        if transition_type not in self.ALLOWED_TRANSITION_TYPES:
            allowed = ", ".join(sorted(self.ALLOWED_TRANSITION_TYPES))
            raise ValueError(f"transition_type must be one of: {allowed}")
        object.__setattr__(self, "transition_type", transition_type)

        raw_log_file = str(self.log_file).strip()
        if not raw_log_file:
            raise ValueError("log_file must be a non-empty path")
        log_path = Path(raw_log_file).expanduser()
        if not log_path.is_absolute():
            raise ValueError("log_file must be an absolute path")
        object.__setattr__(self, "log_file", log_path)

        if (
            self.timestamp.tzinfo is None
            or self.timestamp.tzinfo.utcoffset(self.timestamp) is None
        ):
            raise ValueError("timestamp must be timezone-aware")
        object.__setattr__(self, "timestamp", self.timestamp.astimezone(timezone.utc))
