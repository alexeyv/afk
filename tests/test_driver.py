import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import pytest

from afk.driver import Driver
from afk.git import Git

PROJECT_ROOT = str(Path(__file__).parent.parent)


@pytest.fixture
def git_repo(tmp_path: Path) -> Git:
    """Create a temp git repo with user config."""
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


def fake_claude(
    tmp_path: Path, *, exit_code: int = 0, output: str = "", delay: float = 0
) -> Path:
    """Create a fake claude CLI script. Returns path to bin directory for PATH injection."""
    fake_bin = tmp_path / f"bin_{exit_code}_{delay}"
    fake_bin.mkdir(exist_ok=True)
    script = fake_bin / "claude"

    delay_cmd = f"sleep {delay}" if delay else ""
    script.write_text(f"""#!/bin/bash
echo "Claude received: $@"
{f'echo "{output}"' if output else ""}
{delay_cmd}
exit {exit_code}
""")
    script.chmod(0o755)
    return fake_bin


class TestDriverInit:
    def test_stores_git(self, git_repo: Git):
        driver = Driver(git_repo)
        assert driver.git is git_repo

    def test_model_defaults_to_none(self, git_repo: Git):
        driver = Driver(git_repo)
        assert driver.model is None

    def test_accepts_model_parameter(self, git_repo: Git):
        driver = Driver(git_repo, model="claude-3-5-haiku-latest")
        assert driver.model == "claude-3-5-haiku-latest"


class TestDriverBuildCommand:
    def test_builds_command_without_model(self, git_repo: Git):
        driver = Driver(git_repo)
        cmd = driver._build_command("test prompt", "/tmp/log.txt")  # pyright: ignore[reportPrivateUsage]

        assert cmd[0] == "script"
        assert "claude" in cmd
        assert "--print" in cmd
        assert "test prompt" in cmd
        assert "--model" not in cmd

    def test_builds_command_with_model(self, git_repo: Git):
        driver = Driver(git_repo, model="claude-3-5-haiku-latest")
        cmd = driver._build_command("test prompt", "/tmp/log.txt")  # pyright: ignore[reportPrivateUsage]

        assert "--model" in cmd
        assert "claude-3-5-haiku-latest" in cmd

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_macos_command_format(self, git_repo: Git):
        driver = Driver(git_repo)
        cmd = driver._build_command("my prompt", "/path/to/log.txt")  # pyright: ignore[reportPrivateUsage]

        # macOS: script -q <logfile> claude --print <prompt>
        assert cmd[0] == "script"
        assert cmd[1] == "-q"
        assert cmd[2] == "/path/to/log.txt"
        assert cmd[3] == "claude"
        assert cmd[4] == "--print"
        assert cmd[5] == "my prompt"

    @pytest.mark.skipif(sys.platform == "darwin", reason="Linux-specific test")
    def test_linux_command_format(self, git_repo: Git):
        driver = Driver(git_repo)
        cmd = driver._build_command("my prompt", "/path/to/log.txt")  # pyright: ignore[reportPrivateUsage]

        # Linux: script -q -c "<command>" <logfile>
        assert cmd[0] == "script"
        assert cmd[1] == "-q"
        assert cmd[2] == "-c"
        assert (
            "claude --print 'my prompt'" in cmd[3]
            or "claude --print my prompt" in cmd[3]
        )
        assert cmd[4] == "/path/to/log.txt"

    @pytest.mark.skipif(sys.platform == "darwin", reason="Linux-specific test")
    def test_linux_command_escapes_shell_metacharacters(self, git_repo: Git):
        driver = Driver(git_repo)
        malicious_prompt = "hello; rm -rf / #"
        cmd = driver._build_command(malicious_prompt, "/tmp/log.txt")  # pyright: ignore[reportPrivateUsage]

        # Linux: script -q -c "<escaped command>" <logfile>
        cmd_str = cmd[3]
        # The prompt should be quoted as a single unit
        assert "'hello; rm -rf / #'" in cmd_str


def _init_git_repo(path: Path) -> None:
    """Initialize a git repo at path for subprocess tests."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )


class TestDriverRunWithFakeCLI:
    def test_executes_and_returns_exit_code_zero(self, tmp_path: Path):
        cli = fake_claude(tmp_path)
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git)
exit_code = driver.run('test prompt', '{log_file}')
sys.exit(exit_code)
""",
            ],
            env=env,
            capture_output=True,
        )
        assert result.returncode == 0

    def test_returns_nonzero_exit_code_on_failure(self, tmp_path: Path):
        cli = fake_claude(
            tmp_path, exit_code=1, output="Claude error: something went wrong"
        )
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git)
exit_code = driver.run('test prompt', '{log_file}')
sys.exit(exit_code)
""",
            ],
            env=env,
            capture_output=True,
        )
        assert result.returncode == 1

    def test_creates_log_file(self, tmp_path: Path):
        cli = fake_claude(tmp_path)
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "logs" / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git)
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            capture_output=True,
        )
        assert Path(log_file).exists()

    def test_log_file_contains_output(self, tmp_path: Path):
        cli = fake_claude(tmp_path)
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git)
driver.run('hello world prompt', '{log_file}')
""",
            ],
            env=env,
            capture_output=True,
        )
        content = Path(log_file).read_text()
        assert "hello world prompt" in content

    def test_model_flag_passed_to_cli(self, tmp_path: Path):
        cli = fake_claude(tmp_path)
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git, model='claude-3-5-haiku-latest')
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            capture_output=True,
        )
        content = Path(log_file).read_text()
        assert "--model" in content
        assert "claude-3-5-haiku-latest" in content


class TestDriverSignalHandling:
    @pytest.mark.skipif(
        sys.platform == "win32", reason="SIGINT not available on Windows"
    )
    def test_sigint_terminates_process(self, tmp_path: Path):
        cli = fake_claude(tmp_path, delay=5)
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git)
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        time.sleep(0.5)
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)

        assert proc.poll() is not None

    @pytest.mark.skipif(
        sys.platform == "win32", reason="SIGINT not available on Windows"
    )
    def test_log_created_after_completion(self, tmp_path: Path):
        """Log file should exist after driver completes normally."""
        cli = fake_claude(tmp_path, delay=0.1)
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
import afk.driver
afk.driver._env_checked = False
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git)
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        proc.wait(timeout=10)

        log_path = Path(log_file)
        assert log_path.exists(), "Log file should exist after driver completion"
        assert "test prompt" in log_path.read_text(), "Log should contain prompt"

    @pytest.mark.skipif(
        sys.platform != "linux",
        reason="Linux only: macOS script command doesn't preserve logs on signal kill",
    )
    def test_log_preserved_after_signal_kill(self, tmp_path: Path):
        """Log file should exist after process is killed by signal.

        On Linux, the script command writes partial logs when killed.
        On macOS, the script command does NOT write logs when killed mid-execution.
        This is a platform limitation, not a bug in our code.
        """
        cli = fake_claude(tmp_path, delay=30)  # Long delay, will be killed
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
import afk.driver
afk.driver._env_checked = False
from afk.driver import Driver
from afk.git import Git
git = Git('{repo_path}')
driver = Driver(git)
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        # Give process time to start and script to initialize
        time.sleep(0.5)

        # Kill the process group
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=10)

        # Log should exist after signal termination (Linux only)
        log_path = Path(log_file)
        assert log_path.exists(), "Log file should be preserved after signal kill"


class TestCLIAvailability:
    """Tests for AC #3: CLI availability error message."""

    def test_cli_unavailable_runs_version_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Should use 'claude --version' instead of 'which claude'."""
        import afk.driver

        # Reset the cached check
        afk.driver._env_checked = False  # pyright: ignore[reportPrivateUsage]

        calls: list[list[str]] = []

        original_run = subprocess.run

        def mock_run(cmd: list[str], **kwargs: Any) -> Any:
            calls.append(cmd)
            # Fail claude --version
            if cmd == ["claude", "--version"]:
                return type("Result", (), {"returncode": 1, "stderr": "error"})()
            return cast(Any, original_run(cmd, **kwargs))

        monkeypatch.setattr(subprocess, "run", mock_run)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        with pytest.raises(RuntimeError):
            Driver(Git(str(repo_path)))

        # Should have called claude --version
        assert ["claude", "--version"] in calls

    def test_cli_unavailable_error_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Error message should indicate CLI is unavailable."""
        import afk.driver

        afk.driver._env_checked = False  # pyright: ignore[reportPrivateUsage]

        original_run = subprocess.run

        def mock_run(cmd: list[str], **kwargs: Any) -> Any:
            if cmd == ["claude", "--version"]:
                return type("Result", (), {"returncode": 1, "stderr": "error"})()
            return cast(Any, original_run(cmd, **kwargs))

        monkeypatch.setattr(subprocess, "run", mock_run)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        with pytest.raises(RuntimeError) as exc_info:
            Driver(Git(str(repo_path)))

        error_msg = str(exc_info.value)
        assert "claude" in error_msg and "failed" in error_msg

    def test_cli_unavailable_mentions_version_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Error message should mention version check failed."""
        import afk.driver

        afk.driver._env_checked = False  # pyright: ignore[reportPrivateUsage]

        original_run = subprocess.run

        def mock_run(cmd: list[str], **kwargs: Any) -> Any:
            if cmd == ["claude", "--version"]:
                return type("Result", (), {"returncode": 1, "stderr": "some error"})()
            return cast(Any, original_run(cmd, **kwargs))

        monkeypatch.setattr(subprocess, "run", mock_run)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        with pytest.raises(RuntimeError) as exc_info:
            Driver(Git(str(repo_path)))

        error_msg = str(exc_info.value)
        assert "--version" in error_msg or "version" in error_msg.lower()
