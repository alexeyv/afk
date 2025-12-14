from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from afk.transition_type import TransitionType


@dataclass(frozen=True)
class TurnResult:
    """Frozen record of a completed turn.

    Created by Turn.finish() after successful execution.
    Stored in Session history.
    """

    turn_number: int
    transition_type: TransitionType
    outcome: str | None
    message: str
    commit_hash: str
    log_file: Path
    timestamp: datetime

    MAX_TURN_NUMBER: int = 100_000

    def __post_init__(self) -> None:
        if not isinstance(self.turn_number, int):
            raise TypeError(f"expected int for turn_number, got {self.turn_number!r}")
        if self.turn_number < 1:
            raise ValueError("turn_number must be >= 1")
        if self.turn_number >= self.MAX_TURN_NUMBER:
            raise ValueError(f"turn_number must be < {self.MAX_TURN_NUMBER}")

        if not isinstance(self.transition_type, TransitionType):
            raise TypeError(f"expected TransitionType, got {self.transition_type!r}")

        if self.outcome is not None and not isinstance(self.outcome, str):
            raise TypeError(f"expected str or None for outcome, got {self.outcome!r}")

        if not isinstance(self.message, str):
            raise TypeError(f"expected str for message, got {self.message!r}")

        if not isinstance(self.commit_hash, str):
            raise TypeError(f"expected str for commit_hash, got {self.commit_hash!r}")

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
