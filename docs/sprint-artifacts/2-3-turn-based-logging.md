# Story 2.3: Turn-Based Logging

Status: ready-for-dev

## Story

As a framework user,
I want log files named by turn number and transition type,
so that I can easily find logs for specific turns.

## Acceptance Criteria

1. **Given** turn number 3 with transition type "coding"
   **When** generating the log file name
   **Then** the name follows pattern `turn-003-coding.log`
   **And** the file is created in the session's log directory

2. **Given** a session log directory
   **When** multiple turns execute
   **Then** each turn has its own log file
   **And** log files are never overwritten

3. **Given** a turn's log file path
   **When** I want to review that turn
   **Then** the path is accessible via `turn.log_file`

## Tasks / Subtasks

- [ ] Task 1: Create log file naming function (AC: #1)
  - [ ] 1.1: Create `format_log_filename(turn_number: int, transition_type: str) -> str` function
  - [ ] 1.2: Format turn number with zero-padding to 3 digits (e.g., 003)
  - [ ] 1.3: Return pattern `turn-{NNN}-{type}.log`
  - [ ] 1.4: Place function in appropriate module (see Design Decision below)

- [ ] Task 2: Create log path generation function (AC: #1, #2)
  - [ ] 2.1: Create `log_path_for_turn(log_dir: Path, turn_number: int, transition_type: str) -> Path`
  - [ ] 2.2: Combine log_dir with formatted filename
  - [ ] 2.3: Return absolute Path object

- [ ] Task 3: Write unit tests for log naming (AC: #1, #2, #3)
  - [ ] 3.1: Create `tests/test_log_naming.py`
  - [ ] 3.2: Test `format_log_filename` returns correct pattern for various inputs
  - [ ] 3.3: Test zero-padding works correctly (1 -> "001", 10 -> "010", 100 -> "100")
  - [ ] 3.4: Test `log_path_for_turn` combines directory and filename correctly
  - [ ] 3.5: Test log path is absolute when given absolute log_dir
  - [ ] 3.6: Test different transition types produce different filenames

- [ ] Task 4: Export functions from package (AC: all)
  - [ ] 4.1: Add exports to `afk/__init__.py`

- [ ] Task 5: Run quality gate (all ACs)
  - [ ] 5.1: Run `uv run ruff check afk/ tests/`
  - [ ] 5.2: Run `uv run ruff format --check afk/ tests/`
  - [ ] 5.3: Run `uv run pyright --threads`
  - [ ] 5.4: Run `uv run pytest`

## Dev Notes

### Architecture Compliance

This story implements FR8 from the PRD:
> "FR8: Logs and artifacts are named by turn number and transition type"

From `docs/architecture.md#Cross-Cutting Concerns`:
> "Logging: Every turn logged. Logs preserved even on crash. Named by turn number and transition type."

From `docs/architecture.md#Project Structure`:
> "Flat until it hurts. One file per domain entity."

### Design Decision: Function Location

**Option A: New `afk/logging.py` module** - Creates a dedicated module for log-related utilities.

**Option B: Add to existing `afk/turn.py`** - Keep log naming close to Turn since they're tightly coupled.

**Recommendation: Option A (new module)**
- Log naming is a utility function, not a Turn method
- Keeps Turn as a pure data class (frozen dataclass)
- Future logging utilities (log cleanup, ANSI stripping mentioned in architecture) have a home
- Follows "one file per domain entity" - logging is a domain concern

### Implementation Pattern

```python
# afk/logging.py
from pathlib import Path


def format_log_filename(turn_number: int, transition_type: str) -> str:
    """Format log filename from turn number and transition type.

    Returns filename like: turn-003-coding.log
    """
    return f"turn-{turn_number:03d}-{transition_type}.log"


def log_path_for_turn(log_dir: Path, turn_number: int, transition_type: str) -> Path:
    """Generate absolute path for turn's log file.

    Combines log directory with formatted filename.
    """
    filename = format_log_filename(turn_number, transition_type)
    return (log_dir / filename).resolve()
```

### Zero-Padding Rationale

Using 3-digit zero-padding (`003`) because:
- Sorts correctly in file listings (turn-001, turn-002, ..., turn-010, turn-011)
- Supports up to 999 turns which exceeds any reasonable session
- Architecture mentions max turn limits (FR18) - 999 is more than sufficient
- Consistent with common logging conventions

### Log File Creation

**Important:** This story is about **naming**, not creation. The actual file creation happens in:
- `Driver.run()` already creates parent directories: `log_path.parent.mkdir(parents=True, exist_ok=True)`
- The `script` command writes to the log file during execution

This story provides the naming utilities. Story 2.4 (Turn Execution Integration) will use these functions when creating Turns.

### What NOT to Build

- **Log file cleanup/deletion** - Out of scope
- **ANSI code stripping** - Architecture mentions "clean up later if needed"
- **Log rotation** - Not a requirement
- **Session.execute_turn()** - That's Story 2.4
- **Log directory management** - Caller responsibility

### Existing Code Integration Points

The functions will be used by higher-level code (Story 2.4) like:

```python
# Future usage in session.execute_turn() (Story 2.4):
from afk.logging import log_path_for_turn

log_file = log_path_for_turn(session.log_dir, turn_number, transition_type)
result = execute_turn(driver, prompt, str(log_file))
turn = Turn(
    turn_number=turn_number,
    transition_type=transition_type,
    result=result,
    log_file=log_file,
    timestamp=datetime.now(timezone.utc),
)
```

### Turn.log_file Already Exists

From Story 2.1, the `Turn` dataclass already has:
- `log_file: Path` field
- Validation that it's a non-empty absolute path

AC #3 ("path is accessible via `turn.log_file`") is **already satisfied** by the Turn implementation. This story just needs to provide the naming utility.

### Testing Strategy

Simple unit tests with no external dependencies:

```python
# tests/test_log_naming.py
from pathlib import Path

from afk.logging import format_log_filename, log_path_for_turn


class TestFormatLogFilename:
    def test_basic_format(self):
        assert format_log_filename(1, "init") == "turn-001-init.log"
        assert format_log_filename(3, "coding") == "turn-003-coding.log"

    def test_zero_padding(self):
        assert format_log_filename(1, "coding") == "turn-001-coding.log"
        assert format_log_filename(10, "coding") == "turn-010-coding.log"
        assert format_log_filename(100, "coding") == "turn-100-coding.log"
        assert format_log_filename(999, "coding") == "turn-999-coding.log"

    def test_different_transition_types(self):
        assert format_log_filename(1, "init") == "turn-001-init.log"
        assert format_log_filename(1, "coding") == "turn-001-coding.log"


class TestLogPathForTurn:
    def test_combines_directory_and_filename(self):
        log_dir = Path("/tmp/logs")
        path = log_path_for_turn(log_dir, 3, "coding")
        assert path == Path("/tmp/logs/turn-003-coding.log")

    def test_returns_absolute_path(self):
        log_dir = Path("/tmp/logs")
        path = log_path_for_turn(log_dir, 1, "init")
        assert path.is_absolute()

    def test_resolves_path(self):
        log_dir = Path("/tmp/logs/../logs")
        path = log_path_for_turn(log_dir, 1, "init")
        assert ".." not in str(path)
```

### Project Structure After This Story

```
afk/
├── __init__.py          # Exports: ..., format_log_filename, log_path_for_turn
├── driver.py            # Driver class
├── executor.py          # execute_turn() function
├── git.py               # Git class
├── logging.py           # NEW: Log naming utilities
├── session.py           # Session class
├── turn.py              # Turn dataclass
└── turn_result.py       # TurnResult dataclass

tests/
├── test_driver.py
├── test_executor.py
├── test_git.py
├── test_log_naming.py   # NEW: Log naming tests
├── test_session.py
└── test_turn.py
```

### Previous Story Learnings

From Story 2.2 (Session Tracking):
- Domain classes should be good Python citizens (`__repr__`, etc.) - but these are simple functions, not classes
- Use hard asserts, think through invariants
- Run quality gate before marking complete
- Update `__init__.py` exports

From code review findings:
- Follow Python conventions from project_context.md
- No inline comments - put comments on line above

### Dependencies

- **None** - This is a standalone utility module
- Will be used by Story 2.4 (Turn Execution Integration)

### Epic 2 Context

This is the third story in Epic 2 (Turn Tracking & Session Management):

- **Story 2.1** (done): `Turn` data structure
- **Story 2.2** (review): `Session` class that tracks multiple turns
- **Story 2.3** (this): Log file naming by turn number and transition type
- **Story 2.4**: `execute_turn` integration that creates turns and adds to session

### Functional Requirements Covered

- **FR8**: Logs and artifacts are named by turn number and transition type
  - Implemented by `format_log_filename()` function

### Git Commit Patterns from Recent History

Recent commits follow conventional commit format:
```
8c7bea6 fix: address code review findings for Story 2.2
5d4dc42 feat: add Session class for turn tracking (Story 2.2)
f0adcab feat: add Turn dataclass for tracking prompt executions (Story 2.1)
```

Expected commit for this story:
```
feat: add log file naming utilities (Story 2.3)
```

### References

- [Source: docs/architecture.md#Cross-Cutting Concerns] - Log naming requirement
- [Source: docs/epics.md#Story 2.3] - Acceptance criteria
- [Source: docs/prd.md#FR8] - Logs and artifacts named by turn/type
- [Source: docs/project_context.md#Python Conventions] - Code style requirements
- [Source: afk/turn.py] - Turn.log_file field already exists
- [Source: afk/driver.py:47-49] - Driver.run() creates log directories
- [Source: docs/sprint-artifacts/2-2-session-tracking.md] - Previous story patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
