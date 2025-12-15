import os
import subprocess
from pathlib import Path

import pytest

from afk.driver import Driver
from afk.git import Git
from afk.transition_type import TransitionType
from afk.turn import Turn, TurnState


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


@pytest.fixture
def turn_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Driver, Git]:
    """Set up environment for Turn tests with fake claude."""
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

    fake_bin = fake_claude_noop(tmp_path)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")

    git = Git(str(repo))
    driver = Driver(repo)
    return repo, driver, git


class TestTurnStateMachine:
    def test_turn_starts_in_initial_state(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """New Turn starts in INITIAL state."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        assert turn.state == TurnState.INITIAL

    def test_turn_uses_provided_number_on_start(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """Turn uses the number provided to start()."""
        root_dir, driver, git = turn_env
        turn1 = Turn(driver, git, root_dir)
        turn2 = Turn(driver, git, root_dir)
        turn1.start(1, TransitionType("init"))
        turn2.start(2, TransitionType("coding"))
        assert turn1.number == 1
        assert turn2.number == 2

    def test_start_transitions_to_in_progress(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """start() transitions from INITIAL to IN_PROGRESS."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))
        assert turn.state == TurnState.IN_PROGRESS

    def test_start_creates_log_file(self, turn_env: tuple[Path, Driver, Git]) -> None:
        """start() creates the log file with START marker."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("init"))

        assert turn.log_file.exists()
        content = turn.log_file.read_text()
        assert "=== Turn 1 START ===" in content

    def test_start_captures_head_before(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """start() captures HEAD for later validation."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        assert turn.head_before is not None
        assert len(turn.head_before) == 40  # SHA-1 hash

    def test_cannot_start_twice(self, turn_env: tuple[Path, Driver, Git]) -> None:
        """start() raises if Turn is not in INITIAL state."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        with pytest.raises(RuntimeError, match="Cannot start.*IN_PROGRESS"):
            turn.start(2, TransitionType("coding"))

    def test_execute_requires_in_progress(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """execute() raises if Turn is not in IN_PROGRESS state."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)

        with pytest.raises(RuntimeError, match="Cannot execute.*INITIAL"):
            turn.execute("prompt")

    def test_execute_returns_exit_code(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """execute() returns the driver's exit code."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        exit_code = turn.execute("test prompt")
        assert exit_code == 0

    def test_finish_transitions_to_finished(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """finish() transitions from IN_PROGRESS to FINISHED."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        turn.finish("success", "abc123", "test message")
        assert turn.state == TurnState.FINISHED

    def test_finish_returns_turn_result(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """finish() returns a frozen TurnResult."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        result = turn.finish("success", "abc123", "test message")

        assert result.turn_number == 1
        assert result.transition_type == TransitionType("coding")
        assert result.outcome == "success"
        assert result.commit_hash == "abc123"
        assert result.message == "test message"
        assert result.log_file == turn.log_file

    def test_finish_logs_end_marker(self, turn_env: tuple[Path, Driver, Git]) -> None:
        """finish() writes END marker to log."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))
        turn.finish("success", "abc123", "test message")

        content = turn.log_file.read_text()
        assert "=== Turn 1 END: success ===" in content

    def test_finish_requires_in_progress(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """finish() raises if Turn is not in IN_PROGRESS state."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)

        with pytest.raises(RuntimeError, match="Cannot finish.*INITIAL"):
            turn.finish("success", "abc123", "test message")

    def test_abort_transitions_to_aborted(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """abort() transitions from IN_PROGRESS to ABORTED."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        with pytest.raises(RuntimeError, match="test error"):
            turn.abort(RuntimeError("test error"))

        assert turn.state == TurnState.ABORTED

    def test_abort_logs_abort_marker(self, turn_env: tuple[Path, Driver, Git]) -> None:
        """abort() writes ABORT marker to log."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        with pytest.raises(RuntimeError):
            turn.abort(RuntimeError("something failed"))

        content = turn.log_file.read_text()
        assert "=== Turn 1 ABORT: RuntimeError ===" in content
        assert "something failed" in content

    def test_abort_reraises_exception(self, turn_env: tuple[Path, Driver, Git]) -> None:
        """abort() re-raises the passed exception."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(1, TransitionType("coding"))

        original_error = ValueError("original error")
        with pytest.raises(ValueError, match="original error"):
            turn.abort(original_error)

    def test_abort_requires_in_progress(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """abort() raises if Turn is not in IN_PROGRESS state."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)

        with pytest.raises(RuntimeError, match="Cannot abort.*INITIAL"):
            turn.abort(RuntimeError("error"))


class TestTurnValidation:
    def test_rejects_non_driver(self, turn_env: tuple[Path, Driver, Git]) -> None:
        """Turn requires Driver instance."""
        root_dir, _, git = turn_env
        with pytest.raises(TypeError, match="expected Driver"):
            Turn("not a driver", git, root_dir)  # type: ignore[arg-type]

    def test_rejects_non_git(self, turn_env: tuple[Path, Driver, Git]) -> None:
        """Turn requires Git instance."""
        root_dir, driver, _ = turn_env
        with pytest.raises(TypeError, match="expected Git"):
            Turn(driver, "not a git", root_dir)  # type: ignore[arg-type]

    def test_rejects_non_path_session_root(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """Turn requires Path for session_root."""
        _, driver, git = turn_env
        with pytest.raises(TypeError, match="expected Path"):
            Turn(driver, git, "/tmp/path")  # type: ignore[arg-type]

    def test_rejects_relative_session_root(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """Turn requires absolute path for session_root."""
        _, driver, git = turn_env
        with pytest.raises(ValueError, match="absolute"):
            Turn(driver, git, Path("relative/path"))

    def test_start_rejects_string_transition_type(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """start() requires TransitionType instance."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        with pytest.raises(TypeError, match="expected TransitionType"):
            turn.start(1, "coding")  # type: ignore[arg-type]

    def test_start_rejects_non_int_turn_number(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """start() requires int for turn_number."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        with pytest.raises(TypeError, match="expected int"):
            turn.start("1", TransitionType("coding"))  # type: ignore[arg-type]

    def test_start_rejects_zero_turn_number(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """start() rejects turn_number < 1."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        with pytest.raises(ValueError, match="must be >= 1"):
            turn.start(0, TransitionType("coding"))

    def test_start_rejects_max_turn_number(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """start() rejects turn_number >= MAX_TURN_NUMBER."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        with pytest.raises(ValueError, match=">="):
            turn.start(Turn.MAX_TURN_NUMBER, TransitionType("coding"))

    def test_log_file_raises_before_start(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """log_file property raises if Turn not started."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        with pytest.raises(RuntimeError, match="Cannot get log_file.*INITIAL"):
            _ = turn.log_file


class TestTurnNumberValidation:
    def test_turn_accepts_any_valid_number(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """Turn accepts any valid turn number from caller."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)
        turn.start(42, TransitionType("coding"))
        assert turn.number == 42


class TestTurnRepr:
    def test_repr_shows_number_and_state(
        self, turn_env: tuple[Path, Driver, Git]
    ) -> None:
        """repr shows turn number and current state."""
        root_dir, driver, git = turn_env
        turn = Turn(driver, git, root_dir)

        repr_str = repr(turn)
        assert "Turn" in repr_str
        assert "number=None" in repr_str  # No number before start()
        assert "INITIAL" in repr_str

        turn.start(1, TransitionType("coding"))
        repr_str = repr(turn)
        assert "number=1" in repr_str
        assert "IN_PROGRESS" in repr_str
