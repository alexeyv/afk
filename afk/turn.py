from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from afk.transition_type import TransitionType
from afk.turn_result import TurnResult


@dataclass(frozen=True)
class Turn:
    MAX_TURN_NUMBER: ClassVar[int] = 100_000
    _next_number: ClassVar[int] = 1

    @classmethod
    def next_turn_number(cls, resume_from: int | None = None) -> int:
        """Return and increment the next turn number.

        Args:
            resume_from: If provided, resume counting from this number.
                         Returns this number and sets next to resume_from + 1.
        """
        if resume_from is not None:
            if resume_from < 1:
                raise ValueError(f"resume_from must be >= 1, got {resume_from}")
            if resume_from >= cls.MAX_TURN_NUMBER:
                raise ValueError(f"resume_from {resume_from} >= {cls.MAX_TURN_NUMBER}")
            cls._next_number = resume_from + 1
            return resume_from

        n = cls._next_number
        if n >= cls.MAX_TURN_NUMBER:
            raise ValueError(f"turn_number {n} >= {cls.MAX_TURN_NUMBER}")
        cls._next_number += 1
        return n

    @classmethod
    def reset_turn_counter(cls) -> None:
        """Reset turn counter to 1 (for testing)."""
        cls._next_number = 1

    turn_number: int
    transition_type: TransitionType
    result: TurnResult
    log_file: Path
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.turn_number < 1:
            raise ValueError("turn_number must be >= 1")
        if self.turn_number >= self.MAX_TURN_NUMBER:
            raise ValueError(f"turn_number must be < {self.MAX_TURN_NUMBER}")

        if not isinstance(self.transition_type, TransitionType):
            raise TypeError(f"expected TransitionType, got {self.transition_type!r}")

        if not isinstance(self.result, TurnResult):
            raise TypeError(f"expected TurnResult, got {self.result!r}")

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
