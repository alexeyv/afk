import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from afk.driver import Driver

PROJECT_ROOT = str(Path(__file__).parent.parent)


@pytest.fixture
def workspace(tmp_path: Path) -> str:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return str(ws)


def fake_claude(tmp_path: Path, *, exit_code: int = 0, output: str = "", delay: float = 0) -> Path:
    """Create a fake claude CLI script. Returns path to bin directory for PATH injection."""
    fake_bin = tmp_path / f"bin_{exit_code}_{delay}"
    fake_bin.mkdir(exist_ok=True)
    script = fake_bin / "claude"

    delay_cmd = f"sleep {delay}" if delay else ""
    script.write_text(f"""#!/bin/bash
echo "Claude received: $@"
{f'echo "{output}"' if output else ''}
{delay_cmd}
exit {exit_code}
""")
    script.chmod(0o755)
    return fake_bin


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

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_macos_command_format(self, workspace: str):
        driver = Driver(workspace)
        cmd = driver._build_command("my prompt", "/path/to/log.txt")

        # macOS: script -q <logfile> claude --print <prompt>
        assert cmd[0] == "script"
        assert cmd[1] == "-q"
        assert cmd[2] == "/path/to/log.txt"
        assert cmd[3] == "claude"
        assert cmd[4] == "--print"
        assert cmd[5] == "my prompt"

    @pytest.mark.skipif(sys.platform == "darwin", reason="Linux-specific test")
    def test_linux_command_format(self, workspace: str):
        driver = Driver(workspace)
        cmd = driver._build_command("my prompt", "/path/to/log.txt")

        # Linux: script -q -c "<command>" <logfile>
        assert cmd[0] == "script"
        assert cmd[1] == "-q"
        assert cmd[2] == "-c"
        assert "claude --print 'my prompt'" in cmd[3] or "claude --print my prompt" in cmd[3]
        assert cmd[4] == "/path/to/log.txt"

    @pytest.mark.skipif(sys.platform == "darwin", reason="Linux-specific test")
    def test_linux_command_escapes_shell_metacharacters(self, workspace: str):
        driver = Driver(workspace)
        malicious_prompt = "hello; rm -rf / #"
        cmd = driver._build_command(malicious_prompt, "/tmp/log.txt")

        # Linux: script -q -c "<escaped command>" <logfile>
        cmd_str = cmd[3]
        # The prompt should be quoted as a single unit
        assert "'hello; rm -rf / #'" in cmd_str


class TestDriverRunWithFakeCLI:
    def test_executes_and_returns_exit_code_zero(
        self, workspace: str, tmp_path: Path
    ):
        cli = fake_claude(tmp_path)
        log_file = str(tmp_path / "test.log")

        env = os.environ.copy()
        env["PATH"] = f"{cli}:{env['PATH']}"

        # Run with modified PATH via subprocess
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
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
        self, workspace: str, tmp_path: Path
    ):
        cli = fake_claude(tmp_path, exit_code=1, output="Claude error: something went wrong")
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
driver = Driver('{workspace}')
exit_code = driver.run('test prompt', '{log_file}')
sys.exit(exit_code)
""",
            ],
            env=env,
            capture_output=True,
        )
        assert result.returncode == 1

    def test_creates_log_file(self, workspace: str, tmp_path: Path):
        cli = fake_claude(tmp_path)
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
driver = Driver('{workspace}')
driver.run('test prompt', '{log_file}')
""",
            ],
            env=env,
            capture_output=True,
        )
        assert Path(log_file).exists()

    def test_log_file_contains_output(
        self, workspace: str, tmp_path: Path
    ):
        cli = fake_claude(tmp_path)
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
driver = Driver('{workspace}')
driver.run('hello world prompt', '{log_file}')
""",
            ],
            env=env,
            capture_output=True,
        )
        content = Path(log_file).read_text()
        assert "hello world prompt" in content

    def test_model_flag_passed_to_cli(
        self, workspace: str, tmp_path: Path
    ):
        cli = fake_claude(tmp_path)
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
driver = Driver('{workspace}', model='claude-3-5-haiku-latest')
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
    @pytest.mark.skipif(sys.platform == "win32", reason="SIGINT not available on Windows")
    def test_sigint_terminates_process(
        self, workspace: str, tmp_path: Path
    ):
        cli = fake_claude(tmp_path, delay=5)
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
        self, workspace: str, tmp_path: Path
    ):
        cli = fake_claude(tmp_path, delay=5)
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
