import subprocess
import uuid
from pathlib import Path
from unittest.mock import Mock

import pytest

from afk.driver import Driver
from afk.executor import execute_turn
from afk.git import Git
from afk.turn_result import TurnResult


@pytest.fixture
def git_repo(tmp_path: Path) -> Git:
    """Create a temp git repo with user config for commits."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return Git(str(tmp_path))


def make_commit(git: Git, message: str) -> str:
    """Helper to create a commit and return its hash."""
    repo_path = Path(git.repo_path)
    filename = f"file_{uuid.uuid4().hex[:8]}.txt"
    (repo_path / filename).write_text(f"commit: {message}")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    return git.head_commit()


def mock_driver(git: Git, run_fn) -> Driver:
    """Create a mock driver with custom run function."""
    driver = Mock(spec=Driver)
    driver.git = git
    driver.run = run_fn
    return driver


class TestExecuteTurnWithOneCommit:
    def test_returns_turn_result_with_single_commit(
        self, git_repo: Git, tmp_path: Path
    ):
        make_commit(git_repo, "initial commit")

        def mock_run(prompt: str, log_file: str) -> int:
            make_commit(git_repo, "feat: agent work\n\noutcome: success")
            return 0

        driver = mock_driver(git_repo, mock_run)

        result = execute_turn(
            driver=driver,
            prompt="do something",
            log_file=str(tmp_path / "log.txt"),
        )

        assert isinstance(result, TurnResult)
        assert result.outcome == "success"
        assert "feat: agent work" in result.message
        assert len(result.commit_hash) >= 40

    def test_extracts_outcome_from_commit_message(self, git_repo: Git, tmp_path: Path):
        make_commit(git_repo, "initial commit")

        def mock_run(prompt: str, log_file: str) -> int:
            make_commit(git_repo, "fix: bug fix\n\noutcome: failure")
            return 0

        driver = mock_driver(git_repo, mock_run)

        result = execute_turn(
            driver=driver,
            prompt="fix bug",
            log_file=str(tmp_path / "log.txt"),
        )

        assert result.outcome == "failure"
        assert "fix: bug fix" in result.message

    def test_works_with_no_prior_commits(self, git_repo: Git, tmp_path: Path):
        def mock_run(prompt: str, log_file: str) -> int:
            make_commit(git_repo, "feat: first feature\n\noutcome: success")
            return 0

        driver = mock_driver(git_repo, mock_run)

        result = execute_turn(
            driver=driver,
            prompt="start project",
            log_file=str(tmp_path / "log.txt"),
        )

        assert isinstance(result, TurnResult)
        assert result.outcome == "success"
        assert "feat: first feature" in result.message


class TestExecuteTurnEdgeCases:
    def test_outcome_none_when_not_in_message(self, git_repo: Git, tmp_path: Path):
        make_commit(git_repo, "initial")

        def mock_run(prompt: str, log_file: str) -> int:
            make_commit(git_repo, "chore: update deps")
            return 0

        driver = mock_driver(git_repo, mock_run)

        result = execute_turn(
            driver=driver,
            prompt="update",
            log_file=str(tmp_path / "log.txt"),
        )

        assert result.outcome is None
        assert "chore: update deps" in result.message

    def test_raises_on_nonzero_exit_code(self, git_repo: Git, tmp_path: Path):
        make_commit(git_repo, "initial")

        def mock_run(prompt: str, log_file: str) -> int:
            return 1

        driver = mock_driver(git_repo, mock_run)

        with pytest.raises(RuntimeError, match="Driver exited with code 1"):
            execute_turn(
                driver=driver,
                prompt="fail",
                log_file=str(tmp_path / "log.txt"),
            )
