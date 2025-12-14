import os
import subprocess
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


@pytest.fixture(autouse=True)
def reset_turn_counter() -> None:
    """Reset Turn counter before each test."""
    Turn.reset_turn_counter()


def make_turn(n: int, transition_type: str = "coding") -> Turn:
    """Helper to create Turn instances for testing."""
    return Turn(
        turn_number=n,
        transition_type=TransitionType(transition_type),
        result=TurnResult(outcome="success", message="test", commit_hash="abc123"),
        log_file=Path(f"/logs/turn-{n:03d}.log"),
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
def session_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Driver]:
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
    driver = Driver(git)
    return repo, driver


class TestSession:
    def test_empty_session(self, session_env: tuple[Path, Driver]) -> None:
        """AC#4: Session can be instantiated and returns empty tuple of turns."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        assert session.turns == ()
        assert list(session) == []

    def test_add_single_turn(self, session_env: tuple[Path, Driver]) -> None:
        """AC#1: add_turn adds turn to session."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        turn = make_turn(1, "init")
        session.add_turn(turn)
        assert session.turns == (turn,)

    def test_add_multiple_turns_in_order(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """AC#1: Turns are stored in order of addition."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        t1 = make_turn(1, "init")
        t2 = make_turn(2, "coding")
        t3 = make_turn(3, "coding")
        session.add_turn(t1)
        session.add_turn(t2)
        session.add_turn(t3)
        assert session.turns == (t1, t2, t3)

    def test_turn_lookup_by_number(self, session_env: tuple[Path, Driver]) -> None:
        """AC#2: turn(n) returns correct turn by turn_number."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        t1 = make_turn(1)
        t2 = make_turn(2)
        session.add_turn(t1)
        session.add_turn(t2)
        assert session.turn(1) is t1
        assert session.turn(2) is t2

    def test_turn_lookup_raises_keyerror(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """AC#2: turn(n) raises KeyError for non-existent turn."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        session.add_turn(make_turn(1))
        with pytest.raises(KeyError):
            session.turn(99)

    def test_iteration_chronological_order(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """AC#3: Iteration yields turns in chronological order."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        turns = [make_turn(i) for i in range(1, 4)]
        for t in turns:
            session.add_turn(t)
        assert list(session) == turns

    def test_turns_property_is_immutable(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """AC#4: turns property returns tuple (immutable view)."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        session.add_turn(make_turn(1))
        turns = session.turns
        assert isinstance(turns, tuple)

    def test_first_turn_must_be_one(self, session_env: tuple[Path, Driver]) -> None:
        """First turn must have turn_number 1."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        with pytest.raises(ValueError, match="First turn must be turn 1"):
            session.add_turn(make_turn(5))  # Must start at 1

    def test_add_turn_requires_monotonic_increase(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """Turn numbers must be monotonically increasing."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        session.add_turn(make_turn(1))
        session.add_turn(make_turn(5))  # Gap is fine
        with pytest.raises(ValueError, match="must be > 5"):
            session.add_turn(make_turn(3))  # Going backwards - fails

    def test_add_turn_rejects_duplicate(self, session_env: tuple[Path, Driver]) -> None:
        """Cannot add turn with same number as existing turn."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        session.add_turn(make_turn(1))
        with pytest.raises(ValueError, match="must be > 1"):
            session.add_turn(make_turn(1))  # Duplicate - fails

    def test_failed_add_doesnt_corrupt_state(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """Failed add_turn must leave session state unchanged."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        session.add_turn(make_turn(1))
        with pytest.raises(ValueError):
            session.add_turn(make_turn(1))  # Duplicate - fails
        session.add_turn(make_turn(2))  # Valid next - should work
        assert len(session) == 2
        assert session.turn(1).turn_number == 1
        assert session.turn(2).turn_number == 2


class TestSessionRootDir:
    """Tests for Session root_dir and log_dir properties."""

    def test_root_dir_returns_session_root(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """root_dir property returns the session root directory."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        assert session.root_dir == root_dir

    def test_log_dir_returns_logs_subdirectory(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """log_dir property returns root_dir / 'logs'."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        assert session.log_dir == root_dir / "logs"

    def test_log_dir_is_absolute(self, session_env: tuple[Path, Driver]) -> None:
        """log_dir property returns an absolute path."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        assert session.log_dir.is_absolute()


class TestSessionValidation:
    """Tests for Session input validation."""

    def test_rejects_string_root_dir(self, session_env: tuple[Path, Driver]) -> None:
        """root_dir must be Path, not string."""
        _, driver = session_env
        with pytest.raises(TypeError, match="expected Path, got '/some/path'"):
            Session("/some/path", driver)  # type: ignore[arg-type]

    def test_rejects_relative_root_dir(self, session_env: tuple[Path, Driver]) -> None:
        """root_dir must be absolute."""
        _, driver = session_env
        with pytest.raises(ValueError, match="must be an absolute path"):
            Session(Path("relative/path"), driver)

    def test_rejects_nonexistent_root_dir(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """root_dir must be an existing directory."""
        _, driver = session_env
        with pytest.raises(ValueError, match="must be a directory"):
            Session(Path("/nonexistent/path"), driver)

    def test_rejects_file_as_root_dir(
        self, tmp_path: Path, session_env: tuple[Path, Driver]
    ) -> None:
        """root_dir must be a directory, not a file."""
        _, driver = session_env
        file_path = tmp_path / "somefile.txt"
        file_path.write_text("content")
        with pytest.raises(ValueError, match="must be a directory"):
            Session(file_path, driver)

    def test_rejects_non_driver(self, session_env: tuple[Path, Driver]) -> None:
        """driver must be Driver instance."""
        root_dir, _ = session_env
        with pytest.raises(TypeError, match="expected Driver, got 'not a driver'"):
            Session(root_dir, "not a driver")  # type: ignore[arg-type]

    def test_rejects_non_turn_in_add_turn(
        self, session_env: tuple[Path, Driver]
    ) -> None:
        """add_turn rejects non-Turn values."""
        root_dir, driver = session_env
        session = Session(root_dir, driver)
        with pytest.raises(TypeError, match="expected Turn, got 'not a turn'"):
            session.add_turn("not a turn")  # type: ignore[arg-type]


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
    driver = Driver(git)
    return Session(repo, driver)


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
    driver = Driver(git)
    return Session(repo, driver)


class TestSessionExecuteTurn:
    """Tests for Session.execute_turn() method."""

    def test_creates_turn_with_correct_number(self, execute_session: Session) -> None:
        """AC#1: execute_turn creates Turn with correct turn_number."""
        turn = execute_session.execute_turn("test prompt", TransitionType("init"))

        assert turn.turn_number == 1
        assert turn.result.outcome == "success"

    def test_turn_has_correct_transition_type(self, execute_session: Session) -> None:
        """AC#1: execute_turn creates Turn with correct transition_type."""
        transition_type = TransitionType("coding")
        turn = execute_session.execute_turn("test prompt", transition_type)

        assert turn.transition_type == transition_type

    def test_turn_has_correct_log_file_path(self, execute_session: Session) -> None:
        """AC#1: execute_turn creates Turn with log_file following TurnLog pattern."""
        turn = execute_session.execute_turn("test prompt", TransitionType("init"))

        assert turn.log_file.name == "turn-00001-init.log"
        assert turn.log_file.parent == execute_session.log_dir

    def test_turn_is_added_to_session(self, execute_session: Session) -> None:
        """AC#1: execute_turn adds Turn to session."""
        turn = execute_session.execute_turn("test prompt", TransitionType("init"))

        assert len(execute_session) == 1
        assert execute_session[1] is turn

    def test_sequential_calls_increment_turn_number(
        self, execute_session: Session
    ) -> None:
        """AC#1: Sequential execute_turn calls increment turn_number."""
        turn1 = execute_session.execute_turn("prompt 1", TransitionType("init"))
        turn2 = execute_session.execute_turn("prompt 2", TransitionType("coding"))
        turn3 = execute_session.execute_turn("prompt 3", TransitionType("coding"))

        assert turn1.turn_number == 1
        assert turn2.turn_number == 2
        assert turn3.turn_number == 3

    def test_exception_does_not_create_turn(
        self, execute_session_no_commit: Session
    ) -> None:
        """Failed execution does not create a Turn - no commit means no Turn."""
        with pytest.raises(RuntimeError, match="No commit"):
            execute_session_no_commit.execute_turn(
                "test prompt", TransitionType("init")
            )

        assert len(execute_session_no_commit) == 0


class TestSessionLogging:
    """Tests for Session turn lifecycle logging."""

    def test_successful_turn_logs_start_and_end(self, execute_session: Session) -> None:
        """Successful execute_turn logs start and end markers with outcome."""
        turn = execute_session.execute_turn("test prompt", TransitionType("init"))

        log_content = turn.log_file.read_text()
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
        turn1 = execute_session.execute_turn("prompt 1", TransitionType("init"))
        turn2 = execute_session.execute_turn("prompt 2", TransitionType("coding"))

        log1_content = turn1.log_file.read_text()
        log2_content = turn2.log_file.read_text()

        assert "=== Turn 1 START ===" in log1_content
        assert "=== Turn 1 END: success ===" in log1_content
        assert "=== Turn 2 START ===" in log2_content
        assert "=== Turn 2 END: success ===" in log2_content
