# Story 1.1: Git Operations Foundation

**Status:** Done

## Story

As a framework developer,
I want a git module that queries repo state and parses commit messages,
So that the framework can detect what the agent produced.

## Acceptance Criteria

1. **Given** a git repository exists in the target directory
   **When** I instantiate `Git(repo_path)` and call `git.head_commit()`
   **Then** I receive the current HEAD commit hash
   **And** returns None if no commits exist

2. **Given** a commit with message following conventional format with `[outcome]` footer
   **When** I call `git.parse_commit_message(hash)`
   **Then** I receive a tuple of (outcome, message) where outcome is the parsed value (e.g., "success")
   **And** message is the full commit message text

3. **Given** a commit without an `[outcome]` footer
   **When** I call `git.parse_commit_message(hash)`
   **Then** I receive a tuple of (None, message)
   **And** message is the full commit message text

4. **Given** two commit hashes
   **When** I call `git.commits_between(before, after)`
   **Then** I receive a list of commit hashes made between those points
   **And** the list is ordered oldest to newest

## Tasks / Subtasks

- [x] Task 0: Bootstrap project structure (prerequisite)
  - [x] 0.1: Create `afk/` directory
  - [x] 0.2: Create `afk/__init__.py` (empty file)
  - [x] 0.3: Create `tests/` directory
  - [x] 0.4: Create minimal `pyproject.toml` with pytest dependency
- [x] Task 1: Create `afk/git.py` module with `Git` class (AC: 1, 2, 3, 4)
  - [x] 1.1: Implement `Git` class with `__init__(self, repo_path: str)`
  - [x] 1.2: Implement `_run(self, *args) -> str` private helper for subprocess calls
  - [x] 1.3: Implement `head_commit(self) -> Optional[str]`
  - [x] 1.4: Implement `commit_message(self, commit_hash: str) -> str`
  - [x] 1.5: Implement `parse_commit_message(self, hash: str) -> tuple[Optional[str], str]`
  - [x] 1.6: Implement `commits_between(self, before: Optional[str], after: str) -> list[str]`
- [x] Task 2: Create tests for `Git` class (AC: 1, 2, 3, 4)
  - [x] 2.1: Create `tests/test_git.py` with `git_repo` fixture returning `Git` instance
  - [x] 2.2: Test `git.head_commit()` with repo (has commits) and empty repo (no commits)
  - [x] 2.3: Test `git.parse_commit_message()` with [success], [failure], and no outcome footer
  - [x] 2.4: Test `git.commits_between()` returns correct commits in oldest-to-newest order
  - [x] 2.5: Test `git.commits_between()` with `before=None` (from initial commit)
- [x] Task 3: Verify integration (AC: all)
  - [x] 3.1: Run full test suite with `pytest tests/test_git.py -v`
  - [x] 3.2: Verify all acceptance criteria pass

## Dev Notes

### Project Bootstrap (Task 0)

This is the first story - the project structure doesn't exist yet. Create:

```
afk/
├── __init__.py          # Empty file
└── git.py               # Implement here

tests/
└── test_git.py          # Tests here

pyproject.toml           # Minimal config
```

**Minimal pyproject.toml:**
```toml
[project]
name = "afk"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

After creating, run `pip install -e ".[dev]"` to install pytest.

### Architecture Compliance

**File Location:** `afk/git.py` - One file per domain entity (flat structure per architecture)

**Commit Message Schema:** The framework expects conventional commits with outcome in footer:
```
feat: implement user authentication

Added login flow with session management.

[success] completed as specified
```

- Footer pattern: `[outcome]` followed by optional comment
- The outcome is the word inside brackets (e.g., "success", "failure")
- Default outcomes: `success`, `failure`
- Applications can define additional outcomes

### Technical Requirements

**Python Conventions (enforced by ruff):**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- Use `RuntimeError` with descriptive messages for errors - NO exception hierarchy
- Skip docstrings unless genuinely clarifying
- Let exceptions propagate with full stack trace

**Git Operations:**
- Use `subprocess` to call git CLI directly (not GitPython or similar)
- `Git` class takes `repo_path` in constructor - methods don't repeat it
- Never corrupt git state - read-only operations only in this story

### Implementation Guidance

**Git Class:**
```python
import re
import subprocess
from typing import Optional


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
            raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def head_commit(self) -> Optional[str]:
        try:
            return self._run("rev-parse", "HEAD")
        except RuntimeError as e:
            if "unknown revision" in str(e) or "bad revision" in str(e):
                return None
            raise

    def commit_message(self, commit_hash: str) -> str:
        return self._run("log", "-1", "--format=%B", commit_hash)

    def parse_commit_message(self, commit_hash: str) -> tuple[Optional[str], str]:
        message = self.commit_message(commit_hash)
        match = re.search(r"^\[(\w+)\]", message, re.MULTILINE)
        outcome = match.group(1) if match else None
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
```

### Testing Guidance

**Git Repo Fixture (CRITICAL - must configure git user):**
```python
import pytest
import subprocess
from pathlib import Path
from afk.git import Git

@pytest.fixture
def git_repo(tmp_path: Path) -> Git:
    """Create a temp git repo with user config for commits."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True, capture_output=True
    )
    return Git(str(tmp_path))

def make_commit(git: Git, message: str) -> str:
    """Helper to create a commit and return its hash."""
    repo_path = Path(git.repo_path)
    (repo_path / "file.txt").write_text(f"commit: {message}")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path, check=True, capture_output=True
    )
    return git.head_commit()
```

**Test Cases:**
1. Empty repo (git init, no commits) -> `git.head_commit()` returns None
2. Repo with one commit -> `git.head_commit()` returns SHA
3. Commit with `[success] task done` footer -> `git.parse_commit_message()` returns ("success", message)
4. Commit with `[failure] tests failed` footer -> returns ("failure", message)
5. Commit without outcome footer -> returns (None, message)
6. Three commits A->B->C -> `git.commits_between(A, C)` returns `[B, C]`
7. `git.commits_between(None, C)` returns `[A, B, C]` (from initial)

### Edge Cases

- **Detached HEAD:** Handled identically to normal HEAD - `rev-parse HEAD` returns the SHA regardless
- **No commits:** `git.head_commit()` returns None (not an error)
- **Invalid hash:** Let git error propagate as RuntimeError

### What NOT To Do

- Don't use GitPython or any git library - use subprocess directly
- Don't create exception classes - use RuntimeError
- Don't add docstrings to obvious functions
- Don't handle errors that can't happen
- Don't create config files beyond pyproject.toml
- Don't touch files outside the scope: `afk/__init__.py`, `afk/git.py`, `tests/test_git.py`, `pyproject.toml`

## References

- [Source: docs/architecture.md#Commit Message Schema] - Conventional commits with [outcome] footer
- [Source: docs/architecture.md#Python Conventions] - snake_case, RuntimeError, no docstrings
- [Source: docs/architecture.md#Project Structure] - afk/git.py location
- [Source: docs/architecture.md#Test Strategy] - pytest, fixtures for temp repos
- [Source: docs/project_context.md#Critical Rules] - Version control, Python conventions
- [Source: docs/epics.md#Story 1.1] - Acceptance criteria source

## Dev Agent Record

### Context Reference

<!-- Story created by SM agent create-story workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Bootstrapped project structure with afk/ package and tests/ directory
- Created pyproject.toml with hatchling build system and pytest/ruff dev dependencies
- Implemented Git class with all required methods following architecture guidance
- Used subprocess to call git CLI directly (no GitPython)
- Implemented head_commit(), commit_message(), parse_commit_message(), and commits_between()
- Created comprehensive test suite with 8 tests covering all acceptance criteria
- All tests pass (8/8), ruff linting passes
- Followed red-green-refactor cycle: wrote failing tests first, then implementation

**Code Review Fixes (2025-12-10):**
- Added TestCommitMessage class with tests for commit_message() and invalid hash RuntimeError
- Fixed parse_commit_message() regex to match last [outcome] (footer), not first (body)
- Added test for outcome in footer taking precedence over body
- Exported Git class from afk/__init__.py for cleaner imports
- Improved make_commit() test helper to use UUID for unique filenames (parallel-safe)
- Changed SHA test to accept both SHA-1 (40) and SHA-256 (64) hex strings
- Pinned pytest and ruff versions in pyproject.toml
- Final test count: 15 tests passing, ruff clean

**Note:** Implementation diverges from Dev Notes guidance in places (e.g., test helper uses UUID, outcome regex is more permissive). Actual code is authoritative.

### Change Log

- 2025-12-10: Initial implementation of Git operations foundation - all ACs satisfied
- 2025-12-10: Code review fixes - regex footer matching, test coverage, public API export

### File List

- pyproject.toml (new)
- afk/__init__.py (new, modified: added Git export)
- afk/git.py (new, modified: fixed regex to match footer)
- tests/test_git.py (new, modified: added 3 new tests, improved helper)
