import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from afk.driver import Driver
from afk.git import Git
from afk.session import Session
from afk.transition_type import TransitionType
from afk.turn import Turn
from afk.turn_result import TurnResult

FIXED_TIME = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_result(n: int, transition_type: str = "coding") -> TurnResult:
    """Helper to create TurnResult instances for testing."""
    return TurnResult(
        turn_number=n,
        transition_type=TransitionType(transition_type),
        outcome="success",
        message="test",
        commit_hash="abc123",
        log_file=Path(f"/logs/turn-{n:05d}-{transition_type}.log"),
        timestamp=FIXED_TIME,
    )


def fake_claude_noop(tmp_path: Path) -> Path:
    """Create a no-op fake claude CLI script. Returns bin dir for PATH injection."""
    fake_bin = tmp_path / "fake_bin"
    fake_bin.mkdir(exist_ok=True)
    script = fake_bin / "claude"
    script.write_text("""#!/bin/bash
# Handle --version for Driver._check_environment()
if [[ "$1" == "--version" ]]; then
    echo "claude-fake 1.0.0"
    exit 0
fi
echo "fake claude"
exit 0
""")
    script.chmod(0o755)
    return fake_bin


def fake_claude_with_commit(tmp_path: Path, repo_path: Path) -> Path:
    """Create fake claude that makes a commit with outcome: success. Returns bin dir."""
    fake_bin = tmp_path / "fake_bin_commit"
    fake_bin.mkdir(exist_ok=True)
    script = fake_bin / "claude"
    script.write_text(f"""#!/bin/bash
# Handle --version for Driver._check_environment()
if [[ "$1" == "--version" ]]; then
    echo "claude-fake 1.0.0"
    exit 0
fi
cd {repo_path}
git commit --allow-empty -m "feat: test commit

outcome: success"
exit 0
""")
    script.chmod(0o755)
    return fake_bin


def fake_claude_no_commit(tmp_path: Path) -> Path:
    """Create fake claude that exits without making a commit. Returns bin dir."""
    fake_bin = tmp_path / "fake_bin_no_commit"
    fake_bin.mkdir(exist_ok=True)
    script = fake_bin / "claude"
    script.write_text("""#!/bin/bash
# Handle --version for Driver._check_environment()
if [[ "$1" == "--version" ]]; then
    echo "claude-fake 1.0.0"
    exit 0
fi
echo "No commit made"
exit 0
""")
    script.chmod(0o755)
    return fake_bin


@pytest.fixture
def session_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Driver, Git]:
    """Set up environment for Session tests with fake claude."""
    # Create git repo
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

    # Inject fake claude into PATH
    fake_bin = fake_claude_noop(tmp_path)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    git = Git(str(repo))
    driver = Driver(repo)
    return repo, driver, git


class TestSession:
    def test_empty_session(self, session_env: tuple[Path, Driver, Git]) -> None:
        """AC#4: Session can be instantiated and returns empty tuple of turns."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        assert session.turns == ()
        assert list(session) == []

    def test_add_single_turn(self, session_env: tuple[Path, Driver, Git]) -> None:
        """AC#1: add_turn adds TurnResult to session."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        result = make_result(1, "init")
        session.add_turn(result)
        assert session.turns == (result,)

    def test_add_multiple_turns_in_order(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """AC#1: TurnResults are stored in order of addition."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        r1 = make_result(1, "init")
        r2 = make_result(2, "coding")
        r3 = make_result(3, "coding")
        session.add_turn(r1)
        session.add_turn(r2)
        session.add_turn(r3)
        assert session.turns == (r1, r2, r3)

    def test_turn_lookup_by_number(self, session_env: tuple[Path, Driver, Git]) -> None:
        """AC#2: turn(n) returns correct TurnResult by turn_number."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        r1 = make_result(1)
        r2 = make_result(2)
        session.add_turn(r1)
        session.add_turn(r2)
        assert session.turn(1) is r1
        assert session.turn(2) is r2

    def test_turn_lookup_raises_keyerror(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """AC#2: turn(n) raises KeyError for non-existent turn."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        session.add_turn(make_result(1))
        with pytest.raises(KeyError):
            session.turn(99)

    def test_iteration_chronological_order(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """AC#3: Iteration yields turns in chronological order."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        results = [make_result(i) for i in range(1, 4)]
        for r in results:
            session.add_turn(r)
        assert list(session) == results

    def test_turns_property_is_immutable(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """AC#4: turns property returns tuple (immutable view)."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        session.add_turn(make_result(1))
        turns = session.turns
        assert isinstance(turns, tuple)

    def test_first_turn_must_be_one(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """First turn must have turn_number 1."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        with pytest.raises(ValueError, match="First turn must be turn 1"):
            session.add_turn(make_result(5))  # Must start at 1

    def test_add_turn_requires_monotonic_increase(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """Turn numbers must be monotonically increasing."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        session.add_turn(make_result(1))
        session.add_turn(make_result(5))  # Gap is fine
        with pytest.raises(ValueError, match="must be > 5"):
            session.add_turn(make_result(3))  # Going backwards - fails

    def test_add_turn_rejects_duplicate(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """Cannot add turn with same number as existing turn."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        session.add_turn(make_result(1))
        with pytest.raises(ValueError, match="must be > 1"):
            session.add_turn(make_result(1))  # Duplicate - fails

    def test_failed_add_doesnt_corrupt_state(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """Failed add_turn must leave session state unchanged."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        session.add_turn(make_result(1))
        with pytest.raises(ValueError):
            session.add_turn(make_result(1))  # Duplicate - fails
        session.add_turn(make_result(2))  # Valid next - should work
        assert len(session) == 2
        assert session.turn(1).turn_number == 1
        assert session.turn(2).turn_number == 2


class TestSessionRootDir:
    """Tests for Session root_dir and log_dir properties."""

    def test_root_dir_returns_session_root(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """root_dir property returns the session root directory."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        assert session.root_dir == root_dir

    def test_log_dir_returns_logs_subdirectory(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """log_dir property returns root_dir / 'logs'."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        assert session.log_dir == root_dir / "logs"

    def test_log_dir_is_absolute(self, session_env: tuple[Path, Driver, Git]) -> None:
        """log_dir property returns an absolute path."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        assert session.log_dir.is_absolute()


class TestSessionValidation:
    """Tests for Session input validation."""

    def test_rejects_string_root_dir(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """root_dir must be Path, not string."""
        _, driver, git = session_env
        with pytest.raises(TypeError, match="expected Path, got '/some/path'"):
            Session("/some/path", driver, git)  # type: ignore[arg-type]

    def test_rejects_relative_root_dir(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """root_dir must be absolute."""
        _, driver, git = session_env
        with pytest.raises(ValueError, match="must be an absolute path"):
            Session(Path("relative/path"), driver, git)

    def test_rejects_nonexistent_root_dir(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """root_dir must be an existing directory."""
        _, driver, git = session_env
        with pytest.raises(ValueError, match="must be a directory"):
            Session(Path("/nonexistent/path"), driver, git)

    def test_rejects_file_as_root_dir(
        self, tmp_path: Path, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """root_dir must be a directory, not a file."""
        _, driver, git = session_env
        file_path = tmp_path / "somefile.txt"
        file_path.write_text("content")
        with pytest.raises(ValueError, match="must be a directory"):
            Session(file_path, driver, git)

    def test_rejects_non_driver(self, session_env: tuple[Path, Driver, Git]) -> None:
        """driver must be Driver instance."""
        root_dir, _, git = session_env
        with pytest.raises(TypeError, match="expected Driver, got 'not a driver'"):
            Session(root_dir, "not a driver", git)  # type: ignore[arg-type]

    def test_rejects_non_git(self, session_env: tuple[Path, Driver, Git]) -> None:
        """git must be Git instance."""
        root_dir, driver, _ = session_env
        with pytest.raises(TypeError, match="expected Git, got 'not a git'"):
            Session(root_dir, driver, "not a git")  # type: ignore[arg-type]

    def test_rejects_non_turn_result_in_add_turn(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """add_turn rejects non-TurnResult values."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)
        with pytest.raises(TypeError, match="expected TurnResult, got 'not a result'"):
            session.add_turn("not a result")  # type: ignore[arg-type]


@pytest.fixture
def execute_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    """Set up a Session with fake claude that makes commits."""
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
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    fake_bin = fake_claude_with_commit(tmp_path, repo)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    git = Git(str(repo))
    driver = Driver(repo)
    return Session(repo, driver, git)


@pytest.fixture
def execute_session_no_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Session:
    """Set up a Session with fake claude that does NOT make commits."""
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
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    fake_bin = fake_claude_no_commit(tmp_path)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    git = Git(str(repo))
    driver = Driver(repo)
    return Session(repo, driver, git)


class TestSessionExecuteTurn:
    """Tests for Session.execute_turn() method."""

    def test_creates_turn_with_correct_number(self, execute_session: Session) -> None:
        """AC#1: execute_turn creates TurnResult with correct turn_number."""
        result = execute_session.execute_turn("test prompt", TransitionType("init"))

        assert result.turn_number == 1
        assert result.outcome == "success"

    def test_turn_has_correct_transition_type(self, execute_session: Session) -> None:
        """AC#1: execute_turn creates TurnResult with correct transition_type."""
        transition_type = TransitionType("coding")
        result = execute_session.execute_turn("test prompt", transition_type)

        assert result.transition_type == transition_type

    def test_turn_has_correct_log_file_path(self, execute_session: Session) -> None:
        """AC#1: execute_turn creates TurnResult with log_file following TurnLog pattern."""
        result = execute_session.execute_turn("test prompt", TransitionType("init"))

        assert result.log_file.name == "turn-00001-init.log"
        assert result.log_file.parent == execute_session.log_dir

    def test_turn_is_added_to_session(self, execute_session: Session) -> None:
        """AC#1: execute_turn adds TurnResult to session."""
        result = execute_session.execute_turn("test prompt", TransitionType("init"))

        assert len(execute_session) == 1
        assert execute_session[1] is result

    def test_sequential_calls_increment_turn_number(
        self, execute_session: Session
    ) -> None:
        """AC#1: Sequential execute_turn calls increment turn_number."""
        r1 = execute_session.execute_turn("prompt 1", TransitionType("init"))
        r2 = execute_session.execute_turn("prompt 2", TransitionType("coding"))
        r3 = execute_session.execute_turn("prompt 3", TransitionType("coding"))

        assert r1.turn_number == 1
        assert r2.turn_number == 2
        assert r3.turn_number == 3

    def test_exception_does_not_create_turn(
        self, execute_session_no_commit: Session
    ) -> None:
        """Failed execution does not create a TurnResult - no commit means no Turn."""
        with pytest.raises(RuntimeError, match="No commit"):
            execute_session_no_commit.execute_turn(
                "test prompt", TransitionType("init")
            )

        assert len(execute_session_no_commit) == 0


class TestSessionLogging:
    """Tests for Session turn lifecycle logging."""

    def test_successful_turn_logs_start_and_end(self, execute_session: Session) -> None:
        """Successful execute_turn logs start and end markers with outcome."""
        result = execute_session.execute_turn("test prompt", TransitionType("init"))

        log_content = result.log_file.read_text()
        assert "=== Turn 1 START ===" in log_content
        assert "=== Turn 1 END: success ===" in log_content

    def test_failed_turn_logs_start_and_abort(
        self, execute_session_no_commit: Session
    ) -> None:
        """Failed execute_turn logs start and abort with traceback."""
        log_file = execute_session_no_commit.log_dir / "turn-00001-init.log"

        with pytest.raises(RuntimeError, match="No commit"):
            execute_session_no_commit.execute_turn(
                "test prompt", TransitionType("init")
            )

        log_content = log_file.read_text()
        assert "=== Turn 1 START ===" in log_content
        assert "=== Turn 1 ABORT: RuntimeError ===" in log_content
        assert "No commit" in log_content

    def test_multiple_turns_log_incrementing_numbers(
        self, execute_session: Session
    ) -> None:
        """Multiple successful turns log with correct turn numbers."""
        r1 = execute_session.execute_turn("prompt 1", TransitionType("init"))
        r2 = execute_session.execute_turn("prompt 2", TransitionType("coding"))

        log1_content = r1.log_file.read_text()
        log2_content = r2.log_file.read_text()

        assert "=== Turn 1 START ===" in log1_content
        assert "=== Turn 1 END: success ===" in log1_content
        assert "=== Turn 2 START ===" in log2_content
        assert "=== Turn 2 END: success ===" in log2_content


class TestSessionAllocateTurnNumber:
    """Tests for Session.allocate_turn_number() method."""

    def test_sequential_allocation(self, session_env: tuple[Path, Driver, Git]) -> None:
        """allocate_turn_number returns sequential numbers starting at 1."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)

        assert session.allocate_turn_number() == 1
        assert session.allocate_turn_number() == 2
        assert session.allocate_turn_number() == 3

    def test_resume_from_specific_number(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """allocate_turn_number(resume_from=N) returns N and continues from N+1."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)

        n = session.allocate_turn_number(resume_from=10)
        assert n == 10
        assert session.allocate_turn_number() == 11

    def test_resume_from_rejects_zero(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """allocate_turn_number(resume_from=0) raises."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)

        with pytest.raises(ValueError, match="resume_from must be >= 1"):
            session.allocate_turn_number(resume_from=0)

    def test_resume_from_rejects_max(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """allocate_turn_number(resume_from=MAX) raises."""
        root_dir, driver, git = session_env
        session = Session(root_dir, driver, git)

        with pytest.raises(ValueError, match="resume_from"):
            session.allocate_turn_number(resume_from=Session.MAX_TURN_NUMBER)

    def test_separate_sessions_have_independent_counters(
        self, session_env: tuple[Path, Driver, Git]
    ) -> None:
        """Each Session instance has its own independent counter."""
        root_dir, driver, git = session_env
        session1 = Session(root_dir, driver, git)
        session2 = Session(root_dir, driver, git)

        assert session1.allocate_turn_number() == 1
        assert session1.allocate_turn_number() == 2
        assert session2.allocate_turn_number() == 1  # Independent counter
        assert session1.allocate_turn_number() == 3


# =============================================================================
# Tests for Session.build_turn_result()
# =============================================================================


@pytest.fixture
def session_with_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Session, Git, Driver, Path]:
    """Create a Session with git repo for testing build_turn_result."""
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
    return session, git, driver, repo


def make_turn(driver: Driver, git: Git, repo: Path) -> Turn:
    """Create and start a Turn, capturing current HEAD."""
    turn = Turn(driver, git, repo)
    turn.start(1, TransitionType("test"))
    return turn


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


class TestBuildTurnResultWithOneCommit:
    def test_returns_result_with_single_commit(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial commit")
        turn = make_turn(driver, git, repo)

        make_commit(git, "feat: agent work\n\noutcome: success")

        result = session.build_turn_result(turn, exit_code=0)

        assert result.outcome == "success"
        assert "feat: agent work" in result.message
        assert len(result.commit_hash) >= 40

    def test_extracts_outcome_from_commit_message(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial commit")
        turn = make_turn(driver, git, repo)

        make_commit(git, "fix: bug fix\n\noutcome: failure")

        result = session.build_turn_result(turn, exit_code=0)

        assert result.outcome == "failure"
        assert "fix: bug fix" in result.message

    def test_works_with_no_prior_commits(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        turn = make_turn(driver, git, repo)  # head_before will be None

        make_commit(git, "feat: first feature\n\noutcome: success")

        result = session.build_turn_result(turn, exit_code=0)

        assert result.outcome == "success"
        assert "feat: first feature" in result.message
        assert len(result.commit_hash) >= 40


class TestBuildTurnResultEdgeCases:
    def test_outcome_none_when_not_in_message(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        make_commit(git, "chore: update deps")

        result = session.build_turn_result(turn, exit_code=0)

        assert result.outcome is None
        assert "chore: update deps" in result.message

    def test_raises_on_nonzero_exit_code(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        with pytest.raises(RuntimeError, match="Exit code: 1"):
            session.build_turn_result(turn, exit_code=1)


class TestBuildTurnResultZeroCommitsError:
    """Tests for zero commits error message content."""

    def test_zero_commits_error_says_no_commit_detected(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 0)

        assert "No commit at end of turn" in str(exc_info.value)

    def test_zero_commits_error_includes_head(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        head = make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 0)

        error_msg = str(exc_info.value)
        assert "HEAD:" in error_msg
        assert head[:7] in error_msg

    def test_zero_commits_error_includes_log_file_path(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 0)

        assert str(turn.log_file) in str(exc_info.value)


class TestBuildTurnResultMultipleCommitsError:
    """Tests for multiple commits error message content."""

    def test_multiple_commits_error_says_multiple_detected(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        make_commit(git, "feat: first\n\noutcome: success")
        make_commit(git, "fix: second\n\noutcome: success")

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 0)

        assert "Multiple commits detected" in str(exc_info.value)

    def test_multiple_commits_error_lists_hashes_and_subjects(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        make_commit(git, "feat: first change")
        make_commit(git, "fix: second change")

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 0)

        error_msg = str(exc_info.value)
        assert "first change" in error_msg
        assert "second change" in error_msg


class TestBuildTurnResultNonZeroExitError:
    """Tests for non-zero exit code error message content."""

    def test_nonzero_exit_includes_exit_code(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 42)

        error_msg = str(exc_info.value)
        assert "42" in error_msg
        assert "exit" in error_msg.lower()

    def test_nonzero_exit_includes_log_file_path(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 1)

        assert str(turn.log_file) in str(exc_info.value)


class TestBuildTurnResultSignalError:
    """Tests for signal termination error message content."""

    def test_signal_termination_detected(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, -15)  # SIGTERM

        error_msg = str(exc_info.value)
        assert "signal" in error_msg.lower()
        assert "SIGTERM" in error_msg


class TestBuildTurnResultAncestryMismatchError:
    """Tests for ancestry mismatch error."""

    def test_ancestry_mismatch_error_raised(
        self, session_with_git: tuple[Session, Git, Driver, Path]
    ) -> None:
        session, git, driver, repo = session_with_git
        make_commit(git, "initial")
        turn = make_turn(driver, git, repo)

        # Simulate agent switching to orphan branch
        subprocess.run(
            ["git", "checkout", "--orphan", "orphan"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (repo / "orphan.txt").write_text("orphan content")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "orphan commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        with pytest.raises(RuntimeError) as exc_info:
            session.build_turn_result(turn, 0)

        error_msg = str(exc_info.value)
        assert "ancestry path" in error_msg.lower()
        assert "HEAD" in error_msg
