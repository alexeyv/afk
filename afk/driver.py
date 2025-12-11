import shlex
import subprocess
import sys
from pathlib import Path


if sys.platform == "win32":
    raise RuntimeError("Windows is not supported")

if subprocess.run(["which", "claude"], capture_output=True).returncode != 0:
    raise RuntimeError("`claude` not found on PATH")


class Driver:
    def __init__(self, workspace: str, *, model: str | None = None):
        self.workspace = workspace
        self.model = model

    def run(self, prompt: str, log_file: str) -> int:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._build_command(prompt, str(log_path))

        proc = subprocess.Popen(
            cmd,
            cwd=self.workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        # Stream output to terminal. The `script` command captures everything
        # (including ^C on interrupt) to the log file for later inspection.
        for line in proc.stdout:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        proc.wait()

        return proc.returncode

    def _build_command(self, prompt: str, log_file: str) -> list[str]:
        claude_cmd = ["claude", "--print"]
        if self.model:
            claude_cmd.extend(["--model", self.model])
        claude_cmd.append(prompt)

        if sys.platform == "darwin":
            return ["script", "-q", log_file] + claude_cmd
        else:
            cmd_str = " ".join(shlex.quote(arg) for arg in claude_cmd)
            return ["script", "-q", "-c", cmd_str, log_file]
