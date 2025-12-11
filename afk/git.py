import re
import subprocess
from typing import Optional


OUTCOME_MAX_LENGTH = 50


class Git:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def head_commit(self) -> Optional[str]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()

        # HEAD failed - distinguish unborn branch from broken repo
        repo_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if repo_check.returncode == 0:
            return None  # Valid repo, just no commits yet
        raise RuntimeError(f"Not a git repository: {self.repo_path}")

    def commit_message(self, commit_hash: str) -> str:
        return self._run("log", "-1", "--format=%B", commit_hash, "--")

    def parse_commit_message(self, commit_hash: str) -> tuple[Optional[str], str]:
        message = self.commit_message(commit_hash)
        # Find outcome: value footer (Conventional Commits compliant)
        # Case-insensitive - LLMs capitalize unpredictably
        # Take the last match as it's most likely in the footer
        matches = re.findall(r"^outcome:\s*(\S+)", message, re.MULTILINE | re.IGNORECASE)

        outcome: Optional[str] = None
        for raw in matches:
            candidate = raw.strip()
            if not candidate:
                continue
            if len(candidate) > OUTCOME_MAX_LENGTH:
                continue
            outcome = candidate

        return (outcome, message)

    def commits_between(self, before: Optional[str], after: str) -> list[str]:
        if before is None:
            output = self._run("log", "--reverse", "--format=%H", after, "--")
        else:
            output = self._run(
                "log", "--reverse", "--format=%H", "--ancestry-path", "--first-parent",
                f"{before}..{after}", "--"
            )

        if not output:
            return []

        return output.split("\n")
