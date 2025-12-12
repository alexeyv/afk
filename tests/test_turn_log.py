"""Tests for TurnLog class."""

from pathlib import Path

import pytest

from afk.turn_log import TurnLog


class TestTurnLogFilename:
    """Tests for TurnLog.filename property."""

    def test_basic_format(self, tmp_path: Path) -> None:
        """AC #1: turn number 3 with transition type 'coding' produces 'turn-00003-coding.log'."""
        log = TurnLog(3, "coding", tmp_path)
        assert log.filename == "turn-00003-coding.log"

    def test_zero_padding_single_digit(self, tmp_path: Path) -> None:
        """Single digit turn numbers are zero-padded to 5 digits."""
        log = TurnLog(1, "init", tmp_path)
        assert log.filename == "turn-00001-init.log"

    def test_zero_padding_double_digit(self, tmp_path: Path) -> None:
        """Zero-padding works for double digit turn numbers."""
        log = TurnLog(10, "coding", tmp_path)
        assert log.filename == "turn-00010-coding.log"

    def test_zero_padding_triple_digit(self, tmp_path: Path) -> None:
        """Zero-padding works for triple digit turn numbers."""
        log = TurnLog(100, "coding", tmp_path)
        assert log.filename == "turn-00100-coding.log"

    def test_zero_padding_four_digit(self, tmp_path: Path) -> None:
        """Zero-padding works for four digit turn numbers."""
        log = TurnLog(1000, "coding", tmp_path)
        assert log.filename == "turn-01000-coding.log"

    def test_zero_padding_max_turns(self, tmp_path: Path) -> None:
        """Zero-padding works for maximum turn count."""
        log = TurnLog(99999, "coding", tmp_path)
        assert log.filename == "turn-99999-coding.log"

    def test_different_transition_types_produce_different_filenames(
        self, tmp_path: Path
    ) -> None:
        """AC #2: Different transition types produce different filenames."""
        init_log = TurnLog(1, "init", tmp_path)
        coding_log = TurnLog(1, "coding", tmp_path)
        assert init_log.filename != coding_log.filename
        assert init_log.filename == "turn-00001-init.log"
        assert coding_log.filename == "turn-00001-coding.log"

    def test_different_turn_numbers_produce_different_filenames(
        self, tmp_path: Path
    ) -> None:
        """AC #2: Different turn numbers produce different filenames."""
        turn_1 = TurnLog(1, "coding", tmp_path)
        turn_2 = TurnLog(2, "coding", tmp_path)
        assert turn_1.filename != turn_2.filename


class TestTurnLogPath:
    """Tests for TurnLog.path property."""

    def test_combines_directory_and_filename(self, tmp_path: Path) -> None:
        """Path combines log_dir and filename correctly."""
        log = TurnLog(3, "coding", tmp_path)
        expected = tmp_path / "turn-00003-coding.log"
        assert log.path == expected

    def test_returns_absolute_path(self, tmp_path: Path) -> None:
        """Path property returns an absolute path."""
        log = TurnLog(1, "init", tmp_path)
        assert log.path.is_absolute()

    def test_path_with_nested_directory(self, tmp_path: Path) -> None:
        """Path works with nested directory structures."""
        nested = tmp_path / "runs" / "session-001" / "logs"
        nested.mkdir(parents=True)
        log = TurnLog(5, "review", nested)
        assert log.path == nested / "turn-00005-review.log"
        assert log.path.is_absolute()


class TestTurnLogRepr:
    """Tests for TurnLog.__repr__ method."""

    def test_repr_format(self, tmp_path: Path) -> None:
        """Repr provides useful debugging information."""
        log = TurnLog(3, "coding", tmp_path)
        repr_str = repr(log)
        assert "TurnLog" in repr_str
        assert "3" in repr_str
        assert "coding" in repr_str


class TestTurnLogValidation:
    """Tests for TurnLog input validation."""

    def test_accepts_simple_lowercase(self, tmp_path: Path) -> None:
        """Simple lowercase transition types are valid."""
        log = TurnLog(1, "coding", tmp_path)
        assert log.filename == "turn-00001-coding.log"

    def test_accepts_with_digits(self, tmp_path: Path) -> None:
        """Transition types with digits after first char are valid."""
        log = TurnLog(1, "step2", tmp_path)
        assert log.filename == "turn-00001-step2.log"

    def test_accepts_with_hyphen(self, tmp_path: Path) -> None:
        """Transition types with hyphens are valid."""
        log = TurnLog(1, "code-review", tmp_path)
        assert log.filename == "turn-00001-code-review.log"

    def test_accepts_with_underscore(self, tmp_path: Path) -> None:
        """Transition types with underscores are valid."""
        log = TurnLog(1, "code_review", tmp_path)
        assert log.filename == "turn-00001-code_review.log"

    def test_accepts_with_dot(self, tmp_path: Path) -> None:
        """Transition types with dots after first char are valid."""
        log = TurnLog(1, "v1.0", tmp_path)
        assert log.filename == "turn-00001-v1.0.log"

    def test_rejects_forward_slash(self, tmp_path: Path) -> None:
        """Transition type with forward slash raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "foo/bar", tmp_path)

    def test_rejects_backslash(self, tmp_path: Path) -> None:
        """Transition type with backslash raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "foo\\bar", tmp_path)

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        """Transition type with path traversal raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "../../../etc/passwd", tmp_path)

    def test_rejects_leading_dot(self, tmp_path: Path) -> None:
        """Transition type starting with dot raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, ".hidden", tmp_path)

    def test_rejects_leading_hyphen(self, tmp_path: Path) -> None:
        """Transition type starting with hyphen raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "-verbose", tmp_path)

    def test_rejects_uppercase(self, tmp_path: Path) -> None:
        """Transition type with uppercase raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "Coding", tmp_path)

    def test_rejects_whitespace(self, tmp_path: Path) -> None:
        """Transition type with whitespace raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "code review", tmp_path)

    def test_rejects_empty_string(self, tmp_path: Path) -> None:
        """Empty transition type raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "", tmp_path)

    def test_rejects_dollar_sign(self, tmp_path: Path) -> None:
        """Transition type with dollar sign raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "$var", tmp_path)

    def test_rejects_leading_digit(self, tmp_path: Path) -> None:
        """Transition type starting with digit raises ValueError."""
        with pytest.raises(ValueError, match="lowercase identifier"):
            TurnLog(1, "2step", tmp_path)

    def test_rejects_turn_number_zero(self, tmp_path: Path) -> None:
        """Turn number 0 raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 99999"):
            TurnLog(0, "coding", tmp_path)

    def test_rejects_turn_number_negative(self, tmp_path: Path) -> None:
        """Negative turn number raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 99999"):
            TurnLog(-1, "coding", tmp_path)

    def test_rejects_turn_number_too_large(self, tmp_path: Path) -> None:
        """Turn number > 99999 raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 99999"):
            TurnLog(100000, "coding", tmp_path)

    def test_accepts_turn_number_min(self, tmp_path: Path) -> None:
        """Turn number 1 is valid."""
        log = TurnLog(1, "coding", tmp_path)
        assert log.filename == "turn-00001-coding.log"

    def test_accepts_turn_number_max(self, tmp_path: Path) -> None:
        """Turn number 99999 is valid."""
        log = TurnLog(99999, "coding", tmp_path)
        assert log.filename == "turn-99999-coding.log"
