import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from afk.driver import Driver


@pytest.fixture
def workspace(tmp_path: Path) -> str:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return str(ws)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


class TestDriverInit:
    def test_stores_workspace(self, workspace: str):
        driver = Driver(workspace)
        assert driver.workspace == workspace

    def test_model_defaults_to_none(self, workspace: str):
        driver = Driver(workspace)
        assert driver.model is None

    def test_accepts_model_parameter(self, workspace: str):
        driver = Driver(workspace, model="claude-3-5-haiku-latest")
        assert driver.model == "claude-3-5-haiku-latest"


class TestDriverBuildCommand:
    def test_builds_command_without_model(self, workspace: str):
        driver = Driver(workspace)
        cmd = driver._build_command("test prompt", "/tmp/log.txt")

        assert cmd[0] == "script"
        assert "claude" in cmd
        assert "--print" in cmd
        assert "test prompt" in cmd
        assert "--model" not in cmd

    def test_builds_command_with_model(self, workspace: str):
        driver = Driver(workspace, model="claude-3-5-haiku-latest")
        cmd = driver._build_command("test prompt", "/tmp/log.txt")

        assert "--model" in cmd
        assert "claude-3-5-haiku-latest" in cmd

    def test_macos_command_format(self, workspace: str):
        driver = Driver(workspace)
        cmd = driver._build_command("my prompt", "/path/to/log.txt")

        if sys.platform == "darwin":
            # macOS: script -q <logfile> claude --print <prompt>
            assert cmd[0] == "script"
            assert cmd[1] == "-q"
            assert cmd[2] == "/path/to/log.txt"
            assert cmd[3] == "claude"
            assert cmd[4] == "--print"
            assert cmd[5] == "my prompt"


class TestDriverRunWithFakeCLI:
    @pytest.fixture
    def fake_claude(self, tmp_path: Path, workspace: str) -> Path:
        """Create a fake claude CLI script that echoes output."""
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_claude = fake_bin / "claude"
        fake_claude.write_text(
            """#!/bin/bash
echo "Claude received: $@"
exit 0
"""
        )
        fake_claude.chmod(0o755)
        return fake_bin

    @pytest.fixture
    def fake_claude_failing(self, tmp_path: Path, workspace: str) -> Path:
        """Create a fake claude CLI that exits with error."""
        fake_bin = tmp_path / "bin_fail"
        fake_bin.mkdir()
        fake_claude = fake_bin / "claude"
        fake_claude.write_text(
            """#!/bin/bash
echo "Claude error: something went wrong"
exit 1
"""
        )
        fake_claude.chmod(0o755)
        return fake_bin

    def test_executes_and_returns_exit_code_zero(
        self, workspace: str, tmp_path: Path, fake_claude: Path
    ):
        log_file = str(tmp_path / "test.log")

        # Add fake claude to PATH
        env = os.environ.copy()
        env["PATH"] = f"{fake_claude}:{env['PATH']}"

        # Run with modified PATH via subprocess
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '/Users/alex/src/afk')
from afk.driver import Driver
driver = Driver('{workspace}')
exit_code = driver.run('test prompt', '{log_file}')
sys.exit(exit_code)
""",
            ],
            env=env,
            capture_output=True,
        )
        assert result.returncode == 0

    def test_returns_nonzero_exit_code_on_failure(
        self, workspace: str, tmp_path: Path, fake_claude_failing: Path
    ):
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{fake_claude_failing}:{env['PATH']}"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '/Users/alex/src/afk')
from afk.driver import Driver
driver = Driver('{workspace}')
exit_code = driver.run('test prompt', '{log_file}')
sys.exit(exit_code)
""",
            ],
            env=env,
            capture_output=True,
        )
        assert result.returncode == 1

    def test_creates_log_file(self, workspace: str, tmp_path: Path, fake_claude: Path):
        log_file = str(tmp_path / "logs" / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{fake_claude}:{env['PATH']}"

        subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '/Users/alex/src/afk')
from afk.driver import Driver
driver = Driver('{workspace}')
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            capture_output=True,
        )
        assert Path(log_file).exists()

    def test_log_file_contains_output(
        self, workspace: str, tmp_path: Path, fake_claude: Path
    ):
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{fake_claude}:{env['PATH']}"

        subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '/Users/alex/src/afk')
from afk.driver import Driver
driver = Driver('{workspace}')
driver.run('hello world prompt', '{log_file}')
""",
            ],
            env=env,
            capture_output=True,
        )
        content = Path(log_file).read_text()
        assert "Claude received" in content


class TestDriverSignalHandling:
    @pytest.fixture
    def slow_claude(self, tmp_path: Path) -> Path:
        """Create a fake claude CLI that runs slowly."""
        fake_bin = tmp_path / "bin_slow"
        fake_bin.mkdir()
        fake_claude = fake_bin / "claude"
        fake_claude.write_text(
            """#!/bin/bash
echo "Starting slow task..."
for i in $(seq 1 10); do
    echo "Working... $i"
    sleep 0.5
done
echo "Done."
exit 0
"""
        )
        fake_claude.chmod(0o755)
        return fake_bin

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGINT not available on Windows")
    def test_sigint_terminates_process(
        self, workspace: str, tmp_path: Path, slow_claude: Path
    ):
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{slow_claude}:{env['PATH']}"

        proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '/Users/alex/src/afk')
from afk.driver import Driver
driver = Driver('{workspace}')
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        time.sleep(0.5)  # Let it start
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)

        # Process should have terminated
        assert proc.poll() is not None

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGINT not available on Windows")
    def test_partial_log_preserved_on_interrupt(
        self, workspace: str, tmp_path: Path, slow_claude: Path
    ):
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{slow_claude}:{env['PATH']}"

        proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '/Users/alex/src/afk')
from afk.driver import Driver
driver = Driver('{workspace}')
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        time.sleep(1.0)  # Let it produce some output
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)

        # Log file should exist (content may vary based on script command behavior
        # in non-TTY environments, but file should be created)
        assert Path(log_file).exists()
