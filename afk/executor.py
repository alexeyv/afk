import signal
from pathlib import Path

from afk.driver import Driver
from afk.turn_result import TurnResult

# Map common signals to human-readable names
SIGNAL_NAMES = {
    signal.SIGTERM: "SIGTERM",
    signal.SIGKILL: "SIGKILL",
    signal.SIGINT: "SIGINT",
    signal.SIGSEGV: "SIGSEGV",
    signal.SIGABRT: "SIGABRT",
}


def _read_last_lines(file_path: str, n: int = 5) -> str:
    """Read last n lines from a file, or all if fewer lines exist."""
    try:
        path = Path(file_path)
        if not path.exists():
            return "(log file not found)"
        lines = path.read_text().splitlines()
        last_lines = lines[-n:] if len(lines) >= n else lines
        return "\n".join(last_lines)
    except Exception:
        return "(could not read log file)"


def _multiple_commits_error(
    commits: list[str],
    git: "Git",
) -> RuntimeError:
    """Build detailed error for multiple commits case."""
    from afk.git import Git  # noqa: F811 - type hint forward ref

    # Get hash:subject for each commit
    commit_lines = []
    for commit_hash in commits:
        try:
            output = git._run("log", "-1", "--format=%h: %s", commit_hash, "--")
            commit_lines.append(f"  - {output}")
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
    signal_name = SIGNAL_NAMES.get(signal_num, f"signal {signal_num}")
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


def _no_commit_error(
    head_before: str | None,
    head_after: str,
    log_file: str,
) -> RuntimeError:
    """Build detailed error for zero commits case."""
    last_lines = _read_last_lines(log_file)
    head_before_str = head_before[:7] if head_before else "(empty repo)"
    head_after_str = head_after[:7]

    msg = f"""No commit detected during turn execution.

HEAD before: {head_before_str}
HEAD after: {head_after_str}
Log file: {log_file}

Last 5 lines of log:
{last_lines}"""
    return RuntimeError(msg)


def execute_turn(
    driver: Driver,
    prompt: str,
    log_file: str,
) -> TurnResult:
    """Execute a single turn: run prompt, detect commit, extract result.

    Captures HEAD before execution, runs the driver, detects commits made,
    and returns a TurnResult with the outcome extracted from the commit message.

    This is the happy path implementation - expects exactly one commit.
    Exception handling for zero/multiple commits is deferred to Story 1.4.
    """
    git = driver.git

    # Capture HEAD before execution (may be None for empty repo)
    head_before = git.head_commit()

    # Execute the prompt via driver
    exit_code = driver.run(prompt, log_file)
    if exit_code != 0:
        # Negative exit code indicates signal termination on Unix
        if exit_code < 0:
            raise _signal_error(-exit_code, log_file)
        raise _nonzero_exit_error(exit_code, log_file)

    # Capture HEAD after execution
    head_after = git.head_commit()
    if head_after is None:
        raise RuntimeError("No commits after execution (HEAD is unborn)")

    # Find commits made during execution
    commits = git.commits_between(head_before, head_after)

    # Validate exactly one commit
    if len(commits) == 0:
        raise _no_commit_error(head_before, head_after, log_file)
    if len(commits) > 1:
        raise _multiple_commits_error(commits, git)
    commit_hash = commits[0]

    # Parse outcome from commit message
    outcome, message = git.parse_commit_message(commit_hash)

    return TurnResult(
        outcome=outcome,
        message=message,
        commit_hash=commit_hash,
    )
