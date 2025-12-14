"""Tests for TurnLog class."""

from pathlib import Path

import pytest

from afk.transition_type import TransitionType
from afk.turn_log import TurnLog


class TestTurnLogFilename:
    """Tests for TurnLog.filename property."""

    def test_basic_format(self, tmp_path: Path) -> None:
        """AC #1: turn number 3 with transition type 'coding' produces 'turn-00003-coding.log'."""
        log = TurnLog(3, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-00003-coding.log"

    def test_zero_padding_single_digit(self, tmp_path: Path) -> None:
        """Single digit turn numbers are zero-padded to 5 digits."""
        log = TurnLog(1, TransitionType("init"), tmp_path)
        assert log.filename == "turn-00001-init.log"

    def test_zero_padding_double_digit(self, tmp_path: Path) -> None:
        """Zero-padding works for double digit turn numbers."""
        log = TurnLog(10, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-00010-coding.log"

    def test_zero_padding_triple_digit(self, tmp_path: Path) -> None:
        """Zero-padding works for triple digit turn numbers."""
        log = TurnLog(100, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-00100-coding.log"

    def test_zero_padding_four_digit(self, tmp_path: Path) -> None:
        """Zero-padding works for four digit turn numbers."""
        log = TurnLog(1000, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-01000-coding.log"

    def test_zero_padding_max_turns(self, tmp_path: Path) -> None:
        """Zero-padding works for maximum turn count."""
        log = TurnLog(99999, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-99999-coding.log"

    def test_different_transition_types_produce_different_filenames(
        self, tmp_path: Path
    ) -> None:
        """AC #2: Different transition types produce different filenames."""
        init_log = TurnLog(1, TransitionType("init"), tmp_path)
        coding_log = TurnLog(1, TransitionType("coding"), tmp_path)
        assert init_log.filename != coding_log.filename
        assert init_log.filename == "turn-00001-init.log"
        assert coding_log.filename == "turn-00001-coding.log"

    def test_different_turn_numbers_produce_different_filenames(
        self, tmp_path: Path
    ) -> None:
        """AC #2: Different turn numbers produce different filenames."""
        turn_1 = TurnLog(1, TransitionType("coding"), tmp_path)
        turn_2 = TurnLog(2, TransitionType("coding"), tmp_path)
        assert turn_1.filename != turn_2.filename


class TestTurnLogPath:
    """Tests for TurnLog.path property."""

    def test_combines_session_root_logs_and_filename(self, tmp_path: Path) -> None:
        """Path combines session_root/logs and filename correctly."""
        log = TurnLog(3, TransitionType("coding"), tmp_path)
        expected = tmp_path / "logs" / "turn-00003-coding.log"
        assert log.path == expected

    def test_returns_absolute_path(self, tmp_path: Path) -> None:
        """Path property returns an absolute path."""
        log = TurnLog(1, TransitionType("init"), tmp_path)
        assert log.path.is_absolute()

    def test_path_with_nested_session_root(self, tmp_path: Path) -> None:
        """Path works with nested session root structures."""
        session_root = tmp_path / "runs" / "session-001"
        session_root.mkdir(parents=True)
        log = TurnLog(5, TransitionType("review"), session_root)
        assert log.path == session_root / "logs" / "turn-00005-review.log"
        assert log.path.is_absolute()

    def test_log_dir_returns_session_root_plus_logs(self, tmp_path: Path) -> None:
        """log_dir property returns session_root/logs."""
        log = TurnLog(1, TransitionType("init"), tmp_path)
        assert log.log_dir == tmp_path / "logs"


class TestTurnLogRepr:
    """Tests for TurnLog.__repr__ method."""

    def test_repr_format(self, tmp_path: Path) -> None:
        """Repr provides useful debugging information."""
        log = TurnLog(3, TransitionType("coding"), tmp_path)
        repr_str = repr(log)
        assert "TurnLog" in repr_str
        assert "3" in repr_str
        assert "coding" in repr_str


class TestTurnLogValidation:
    """Tests for TurnLog input validation (transition type validation delegated to TransitionType)."""

    def test_accepts_simple_lowercase(self, tmp_path: Path) -> None:
        """Simple lowercase transition types are valid."""
        log = TurnLog(1, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-00001-coding.log"

    def test_accepts_with_digits(self, tmp_path: Path) -> None:
        """Transition types with digits after first char are valid."""
        log = TurnLog(1, TransitionType("step2"), tmp_path)
        assert log.filename == "turn-00001-step2.log"

    def test_accepts_with_hyphen(self, tmp_path: Path) -> None:
        """Transition types with hyphens are valid."""
        log = TurnLog(1, TransitionType("code-review"), tmp_path)
        assert log.filename == "turn-00001-code-review.log"

    def test_accepts_with_underscore(self, tmp_path: Path) -> None:
        """Transition types with underscores are valid."""
        log = TurnLog(1, TransitionType("code_review"), tmp_path)
        assert log.filename == "turn-00001-code_review.log"

    def test_accepts_with_dot(self, tmp_path: Path) -> None:
        """Transition types with dots after first char are valid."""
        log = TurnLog(1, TransitionType("v1.0"), tmp_path)
        assert log.filename == "turn-00001-v1.0.log"

    def test_rejects_turn_number_zero(self, tmp_path: Path) -> None:
        """Turn number 0 raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 99999"):
            TurnLog(0, TransitionType("coding"), tmp_path)

    def test_rejects_turn_number_negative(self, tmp_path: Path) -> None:
        """Negative turn number raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 99999"):
            TurnLog(-1, TransitionType("coding"), tmp_path)

    def test_rejects_turn_number_too_large(self, tmp_path: Path) -> None:
        """Turn number > 99999 raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 99999"):
            TurnLog(100000, TransitionType("coding"), tmp_path)

    def test_accepts_turn_number_min(self, tmp_path: Path) -> None:
        """Turn number 1 is valid."""
        log = TurnLog(1, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-00001-coding.log"

    def test_accepts_turn_number_max(self, tmp_path: Path) -> None:
        """Turn number 99999 is valid."""
        log = TurnLog(99999, TransitionType("coding"), tmp_path)
        assert log.filename == "turn-99999-coding.log"

    def test_rejects_string_transition_type(self, tmp_path: Path) -> None:
        """String transition type raises TypeError."""
        with pytest.raises(TypeError, match="expected TransitionType, got 'coding'"):
            TurnLog(1, "coding", tmp_path)  # type: ignore[arg-type]

    def test_rejects_string_session_root(self) -> None:
        """String session_root raises TypeError."""
        with pytest.raises(TypeError, match="expected Path"):
            TurnLog(1, TransitionType("coding"), "/tmp")  # type: ignore[arg-type]
