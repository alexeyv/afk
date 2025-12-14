from pathlib import Path
from typing import Iterator

from afk.driver import Driver
from afk.executor import validate_turn_execution
from afk.transition_type import TransitionType
from afk.turn import Turn
from afk.turn_result import TurnResult


class Session:
    """Tracks all turns in sequence for a session run.

    A mutable container that stores TurnResult instances and provides
    chronological access. Turn numbers must be added sequentially
    starting from 1.
    """

    def __init__(self, root_dir: Path, driver: Driver) -> None:
        self._validate_root_dir(root_dir)
        self._validate_driver(driver)
        self._root_dir = root_dir
        self._driver = driver
        self._turns: list[TurnResult] = []

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

    def execute_turn(self, prompt: str, transition_type: TransitionType) -> TurnResult:
        """Execute a turn and record it in the session.

        Creates a Turn, executes via Driver, validates the git result,
        and records the TurnResult. Only records on success. Exceptions
        propagate after logging ABORT.
        """
        turn = Turn(self._driver, self._root_dir)
        turn.start(transition_type)

        try:
            exit_code = turn.execute(prompt)
            log_file_path = str(turn.log_file)

            # Validate execution result and get commit info
            outcome, commit_hash, message = validate_turn_execution(
                self._driver.git, exit_code, log_file_path, turn.head_before
            )

            result = turn.finish(outcome, commit_hash, message)
        except Exception as e:
            turn.abort(e)
            # abort() re-raises, so this line is never reached
            raise  # for type checker

        self._add_result(result)
        return result

    def _add_result(self, result: TurnResult) -> None:
        """Add a TurnResult to the session.

        Args:
            result: The TurnResult to add. Must have turn_number greater than
                    the last result's number (monotonically increasing).

        Raises:
            TypeError: If result is not a TurnResult instance.
            ValueError: If turn_number is not monotonically increasing.
        """
        if not isinstance(result, TurnResult):
            raise TypeError(f"expected TurnResult, got {result!r}")
        if self._turns:
            last = self._turns[-1].turn_number
            if result.turn_number <= last:
                raise ValueError(
                    f"Turn number must be > {last}, got {result.turn_number}"
                )
        else:
            if result.turn_number != 1:
                raise ValueError(f"First turn must be turn 1, got {result.turn_number}")
        self._turns.append(result)

    def add_turn(self, result: TurnResult) -> None:
        """Add a TurnResult to the session (public API for testing)."""
        self._add_result(result)

    def turn(self, n: int) -> TurnResult:
        """Get a TurnResult by its turn number.

        Args:
            n: The turn number to look up.

        Returns:
            The TurnResult with the specified turn_number.

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

    def __iter__(self) -> Iterator[TurnResult]:
        """Iterate over turns in chronological order."""
        return iter(tuple(self._turns))

    def __len__(self) -> int:
        return len(self._turns)

    def __repr__(self) -> str:
        return f"Session(root_dir={self._root_dir}, turns={len(self._turns)})"

    def __getitem__(self, n: int) -> TurnResult:
        return self.turn(n)

    @property
    def turns(self) -> tuple[TurnResult, ...]:
        """Immutable view of all turns in chronological order."""
        return tuple(self._turns)
