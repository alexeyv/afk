"""Turn log file naming utilities.

This module provides the TurnLog class for generating log file names
following the pattern turn-{NNN}-{type}.log.
"""

from pathlib import Path

from afk.transition_type import TransitionType


class TurnLog:
    """Log file for a specific turn.

    Creates a fresh log file at instantiation with a START marker.
    Subsequent log() calls append to the file.

    Args:
        turn_number: The turn number (1-99999).
        transition_type: The type of transition (e.g., "init", "coding").
        session_root: Session root directory. Logs go in session_root/logs/.

    Example:
        >>> log = TurnLog(3, TransitionType("coding"), Path("/session"))
        >>> log.filename
        'turn-00003-coding.log'
        >>> log.path
        Path('/session/logs/turn-00003-coding.log')
    """

    def __init__(
        self, turn_number: int, transition_type: TransitionType, session_root: Path
    ) -> None:
        if not 1 <= turn_number <= 99999:
            raise ValueError(
                f"turn_number must be between 1 and 99999, got {turn_number}"
            )
        if not isinstance(transition_type, TransitionType):
            raise TypeError(f"expected TransitionType, got {transition_type!r}")
        if not isinstance(session_root, Path):
            raise TypeError(f"expected Path, got {session_root!r}")
        self._turn_number = turn_number
        self._transition_type = transition_type
        self._session_root = session_root
        self._init_log_file()

    def _init_log_file(self) -> None:
        """Create fresh log file with START marker."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            f.write(f"=== Turn {self._turn_number} START ===\n")

    @property
    def filename(self) -> str:
        """Return the log filename following pattern turn-{NNNNN}-{type}.log."""
        return f"turn-{self._turn_number:05d}-{self._transition_type}.log"

    @property
    def log_dir(self) -> Path:
        """Return the log directory (session_root/logs)."""
        return self._session_root / "logs"

    @property
    def path(self) -> Path:
        """Return the absolute path to the log file."""
        return (self.log_dir / self.filename).absolute()

    def log(self, message: str) -> None:
        """Append a message to the log file, creating the log directory if needed."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(message + "\n")

    def __repr__(self) -> str:
        return f"TurnLog({self._turn_number}, {self._transition_type!r}, {self._session_root!r})"
