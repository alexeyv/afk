import traceback
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import ClassVar

from afk.driver import Driver
from afk.git import Git
from afk.transition_type import TransitionType
from afk.turn_log import TurnLog
from afk.turn_result import TurnResult


class TurnState(Enum):
    """States of a Turn in its lifecycle."""

    INITIAL = auto()
    IN_PROGRESS = auto()
    FINISHED = auto()
    ABORTED = auto()


class Turn:
    """Mutable state machine representing an active turn.

    Lifecycle:
        Initial -> InProgress (via start())
        InProgress -> Finished (via finish())
        InProgress -> Aborted (via abort())

    The Turn owns its lifecycle and logging. Session creates a Turn,
    calls start(), execute(), then finish() or abort().
    """

    MAX_TURN_NUMBER: ClassVar[int] = 100_000

    def __init__(self, driver: Driver, git: Git, session_root: Path) -> None:
        """Create a new Turn in Initial state.

        Args:
            driver: The Driver to use for execution.
            git: The Git instance for repository operations.
            session_root: Session root directory for logging.
        """
        if not isinstance(driver, Driver):
            raise TypeError(f"expected Driver, got {driver!r}")
        if not isinstance(git, Git):
            raise TypeError(f"expected Git, got {git!r}")
        if not isinstance(session_root, Path):
            raise TypeError(f"expected Path, got {session_root!r}")
        if not session_root.is_absolute():
            raise ValueError("session_root must be an absolute path")

        self._driver = driver
        self._git = git
        self._session_root = session_root
        self._number: int | None = None  # Allocated in start() to prevent leaks
        self._state = TurnState.INITIAL
        self._turn_log: TurnLog | None = None
        self._transition_type: TransitionType | None = None
        self._timestamp: datetime | None = None
        self._head_before: str | None = None

    def __repr__(self) -> str:
        return f"Turn(number={self._number}, state={self._state.name})"

    @property
    def number(self) -> int:
        """Return the turn number. Raises if not started."""
        if self._number is None:
            raise RuntimeError(
                f"Cannot get number: Turn is in {self._state.name} state, expected IN_PROGRESS or later"
            )
        return self._number

    @property
    def state(self) -> TurnState:
        """Return the current state."""
        return self._state

    @property
    def log_file(self) -> Path:
        """Return the log file path. Raises if not started."""
        if self._turn_log is None:
            raise RuntimeError(
                f"Cannot get log_file: Turn is in {self._state.name} state, expected IN_PROGRESS or later"
            )
        return self._turn_log.path

    @property
    def head_before(self) -> str | None:
        """Return HEAD commit hash captured at start(). None for empty repo."""
        return self._head_before

    def start(self, turn_number: int, transition_type: TransitionType) -> None:
        """Transition from Initial to InProgress.

        Creates the TurnLog and writes START marker.

        Args:
            turn_number: The turn number allocated by Session.
            transition_type: The type of transition for this turn.

        Raises:
            RuntimeError: If not in Initial state.
            TypeError: If turn_number or transition_type have wrong types.
            ValueError: If turn_number is out of valid range.
        """
        if self._state != TurnState.INITIAL:
            raise RuntimeError(
                f"Cannot start: Turn is in {self._state.name} state, expected INITIAL"
            )
        if not isinstance(turn_number, int):
            raise TypeError(f"expected int for turn_number, got {turn_number!r}")
        if turn_number < 1:
            raise ValueError(f"turn_number must be >= 1, got {turn_number}")
        if turn_number >= self.MAX_TURN_NUMBER:
            raise ValueError(f"turn_number {turn_number} >= {self.MAX_TURN_NUMBER}")
        if not isinstance(transition_type, TransitionType):
            raise TypeError(f"expected TransitionType, got {transition_type!r}")

        self._number = turn_number
        self._transition_type = transition_type
        self._timestamp = datetime.now(timezone.utc)
        self._head_before = self._git.head_commit()
        self._turn_log = TurnLog(self._number, transition_type, self._session_root)
        self._state = TurnState.IN_PROGRESS

    def execute(self, prompt: str) -> int:
        """Execute the turn via the driver.

        Requires InProgress state. Uses the log file created during start().

        Args:
            prompt: The prompt to send to the driver.

        Returns:
            Exit code from the driver.

        Raises:
            RuntimeError: If not in InProgress state.
        """
        if self._state != TurnState.IN_PROGRESS:
            raise RuntimeError(
                f"Cannot execute: Turn is in {self._state.name} state, expected IN_PROGRESS"
            )

        assert self._turn_log is not None
        return self._driver.run(prompt, str(self._turn_log.path))

    def finish(self, outcome: str | None, commit_hash: str, message: str) -> TurnResult:
        """Transition from InProgress to Finished.

        Logs END marker and creates frozen TurnResult.

        Args:
            outcome: The outcome string (e.g., "success", "failure").
            commit_hash: The git commit hash.
            message: The commit message.

        Returns:
            Frozen TurnResult record.

        Raises:
            RuntimeError: If not in InProgress state.
        """
        if self._state != TurnState.IN_PROGRESS:
            raise RuntimeError(
                f"Cannot finish: Turn is in {self._state.name} state, expected IN_PROGRESS"
            )

        assert self._number is not None
        assert self._turn_log is not None
        assert self._transition_type is not None
        assert self._timestamp is not None

        self._turn_log.log(f"=== Turn {self._number} END: {outcome} ===")
        self._state = TurnState.FINISHED

        return TurnResult(
            turn_number=self._number,
            transition_type=self._transition_type,
            outcome=outcome,
            message=message,
            commit_hash=commit_hash,
            log_file=self._turn_log.path,
            timestamp=self._timestamp,
        )

    def abort(self, exception: Exception) -> None:
        """Transition from InProgress to Aborted.

        Logs ABORT marker with exception details and re-raises.

        Args:
            exception: The exception that caused the abort.

        Raises:
            The passed exception after logging.
        """
        if self._state != TurnState.IN_PROGRESS:
            raise RuntimeError(
                f"Cannot abort: Turn is in {self._state.name} state, expected IN_PROGRESS"
            )

        if self._turn_log is not None:
            try:
                self._turn_log.log(
                    f"=== Turn {self._number} ABORT: {type(exception).__name__} ===\n"
                    f"{exception}\n{traceback.format_exc()}"
                )
            except Exception:
                pass

        self._state = TurnState.ABORTED
        raise exception
