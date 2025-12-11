from afk.driver import Driver
from afk.turn_result import TurnResult


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
        raise RuntimeError(f"Driver exited with code {exit_code}")

    # Capture HEAD after execution
    head_after = git.head_commit()
    if head_after is None:
        raise RuntimeError("No commits after execution (HEAD is unborn)")

    # Find commits made during execution
    commits = git.commits_between(head_before, head_after)

    # Happy path: exactly one commit
    if len(commits) != 1:
        raise RuntimeError(f"Expected 1 commit, got {len(commits)}")
    commit_hash = commits[0]

    # Parse outcome from commit message
    outcome, message = git.parse_commit_message(commit_hash)

    return TurnResult(
        outcome=outcome,
        message=message,
        commit_hash=commit_hash,
    )
