"""Tests for TransitionType value class."""

import pytest

from afk.transition_type import TransitionType


class TestTransitionTypeCreation:
    """Tests for TransitionType construction."""

    def test_accepts_simple_lowercase(self) -> None:
        """Simple lowercase transition types are valid."""
        tt = TransitionType("init")
        assert str(tt) == "init"

    def test_accepts_with_digits(self) -> None:
        """Transition types with digits after first char are valid."""
        tt = TransitionType("step2")
        assert str(tt) == "step2"

    def test_accepts_with_hyphen(self) -> None:
        """Transition types with hyphens are valid."""
        tt = TransitionType("code-review")
        assert str(tt) == "code-review"

    def test_accepts_with_underscore(self) -> None:
        """Transition types with underscores are valid."""
        tt = TransitionType("code_review")
        assert str(tt) == "code_review"

    def test_accepts_with_dot(self) -> None:
        """Transition types with dots after first char are valid."""
        tt = TransitionType("v1.0")
        assert str(tt) == "v1.0"

    def test_accepts_coding(self) -> None:
        """'coding' is a valid transition type."""
        tt = TransitionType("coding")
        assert str(tt) == "coding"


class TestTransitionTypeValidation:
    """Tests for TransitionType input validation."""

    def test_rejects_empty_string(self) -> None:
        """Empty transition type raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("")

    def test_rejects_uppercase(self) -> None:
        """Transition type with uppercase raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("Coding")

    def test_rejects_leading_digit(self) -> None:
        """Transition type starting with digit raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("2step")

    def test_rejects_leading_dot(self) -> None:
        """Transition type starting with dot raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType(".hidden")

    def test_rejects_leading_hyphen(self) -> None:
        """Transition type starting with hyphen raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("-verbose")

    def test_rejects_whitespace(self) -> None:
        """Transition type with whitespace raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("code review")

    def test_rejects_forward_slash(self) -> None:
        """Transition type with forward slash raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("foo/bar")

    def test_rejects_backslash(self) -> None:
        """Transition type with backslash raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("foo\\bar")

    def test_rejects_dollar_sign(self) -> None:
        """Transition type with dollar sign raises ValueError."""
        with pytest.raises(ValueError, match="must match pattern"):
            TransitionType("$var")

    def test_rejects_none(self) -> None:
        """None raises TypeError with clear message."""
        with pytest.raises(TypeError, match="expected str, got None"):
            TransitionType(None)  # type: ignore[arg-type]

    def test_rejects_int(self) -> None:
        """Integer raises TypeError with clear message."""
        with pytest.raises(TypeError, match="expected str, got 123"):
            TransitionType(123)  # type: ignore[arg-type]


class TestTransitionTypeEquality:
    """Tests for TransitionType equality."""

    def test_equal_values_are_equal(self) -> None:
        """Two TransitionTypes with same value are equal."""
        tt1 = TransitionType("init")
        tt2 = TransitionType("init")
        assert tt1 == tt2

    def test_different_values_not_equal(self) -> None:
        """Two TransitionTypes with different values are not equal."""
        tt1 = TransitionType("init")
        tt2 = TransitionType("coding")
        assert tt1 != tt2

    def test_not_equal_to_string(self) -> None:
        """TransitionType is not equal to raw string."""
        tt = TransitionType("init")
        assert tt != "init"

    def test_not_equal_to_none(self) -> None:
        """TransitionType is not equal to None."""
        tt = TransitionType("init")
        assert tt != None  # noqa: E711


class TestTransitionTypeHash:
    """Tests for TransitionType hashability."""

    def test_is_hashable(self) -> None:
        """TransitionType can be hashed."""
        tt = TransitionType("init")
        hash(tt)

    def test_equal_values_have_same_hash(self) -> None:
        """Equal TransitionTypes have the same hash."""
        tt1 = TransitionType("init")
        tt2 = TransitionType("init")
        assert hash(tt1) == hash(tt2)

    def test_usable_in_set(self) -> None:
        """TransitionType can be used in sets."""
        tt1 = TransitionType("init")
        tt2 = TransitionType("init")
        tt3 = TransitionType("coding")
        s = {tt1, tt2, tt3}
        assert len(s) == 2

    def test_usable_as_dict_key(self) -> None:
        """TransitionType can be used as dict key."""
        tt = TransitionType("init")
        d = {tt: "value"}
        assert d[TransitionType("init")] == "value"


class TestTransitionTypeRepr:
    """Tests for TransitionType string representations."""

    def test_str_returns_value(self) -> None:
        """__str__ returns the raw value."""
        tt = TransitionType("init")
        assert str(tt) == "init"

    def test_repr_includes_class_name(self) -> None:
        """__repr__ returns TransitionType('value') format."""
        tt = TransitionType("init")
        assert repr(tt) == "TransitionType('init')"
