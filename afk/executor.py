import signal
import subprocess

from afk.git import Git

# Map common signals to human-readable names
SIGNAL_NAMES: dict[int, str] = {
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
        # First cap bytes to avoid reading huge files, then take last 5 lines
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


def _multiple_commits_error(
    commits: list[str],
    git: Git,
) -> RuntimeError:
    """Build detailed error for multiple commits case."""

    # Get hash:subject for each commit
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
    head: str,
    log_file: str,
) -> RuntimeError:
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


def validate_turn_execution(
    git: Git,
    exit_code: int,
    log_file: str,
    head_before: str | None,
) -> tuple[str | None, str, str]:
    """Validate turn execution and extract commit info.

    Called after Turn.execute() to validate the result and extract
    outcome, commit_hash, and message for Turn.finish().

    Args:
        git: Git instance for the repository.
        exit_code: Exit code from driver.run().
        log_file: Path to the turn log file.
        head_before: HEAD commit hash captured before execution (None for empty repo).

    Returns:
        Tuple of (outcome, commit_hash, message).

    Raises:
        RuntimeError: For zero commits, multiple commits, non-zero exit,
                      signal termination, or other validation failures.
    """
    # Check exit code first
    if exit_code != 0:
        if exit_code < 0:
            raise _signal_error(-exit_code, log_file)
        raise _nonzero_exit_error(exit_code, log_file)

    # Capture HEAD after execution
    head_after = git.head_commit()
    if head_after is None:
        raise RuntimeError("No commits after execution (HEAD is unborn)")

    # Check if HEAD changed at all
    if head_before == head_after:
        raise _no_commit_error(head_after, log_file)

    # Find commits made during execution
    commits = git.commits_between(head_before, head_after)

    # Validate exactly one commit
    if len(commits) == 0:
        raise _ancestry_mismatch_error(head_before, head_after, log_file)
    if len(commits) > 1:
        raise _multiple_commits_error(commits, git)
    commit_hash = commits[0]

    # Parse outcome from commit message
    outcome, message = git.parse_commit_message(commit_hash)

    return (outcome, commit_hash, message)
