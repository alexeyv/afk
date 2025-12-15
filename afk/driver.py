import os
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path

_env_checked = False


def _require_command(name: str, check_args: list[str] | None = None) -> None:
    """Check that a command exists and optionally runs with given args."""
    if shutil.which(name) is None:
        raise RuntimeError(f"`{name}` not found on PATH")
    if check_args is not None:
        cmd = [name] + check_args
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"`{' '.join(cmd)}` failed (exit {result.returncode})")


def _check_environment() -> None:
    """Check runtime environment once, cache result."""
    global _env_checked
    if _env_checked:
        return

    if sys.platform == "win32":
        raise RuntimeError("Windows is not supported")

    _require_command("git", ["--version"])
    _require_command("script")
    _require_command("claude", ["--version"])

    _env_checked = True


class Driver:
    __slots__ = ("_working_dir", "_model")

    def __init__(self, working_dir: Path, *, model: str | None = None):
        _check_environment()
        if not isinstance(working_dir, Path):
            raise TypeError(f"expected Path, got {working_dir!r}")
        if not working_dir.is_absolute():
            raise ValueError("working_dir must be an absolute path")
        self._working_dir = working_dir
        self._model = model

    def __repr__(self) -> str:
        return f"Driver({self._working_dir!r}, model={self._model!r})"

    @property
    def working_dir(self) -> Path:
        """Return the working directory for command execution."""
        return self._working_dir

    @property
    def model(self) -> str | None:
        return self._model

    def run(self, prompt: str, log_file: str) -> int:
        log_path = Path(log_file).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._build_command(prompt, str(log_path))

        proc = subprocess.Popen(
            cmd,
            cwd=self._working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        try:
            # Stream output to terminal. The `script` command captures everything
            # (including ^C) to the log file for debugging.
            #
            # KeyboardInterrupt propagates intentionally - user interrupts should
            # abort immediately. The log file preserves ^C for post-mortem.
            if proc.stdout is None:
                raise RuntimeError("internal error: stdout not captured")
            for line in proc.stdout:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            proc.wait()
        finally:
            # Ensure child process group is terminated on any exit.
            # start_new_session=True puts child in its own group, so we must
            # explicitly clean up to avoid orphans.
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    proc.wait()

        return proc.returncode

    def _build_command(self, prompt: str, log_file: str) -> list[str]:
        claude_cmd = ["claude", "--print"]
        if self._model:
            claude_cmd.extend(["--model", self._model])
        claude_cmd.append(prompt)

        if sys.platform == "darwin":
            return ["script", "-a", "-q", log_file] + claude_cmd
        else:
            cmd_str = " ".join(shlex.quote(arg) for arg in claude_cmd)
            return ["script", "-a", "-q", "-c", cmd_str, log_file]
