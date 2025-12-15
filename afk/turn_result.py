"""TurnResult - immutable record of a completed turn."""

from datetime import datetime, timezone
from pathlib import Path

from afk.transition_type import TransitionType


class TurnResult:
    """Immutable record of a completed turn.

    Created by Turn.finish() after successful execution.
    Stored in Session history.
    """

    __slots__ = (
        "_turn_number",
        "_transition_type",
        "_outcome",
        "_message",
        "_commit_hash",
        "_log_file",
        "_timestamp",
    )

    def __init__(
        self,
        turn_number: int,
        transition_type: TransitionType,
        outcome: str | None,
        message: str,
        commit_hash: str,
        log_file: Path,
        timestamp: datetime,
    ) -> None:
        # turn_number validation
        if not isinstance(turn_number, int):
            raise TypeError(f"expected int for turn_number, got {turn_number!r}")
        if turn_number < 1:
            raise ValueError("turn_number must be >= 1")

        # transition_type validation
        if not isinstance(transition_type, TransitionType):
            raise TypeError(f"expected TransitionType, got {transition_type!r}")

        # outcome validation
        if outcome is not None and not isinstance(outcome, str):
            raise TypeError(f"expected str or None for outcome, got {outcome!r}")

        # message validation
        if not isinstance(message, str):
            raise TypeError(f"expected str for message, got {message!r}")

        # commit_hash validation
        if not isinstance(commit_hash, str):
            raise TypeError(f"expected str for commit_hash, got {commit_hash!r}")

        # log_file validation
        if not isinstance(log_file, Path):
            raise TypeError(f"expected Path for log_file, got {log_file!r}")
        if not log_file.is_absolute():
            raise ValueError("log_file must be an absolute path")

        # timestamp validation
        if not isinstance(timestamp, datetime):
            raise TypeError(f"expected datetime for timestamp, got {timestamp!r}")
        if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) is None:
            raise ValueError("timestamp must be timezone-aware")

        # Assign all values
        self._turn_number = turn_number
        self._transition_type = transition_type
        self._outcome = outcome
        self._message = message
        self._commit_hash = commit_hash
        self._log_file = log_file
        self._timestamp = timestamp.astimezone(timezone.utc)

    @property
    def turn_number(self) -> int:
        return self._turn_number

    @property
    def transition_type(self) -> TransitionType:
        return self._transition_type

    @property
    def outcome(self) -> str | None:
        return self._outcome

    @property
    def message(self) -> str:
        return self._message

    @property
    def commit_hash(self) -> str:
        return self._commit_hash

    @property
    def log_file(self) -> Path:
        return self._log_file

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    def __repr__(self) -> str:
        return (
            f"TurnResult(turn_number={self._turn_number}, "
            f"transition_type={self._transition_type!r}, "
            f"outcome={self._outcome!r}, "
            f"commit_hash={self._commit_hash!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TurnResult):
            return False
        return (
            self._turn_number == other._turn_number
            and self._transition_type == other._transition_type
            and self._outcome == other._outcome
            and self._message == other._message
            and self._commit_hash == other._commit_hash
            and self._log_file == other._log_file
            and self._timestamp == other._timestamp
        )

    def __hash__(self) -> int:
        return hash(
            (
                self._turn_number,
                self._transition_type,
                self._outcome,
                self._message,
                self._commit_hash,
                self._log_file,
                self._timestamp,
            )
        )
