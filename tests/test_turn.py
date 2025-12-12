from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from afk.turn import Turn
from afk.turn_result import TurnResult


class TestTurn:
    def test_turn_with_successful_result(self):
        result = TurnResult(
            outcome="success", message="feat: add foo", commit_hash="abc123"
        )
        log_file = Path("/path/to/log.txt")
        turn = Turn(
            turn_number=1,
            transition_type="init",
            result=result,
            log_file=log_file,
            timestamp=datetime.now(timezone.utc),
        )

        assert turn.turn_number == 1
        assert turn.transition_type == "init"
        assert turn.result is result
        assert turn.log_file == log_file
        assert isinstance(turn.timestamp, datetime)

    def test_turn_with_none_result(self):
        log_file = Path("/path/to/log.txt")
        turn = Turn(
            turn_number=2,
            transition_type="coding",
            result=None,
            log_file=log_file,
            timestamp=datetime.now(timezone.utc),
        )

        assert turn.result is None

    def test_turn_is_immutable(self):
        turn = Turn(
            turn_number=1,
            transition_type="init",
            result=None,
            log_file=Path("/path/to/log.txt"),
            timestamp=datetime.now(timezone.utc),
        )

        with pytest.raises(FrozenInstanceError):
            turn.turn_number = 2  # type: ignore[misc]

    def test_turn_with_various_transition_types(self):
        for transition_type in Turn.ALLOWED_TRANSITION_TYPES:
            turn = Turn(
                turn_number=1,
                transition_type=transition_type.upper(),
                result=None,
                log_file=Path("/path/to/log.txt"),
                timestamp=datetime.now(timezone.utc),
            )
            assert turn.transition_type == transition_type

    def test_turn_fields_accessible(self):
        ts = datetime.now(timezone.utc)
        result = TurnResult(
            outcome="failure", message="fix: broken", commit_hash="def456"
        )
        turn = Turn(
            turn_number=5,
            transition_type="coding",
            result=result,
            log_file=Path("/logs/turn-5.txt"),
            timestamp=ts,
        )

        assert turn.turn_number == 5
        assert turn.transition_type == "coding"
        assert turn.result is not None
        assert turn.result == result
        assert turn.result.outcome == "failure"
        assert turn.log_file == Path("/logs/turn-5.txt")
        assert turn.timestamp == ts

    def test_turn_rejects_invalid_turn_number(self):
        with pytest.raises(ValueError, match="turn_number"):
            Turn(
                turn_number=0,
                transition_type="init",
                result=None,
                log_file=Path("/logs/turn-0.txt"),
                timestamp=datetime.now(timezone.utc),
            )

    def test_turn_rejects_unknown_transition_type(self):
        with pytest.raises(ValueError, match="transition_type must be one of"):
            Turn(
                turn_number=1,
                transition_type="unknown",
                result=None,
                log_file=Path("/logs/turn-1.txt"),
                timestamp=datetime.now(timezone.utc),
            )

    def test_turn_requires_absolute_log_file(self):
        with pytest.raises(ValueError, match="absolute"):
            Turn(
                turn_number=1,
                transition_type="init",
                result=None,
                log_file=Path("logs/relative.txt"),
                timestamp=datetime.now(timezone.utc),
            )

    def test_turn_requires_timezone_aware_timestamp(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            Turn(
                turn_number=1,
                transition_type="init",
                result=None,
                log_file=Path("/logs/turn-1.txt"),
                timestamp=datetime.now(),
            )

    def test_turn_normalizes_timestamp_to_utc(self):
        ts = datetime(2025, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))
        turn = Turn(
            turn_number=3,
            transition_type="coding",
            result=None,
            log_file=Path("/logs/turn-3.txt"),
            timestamp=ts,
        )

        assert turn.timestamp.tzinfo == timezone.utc
        assert turn.timestamp == ts.astimezone(timezone.utc)
