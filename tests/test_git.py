import subprocess
import uuid
from pathlib import Path

import pytest

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


class TestHeadCommit:
    def test_empty_repo_returns_none(self, git_repo: Git):
        assert git_repo.head_commit() is None

    def test_repo_with_commit_returns_sha(self, git_repo: Git):
        make_commit(git_repo, "initial commit")
        result = git_repo.head_commit()
        assert result is not None
        assert len(result) in (40, 64)  # SHA-1 or SHA-256
        assert all(c in "0123456789abcdef" for c in result)


class TestCommitMessage:
    def test_returns_full_commit_message(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "feat: add feature\n\nBody text here.")
        message = git_repo.commit_message(commit_hash)
        assert "feat: add feature" in message
        assert "Body text here." in message

    def test_invalid_hash_raises_runtime_error(self, git_repo: Git):
        make_commit(git_repo, "initial")  # Need at least one commit for valid repo
        with pytest.raises(RuntimeError):
            git_repo.commit_message("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")


class TestCommitSummary:
    def test_returns_short_hash_and_subject(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "feat: add feature\n\nBody text here.")
        summary = git_repo.commit_summary(commit_hash)
        assert ": feat: add feature" in summary
        assert len(summary.split(":")[0]) == 7  # Short hash is 7 chars

    def test_invalid_hash_raises_runtime_error(self, git_repo: Git):
        make_commit(git_repo, "initial")
        with pytest.raises(RuntimeError):
            git_repo.commit_summary("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")


class TestParseCommitMessage:
    def test_commit_with_success_outcome(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "feat: add feature\n\noutcome: success")
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome == "success"
        assert "outcome: success" in message

    def test_commit_with_failure_outcome(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "fix: attempt fix\n\noutcome: failure")
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome == "failure"
        assert "outcome: failure" in message

    def test_commit_without_outcome(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "chore: update deps")
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome is None
        assert "chore: update deps" in message

    def test_outcome_in_footer_takes_precedence(self, git_repo: Git):
        # Multiple outcome lines - last one wins (footer position)
        msg = "feat: add feature\n\noutcome: partial\n\noutcome: success"
        commit_hash = make_commit(git_repo, msg)
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome == "success"  # Last one wins
        assert "outcome: success" in message

    def test_outcome_allows_hyphenated_values(self, git_repo: Git):
        msg = "feat: add feature\n\noutcome: partial-success"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == "partial-success"

    def test_outcome_ignores_empty_value(self, git_repo: Git):
        msg = "feat: add feature\n\noutcome: "
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome is None

    def test_outcome_accepts_long_values(self, git_repo: Git):
        long_value = "x" * 200
        msg = f"feat: add feature\n\noutcome: {long_value}"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == long_value

    def test_outcome_with_special_characters(self, git_repo: Git):
        # Outcomes can include hyphens, underscores
        msg = "feat: add feature\n\noutcome: partial-success"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == "partial-success"

        msg2 = "feat: another\n\noutcome: needs_review"
        commit_hash2 = make_commit(git_repo, msg2)
        outcome2, _ = git_repo.parse_commit_message(commit_hash2)
        assert outcome2 == "needs_review"

    def test_outcome_key_is_case_insensitive(self, git_repo: Git):
        # LLMs capitalize unpredictably
        msg1 = "feat: test\n\nOutcome: success"
        commit_hash1 = make_commit(git_repo, msg1)
        outcome1, _ = git_repo.parse_commit_message(commit_hash1)
        assert outcome1 == "success"

        msg2 = "feat: test\n\nOUTCOME: failure"
        commit_hash2 = make_commit(git_repo, msg2)
        outcome2, _ = git_repo.parse_commit_message(commit_hash2)
        assert outcome2 == "failure"

    def test_outcome_value_is_lowercased(self, git_repo: Git):
        # Normalize outcome values for consistent comparison
        msg = "feat: test\n\noutcome: SUCCESS"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == "success"

    def test_outcome_captures_multi_word_value(self, git_repo: Git):
        # LLMs may write multi-word outcomes - capture fully for error messages
        msg = "feat: test\n\noutcome: needs review"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == "needs review"

    def test_outcome_captures_fuzzy_llm_output(self, git_repo: Git):
        # LLM might write something verbose - capture it all
        msg = (
            "feat: test\n\noutcome: I think this was successful but needs verification"
        )
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == "i think this was successful but needs verification"


class TestCommitsBetween:
    def test_returns_commits_between_two_points(self, git_repo: Git):
        commit_a = make_commit(git_repo, "commit A")
        commit_b = make_commit(git_repo, "commit B")
        commit_c = make_commit(git_repo, "commit C")

        result = git_repo.commits_between(since=commit_a, until=commit_c)
        assert result == [commit_b, commit_c]

    def test_returns_all_commits_when_since_is_none(self, git_repo: Git):
        commit_a = make_commit(git_repo, "commit A")
        commit_b = make_commit(git_repo, "commit B")
        commit_c = make_commit(git_repo, "commit C")

        result = git_repo.commits_between(since=None, until=commit_c)
        assert result == [commit_a, commit_b, commit_c]

    def test_returns_empty_list_when_no_commits_between(self, git_repo: Git):
        commit_a = make_commit(git_repo, "commit A")
        result = git_repo.commits_between(since=commit_a, until=commit_a)
        assert result == []


class TestRootCommit:
    def test_returns_single_root(self, git_repo: Git):
        commit_a = make_commit(git_repo, "commit A")
        make_commit(git_repo, "commit B")

        assert git_repo.root_commit() == commit_a

    def test_raises_on_multiple_roots(self, git_repo: Git, tmp_path: Path):
        # Create first root
        make_commit(git_repo, "root A")

        # Create orphan branch with second root
        subprocess.run(
            ["git", "checkout", "--orphan", "orphan"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "orphan.txt").write_text("orphan")
        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "root B"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Merge unrelated histories to have both roots reachable from HEAD
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "--allow-unrelated-histories", "-m", "merge", "orphan"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        with pytest.raises(RuntimeError, match=r"\d+ root commits"):
            git_repo.root_commit()

    def test_empty_repo_raises(self, tmp_path: Path):
        """Empty repo should raise error (git rev-list fails on unborn HEAD)."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        git = Git(str(tmp_path))

        with pytest.raises(RuntimeError):
            git.root_commit()


class TestHeadCommitErrors:
    """Tests for head_commit error paths."""

    def test_not_git_repo_raises(self, tmp_path: Path):
        """Non-git directory should raise 'Not a git repository'."""
        git = Git(str(tmp_path))

        with pytest.raises(RuntimeError, match="Not a git repository"):
            git.head_commit()


# =============================================================================
# Tests for Git repo initialization and tagging methods (Story 3.1)
# =============================================================================


class TestGitIsRepo:
    """Tests for Git.is_repo() method."""

    def test_returns_true_for_git_repo(self, git_repo: Git) -> None:
        """is_repo() returns True for initialized git repository."""
        assert git_repo.is_repo() is True

    def test_returns_false_for_non_repo(self, tmp_path: Path) -> None:
        """is_repo() returns False for non-git directory."""
        git = Git(str(tmp_path))
        assert git.is_repo() is False


class TestGitInit:
    """Tests for Git.init() method."""

    def test_initializes_new_repo(self, tmp_path: Path) -> None:
        """init() creates a new git repository."""
        git = Git(str(tmp_path))
        assert git.is_repo() is False

        git.init()

        assert git.is_repo() is True


class TestGitCommitEmpty:
    """Tests for Git.commit_empty() method."""

    def test_creates_empty_commit(self, git_repo: Git) -> None:
        """commit_empty() creates commit with given message and returns hash."""
        commit_hash = git_repo.commit_empty("test: empty commit")

        assert commit_hash is not None
        assert len(commit_hash) >= 40
        assert git_repo.head_commit() == commit_hash
        message = git_repo.commit_message(commit_hash)
        assert "test: empty commit" in message


class TestGitIsEmptyDirectory:
    """Tests for Git.is_empty_directory() method."""

    def test_returns_true_for_empty_dir(self, tmp_path: Path) -> None:
        """is_empty_directory() returns True for empty directory."""
        git = Git(str(tmp_path))
        assert git.is_empty_directory() is True

    def test_returns_false_for_dir_with_files(self, tmp_path: Path) -> None:
        """is_empty_directory() returns False for directory with files."""
        (tmp_path / "file.txt").write_text("content")
        git = Git(str(tmp_path))
        assert git.is_empty_directory() is False

    def test_returns_true_for_git_repo_only(self, tmp_path: Path) -> None:
        """is_empty_directory() returns True for dir with only .git folder."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        git = Git(str(tmp_path))
        # Only .git exists, so "empty" from user content perspective
        assert git.is_empty_directory() is True


class TestGitTagExists:
    """Tests for Git.tag_exists() method."""

    def test_returns_false_for_nonexistent_tag(self, git_repo: Git) -> None:
        """tag_exists() returns False when tag doesn't exist."""
        make_commit(git_repo, "initial")
        assert git_repo.tag_exists("nonexistent-tag") is False

    def test_returns_true_for_existing_tag(self, git_repo: Git, tmp_path: Path) -> None:
        """tag_exists() returns True when tag exists."""
        commit_hash = make_commit(git_repo, "initial")
        subprocess.run(
            ["git", "tag", "v1.0.0", commit_hash],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        assert git_repo.tag_exists("v1.0.0") is True


class TestGitTag:
    """Tests for Git.tag() method."""

    def test_creates_tag_pointing_to_commit(
        self, git_repo: Git, tmp_path: Path
    ) -> None:
        """tag() creates lightweight tag pointing to specified commit."""
        commit_hash = make_commit(git_repo, "initial")

        git_repo.tag("my-tag", commit_hash)

        assert git_repo.tag_exists("my-tag") is True
        # Verify tag points to correct commit
        tag_commit = subprocess.run(
            ["git", "rev-parse", "my-tag"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert tag_commit == commit_hash

    def test_raises_if_tag_already_exists(self, git_repo: Git, tmp_path: Path) -> None:
        """tag() raises RuntimeError if tag already exists (pre-check)."""
        commit_hash = make_commit(git_repo, "initial")
        subprocess.run(
            ["git", "tag", "existing-tag", commit_hash],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        with pytest.raises(RuntimeError, match="Tag already exists"):
            git_repo.tag("existing-tag", commit_hash)

    def test_raises_on_invalid_commit(self, git_repo: Git) -> None:
        """tag() raises RuntimeError for invalid commit hash."""
        make_commit(git_repo, "initial")

        with pytest.raises(RuntimeError):
            git_repo.tag("bad-tag", "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
