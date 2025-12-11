from typing import Optional, Protocol

from afk.git import Git
from afk.turn_result import TurnResult


class DriverProtocol(Protocol):
    def run(self, prompt: str, log_file: str) -> int: ...


def execute_turn(
    driver: DriverProtocol,
    git: Git,
    prompt: str,
    log_file: str,
) -> TurnResult:
    """Execute a single turn: run prompt, detect commit, extract result.

    Captures HEAD before execution, runs the driver, detects commits made,
    and returns a TurnResult with the outcome extracted from the commit message.

    This is the happy path implementation - expects exactly one commit.
    Exception handling for zero/multiple commits is deferred to Story 1.4.
    """
    # Capture HEAD before execution (may be None for empty repo)
    head_before: Optional[str] = git.head_commit()

    # Execute the prompt via driver
    driver.run(prompt, log_file)

    # Capture HEAD after execution
    head_after: Optional[str] = git.head_commit()

    # Find commits made during execution
    commits = git.commits_between(head_before, head_after)

    # Happy path: exactly one commit
    # Story 1.4 will handle zero/multiple commits
    assert len(commits) == 1, f"Expected 1 commit, got {len(commits)}"
    commit_hash = commits[0]

    # Parse outcome from commit message
    outcome, message = git.parse_commit_message(commit_hash)

    return TurnResult(
        outcome=outcome,
        message=message,
        commit_hash=commit_hash,
    )
