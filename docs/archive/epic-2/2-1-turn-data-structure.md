# Story 2.1: Turn Data Structure

Status: done

## Story

As a framework developer,
I want a `Turn` class that captures all information about a single prompt execution,
so that I can track and reference individual turns in a session.

## Acceptance Criteria

1. **Given** a prompt execution completes
   **When** I create a `Turn` instance
   **Then** it contains turn_number (int, starting from 1)
   **And** it contains transition_type (string, e.g., "init", "coding")
   **And** it contains result (TurnResult or None if exception)
   **And** it contains log_file path
   **And** it contains timestamp of execution

2. **Given** a `Turn` instance exists
   **When** I access its properties
   **Then** all fields are immutable (dataclass frozen=True)

## Tasks / Subtasks

- [x] Task 1: Create `Turn` dataclass in `afk/turn.py` (AC: #1, #2)
  - [x] 1.1: Create new file `afk/turn.py`
  - [x] 1.2: Define `Turn` dataclass with `frozen=True`
  - [x] 1.3: Add field `turn_number: int`
  - [x] 1.4: Add field `transition_type: str`
  - [x] 1.5: Add field `result: TurnResult | None`
  - [x] 1.6: Add field `log_file: str`
  - [x] 1.7: Add field `timestamp: datetime` (from `datetime.datetime`)

- [x] Task 2: Write unit tests for `Turn` (AC: #1, #2)
  - [x] 2.1: Create `tests/test_turn.py`
  - [x] 2.2: Test `Turn` can be instantiated with all required fields
  - [x] 2.3: Test `Turn` fields are accessible as properties
  - [x] 2.4: Test `Turn` is immutable (frozen) - attempting to modify raises FrozenInstanceError
  - [x] 2.5: Test `Turn` accepts `result=None` for exception cases
  - [x] 2.6: Test `Turn` with various transition_type values ("init", "coding", etc.)

- [x] Task 3: Export `Turn` from package (AC: #1)
  - [x] 3.1: Add `Turn` to `afk/__init__.py` exports

- [x] Task 4: Run quality gate (all ACs)
  - [x] 4.1: Run `uv run ruff check afk/ tests/`
  - [x] 4.2: Run `uv run ruff format --check afk/ tests/`
  - [x] 4.3: Run `uv run pyright --threads`
  - [x] 4.4: Run `uv run pytest`

## Dev Notes

### Architecture Compliance

This story introduces the `Turn` class per the architecture document:

From `docs/architecture.md#Project Structure`:
```
afk/
├── turn.py               # Turn (transition + commit + log)
```

From `docs/architecture.md#Implementation Patterns`:
- Use `@dataclass(frozen=True)` for immutability (matches `TurnResult` pattern)
- Standard Python naming: `snake_case` for fields
- No docstrings unless genuinely clarifying

### Existing Pattern to Follow

The `TurnResult` dataclass in `afk/turn_result.py` establishes the pattern:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnResult:
    outcome: str | None
    message: str
    commit_hash: str
```

Follow this same pattern for `Turn`:
- Frozen dataclass
- Simple type annotations
- No default values (all fields required)
- No methods initially

### Turn Field Details

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `turn_number` | `int` | Sequential number starting from 1 | FR6: "System assigns sequential turn numbers starting from 1" |
| `transition_type` | `str` | Label like "init", "coding" | FR7: "Each turn is labeled with its transition type" |
| `result` | `TurnResult \| None` | Execution result, None if exception | Architecture: "Result (TurnResult or None if exception)" |
| `log_file` | `str` | Path to turn's log file | FR3, FR8: "Logs and artifacts are named by turn number" |
| `timestamp` | `datetime` | When the turn executed | Epics Story 2.1: "timestamp of execution" |

### What NOT to Build

This story is specifically about the `Turn` **data structure**. The following are OUT OF SCOPE:

- **Session class** - Story 2.2
- **Log file naming** - Story 2.3
- **Turn execution** - Story 2.4
- **Factory functions** to create Turn from execution
- **Any file I/O or git operations**

The `Turn` class is a simple container. It doesn't know how to create itself from execution results - that's Story 2.4's responsibility.

### Timestamp Implementation

Use `datetime.datetime` from the standard library:

```python
from dataclasses import dataclass
from datetime import datetime

from afk.turn_result import TurnResult


@dataclass(frozen=True)
class Turn:
    turn_number: int
    transition_type: str
    result: TurnResult | None
    log_file: str
    timestamp: datetime
```

The caller (Story 2.4) will provide the timestamp, typically using `datetime.now()` or `datetime.now(timezone.utc)`.

### Testing Strategy

Simple unit tests - no mocks or fixtures needed:

```python
from datetime import datetime, timezone

import pytest

from afk.turn import Turn
from afk.turn_result import TurnResult


class TestTurn:
    def test_turn_with_successful_result(self):
        result = TurnResult(outcome="success", message="feat: add foo", commit_hash="abc123")
        turn = Turn(
            turn_number=1,
            transition_type="init",
            result=result,
            log_file="/path/to/log.txt",
            timestamp=datetime.now(timezone.utc),
        )

        assert turn.turn_number == 1
        assert turn.transition_type == "init"
        assert turn.result is result
        assert turn.log_file == "/path/to/log.txt"
        assert isinstance(turn.timestamp, datetime)

    def test_turn_with_none_result(self):
        turn = Turn(
            turn_number=2,
            transition_type="coding",
            result=None,
            log_file="/path/to/log.txt",
            timestamp=datetime.now(timezone.utc),
        )

        assert turn.result is None

    def test_turn_is_immutable(self):
        turn = Turn(
            turn_number=1,
            transition_type="init",
            result=None,
            log_file="/path/to/log.txt",
            timestamp=datetime.now(timezone.utc),
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            turn.turn_number = 2
```

### Project Structure After This Story

```
afk/
├── __init__.py          # Exports: Driver, Git, TurnResult, execute_turn, Turn
├── driver.py            # Driver class
├── executor.py          # execute_turn() function
├── git.py               # Git class
├── turn.py              # NEW: Turn dataclass
└── turn_result.py       # TurnResult dataclass

tests/
├── test_driver.py
├── test_executor.py
├── test_git.py
└── test_turn.py         # NEW: Turn tests
```

### Previous Story Learnings

From Story 1.4 (just completed):
- Follow the existing dataclass pattern from `TurnResult`
- Keep tests straightforward - test the actual behavior, not implementation details
- Run quality gate before marking complete
- Update `__init__.py` exports

### Dependencies

- **TurnResult** from Story 1.3 - used as type for `result` field
- No other dependencies

### Epic 2 Context

This is the first story in Epic 2 (Turn Tracking & Session Management). The `Turn` class is the foundation that other stories build on:

- **Story 2.1** (this): Define the data structure
- **Story 2.2**: `Session` class that tracks multiple `Turn` instances
- **Story 2.3**: Log file naming by turn number and transition type
- **Story 2.4**: `execute_turn` integration that creates `Turn` instances

### References

- [Source: docs/architecture.md#Project Structure] - `turn.py` file location
- [Source: docs/architecture.md#Implementation Patterns] - Frozen dataclass pattern
- [Source: docs/epics.md#Story 2.1] - Acceptance criteria
- [Source: docs/prd.md#FR6] - Sequential turn numbers
- [Source: docs/prd.md#FR7] - Transition type labeling
- [Source: docs/prd.md#FR8] - Artifact naming
- [Source: afk/turn_result.py] - Existing dataclass pattern to follow
- [Source: docs/project-context.md] - Quality gate requirements

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Created `Turn` frozen dataclass following the established `TurnResult` pattern
- Implemented 5 unit tests covering: successful result, None result, immutability, various transition types, and field accessibility
- Added `Turn` to package exports in `afk/__init__.py`
- All quality gates passed: ruff check, ruff format, pyright (0 errors), pytest (74 passed, 3 skipped)

### Change Log

- 2025-12-11: Implemented Turn data structure per Story 2.1 acceptance criteria
- 2025-12-11: Code review fixed pyright error in test_turn.py (added type narrowing for Optional access)

### File List

- afk/turn.py (new)
- afk/__init__.py (modified)
- tests/test_turn.py (new, modified by review)
