import os
import subprocess
import uuid
from pathlib import Path

import pytest

from afk.driver import Driver
from afk.git import Git
from afk.session import Session


def fake_claude_noop(tmp_path: Path) -> Path:
    """Create a no-op fake claude CLI script. Returns bin dir for PATH injection."""
    fake_bin = tmp_path / "fake_bin"
    fake_bin.mkdir(exist_ok=True)
    script = fake_bin / "claude"
    script.write_text("""#!/bin/bash
if [[ "$1" == "--version" ]]; then
    echo "claude-fake 1.0.0"
    exit 0
fi
echo "fake claude"
exit 0
""")
    script.chmod(0o755)
    return fake_bin


@pytest.fixture
def session_with_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Session, Git]:
    """Create a Session with git repo for testing current_turn_result."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    fake_bin = fake_claude_noop(tmp_path)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    git = Git(str(repo))
    driver = Driver(repo)
    session = Session(repo, driver, git)
    return session, git


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
    commit_hash = git.head_commit()
    assert commit_hash is not None
    return commit_hash


class TestCurrentTurnResultWithOneCommit:
    def test_returns_result_with_single_commit(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        session, git = session_with_git
        make_commit(git, "initial commit")
        head_before = git.head_commit()

        make_commit(git, "feat: agent work\n\noutcome: success")

        outcome, commit_hash, message = session.current_turn_result(
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome == "success"
        assert "feat: agent work" in message
        assert len(commit_hash) >= 40

    def test_extracts_outcome_from_commit_message(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        session, git = session_with_git
        make_commit(git, "initial commit")
        head_before = git.head_commit()

        make_commit(git, "fix: bug fix\n\noutcome: failure")

        outcome, _, message = session.current_turn_result(
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome == "failure"
        assert "fix: bug fix" in message

    def test_works_with_no_prior_commits(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        session, git = session_with_git
        head_before = git.head_commit()  # None for empty repo
        assert head_before is None

        make_commit(git, "feat: first feature\n\noutcome: success")

        outcome, commit_hash, message = session.current_turn_result(
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome == "success"
        assert "feat: first feature" in message
        assert len(commit_hash) >= 40


class TestCurrentTurnResultEdgeCases:
    def test_outcome_none_when_not_in_message(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()

        make_commit(git, "chore: update deps")

        outcome, _, message = session.current_turn_result(
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome is None
        assert "chore: update deps" in message

    def test_raises_on_nonzero_exit_code(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()

        with pytest.raises(RuntimeError, match="Exit code: 1"):
            session.current_turn_result(
                exit_code=1,
                log_file=str(tmp_path / "log.txt"),
                head_before=head_before,
            )


class TestZeroCommitsError:
    """Tests for AC #1: zero commits error message content."""

    def test_zero_commits_error_says_no_commit_detected(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should say 'No commit detected' not generic message."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        # No new commit made

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        assert "No commit at end of turn" in str(exc_info.value)

    def test_zero_commits_error_includes_head(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should include HEAD value."""
        session, git = session_with_git
        head = make_commit(git, "initial")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head)

        error_msg = str(exc_info.value)
        assert "HEAD:" in error_msg
        assert head[:7] in error_msg  # Short hash should appear

    def test_zero_commits_error_includes_log_file_path(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should include path to log file."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("some log content")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, log_path, head_before)

        assert log_path in str(exc_info.value)

    def test_zero_commits_error_includes_last_lines_of_log(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should include last 5 lines of log file."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text(
            "line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7"
        )

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, log_path, head_before)

        error_msg = str(exc_info.value)
        # Should include last 5 lines
        assert "line 7" in error_msg
        assert "line 3" in error_msg


class TestMultipleCommitsError:
    """Tests for AC #2: multiple commits error message content."""

    def test_multiple_commits_error_says_multiple_detected(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should say 'Multiple commits detected'."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()

        make_commit(git, "feat: first\n\noutcome: success")
        make_commit(git, "fix: second\n\noutcome: success")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        assert "Multiple commits detected" in str(exc_info.value)

    def test_multiple_commits_error_shows_expected_and_found(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should show expected vs found count."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()

        make_commit(git, "feat: first\n\noutcome: success")
        make_commit(git, "fix: second\n\noutcome: success")
        make_commit(git, "docs: third\n\noutcome: success")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        error_msg = str(exc_info.value)
        assert "Expected: 1 commit" in error_msg or "Expected: 1" in error_msg
        assert "Found: 3" in error_msg or "3 commits" in error_msg

    def test_multiple_commits_error_lists_hashes_and_subjects(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should list commit hashes and subject lines."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()

        make_commit(git, "feat: first change")
        make_commit(git, "fix: second change")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        error_msg = str(exc_info.value)
        # Should list commits with hash: subject format
        assert "first change" in error_msg
        assert "second change" in error_msg


class TestNonZeroExitError:
    """Tests for AC #4: non-zero exit code error message content."""

    def test_nonzero_exit_includes_exit_code(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should include the exit code."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("some output")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(42, log_path, head_before)

        error_msg = str(exc_info.value)
        assert "42" in error_msg
        assert "exit" in error_msg.lower()

    def test_nonzero_exit_includes_log_file_path(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error message should include path to log file for debugging."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "debug.log")
        Path(log_path).write_text("error details")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(1, log_path, head_before)

        assert log_path in str(exc_info.value)

    def test_nonzero_exit_log_file_preserved(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Log file should be preserved on error for debugging (AC #4)."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "preserved.log")
        Path(log_path).write_text("debug output before crash")

        with pytest.raises(RuntimeError):
            session.current_turn_result(1, log_path, head_before)

        # Log should still exist for debugging
        assert Path(log_path).exists()
        assert "debug output" in Path(log_path).read_text()


class TestSignalTerminationError:
    """Tests for AC #4: signal termination error message content."""

    def test_signal_termination_detected(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Negative return code indicates signal termination."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("output before kill")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(-15, log_path, head_before)  # SIGTERM

        error_msg = str(exc_info.value)
        assert "signal" in error_msg.lower()

    def test_signal_termination_includes_signal_name(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error should include human-readable signal name."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("output")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(-15, log_path, head_before)  # SIGTERM

        error_msg = str(exc_info.value)
        assert "SIGTERM" in error_msg

    def test_signal_termination_includes_signal_number(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error should include signal number."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("output")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(-9, log_path, head_before)  # SIGKILL

        error_msg = str(exc_info.value)
        assert "9" in error_msg or "SIGKILL" in error_msg

    def test_signal_termination_includes_log_path(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error should include log file path."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        log_path = str(tmp_path / "signal.log")
        Path(log_path).write_text("output")

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(-2, log_path, head_before)  # SIGINT

        assert log_path in str(exc_info.value)


class TestAncestryMismatchError:
    """Tests for ancestry mismatch error (HEAD moved but not on expected path)."""

    def test_ancestry_mismatch_error_raised(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error raised when HEAD changes but commits_between returns empty."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()

        # Simulate agent switching to orphan branch
        repo_path = Path(git.repo_path)
        subprocess.run(
            ["git", "checkout", "--orphan", "orphan"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        (repo_path / "orphan.txt").write_text("orphan content")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "orphan commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        error_msg = str(exc_info.value)
        assert "ancestry path" in error_msg.lower()
        assert "HEAD" in error_msg

    def test_ancestry_mismatch_shows_before_and_after(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error should show HEAD before and after values."""
        session, git = session_with_git
        head_before = make_commit(git, "initial")

        repo_path = Path(git.repo_path)
        subprocess.run(
            ["git", "checkout", "--orphan", "orphan"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        (repo_path / "orphan.txt").write_text("orphan")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "orphan"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        error_msg = str(exc_info.value)
        assert head_before[:7] in error_msg
        assert "HEAD before" in error_msg
        assert "HEAD after" in error_msg


class TestReadLogTailErrors:
    """Tests for _read_log_tail error handling."""

    def test_log_tail_handles_missing_file(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Should gracefully handle missing log file."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()
        # Don't create log file

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(
                0, str(tmp_path / "nonexistent.log"), head_before
            )

        # Should still get error message, just with fallback log content
        assert "No commit at end of turn" in str(exc_info.value)


class TestMultipleCommitsErrorEdgeCases:
    """Tests for edge cases in multiple commits error."""

    def test_handles_unreadable_commit(
        self,
        session_with_git: tuple[Session, Git],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should handle case where commit_summary fails for a commit."""
        session, git = session_with_git
        make_commit(git, "initial")
        head_before = git.head_commit()

        make_commit(git, "feat: first")
        make_commit(git, "fix: second")

        # Make commit_summary fail
        def failing_summary(commit_hash: str) -> str:
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(git, "commit_summary", failing_summary)

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        error_msg = str(exc_info.value)
        assert "could not read" in error_msg.lower()


class TestHeadUnbornAfterExecution:
    """Tests for HEAD unborn after execution edge case."""

    def test_head_unborn_after_execution_raises(
        self, session_with_git: tuple[Session, Git], tmp_path: Path
    ) -> None:
        """Error raised if HEAD is unborn after execution."""
        session, git = session_with_git
        # Start with a commit
        make_commit(git, "initial")
        head_before = git.head_commit()

        # Simulate agent doing something that leaves HEAD unborn
        repo_path = Path(git.repo_path)
        # Switch to orphan branch and don't commit
        subprocess.run(
            ["git", "checkout", "--orphan", "empty"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "rm", "-rf", "."],
            cwd=repo_path,
            capture_output=True,
        )

        with pytest.raises(RuntimeError) as exc_info:
            session.current_turn_result(0, str(tmp_path / "test.log"), head_before)

        assert "unborn" in str(exc_info.value).lower()
