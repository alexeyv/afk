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
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 128:
            return None  # No commits yet
        if result.returncode != 0:
            raise RuntimeError(f"git rev-parse failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def commit_message(self, commit_hash: str) -> str:
        return self._run("log", "-1", "--format=%B", commit_hash)

    def parse_commit_message(self, commit_hash: str) -> tuple[Optional[str], str]:
        message = self.commit_message(commit_hash)
        # Find all [outcome] at line starts, take the last valid one (footer-like)
        matches = re.findall(r"^\[([^\[\]\r\n]+)\]", message, re.MULTILINE)

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
            output = self._run("log", "--format=%H", after)
        else:
            output = self._run("log", "--format=%H", f"{before}..{after}")

        if not output:
            return []

        commits = output.split("\n")
        commits.reverse()
        return commits
