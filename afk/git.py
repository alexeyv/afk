import re
import subprocess
from pathlib import Path
from typing import Optional


class Git:
    __slots__ = ("_repo_path",)

    def __init__(self, repo_path: str):
        if not isinstance(repo_path, str):
            raise RuntimeError(f"repo_path must be str, got {type(repo_path).__name__}")
        path = Path(repo_path)
        if not path.exists():
            raise RuntimeError(f"repo_path does not exist: {repo_path}")
        if not path.is_dir():
            raise RuntimeError(f"repo_path is not a directory: {repo_path}")
        self._repo_path = repo_path

    def __repr__(self) -> str:
        return f"Git({self._repo_path!r})"

    @property
    def repo_path(self) -> str:
        return self._repo_path

    def head_commit(self) -> Optional[str]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
            cwd=self._repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()

        # HEAD failed - distinguish unborn branch from broken repo
        repo_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=self._repo_path,
            capture_output=True,
            text=True,
        )
        if repo_check.returncode == 0:
            return None  # Valid repo, just no commits yet
        raise RuntimeError(f"Not a git repository: {self._repo_path}")

    def commit_message(self, commit_hash: str) -> str:
        return self._run("log", "-1", "--format=%B", commit_hash, "--")

    def commit_summary(self, commit_hash: str) -> str:
        """Return short hash and subject line, e.g. 'abc1234: feat: add foo'."""
        return self._run("log", "-1", "--format=%h: %s", commit_hash, "--")

    def parse_commit_message(self, commit_hash: str) -> tuple[Optional[str], str]:
        message = self.commit_message(commit_hash)
        # Find outcome: value footer (Conventional Commits compliant)
        # Case-insensitive - LLMs capitalize unpredictably
        # Capture full value to end of line so we can show exactly what LLM wrote
        # Take the last match as it's most likely in the footer
        matches = re.findall(
            r"^outcome:\s*(.+)$", message, re.MULTILINE | re.IGNORECASE
        )

        outcome: Optional[str] = None
        for raw in matches:
            candidate = raw.strip()
            if not candidate:
                continue
            outcome = candidate.lower()

        return (outcome, message)

    def root_commit(self) -> str:
        """Return the single root commit. Raises if repo has multiple roots."""
        output = self._run("rev-list", "--max-parents=0", "HEAD")
        roots = output.split("\n") if output else []

        if len(roots) == 0:
            raise RuntimeError("No root commit found")
        if len(roots) > 1:
            raise RuntimeError(
                f"Repository has {len(roots)} root commits; only single-root repos are supported"
            )

        return roots[0]

    def commits_between(self, since: str | None, until: str) -> list[str]:
        """Return commits from since (exclusive) to until (inclusive), oldest first.

        If since is None, returns all commits from the repo's root commit.
        Note: Uses --first-parent; merge branch history not traversed.
        """
        if since is None:
            since = self.root_commit()
            # Root commit is excluded by A..B syntax, so include it explicitly
            output = self._run(
                "log",
                "--reverse",
                "--format=%H",
                "--ancestry-path",
                "--first-parent",
                f"{since}..{until}",
                "--",
            )
            commits = output.split("\n") if output else []
            return [since] + commits

        output = self._run(
            "log",
            "--reverse",
            "--format=%H",
            "--ancestry-path",
            "--first-parent",
            f"{since}..{until}",
            "--",
        )

        if not output:
            return []

        return output.split("\n")

    def is_repo(self) -> bool:
        """Check if the directory is a git repository."""
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=self._repo_path,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def init(self) -> None:
        """Initialize a new git repository."""
        self._run("init")

    def commit_empty(self, message: str) -> str:
        """Create an empty commit with the given message and return its hash."""
        self._run("commit", "--allow-empty", "-m", message)
        commit_hash = self.head_commit()
        if commit_hash is None:
            raise RuntimeError("Failed to create empty commit")
        return commit_hash

    def is_empty_directory(self) -> bool:
        """Check if directory has no files/subdirs (excluding .git)."""
        repo_path = Path(self._repo_path)
        for item in repo_path.iterdir():
            if item.name != ".git":
                return False
        return True

    def tag_exists(self, name: str) -> bool:
        """Check if a tag with the given name exists."""
        output = self._run("tag", "-l", name)
        return bool(output.strip())

    def tag(self, name: str, commit_hash: str) -> None:
        """Create a lightweight tag pointing to the specified commit.

        Raises RuntimeError if tag already exists (checked before attempting).
        """
        if self.tag_exists(name):
            raise RuntimeError(f"Tag already exists: {name}")
        self._run("tag", name, commit_hash)

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self._repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()
