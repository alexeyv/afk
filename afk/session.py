import signal
import subprocess
from pathlib import Path
from typing import Iterator

from afk.driver import Driver
from afk.git import Git
from afk.transition_type import TransitionType
from afk.turn import Turn
from afk.turn_result import TurnResult

# Map common signals to human-readable names
_SIGNAL_NAMES: dict[int, str] = {
    signal.SIGTERM: "SIGTERM",
    signal.SIGKILL: "SIGKILL",
    signal.SIGINT: "SIGINT",
    signal.SIGSEGV: "SIGSEGV",
    signal.SIGABRT: "SIGABRT",
}


def _read_log_tail(file_path: str) -> str:
    """Read last 5 lines from log, max 2000 bytes total."""
    import shlex

    try:
        result = subprocess.run(
            f"tail -c 2000 {shlex.quote(file_path)} | tail -n 5",
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return "(could not read log file)"
        return result.stdout.rstrip("\n")
    except Exception:
        return "(could not read log file)"


def _multiple_commits_error(commits: list[str], git: Git) -> RuntimeError:
    """Build detailed error for multiple commits case."""
    commit_lines: list[str] = []
    for commit_hash in commits:
        try:
            summary = git.commit_summary(commit_hash)
            commit_lines.append(f"  - {summary}")
        except Exception:
            commit_lines.append(f"  - {commit_hash[:7]}: (could not read)")

    commits_list = "\n".join(commit_lines)

    msg = f"""Multiple commits detected during turn execution.

Expected: 1 commit
Found: {len(commits)} commits
{commits_list}

The framework expects exactly one commit per turn. Review the prompt
to ensure the agent commits all work in a single commit."""
    return RuntimeError(msg)


def _signal_error(signal_num: int, log_file: str) -> RuntimeError:
    """Build detailed error for signal termination case."""
    signal_name = _SIGNAL_NAMES.get(signal_num, f"signal {signal_num}")
    msg = f"""Claude Code CLI process was terminated by signal.

Signal: {signal_name} ({signal_num})
Log file: {log_file}

The process was killed externally. This may indicate:
- User pressed Ctrl+C
- System ran out of resources
- Process was killed by another tool"""
    return RuntimeError(msg)


def _nonzero_exit_error(exit_code: int, log_file: str) -> RuntimeError:
    """Build detailed error for non-zero exit code case."""
    msg = f"""Claude Code CLI process failed.

Exit code: {exit_code}
Log file: {log_file}

Review the log file for error details."""
    return RuntimeError(msg)


def _no_commit_error(head: str, log_file: str) -> RuntimeError:
    """Build detailed error when HEAD unchanged (agent made no commit)."""
    last_lines = _read_log_tail(log_file)

    msg = f"""No commit at end of turn.

HEAD: {head[:7]}
Log file: {log_file}

Log tail:
{last_lines}"""
    return RuntimeError(msg)


def _ancestry_mismatch_error(
    head_before: str | None,
    head_after: str,
    log_file: str,
) -> RuntimeError:
    """Build detailed error when HEAD moved but not on expected ancestry path."""
    head_before_str = head_before[:7] if head_before else "(empty repo)"

    msg = f"""HEAD changed but no commits found on ancestry path.

HEAD before: {head_before_str}
HEAD after: {head_after[:7]}
Log file: {log_file}

This may indicate the agent switched branches or reset HEAD."""
    return RuntimeError(msg)


class Session:
    __slots__ = ("_root_dir", "_driver", "_git", "_turns", "_next_turn_number")

    """Tracks all turns in sequence for a session run.

    A mutable container that stores TurnResult instances and provides
    chronological access. Turn numbers must be added sequentially
    starting from 1.
    """

    MAX_TURN_NUMBER: int = 100_000

    def __init__(self, root_dir: Path, driver: Driver, git: Git) -> None:
        self._validate_root_dir(root_dir)
        self._validate_driver(driver)
        self._validate_git(git)
        self._root_dir = root_dir
        self._driver = driver
        self._git = git
        self._turns: list[TurnResult] = []
        self._next_turn_number = 1

    def __repr__(self) -> str:
        return f"Session(root_dir={self._root_dir}, turns={len(self._turns)})"

    def __iter__(self) -> Iterator[TurnResult]:
        """Iterate over turns in chronological order."""
        return iter(tuple(self._turns))

    def __len__(self) -> int:
        return len(self._turns)

    def __getitem__(self, n: int) -> TurnResult:
        return self.turn(n)

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

    @staticmethod
    def _validate_git(git: Git) -> None:
        if not isinstance(git, Git):
            raise TypeError(f"expected Git, got {git!r}")

    @property
    def root_dir(self) -> Path:
        """Return the session root directory."""
        return self._root_dir

    @property
    def log_dir(self) -> Path:
        """Return the log directory (root_dir / 'logs')."""
        return self._root_dir / "logs"

    @property
    def turns(self) -> tuple[TurnResult, ...]:
        """Immutable view of all turns in chronological order."""
        return tuple(self._turns)

    def allocate_turn_number(self, resume_from: int | None = None) -> int:
        """Allocate and return the next turn number.

        Args:
            resume_from: If provided, resume counting from this number.
                         Returns this number and sets next to resume_from + 1.

        Returns:
            The allocated turn number.

        Raises:
            ValueError: If resume_from is invalid or number exceeds maximum.
        """
        if resume_from is not None:
            if resume_from < 1:
                raise ValueError(f"resume_from must be >= 1, got {resume_from}")
            if resume_from >= self.MAX_TURN_NUMBER:
                raise ValueError(f"resume_from {resume_from} >= {self.MAX_TURN_NUMBER}")
            self._next_turn_number = resume_from + 1
            return resume_from

        n = self._next_turn_number
        if n >= self.MAX_TURN_NUMBER:
            raise ValueError(f"turn_number {n} >= {self.MAX_TURN_NUMBER}")
        self._next_turn_number += 1
        return n

    def build_turn_result(
        self,
        turn: Turn,
        exit_code: int,
    ) -> TurnResult:
        """Build TurnResult from execution state.

        Validates exit code and git state, then constructs TurnResult.
        Override in subclasses for custom validation policies.

        Args:
            turn: The Turn being completed (provides metadata and log file).
            exit_code: Exit code from driver.run().

        Returns:
            Completed TurnResult.

        Raises:
            RuntimeError: For zero commits, multiple commits, non-zero exit,
                          signal termination, or other validation failures.
        """
        log_file = str(turn.log_file)
        head_before = turn.head_before
        # Check exit code first
        if exit_code != 0:
            if exit_code < 0:
                raise _signal_error(-exit_code, log_file)
            raise _nonzero_exit_error(exit_code, log_file)

        # Capture HEAD after execution
        head_after = self._git.head_commit()
        if head_after is None:
            raise RuntimeError("No commits after execution (HEAD is unborn)")

        # Check if HEAD changed at all
        if head_before == head_after:
            raise _no_commit_error(head_after, log_file)

        # Find commits made during execution
        commits = self._git.commits_between(head_before, head_after)

        # Validate exactly one commit
        if len(commits) == 0:
            raise _ancestry_mismatch_error(head_before, head_after, log_file)
        if len(commits) > 1:
            raise _multiple_commits_error(commits, self._git)
        commit_hash = commits[0]

        # Parse outcome from commit message
        outcome, message = self._git.parse_commit_message(commit_hash)

        return turn.finish(outcome, commit_hash, message)

    def execute_turn(self, prompt: str, transition_type: TransitionType) -> TurnResult:
        """Execute a turn and record it in the session.

        Creates a Turn, executes via Driver, resolves the turn result,
        and records the TurnResult. Only records on success. Exceptions
        propagate after logging ABORT.
        """
        turn_number = self.allocate_turn_number()
        turn = Turn(self._driver, self._git, self._root_dir)
        turn.start(turn_number, transition_type)

        try:
            exit_code = turn.execute(prompt)
            result = self.build_turn_result(turn, exit_code)
        except Exception as e:
            turn.abort(e)
            # abort() re-raises, so this line is never reached
            raise  # for type checker

        self._add_result(result)
        return result

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
            if t.turn_number <= prev:
                raise RuntimeError("internal error: turns not monotonic")
            if t.turn_number == n:
                return t
            if t.turn_number > n:
                break
            prev = t.turn_number
        raise KeyError(n)

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
