"""Turn log file naming utilities.

This module provides the TurnLog class for generating log file names
following the pattern turn-{NNN}-{type}.log.
"""

import re
from pathlib import Path

_TRANSITION_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")


class TurnLog:
    """Log file naming for a specific turn.

    Generates log file names following the pattern turn-{NNNNN}-{type}.log
    where NNNNN is a zero-padded 5-digit turn number.

    Args:
        turn_number: The turn number (1-99999).
        transition_type: The type of transition (e.g., "init", "coding").
        log_dir: Directory where log files are stored.

    Example:
        >>> log = TurnLog(3, "coding", Path("/logs"))
        >>> log.filename
        'turn-00003-coding.log'
        >>> log.path
        Path('/logs/turn-00003-coding.log')
    """

    def __init__(self, turn_number: int, transition_type: str, log_dir: Path) -> None:
        if not 1 <= turn_number <= 99999:
            raise ValueError(
                f"turn_number must be between 1 and 99999, got {turn_number}"
            )
        if not _TRANSITION_TYPE_PATTERN.match(transition_type):
            raise ValueError(
                f"transition_type must be lowercase identifier "
                f"(letters, digits, underscore, hyphen, dot; must start with letter): "
                f"{transition_type!r}"
            )
        self._turn_number = turn_number
        self._transition_type = transition_type
        self._log_dir = log_dir

    @property
    def filename(self) -> str:
        """Return the log filename following pattern turn-{NNNNN}-{type}.log."""
        return f"turn-{self._turn_number:05d}-{self._transition_type}.log"

    @property
    def path(self) -> Path:
        """Return the absolute path to the log file."""
        return (self._log_dir / self.filename).absolute()

    def __repr__(self) -> str:
        return (
            f"TurnLog({self._turn_number}, {self._transition_type!r}, {self._log_dir})"
        )
