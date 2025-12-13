# Story 1.4: Exception Handling for Prompt Execution

Status: Done

## Story

As a framework user,
I want clear errors when prompt execution fails,
so that I can understand what went wrong and take corrective action.

## Acceptance Criteria

1. **Given** a prompt execution that produces zero commits
   **When** the driver completes
   **Then** a `RuntimeError` is raised with message indicating no commit was detected

2. **Given** a prompt execution that produces multiple commits
   **When** the driver completes
   **Then** a `RuntimeError` is raised with message listing the commit hashes

3. **Given** Claude Code CLI is not available or not working
   **When** I attempt to run a prompt
   **Then** a `RuntimeError` is raised indicating Claude Code CLI is unavailable

4. **Given** the CLI process dies unexpectedly (non-zero exit, signal)
   **When** the driver completes
   **Then** a `RuntimeError` is raised with exit code or signal information
   **And** the partial log file is preserved for debugging

## Tasks / Subtasks

- [x] Task 1: Improve zero-commit error handling in `execute_turn` (AC: #1)
  - [x] 1.1: Replace generic "Expected 1 commit" with "No commit detected" message
  - [x] 1.2: Include HEAD before, HEAD after, log file path
  - [x] 1.3: Include last 5 lines of log file in error message

- [x] Task 2: Improve multiple-commit error handling in `execute_turn` (AC: #2)
  - [x] 2.1: Replace generic message with "Multiple commits detected" message
  - [x] 2.2: List all commits with hash + subject line (use `git log --format="%h: %s"`)

- [x] Task 3: Improve CLI availability check in `Driver` (AC: #3)
  - [x] 3.1: Change `which claude` to `claude --version` (catches aliases, auth issues, etc.)
  - [x] 3.2: Verify error is raised before any execution attempt

- [x] Task 4: Enhance non-zero exit code handling (AC: #4)
  - [x] 4.1: Current implementation raises RuntimeError on non-zero exit - enhance message
  - [x] 4.2: Include exit code in message
  - [x] 4.3: For signal termination, include signal number if available
  - [x] 4.4: Include log file path in error message for debugging

- [x] Task 5: Add signal/termination detection (AC: #4)
  - [x] 5.1: Detect if process was killed by signal (negative return code on Unix)
  - [x] 5.2: Map common signals to human-readable names (SIGTERM, SIGKILL, SIGINT)
  - [x] 5.3: Include signal info in error message

- [x] Task 6: Write comprehensive tests (AC: all)
  - [x] 6.1: Test zero commits error message content
  - [x] 6.2: Test multiple commits error message lists hashes
  - [x] 6.3: Test CLI unavailable error message contains install URL
  - [x] 6.4: Test non-zero exit includes exit code
  - [x] 6.5: Test signal termination includes signal info
  - [x] 6.6: Test log file is preserved on all error conditions

## Dev Notes

### Architecture Compliance

This story completes Epic 1 by adding proper exception handling. Per architecture:

- **Use `RuntimeError` with descriptive messages** - no custom exception classes
- **Exceptions halt the machine** - no partial state, human intervention required
- **Crash with full context** - don't swallow stack traces
- **Preserve logs even on crash** (NFR6)

From `docs/architecture.md#Error/Exception Handling`:
> "Exceptions bubble up naturally, no catching unless adding value"
> "Framework raises exceptions for its failure modes (no commit, multiple commits, process died)"
> "Crash with full context is the right behavior for a lab tool"

### What Already Exists

**In `executor.py`:**
```python
# Current error handling (basic)
if exit_code != 0:
    raise RuntimeError(f"Driver exited with code {exit_code}")

if head_after is None:
    raise RuntimeError("No commits after execution (HEAD is unborn)")

if len(commits) != 1:
    raise RuntimeError(f"Expected 1 commit, got {len(commits)}")
```

**In `driver.py`:**
```python
def _check_environment() -> None:
    # ...
    if subprocess.run(["which", "claude"], capture_output=True).returncode != 0:
        raise RuntimeError("`claude` not found on PATH")
```

These need to be enhanced with better messages, not replaced with different error types.

### Exception Categories (from Architecture)

Per `docs/architecture.md#Execution Model`:

| Exception | Meaning | Current Status |
|-----------|---------|----------------|
| Zero commits | Turn didn't complete | Basic handling exists |
| Multiple commits | Turn violated invariant | Basic handling exists |
| Timeout | Agent took too long | **OUT OF SCOPE** - future story |
| Process died | CLI crashed | Basic handling exists |
| CLI unavailable | Can't execute | Basic handling exists |

This story improves the **error messages**, not the detection logic.

### Error Message Guidelines

Each error message should include:
1. **What happened** - Clear description of the failure
2. **Context** - Relevant state (HEAD values, commit hashes, exit codes)
3. **Debug info** - Log file path, last 5 lines of log where relevant

Example improved messages:

**Zero commits:**
```
No commit detected.

HEAD before: abc123
HEAD after: abc123
Log: /path/to/log.txt

[last 5 lines of log]
```

**Multiple commits:**
```
Multiple commits detected during turn execution.

Expected: 1 commit
Found: 3 commits
  - def456: feat: first change
  - ghi789: fix: correction
  - jkl012: docs: update readme

The framework expects exactly one commit per turn. Review the prompt
to ensure the agent commits all work in a single commit.
```

**CLI unavailable:**
```
Claude Code CLI is not available.

`claude --version` failed with exit code 1.
```

**Process died:**
```
Claude Code CLI process failed.

Exit code: 1
Log file: /path/to/log.txt

Review the log file for error details.
```

**Signal termination:**
```
Claude Code CLI process was terminated by signal.

Signal: SIGTERM (15)
Log file: /path/to/log.txt

The process was killed externally. This may indicate:
- User pressed Ctrl+C
- System ran out of resources
- Process was killed by another tool
```

### Known Limitation: macOS Exit Codes

On macOS, the `script` command does not propagate exit codes reliably. Non-zero exits often appear as 0.

**For this story:** Implement AC #4 (non-zero exit handling) normally. It will work on Linux. On macOS, failures may surface as "no commit" errors instead - that's acceptable for now.

### Signal Handling on Unix

On Unix systems, if a process is killed by a signal, `returncode` is negative:
- `returncode = -signal_number`
- Example: SIGTERM (15) -> returncode = -15

Common signals to handle:
```python
import signal

SIGNAL_NAMES = {
    signal.SIGTERM: "SIGTERM",
    signal.SIGKILL: "SIGKILL",
    signal.SIGINT: "SIGINT",
    signal.SIGSEGV: "SIGSEGV",
}
```

### Implementation Approach

**Option A: Enhance `execute_turn` inline**
Add more context to existing error raises.

**Option B: Create error helper functions**
```python
def _no_commit_error(head_before, head_after, log_file):
    return RuntimeError(f"""No commit detected during turn execution.

HEAD before: {head_before or 'None (empty repo)'}
HEAD after: {head_after}
Log file: {log_file}
...""")
```

**Recommended: Option B** - Helper functions keep the main flow readable while allowing detailed messages.

### Testing Strategy

Use the existing mock driver pattern from `test_executor.py`:

```python
def test_zero_commits_error_contains_context(self, git_repo, tmp_path):
    make_commit(git_repo, "initial")

    def mock_run(prompt: str, log_file: str) -> int:
        return 0  # Success but no commit

    driver = mock_driver(git_repo, mock_run)
    log_path = str(tmp_path / "test.log")

    with pytest.raises(RuntimeError) as exc_info:
        execute_turn(driver, "test", log_path)

    error_msg = str(exc_info.value)
    assert "No commit detected" in error_msg
    assert log_path in error_msg
```

For CLI unavailability, mock `subprocess.run` to return non-zero for `which claude`:

```python
def test_cli_unavailable_shows_install_url(self, monkeypatch):
    def mock_run(*args, **kwargs):
        if args[0] == ["which", "claude"]:
            return Mock(returncode=1)
        return Mock(returncode=0)

    monkeypatch.setattr("subprocess.run", mock_run)

    # Reset the cached check
    import afk.driver
    afk.driver._env_checked = False

    with pytest.raises(RuntimeError) as exc_info:
        Driver(some_git)

    assert "https://claude.ai/download" in str(exc_info.value)
```

### What NOT To Do

- Don't create custom exception classes
- Don't catch exceptions just to re-raise with different type
- Don't add timeout handling (future story)
- Don't modify the detection logic (zero/multiple commits) - just improve messages
- Don't change the API signatures

### Files to Modify

- `afk/executor.py` - Enhance error messages in `execute_turn`
- `afk/driver.py` - Enhance CLI check error message
- `tests/test_executor.py` - Add tests for error message content
- `tests/test_driver.py` - Add test for CLI unavailable message

### Dependencies

Story 1.3 (in review) established:
- `execute_turn()` function structure
- Basic error handling for zero/multiple commits
- Non-zero exit code handling

This story enhances but doesn't restructure that work.

### Project Structure Notes

Current structure:
```
afk/
├── __init__.py          # Exports: Driver, Git, TurnResult, execute_turn
├── driver.py            # Driver class, _check_environment()
├── executor.py          # execute_turn() function
├── git.py               # Git class
└── turn_result.py       # TurnResult dataclass
```

No new files needed - this is an enhancement story.

### References

- [Source: docs/architecture.md#Error/Exception Handling] - RuntimeError, crash with context
- [Source: docs/architecture.md#Execution Model] - Exception types (zero commits, multiple, process died)
- [Source: docs/prd.md#NFR2] - Graceful CLI unavailability handling
- [Source: docs/prd.md#NFR5] - Clean interrupt handling
- [Source: docs/prd.md#NFR6] - Preserve logs even on crash
- [Source: docs/epics.md#Story 1.4] - Acceptance criteria
- [Source: afk/executor.py] - Current execute_turn implementation
- [Source: afk/driver.py] - Current _check_environment implementation
- [Source: tests/test_executor.py] - Existing test patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Implemented error helper functions (`_no_commit_error`, `_multiple_commits_error`, `_nonzero_exit_error`, `_signal_error`) to keep main flow readable
- Enhanced zero-commit error to include HEAD before/after, log file path, and last 5 lines of log
- Enhanced multiple-commit error to list each commit with hash and subject line
- Changed CLI check from `which claude` to `claude --version` for better detection
- Added signal detection for negative return codes with human-readable signal names (SIGTERM, SIGKILL, SIGINT, SIGSEGV, SIGABRT)
- All error messages now include log file path for debugging per NFR6
- Added 17 new tests covering all error scenarios
- Fixed flaky `test_partial_log_preserved_on_interrupt` - replaced timing-dependent test with reliable platform-specific tests
- Added "Testing Rules" section to project-context.md documenting no-flaky-tests policy
- All 60 tests pass (3 OS-specific skipped)

### File List

- afk/executor.py (modified) - Added error helper functions, signal detection
- afk/driver.py (modified) - Changed CLI check to use `claude --version`
- tests/test_executor.py (modified) - Added TestZeroCommitsError, TestMultipleCommitsError, TestNonZeroExitError, TestSignalTerminationError
- tests/test_driver.py (modified) - Added TestCLIAvailability, fixed flaky signal tests
- docs/project-context.md (modified) - Added Testing Rules section

## Change Log

- 2025-12-11: Story 1.4 implementation complete - enhanced all error messages with context per AC #1-4
- 2025-12-11: Fixed flaky test, added testing rules to project context
- 2025-12-11: Code review completed (parallel reviews with custom deduplication - no formal review artifact generated)
