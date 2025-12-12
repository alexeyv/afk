from datetime import datetime, timezone

import pytest

from afk.turn import Turn
from afk.turn_result import TurnResult


class TestTurn:
    def test_turn_with_successful_result(self):
        result = TurnResult(
            outcome="success", message="feat: add foo", commit_hash="abc123"
        )
        turn = Turn(
            turn_number=1,
            transition_type="init",
            result=result,
            log_file="/path/to/log.txt",
            timestamp=datetime.now(timezone.utc),
        )

        assert turn.turn_number == 1
        assert turn.transition_type == "init"
        assert turn.result is result
        assert turn.log_file == "/path/to/log.txt"
        assert isinstance(turn.timestamp, datetime)

    def test_turn_with_none_result(self):
        turn = Turn(
            turn_number=2,
            transition_type="coding",
            result=None,
            log_file="/path/to/log.txt",
            timestamp=datetime.now(timezone.utc),
        )

        assert turn.result is None

    def test_turn_is_immutable(self):
        turn = Turn(
            turn_number=1,
            transition_type="init",
            result=None,
            log_file="/path/to/log.txt",
            timestamp=datetime.now(timezone.utc),
        )

        with pytest.raises(Exception):
            turn.turn_number = 2  # type: ignore[misc]

    def test_turn_with_various_transition_types(self):
        for transition_type in ["init", "coding", "review", "debug"]:
            turn = Turn(
                turn_number=1,
                transition_type=transition_type,
                result=None,
                log_file="/path/to/log.txt",
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
            log_file="/logs/turn-5.txt",
            timestamp=ts,
        )

        assert turn.turn_number == 5
        assert turn.transition_type == "coding"
        assert turn.result is not None
        assert turn.result == result
        assert turn.result.outcome == "failure"
        assert turn.log_file == "/logs/turn-5.txt"
        assert turn.timestamp == ts
