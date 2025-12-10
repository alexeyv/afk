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
    return git.head_commit()


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


class TestParseCommitMessage:
    def test_commit_with_success_outcome(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "feat: add feature\n\n[success] task done")
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome == "success"
        assert "[success]" in message

    def test_commit_with_failure_outcome(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "fix: attempt fix\n\n[failure] tests failed")
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome == "failure"
        assert "[failure]" in message

    def test_commit_without_outcome(self, git_repo: Git):
        commit_hash = make_commit(git_repo, "chore: update deps")
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome is None
        assert "chore: update deps" in message

    def test_outcome_in_footer_takes_precedence_over_body(self, git_repo: Git):
        # [note] in body should be ignored, [success] in footer should be extracted
        msg = "feat: add feature\n\n[note] this is body text\n\n[success] completed"
        commit_hash = make_commit(git_repo, msg)
        outcome, message = git_repo.parse_commit_message(commit_hash)
        assert outcome == "success"  # Footer wins, not body
        assert "[success]" in message

    def test_outcome_allows_hyphenated_values(self, git_repo: Git):
        msg = "feat: add feature\n\n[partial-success] completed"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == "partial-success"

    def test_outcome_ignores_whitespace_only_marker(self, git_repo: Git):
        msg = "feat: add feature\n\n[   ]"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome is None

    def test_outcome_ignores_excessively_long_marker(self, git_repo: Git):
        long_marker = "x" * 60
        msg = f"feat: add feature\n\n[{long_marker}]"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome is None

    def test_outcome_with_special_characters(self, git_repo: Git):
        # Outcomes can include hyphens, underscores, dots, colons
        msg = "feat: add feature\n\n[partial-success] mostly done"
        commit_hash = make_commit(git_repo, msg)
        outcome, _ = git_repo.parse_commit_message(commit_hash)
        assert outcome == "partial-success"

        msg2 = "feat: another\n\n[needs_review:urgent] please check"
        commit_hash2 = make_commit(git_repo, msg2)
        outcome2, _ = git_repo.parse_commit_message(commit_hash2)
        assert outcome2 == "needs_review:urgent"


class TestCommitsBetween:
    def test_returns_commits_between_two_points(self, git_repo: Git):
        commit_a = make_commit(git_repo, "commit A")
        commit_b = make_commit(git_repo, "commit B")
        commit_c = make_commit(git_repo, "commit C")

        result = git_repo.commits_between(commit_a, commit_c)
        assert result == [commit_b, commit_c]

    def test_returns_all_commits_when_before_is_none(self, git_repo: Git):
        commit_a = make_commit(git_repo, "commit A")
        commit_b = make_commit(git_repo, "commit B")
        commit_c = make_commit(git_repo, "commit C")

        result = git_repo.commits_between(None, commit_c)
        assert result == [commit_a, commit_b, commit_c]

    def test_returns_empty_list_when_no_commits_between(self, git_repo: Git):
        commit_a = make_commit(git_repo, "commit A")
        result = git_repo.commits_between(commit_a, commit_a)
        assert result == []
