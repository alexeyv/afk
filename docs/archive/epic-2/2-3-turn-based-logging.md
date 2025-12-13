# Story 2.3: Turn-Based Logging

Status: done

## Story

As a framework user,
I want log files named by turn number and transition type,
so that I can easily find logs for specific turns.

## Acceptance Criteria

1. **Given** turn number 3 with transition type "coding"
   **When** generating the log file name
   **Then** the name follows pattern `turn-003-coding.log`

2. **Given** different turn numbers or transition types
   **When** generating log file names
   **Then** each unique (turn_number, transition_type) combination produces a unique filename

## Tasks / Subtasks

- [x] Task 1: Create TurnLog class (AC: #1, #2)
  - [x] 1.1: Create `afk/turn_log.py` module
  - [x] 1.2: Create `TurnLog` class with constructor `(turn_number, transition_type, log_dir)`
  - [x] 1.3: Add `filename` property returning `turn-{NNN}-{type}.log` pattern
  - [x] 1.4: Add `path` property returning absolute Path

- [x] Task 2: Write unit tests for TurnLog (AC: #1, #2)
  - [x] 2.1: Create `tests/test_turn_log.py`
  - [x] 2.2: Test `filename` property returns correct pattern
  - [x] 2.3: Test zero-padding works correctly (1 -> "001", 10 -> "010", 100 -> "100")
  - [x] 2.4: Test `path` property combines directory and filename correctly
  - [x] 2.5: Test `path` is absolute
  - [x] 2.6: Test different transition types produce different filenames

- [x] Task 3: Export TurnLog from package (AC: all)
  - [x] 3.1: Add `TurnLog` to `afk/__init__.py`

- [x] Task 4: Run quality gate (all ACs)
  - [x] 4.1: Run `uv run ruff check afk/ tests/`
  - [x] 4.2: Run `uv run ruff format --check afk/ tests/`
  - [x] 4.3: Run `uv run pyright --threads`
  - [x] 4.4: Run `uv run pytest`

## Dev Notes

### Architecture Compliance

This story implements FR8 from the PRD:
> "FR8: Logs and artifacts are named by turn number and transition type"

From `docs/architecture.md#Cross-Cutting Concerns`:
> "Logging: Every turn logged. Logs preserved even on crash. Named by turn number and transition type."

From `docs/architecture.md#Project Structure`:
> "Flat until it hurts. One file per domain entity."

### Design Decision: Class vs Functions

**Option A: `TurnLog` class** - One instance per turn, properties for filename/path.

**Option B: Pure functions** - `format_log_filename()` and `log_path_for_turn()` as standalone functions.

**Recommendation: Option A (class)**
- One instance per turn mirrors domain model
- Properties (`filename`, `path`) are natural for an object
- Keeps Turn as a pure data class (frozen dataclass)
- Future turn log utilities (ANSI stripping, cleanup) can be methods
- Leaves room for other log classes (e.g., MachineLog) later
- No static methods: need a path? Create a TurnLog instance

### Implementation Pattern

```python
# afk/turn_log.py
from pathlib import Path


class TurnLog:
    def __init__(self, turn_number: int, transition_type: str, log_dir: Path) -> None:
        self._turn_number = turn_number
        self._transition_type = transition_type
        self._log_dir = log_dir

    @property
    def filename(self) -> str:
        return f"turn-{self._turn_number:03d}-{self._transition_type}.log"

    @property
    def path(self) -> Path:
        return (self._log_dir / self.filename).absolute()

    def __repr__(self) -> str:
        return f"TurnLog({self._turn_number}, {self._transition_type!r}, {self._log_dir})"
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

The class will be used by higher-level code (Story 2.4) like:

```python
# Future usage in session.execute_turn() (Story 2.4):
from afk.turn_log import TurnLog

turn_log = TurnLog(turn_number, transition_type, session.log_dir)
result = execute_turn(driver, prompt, str(turn_log.path))
turn = Turn(
    turn_number=turn_number,
    transition_type=transition_type,
    result=result,
    log_file=turn_log.path,
    timestamp=datetime.now(timezone.utc),
)
```

### Where log_dir Comes From

**Prerequisite for Story 2.4:** Session needs `root_dir` in constructor and `log_dir` as read-only property.

```python
class Session:
    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._turns: list[Turn] = []

    @property
    def log_dir(self) -> Path:
        return self._root_dir / "logs"
```

Run directory structure:
```
~/runs/trivial-001/        # root_dir (Session constructor arg)
├── logs/                  # session.log_dir
│   ├── turn-001-init.log
│   ├── turn-002-coding.log
│   └── ...
└── ...
```

This change to Session is **not part of Story 2.3** - it should be added in Story 2.4 when `execute_turn` integration is built.

### Testing Strategy

Simple unit tests with no external dependencies:

```python
# tests/test_turn_log.py
from afk.turn_log import TurnLog


class TestTurnLogFilename:
    def test_basic_format(self, tmp_path):
        log = TurnLog(1, "init", tmp_path)
        assert log.filename == "turn-001-init.log"

    def test_zero_padding(self, tmp_path):
        assert TurnLog(1, "coding", tmp_path).filename == "turn-001-coding.log"
        assert TurnLog(10, "coding", tmp_path).filename == "turn-010-coding.log"
        assert TurnLog(100, "coding", tmp_path).filename == "turn-100-coding.log"
        assert TurnLog(999, "coding", tmp_path).filename == "turn-999-coding.log"

    def test_different_transition_types(self, tmp_path):
        assert TurnLog(1, "init", tmp_path).filename == "turn-001-init.log"
        assert TurnLog(1, "coding", tmp_path).filename == "turn-001-coding.log"


class TestTurnLogPath:
    def test_combines_directory_and_filename(self, tmp_path):
        log = TurnLog(3, "coding", tmp_path)
        assert log.path == tmp_path / "turn-003-coding.log"

    def test_returns_absolute_path(self, tmp_path):
        log = TurnLog(1, "init", tmp_path)
        assert log.path.is_absolute()
```

### Project Structure After This Story

```
afk/
├── __init__.py          # Exports: ..., TurnLog
├── driver.py            # Driver class
├── executor.py          # execute_turn() function
├── git.py               # Git class
├── turn_log.py          # NEW: TurnLog class
├── session.py           # Session class
├── turn.py              # Turn dataclass
└── turn_result.py       # TurnResult dataclass

tests/
├── test_driver.py
├── test_executor.py
├── test_git.py
├── test_turn_log.py     # NEW: TurnLog tests
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
- Follow Python conventions from project-context.md
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
  - Implemented by `TurnLog` class

### Git Commit Patterns from Recent History

Recent commits follow conventional commit format:
```
8c7bea6 fix: address code review findings for Story 2.2
5d4dc42 feat: add Session class for turn tracking (Story 2.2)
f0adcab feat: add Turn dataclass for tracking prompt executions (Story 2.1)
```

Expected commit for this story:
```
feat: add TurnLog class for log file naming (Story 2.3)
```

### References

- [Source: docs/architecture.md#Cross-Cutting Concerns] - Log naming requirement
- [Source: docs/epics.md#Story 2.3] - Acceptance criteria
- [Source: docs/prd.md#FR8] - Logs and artifacts named by turn/type
- [Source: docs/project-context.md#Python Conventions] - Code style requirements
- [Source: afk/turn.py] - Turn.log_file field already exists
- [Source: afk/driver.py:47-49] - Driver.run() creates log directories
- [Source: docs/sprint-artifacts/2-2-session-tracking.md] - Previous story patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Implementation straightforward, no debugging required.

### Completion Notes List

- Implemented `TurnLog` class following the design pattern from Dev Notes (Option A: class approach)
- Class provides `filename` property returning `turn-{NNN}-{type}.log` pattern with 3-digit zero-padding
- Class provides `path` property returning absolute Path by combining `log_dir` and `filename`
- Added `__repr__` for debugging/logging
- 11 unit tests covering all ACs:
  - AC #1: Basic format test (`turn-003-coding.log`)
  - AC #2: Different turn numbers and transition types produce unique filenames
  - Zero-padding edge cases (1, 10, 100, 999)
  - Path combination and absoluteness
- Exported `TurnLog` from `afk/__init__.py`
- All quality gates passed: ruff check, ruff format, pyright (0 errors), pytest (101 passed)

### File List

- `afk/turn_log.py` (NEW) - TurnLog class implementation
- `afk/__init__.py` (MODIFIED) - Added TurnLog export
- `tests/test_turn_log.py` (NEW) - Unit tests for TurnLog
- `docs/sprint-artifacts/sprint-status.yaml` (MODIFIED) - Status: in-progress → review
- `docs/sprint-artifacts/2-3-turn-based-logging.md` (MODIFIED) - Tasks marked complete, status updated
- `docs/sprint-artifacts/2-2-session-tracking.md` (MODIFIED) - Status: review → done

### Change Log

- 2025-12-12: Story 2.3 implemented - TurnLog class for turn-based log file naming (AC #1, #2 satisfied)
