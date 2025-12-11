import os
import signal
import subprocess
import sys
from pathlib import Path


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

        try:
            for line in proc.stdout:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            proc.wait()
        except KeyboardInterrupt:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
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
            cmd_str = " ".join(claude_cmd)
            return ["script", "-q", "-c", cmd_str, log_file]
