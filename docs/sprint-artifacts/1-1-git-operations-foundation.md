# Story 1.1: Git Operations Foundation

**Status:** ready-for-dev

## Story

As a framework developer,
I want a git module that queries repo state and parses commit messages,
So that the framework can detect what the agent produced.

## Acceptance Criteria

1. **Given** a git repository exists in the target directory
   **When** I call `get_head_commit()`
   **Then** I receive the current HEAD commit hash
   **And** returns None if no commits exist

2. **Given** a commit with message following conventional format with `[outcome]` footer
   **When** I call `parse_commit_message(hash)`
   **Then** I receive a tuple of (outcome, message) where outcome is the parsed value (e.g., "success")
   **And** message is the full commit message text

3. **Given** a commit without an `[outcome]` footer
   **When** I call `parse_commit_message(hash)`
   **Then** I receive a tuple of (None, message)
   **And** message is the full commit message text

4. **Given** two commit hashes
   **When** I call `commits_between(before, after)`
   **Then** I receive a list of commit hashes made between those points
   **And** the list is ordered oldest to newest

## Tasks / Subtasks

- [ ] Task 0: Bootstrap project structure (prerequisite)
  - [ ] 0.1: Create `afk/` directory
  - [ ] 0.2: Create `afk/__init__.py` (empty file)
  - [ ] 0.3: Create `tests/` directory
  - [ ] 0.4: Create minimal `pyproject.toml` with pytest dependency
- [ ] Task 1: Create `afk/git.py` module with git operations (AC: 1, 2, 3, 4)
  - [ ] 1.1: Implement `run_git()` helper for subprocess calls
  - [ ] 1.2: Implement `get_head_commit(repo_path) -> Optional[str]`
  - [ ] 1.3: Implement `get_commit_message(repo_path, commit_hash) -> str`
  - [ ] 1.4: Implement `parse_outcome_from_message(message) -> Optional[str]`
  - [ ] 1.5: Implement `parse_commit_message(repo_path, hash) -> tuple[Optional[str], str]`
  - [ ] 1.6: Implement `commits_between(repo_path, before, after) -> list[str]`
- [ ] Task 2: Create tests for git module (AC: 1, 2, 3, 4)
  - [ ] 2.1: Create `tests/test_git.py` with `git_repo` fixture
  - [ ] 2.2: Test `get_head_commit` with repo (has commits) and empty repo (no commits)
  - [ ] 2.3: Test `parse_commit_message` with [success], [failure], and no outcome footer
  - [ ] 2.4: Test `commits_between` returns correct commits in oldest-to-newest order
  - [ ] 2.5: Test `commits_between` with `before=None` (from initial commit)
- [ ] Task 3: Verify integration (AC: all)
  - [ ] 3.1: Run full test suite with `pytest tests/test_git.py -v`
  - [ ] 3.2: Verify all acceptance criteria pass

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
- `PascalCase` for classes (none needed in this story)
- Use `RuntimeError` with descriptive messages for errors - NO exception hierarchy
- Skip docstrings unless genuinely clarifying
- Let exceptions propagate with full stack trace

**Git Operations:**
- Use `subprocess` to call git CLI directly (not GitPython or similar)
- All functions take `repo_path` as first argument to support run workspaces
- Never corrupt git state - read-only operations only in this story

### Implementation Guidance

**Subprocess Helper Pattern:**
```python
import subprocess
from typing import Optional

def run_git(repo_path: str, *args: str) -> str:
    """Run git command and return stdout. Raises RuntimeError on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()
```

**get_head_commit(repo_path):**
```python
def get_head_commit(repo_path: str) -> Optional[str]:
    try:
        return run_git(repo_path, "rev-parse", "HEAD")
    except RuntimeError as e:
        if "unknown revision" in str(e) or "bad revision" in str(e):
            return None  # No commits yet
        raise
```

**get_commit_message(repo_path, commit_hash):**
```python
def get_commit_message(repo_path: str, commit_hash: str) -> str:
    return run_git(repo_path, "log", "-1", "--format=%B", commit_hash)
```

**parse_outcome_from_message(message):**
```python
import re

def parse_outcome_from_message(message: str) -> Optional[str]:
    # Match [word] at start of any line, capture just the word
    match = re.search(r"^\[(\w+)\]", message, re.MULTILINE)
    return match.group(1) if match else None
```

**parse_commit_message(repo_path, hash):**
```python
def parse_commit_message(repo_path: str, commit_hash: str) -> tuple[Optional[str], str]:
    message = get_commit_message(repo_path, commit_hash)
    outcome = parse_outcome_from_message(message)
    return (outcome, message)
```

**commits_between(repo_path, before, after):**
```python
def commits_between(repo_path: str, before: Optional[str], after: str) -> list[str]:
    if before is None:
        # From initial commit to after
        output = run_git(repo_path, "log", "--format=%H", after)
    else:
        # Commits after 'before' up to and including 'after'
        output = run_git(repo_path, "log", "--format=%H", f"{before}..{after}")

    if not output:
        return []

    # git log returns newest-first, reverse to get oldest-first
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

@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
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
    return tmp_path

def make_commit(repo_path: Path, message: str) -> str:
    """Helper to create a commit and return its hash."""
    # Create/modify a file to have something to commit
    (repo_path / "file.txt").write_text(f"commit: {message}")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path, check=True, capture_output=True
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()
```

**Test Cases:**
1. Empty repo (git init, no commits) -> `get_head_commit` returns None
2. Repo with one commit -> `get_head_commit` returns SHA
3. Commit with `[success] task done` footer -> `parse_outcome_from_message` returns "success"
4. Commit with `[failure] tests failed` footer -> returns "failure"
5. Commit without outcome footer -> returns None for outcome
6. `parse_commit_message` returns tuple `(outcome, full_message)`
7. Three commits A->B->C -> `commits_between(A, C)` returns `[B, C]`
8. `commits_between(None, C)` returns `[A, B, C]` (from initial)

### Edge Cases

- **Detached HEAD:** Handled identically to normal HEAD - `rev-parse HEAD` returns the SHA regardless
- **No commits:** `get_head_commit` returns None (not an error)
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

<!-- To be filled by dev agent -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
- pyproject.toml (new)
- afk/__init__.py (new)
- afk/git.py (new)
- tests/test_git.py (new)
