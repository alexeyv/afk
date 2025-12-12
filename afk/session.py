from typing import Iterator

from afk.turn import Turn


class Session:
    """Tracks all turns in sequence for a session run.

    A mutable container that stores Turn instances and provides
    chronological access. Turn numbers must be added sequentially
    starting from 1.
    """

    def __init__(self) -> None:
        self._turns: list[Turn] = []

    def add_turn(self, turn: Turn) -> None:
        """Add a turn to the session.

        Args:
            turn: The Turn to add. Must have turn_number matching
                  the expected next sequential number.

        Raises:
            ValueError: If turn_number doesn't match expected sequence.
        """
        expected = len(self._turns) + 1
        if turn.turn_number != expected:
            raise ValueError(f"Expected turn number {expected}, got {turn.turn_number}")
        self._turns.append(turn)

    def turn(self, n: int) -> Turn:
        """Get a turn by its turn number.

        Args:
            n: The turn number to look up.

        Returns:
            The Turn with the specified turn_number.

        Raises:
            KeyError: If no turn with that number exists.
        """
        prev = 0
        for t in self._turns:
            assert t.turn_number > prev, "Turns not monotonic"
            if t.turn_number == n:
                return t
            if t.turn_number > n:
                break
            prev = t.turn_number
        raise KeyError(n)

    def __iter__(self) -> Iterator[Turn]:
        """Iterate over turns in chronological order."""
        return iter(tuple(self._turns))

    def __len__(self) -> int:
        return len(self._turns)

    def __repr__(self) -> str:
        return f"Session(turns={len(self._turns)})"

    def __getitem__(self, n: int) -> Turn:
        return self.turn(n)

    @property
    def turns(self) -> tuple[Turn, ...]:
        """Immutable view of all turns in chronological order."""
        return tuple(self._turns)
