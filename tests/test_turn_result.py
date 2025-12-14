from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from afk.transition_type import TransitionType
from afk.turn_result import TurnResult


def _make_result(**overrides) -> TurnResult:
    """Helper to create TurnResult with sensible defaults."""
    defaults = {
        "turn_number": 1,
        "transition_type": TransitionType("coding"),
        "outcome": "success",
        "message": "test message",
        "commit_hash": "abc123",
        "log_file": Path("/logs/turn-00001-coding.log"),
        "timestamp": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return TurnResult(**defaults)


class TestTurnResultDataclass:
    def test_creates_turn_result_with_all_fields(self) -> None:
        ts = datetime.now(timezone.utc)
        log_file = Path("/logs/turn-00001-init.log")
        transition_type = TransitionType("init")

        result = TurnResult(
            turn_number=1,
            transition_type=transition_type,
            outcome="success",
            message="feat: add feature\n\noutcome: success",
            commit_hash="abc123def456",
            log_file=log_file,
            timestamp=ts,
        )

        assert result.turn_number == 1
        assert result.transition_type == transition_type
        assert result.outcome == "success"
        assert result.message == "feat: add feature\n\noutcome: success"
        assert result.commit_hash == "abc123def456"
        assert result.log_file == log_file
        assert result.timestamp == ts

    def test_turn_result_is_frozen(self) -> None:
        result = _make_result()
        with pytest.raises(FrozenInstanceError):
            result.outcome = "failure"  # type: ignore[misc]

    def test_turn_result_equality(self) -> None:
        ts = datetime.now(timezone.utc)
        kwargs = {
            "turn_number": 1,
            "transition_type": TransitionType("coding"),
            "outcome": "success",
            "message": "msg",
            "commit_hash": "abc123",
            "log_file": Path("/logs/turn.log"),
            "timestamp": ts,
        }
        result1 = TurnResult(**kwargs)
        result2 = TurnResult(**kwargs)
        assert result1 == result2

    def test_turn_result_repr(self) -> None:
        result = _make_result()
        repr_str = repr(result)
        assert "TurnResult" in repr_str
        assert "success" in repr_str
        assert "abc123" in repr_str


class TestTurnResultValidation:
    def test_rejects_non_int_turn_number(self) -> None:
        with pytest.raises(TypeError, match="expected int for turn_number"):
            _make_result(turn_number="1")  # type: ignore[arg-type]

    def test_rejects_turn_number_zero(self) -> None:
        with pytest.raises(ValueError, match="turn_number must be >= 1"):
            _make_result(turn_number=0)

    def test_rejects_negative_turn_number(self) -> None:
        with pytest.raises(ValueError, match="turn_number must be >= 1"):
            _make_result(turn_number=-1)

    def test_rejects_turn_number_at_max(self) -> None:
        with pytest.raises(ValueError, match="turn_number must be < 100000"):
            _make_result(turn_number=100000)

    def test_accepts_turn_number_at_max_minus_one(self) -> None:
        result = _make_result(turn_number=99999)
        assert result.turn_number == 99999

    def test_rejects_string_transition_type(self) -> None:
        with pytest.raises(TypeError, match="expected TransitionType"):
            _make_result(transition_type="coding")  # type: ignore[arg-type]

    def test_rejects_non_string_outcome(self) -> None:
        with pytest.raises(TypeError, match="expected str or None for outcome"):
            _make_result(outcome=123)  # type: ignore[arg-type]

    def test_accepts_none_outcome(self) -> None:
        result = _make_result(outcome=None)
        assert result.outcome is None

    def test_rejects_non_string_message(self) -> None:
        with pytest.raises(TypeError, match="expected str for message"):
            _make_result(message=123)  # type: ignore[arg-type]

    def test_rejects_non_string_commit_hash(self) -> None:
        with pytest.raises(TypeError, match="expected str for commit_hash"):
            _make_result(commit_hash=123)  # type: ignore[arg-type]

    def test_rejects_relative_log_file(self) -> None:
        with pytest.raises(ValueError, match="absolute"):
            _make_result(log_file=Path("relative/path.log"))

    def test_rejects_empty_log_file(self) -> None:
        with pytest.raises(ValueError, match="absolute"):
            _make_result(log_file=Path(""))

    def test_rejects_naive_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            _make_result(timestamp=datetime.now())

    def test_normalizes_timestamp_to_utc(self) -> None:
        ts = datetime(2025, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))
        result = _make_result(timestamp=ts)
        assert result.timestamp.tzinfo == timezone.utc
        assert result.timestamp == ts.astimezone(timezone.utc)
