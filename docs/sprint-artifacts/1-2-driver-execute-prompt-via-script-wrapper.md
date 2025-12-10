# Story 1.2: Driver - Execute Prompt via Script Wrapper

**Status:** ready-for-dev

## Story

As a framework user,
I want a `Driver` class to execute prompts against Claude Code CLI with real-time streaming,
So that I can watch the agent work and have output logged.

## Acceptance Criteria

1. **Given** Claude Code CLI is available on PATH
   **When** I instantiate `Driver(workspace)` and call `driver.run(prompt, log_file)`
   **Then** the prompt is passed to Claude Code CLI in the specified workspace
   **And** output streams to terminal in real-time
   **And** output is captured to the specified log file
   **And** the method blocks until the process exits

2. **Given** the `script` command is used to wrap CLI execution
   **When** the agent runs
   **Then** Claude Code CLI behaves as if in a real terminal (proper streaming)
   **And** all output including ANSI codes is captured to log

3. **Given** a prompt execution is in progress
   **When** I send SIGINT (Ctrl+C)
   **Then** the CLI process is terminated
   **And** no orphan processes remain
   **And** partial log output is preserved

## Tasks / Subtasks

- [ ] Task 1: Create `afk/driver.py` module with `Driver` class (AC: 1, 2)
  - [ ] 1.1: Implement `Driver` class with `__init__(self, workspace: str)`
  - [ ] 1.2: Implement `run(self, prompt: str, log_file: str) -> int` using `script` command
  - [ ] 1.3: Build command array for `script` wrapping `claude` CLI with `--print` flag
  - [ ] 1.4: Implement subprocess execution with real-time stdout passthrough
  - [ ] 1.5: Ensure log file captures all output via `script` mechanism
- [ ] Task 2: Implement signal handling for clean interruption (AC: 3)
  - [ ] 2.1: Handle SIGINT gracefully - terminate child process group
  - [ ] 2.2: Ensure no orphan processes (use process groups or explicit cleanup)
  - [ ] 2.3: Preserve partial log output on interrupt
- [ ] Task 3: Create tests for `Driver` class (AC: 1, 2, 3)
  - [ ] 3.1: Create `tests/test_driver.py` with workspace fixture
  - [ ] 3.2: Create `tests/fixtures/` directory with fake CLI scripts
  - [ ] 3.3: Test `driver.run()` executes command and returns exit code
  - [ ] 3.4: Test log file is created and contains output
  - [ ] 3.5: Test SIGINT handling (process terminates, log preserved)
- [ ] Task 4: Export Driver from package (AC: all)
  - [ ] 4.1: Add `Driver` to `afk/__init__.py` exports
- [ ] Task 5: Verify integration (AC: all)
  - [ ] 5.1: Run full test suite with `pytest tests/test_driver.py -v`
  - [ ] 5.2: Verify all acceptance criteria pass
  - [ ] 5.3: Run `ruff check afk/ tests/` to verify linting

## Dev Notes

### Architecture Compliance

**File Location:** `afk/driver.py` - One file per domain entity (flat structure per architecture)

**Driver Role:** The Driver is the Claude Code CLI wrapper. It:
- Uses `script` command to make Claude Code think it's in a terminal
- Passes through output to terminal in real-time
- Captures all output (including ANSI codes) to log file
- Returns exit code (does NOT interpret results - that's for higher layers)

### Technical Requirements

**The `script` Command:**
- macOS/Linux utility that records terminal sessions
- Makes wrapped process think it's in a real PTY (pseudo-terminal)
- Claude Code CLI streams properly when it detects a terminal
- Syntax: `script -q <logfile> <command>`
- On macOS: `script -q <logfile> <command>` runs command and logs to file
- On Linux: `script -q -c "<command>" <logfile>` (slightly different syntax)

**Platform Detection:**
- Use `sys.platform` to detect OS
- macOS: `sys.platform == "darwin"`
- Linux: `sys.platform.startswith("linux")`
- Build command appropriately for each platform

**Claude Code CLI:**
- Command: `claude`
- Flag for non-interactive: `--print` (outputs response without interactive UI)
- The prompt is passed via stdin or as argument
- For MVP: pass prompt as argument with `--print` flag
- Full command: `claude --print "prompt text"`

**Process Management:**
- Use `subprocess.Popen` for streaming output
- Create new process group to enable clean termination
- On interrupt: kill entire process group (not just parent)
- Use `os.killpg(os.getpgid(proc.pid), signal.SIGTERM)`

### Implementation Guidance

**Driver Class Structure:**
```python
import os
import signal
import subprocess
import sys
from pathlib import Path


class Driver:
    def __init__(self, workspace: str):
        self.workspace = workspace

    def run(self, prompt: str, log_file: str) -> int:
        """Execute prompt against Claude Code CLI, return exit code."""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._build_command(prompt, str(log_path))

        # Start process in new process group for clean termination
        proc = subprocess.Popen(
            cmd,
            cwd=self.workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # Creates new process group
        )

        try:
            # Stream output to terminal while script captures to file
            for line in proc.stdout:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            proc.wait()
        except KeyboardInterrupt:
            # Kill entire process group on Ctrl+C
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait()

        return proc.returncode

    def _build_command(self, prompt: str, log_file: str) -> list[str]:
        """Build script-wrapped claude command for current platform."""
        claude_cmd = ["claude", "--print", prompt]

        if sys.platform == "darwin":
            # macOS: script -q <logfile> <command...>
            return ["script", "-q", log_file] + claude_cmd
        else:
            # Linux: script -q -c "command" <logfile>
            cmd_str = " ".join(claude_cmd)
            return ["script", "-q", "-c", cmd_str, log_file]
```

**Important Notes:**
- The `script` command handles the log file creation and writing
- We still need to pass through stdout for real-time display
- `start_new_session=True` creates a new process group (equivalent to `os.setpgrp()`)
- On SIGINT, we kill the process group, not just the parent process

### Testing Guidance

**Fake CLI Fixtures:**
Create simple Python scripts that simulate Claude Code CLI behavior for testing:

```python
# tests/fixtures/cli_success.py
#!/usr/bin/env python3
"""Fake CLI that prints output and exits 0."""
import sys
import time

print("Starting task...")
sys.stdout.flush()
time.sleep(0.1)
print("Task completed successfully.")
sys.exit(0)
```

```python
# tests/fixtures/cli_failure.py
#!/usr/bin/env python3
"""Fake CLI that prints output and exits 1."""
import sys

print("Starting task...")
print("Error: Something went wrong.")
sys.exit(1)
```

```python
# tests/fixtures/cli_slow.py
#!/usr/bin/env python3
"""Fake CLI that runs slowly (for interrupt testing)."""
import sys
import time

print("Starting slow task...")
sys.stdout.flush()
for i in range(10):
    print(f"Working... {i}")
    sys.stdout.flush()
    time.sleep(0.5)
print("Done.")
sys.exit(0)
```

**Test Structure:**
```python
import os
import subprocess
from pathlib import Path

import pytest

from afk.driver import Driver


@pytest.fixture
def workspace(tmp_path: Path) -> str:
    """Create a temp workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return str(ws)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


class TestDriverRun:
    def test_executes_command_and_returns_exit_code(
        self, workspace: str, tmp_path: Path, fixtures_dir: Path
    ):
        driver = Driver(workspace)
        log_file = str(tmp_path / "test.log")

        # Use a simple echo command instead of fake CLI for basic test
        # (We'll test with fake CLI in integration tests)
        # For unit test, verify the mechanism works

        # ... test implementation

    def test_creates_log_file_with_output(
        self, workspace: str, tmp_path: Path
    ):
        driver = Driver(workspace)
        log_file = str(tmp_path / "test.log")

        # Run command that produces output
        # Verify log file exists and contains output
```

**Testing Approach:**
1. Unit tests use simple commands (echo, cat) to verify mechanism
2. Integration tests use fake CLI scripts to simulate real behavior
3. Signal handling tests use `cli_slow.py` with subprocess to send SIGINT
4. Make fixtures executable: `chmod +x tests/fixtures/*.py`

### Previous Story Learnings (from 1-1)

From the completed Story 1.1:
- Use `subprocess.run` for simple commands, `subprocess.Popen` for streaming
- Always configure git user in test fixtures before making commits
- Use `uuid.uuid4().hex[:8]` for unique filenames in tests
- `RuntimeError` for all errors (no custom exception classes)
- Tests organized by class: `TestDriverRun`, `TestSignalHandling`, etc.
- Use `tmp_path` fixture from pytest for temporary directories
- Pin dependency versions in pyproject.toml

### Code Patterns from Existing Codebase

**From `afk/git.py`:**
```python
# Subprocess error handling pattern
result = subprocess.run(
    ["git", *args],
    cwd=self.repo_path,
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
```

**From `tests/test_git.py`:**
```python
# Fixture pattern
@pytest.fixture
def git_repo(tmp_path: Path) -> Git:
    """Create a temp git repo with user config for commits."""
    # setup code
    return Git(str(tmp_path))
```

### Edge Cases

- **Claude Code CLI not installed:** `FileNotFoundError` when subprocess tries to run `claude`. Let it propagate - caller should check CLI availability before calling Driver.
- **Prompt with special characters:** Shell escaping handled by subprocess when using list form (not shell=True)
- **Very long prompts:** May hit command-line length limits. For MVP, accept this limitation. Future: use stdin or temp file.
- **Log file in non-existent directory:** Create parent directories with `mkdir(parents=True)`
- **Permission denied on log file:** Let exception propagate with full context

### What NOT To Do

- Don't validate that Claude Code CLI exists - let subprocess fail naturally
- Don't parse or interpret CLI output - just pass it through
- Don't create custom exception classes
- Don't add timeout handling yet (that's Story 1.4)
- Don't handle multiple commits (that's Story 1.3)
- Don't use `shell=True` in subprocess calls (security risk, escaping issues)
- Don't mock subprocess in tests - use real processes with fake scripts

### Dependencies

**From pyproject.toml (already present):**
- pytest>=9,<10
- ruff>=0.14,<1

**No new dependencies needed** - uses only stdlib:
- subprocess
- os
- signal
- sys
- pathlib

## References

- [Source: docs/architecture.md#Driver Interface] - Use `script` command to wrap CLI
- [Source: docs/architecture.md#Streaming] - `script` handles terminal emulation and logging
- [Source: docs/architecture.md#Python Conventions] - snake_case, RuntimeError, no docstrings
- [Source: docs/architecture.md#Project Structure] - afk/driver.py location
- [Source: docs/architecture.md#Test Strategy] - Fake CLI scripts for integration tests
- [Source: docs/prd.md#FR1] - Execute prompt against CLI with structured results
- [Source: docs/prd.md#FR2] - Real-time streaming to terminal
- [Source: docs/prd.md#NFR5] - Clean interrupt handling (no orphan processes)
- [Source: docs/epics.md#Story 1.2] - Acceptance criteria source
- [Source: docs/sprint-artifacts/1-1-git-operations-foundation.md] - Previous story patterns

## Dev Agent Record

### Context Reference

<!-- Story created by SM agent create-story workflow (YOLO mode) -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### Change Log

### File List
