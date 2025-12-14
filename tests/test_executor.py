import subprocess
import uuid
from pathlib import Path

import pytest

from afk.executor import validate_turn_execution
from afk.git import Git


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
    commit_hash = git.head_commit()
    assert commit_hash is not None
    return commit_hash


class TestValidateTurnExecutionWithOneCommit:
    def test_returns_result_with_single_commit(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        make_commit(git_repo, "initial commit")
        head_before = git_repo.head_commit()

        make_commit(git_repo, "feat: agent work\n\noutcome: success")

        outcome, commit_hash, message = validate_turn_execution(
            git=git_repo,
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome == "success"
        assert "feat: agent work" in message
        assert len(commit_hash) >= 40

    def test_extracts_outcome_from_commit_message(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        make_commit(git_repo, "initial commit")
        head_before = git_repo.head_commit()

        make_commit(git_repo, "fix: bug fix\n\noutcome: failure")

        outcome, _, message = validate_turn_execution(
            git=git_repo,
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome == "failure"
        assert "fix: bug fix" in message

    def test_works_with_no_prior_commits(self, git_repo: Git, tmp_path: Path) -> None:
        head_before = git_repo.head_commit()  # None for empty repo
        assert head_before is None

        make_commit(git_repo, "feat: first feature\n\noutcome: success")

        outcome, commit_hash, message = validate_turn_execution(
            git=git_repo,
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome == "success"
        assert "feat: first feature" in message
        assert len(commit_hash) >= 40


class TestValidateTurnExecutionEdgeCases:
    def test_outcome_none_when_not_in_message(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        make_commit(git_repo, "chore: update deps")

        outcome, _, message = validate_turn_execution(
            git=git_repo,
            exit_code=0,
            log_file=str(tmp_path / "log.txt"),
            head_before=head_before,
        )

        assert outcome is None
        assert "chore: update deps" in message

    def test_raises_on_nonzero_exit_code(self, git_repo: Git, tmp_path: Path) -> None:
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        with pytest.raises(RuntimeError, match="Exit code: 1"):
            validate_turn_execution(
                git=git_repo,
                exit_code=1,
                log_file=str(tmp_path / "log.txt"),
                head_before=head_before,
            )


class TestZeroCommitsError:
    """Tests for AC #1: zero commits error message content."""

    def test_zero_commits_error_says_no_commit_detected(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should say 'No commit detected' not generic message."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        # No new commit made

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        assert "No commit at end of turn" in str(exc_info.value)

    def test_zero_commits_error_includes_head(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should include HEAD value."""
        head = make_commit(git_repo, "initial")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, 0, str(tmp_path / "test.log"), head)

        error_msg = str(exc_info.value)
        assert "HEAD:" in error_msg
        assert head[:7] in error_msg  # Short hash should appear

    def test_zero_commits_error_includes_log_file_path(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should include path to log file."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("some log content")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, 0, log_path, head_before)

        assert log_path in str(exc_info.value)

    def test_zero_commits_error_includes_last_lines_of_log(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should include last 5 lines of log file."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text(
            "line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7"
        )

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, 0, log_path, head_before)

        error_msg = str(exc_info.value)
        # Should include last 5 lines
        assert "line 7" in error_msg
        assert "line 3" in error_msg


class TestMultipleCommitsError:
    """Tests for AC #2: multiple commits error message content."""

    def test_multiple_commits_error_says_multiple_detected(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should say 'Multiple commits detected'."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        make_commit(git_repo, "feat: first\n\noutcome: success")
        make_commit(git_repo, "fix: second\n\noutcome: success")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        assert "Multiple commits detected" in str(exc_info.value)

    def test_multiple_commits_error_shows_expected_and_found(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should show expected vs found count."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        make_commit(git_repo, "feat: first\n\noutcome: success")
        make_commit(git_repo, "fix: second\n\noutcome: success")
        make_commit(git_repo, "docs: third\n\noutcome: success")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        error_msg = str(exc_info.value)
        assert "Expected: 1 commit" in error_msg or "Expected: 1" in error_msg
        assert "Found: 3" in error_msg or "3 commits" in error_msg

    def test_multiple_commits_error_lists_hashes_and_subjects(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should list commit hashes and subject lines."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        make_commit(git_repo, "feat: first change")
        make_commit(git_repo, "fix: second change")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        error_msg = str(exc_info.value)
        # Should list commits with hash: subject format
        assert "first change" in error_msg
        assert "second change" in error_msg


class TestNonZeroExitError:
    """Tests for AC #4: non-zero exit code error message content."""

    def test_nonzero_exit_includes_exit_code(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should include the exit code."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("some output")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, 42, log_path, head_before)

        error_msg = str(exc_info.value)
        assert "42" in error_msg
        assert "exit" in error_msg.lower()

    def test_nonzero_exit_includes_log_file_path(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error message should include path to log file for debugging."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "debug.log")
        Path(log_path).write_text("error details")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, 1, log_path, head_before)

        assert log_path in str(exc_info.value)

    def test_nonzero_exit_log_file_preserved(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Log file should be preserved on error for debugging (AC #4)."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "preserved.log")
        Path(log_path).write_text("debug output before crash")

        with pytest.raises(RuntimeError):
            validate_turn_execution(git_repo, 1, log_path, head_before)

        # Log should still exist for debugging
        assert Path(log_path).exists()
        assert "debug output" in Path(log_path).read_text()


class TestSignalTerminationError:
    """Tests for AC #4: signal termination error message content."""

    def test_signal_termination_detected(self, git_repo: Git, tmp_path: Path) -> None:
        """Negative return code indicates signal termination."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("output before kill")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, -15, log_path, head_before)  # SIGTERM

        error_msg = str(exc_info.value)
        assert "signal" in error_msg.lower()

    def test_signal_termination_includes_signal_name(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error should include human-readable signal name."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("output")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, -15, log_path, head_before)  # SIGTERM

        error_msg = str(exc_info.value)
        assert "SIGTERM" in error_msg

    def test_signal_termination_includes_signal_number(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error should include signal number."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "test.log")
        Path(log_path).write_text("output")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, -9, log_path, head_before)  # SIGKILL

        error_msg = str(exc_info.value)
        assert "9" in error_msg or "SIGKILL" in error_msg

    def test_signal_termination_includes_log_path(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error should include log file path."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        log_path = str(tmp_path / "signal.log")
        Path(log_path).write_text("output")

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(git_repo, -2, log_path, head_before)  # SIGINT

        assert log_path in str(exc_info.value)


class TestAncestryMismatchError:
    """Tests for ancestry mismatch error (HEAD moved but not on expected path)."""

    def test_ancestry_mismatch_error_raised(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error raised when HEAD changes but commits_between returns empty."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        # Simulate agent switching to orphan branch
        repo_path = Path(git_repo.repo_path)
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
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        error_msg = str(exc_info.value)
        assert "ancestry path" in error_msg.lower()
        assert "HEAD" in error_msg

    def test_ancestry_mismatch_shows_before_and_after(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error should show HEAD before and after values."""
        head_before = make_commit(git_repo, "initial")

        repo_path = Path(git_repo.repo_path)
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
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        error_msg = str(exc_info.value)
        assert head_before[:7] in error_msg
        assert "HEAD before" in error_msg
        assert "HEAD after" in error_msg


class TestReadLogTailErrors:
    """Tests for _read_log_tail error handling."""

    def test_log_tail_handles_missing_file(self, git_repo: Git, tmp_path: Path) -> None:
        """Should gracefully handle missing log file."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()
        # Don't create log file

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "nonexistent.log"), head_before
            )

        # Should still get error message, just with fallback log content
        assert "No commit at end of turn" in str(exc_info.value)


class TestMultipleCommitsErrorEdgeCases:
    """Tests for edge cases in multiple commits error."""

    def test_handles_unreadable_commit(
        self, git_repo: Git, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should handle case where commit_summary fails for a commit."""
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        make_commit(git_repo, "feat: first")
        make_commit(git_repo, "fix: second")

        # Make commit_summary fail
        def failing_summary(commit_hash: str) -> str:
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(git_repo, "commit_summary", failing_summary)

        with pytest.raises(RuntimeError) as exc_info:
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        error_msg = str(exc_info.value)
        assert "could not read" in error_msg.lower()


class TestHeadUnbornAfterExecution:
    """Tests for HEAD unborn after execution edge case."""

    def test_head_unborn_after_execution_raises(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """Error raised if HEAD is unborn after execution."""
        # Start with a commit
        make_commit(git_repo, "initial")
        head_before = git_repo.head_commit()

        # Simulate agent doing something that leaves HEAD unborn
        repo_path = Path(git_repo.repo_path)
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
            validate_turn_execution(
                git_repo, 0, str(tmp_path / "test.log"), head_before
            )

        assert "unborn" in str(exc_info.value).lower()
