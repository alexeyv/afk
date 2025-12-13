"""TransitionType value class for validated transition type identifiers."""

import re


_TRANSITION_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")


class TransitionType:
    """Immutable value class for transition type identifiers.

    Validates that the transition type matches the pattern ^[a-z][a-z0-9_.-]*$
    at construction time. Implements __str__, __repr__, __eq__, and __hash__
    for use as a value object in sets and dicts.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"expected str, got {value!r}")
        if not _TRANSITION_TYPE_PATTERN.match(value):
            raise ValueError(
                f"TransitionType must match pattern ^[a-z][a-z0-9_.-]*$: {value!r}"
            )
        self._value = value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"TransitionType({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransitionType):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
