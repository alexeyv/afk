from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from afk.transition_type import TransitionType
from afk.turn import Turn
from afk.turn_result import TurnResult


# Helper to create a valid TurnResult for tests that don't care about result contents
def _dummy_result() -> TurnResult:
    return TurnResult(outcome="success", message="test", commit_hash="abc123")


class TestTurn:
    def test_turn_with_successful_result(self) -> None:
        result = TurnResult(
            outcome="success", message="feat: add foo", commit_hash="abc123"
        )
        log_file = Path("/path/to/log.txt")
        transition_type = TransitionType("init")
        turn = Turn(
            turn_number=1,
            transition_type=transition_type,
            result=result,
            log_file=log_file,
            timestamp=datetime.now(timezone.utc),
        )

        assert turn.turn_number == 1
        assert turn.transition_type == transition_type
        assert turn.result is result
        assert turn.log_file == log_file
        assert isinstance(turn.timestamp, datetime)

    def test_turn_is_immutable(self) -> None:
        turn = Turn(
            turn_number=1,
            transition_type=TransitionType("init"),
            result=_dummy_result(),
            log_file=Path("/path/to/log.txt"),
            timestamp=datetime.now(timezone.utc),
        )

        with pytest.raises(FrozenInstanceError):
            turn.turn_number = 2  # type: ignore[misc]

    def test_turn_with_various_transition_types(self) -> None:
        for transition_type_str in ["init", "coding", "review", "debug"]:
            transition_type = TransitionType(transition_type_str)
            turn = Turn(
                turn_number=1,
                transition_type=transition_type,
                result=_dummy_result(),
                log_file=Path("/path/to/log.txt"),
                timestamp=datetime.now(timezone.utc),
            )
            assert str(turn.transition_type) == transition_type_str

    def test_turn_fields_accessible(self) -> None:
        ts = datetime.now(timezone.utc)
        result = TurnResult(
            outcome="failure", message="fix: broken", commit_hash="def456"
        )
        transition_type = TransitionType("coding")
        turn = Turn(
            turn_number=5,
            transition_type=transition_type,
            result=result,
            log_file=Path("/logs/turn-5.txt"),
            timestamp=ts,
        )

        assert turn.turn_number == 5
        assert turn.transition_type == transition_type
        assert turn.result is not None
        assert turn.result == result
        assert turn.result.outcome == "failure"
        assert turn.log_file == Path("/logs/turn-5.txt")
        assert turn.timestamp == ts

    def test_turn_rejects_invalid_turn_number(self) -> None:
        with pytest.raises(ValueError, match="turn_number"):
            Turn(
                turn_number=0,
                transition_type=TransitionType("init"),
                result=_dummy_result(),
                log_file=Path("/logs/turn-0.txt"),
                timestamp=datetime.now(timezone.utc),
            )

    def test_turn_rejects_turn_number_at_max(self) -> None:
        with pytest.raises(ValueError, match="turn_number must be < 100000"):
            Turn(
                turn_number=Turn.MAX_TURN_NUMBER,
                transition_type=TransitionType("init"),
                result=_dummy_result(),
                log_file=Path("/logs/turn.txt"),
                timestamp=datetime.now(timezone.utc),
            )

    def test_turn_requires_absolute_log_file(self) -> None:
        with pytest.raises(ValueError, match="absolute"):
            Turn(
                turn_number=1,
                transition_type=TransitionType("init"),
                result=_dummy_result(),
                log_file=Path("logs/relative.txt"),
                timestamp=datetime.now(timezone.utc),
            )

    def test_turn_requires_timezone_aware_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            Turn(
                turn_number=1,
                transition_type=TransitionType("init"),
                result=_dummy_result(),
                log_file=Path("/logs/turn-1.txt"),
                timestamp=datetime.now(),
            )

    def test_turn_normalizes_timestamp_to_utc(self) -> None:
        ts = datetime(2025, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))
        turn = Turn(
            turn_number=3,
            transition_type=TransitionType("coding"),
            result=_dummy_result(),
            log_file=Path("/logs/turn-3.txt"),
            timestamp=ts,
        )

        assert turn.timestamp.tzinfo == timezone.utc
        assert turn.timestamp == ts.astimezone(timezone.utc)

    def test_turn_rejects_string_transition_type(self) -> None:
        with pytest.raises(TypeError, match="expected TransitionType, got 'init'"):
            Turn(
                turn_number=1,
                transition_type="init",  # type: ignore[arg-type]
                result=_dummy_result(),
                log_file=Path("/logs/turn-1.txt"),
                timestamp=datetime.now(timezone.utc),
            )
