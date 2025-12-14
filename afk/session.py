from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from afk.driver import Driver
from afk.executor import execute_turn as executor_execute_turn
from afk.transition_type import TransitionType
from afk.turn import Turn
from afk.turn_log import TurnLog


class Session:
    """Tracks all turns in sequence for a session run.

    A mutable container that stores Turn instances and provides
    chronological access. Turn numbers must be added sequentially
    starting from 1.
    """

    def __init__(self, root_dir: Path, driver: Driver) -> None:
        self._validate_root_dir(root_dir)
        self._validate_driver(driver)
        self._root_dir = root_dir
        self._driver = driver
        self._turns: list[Turn] = []

    @staticmethod
    def _validate_root_dir(root_dir: Path) -> None:
        if not isinstance(root_dir, Path):
            raise TypeError(f"expected Path, got {root_dir!r}")
        if not root_dir.is_absolute():
            raise ValueError("root_dir must be an absolute path")
        if not root_dir.is_dir():
            raise ValueError(f"root_dir must be a directory: {root_dir}")

    @staticmethod
    def _validate_driver(driver: Driver) -> None:
        if not isinstance(driver, Driver):
            raise TypeError(f"expected Driver, got {driver!r}")

    @property
    def root_dir(self) -> Path:
        """Return the session root directory."""
        return self._root_dir

    @property
    def log_dir(self) -> Path:
        """Return the log directory (root_dir / 'logs')."""
        return self._root_dir / "logs"

    def execute_turn(self, prompt: str, transition_type: TransitionType) -> Turn:
        """Execute a turn and record it in the session.

        Creates the next sequential turn, executes via Driver, and adds
        to session. Only records a Turn if execution succeeds and produces
        a commit. Exceptions propagate without recording a Turn.
        """
        turn_number = Turn.next_turn_number()
        turn_log = TurnLog(turn_number, transition_type, self.root_dir)
        timestamp = datetime.now(timezone.utc)

        result = executor_execute_turn(self._driver, prompt, str(turn_log.path))
        turn = Turn(
            turn_number=turn_number,
            transition_type=transition_type,
            result=result,
            log_file=turn_log.path,
            timestamp=timestamp,
        )
        self.add_turn(turn)
        return turn

    def add_turn(self, turn: Turn) -> None:
        """Add a turn to the session.

        Args:
            turn: The Turn to add. Must have turn_number greater than
                  the last turn's number (monotonically increasing).

        Raises:
            TypeError: If turn is not a Turn instance.
            ValueError: If turn_number is not monotonically increasing.
        """
        if not isinstance(turn, Turn):
            raise TypeError(f"expected Turn, got {turn!r}")
        if self._turns:
            last = self._turns[-1].turn_number
            if turn.turn_number <= last:
                raise ValueError(
                    f"Turn number must be > {last}, got {turn.turn_number}"
                )
        else:
            if turn.turn_number != 1:
                raise ValueError(f"First turn must be turn 1, got {turn.turn_number}")
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
        return f"Session(root_dir={self._root_dir}, turns={len(self._turns)})"

    def __getitem__(self, n: int) -> Turn:
        return self.turn(n)

    @property
    def turns(self) -> tuple[Turn, ...]:
        """Immutable view of all turns in chronological order."""
        return tuple(self._turns)
