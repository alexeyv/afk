# Story 2.2: Session Tracking

Status: review

## Story

As a framework user,
I want a `Session` class that tracks all turns in sequence,
so that I can review what happened across the entire run.

## Acceptance Criteria

1. **Given** a new `Session` is created
   **When** I add turns to it
   **Then** turn numbers are assigned sequentially starting from 1
   **And** turns are stored in order

2. **Given** a `Session` with multiple turns
   **When** I call `session.turn(n)`
   **Then** I receive the `Turn` with turn_number == n
   **And** raises KeyError if turn doesn't exist

3. **Given** a `Session` with turns
   **When** I iterate over the session
   **Then** I receive turns in chronological order

4. **Given** a `Session`
   **When** I access `session.turns`
   **Then** I receive an immutable view of all turns

## Tasks / Subtasks

- [x] Task 1: Create `Session` class in `afk/session.py` (AC: #1, #2, #3, #4)
  - [x] 1.1: Create new file `afk/session.py`
  - [x] 1.2: Create `Session` class (NOT a frozen dataclass - needs to be mutable to add turns)
  - [x] 1.3: Add private `_turns: list[Turn]` storage
  - [x] 1.4: Add `add_turn(turn: Turn) -> None` method that appends turn to list
  - [x] 1.5: Add validation in `add_turn` that turn_number matches expected next number
  - [x] 1.6: Add `turn(n: int) -> Turn` method that returns Turn by turn_number
  - [x] 1.7: Add `KeyError` raise when turn number not found
  - [x] 1.8: Add `__iter__` method for chronological iteration
  - [x] 1.9: Add `turns` property returning `tuple[Turn, ...]` (immutable view)

- [x] Task 2: Write unit tests for `Session` (AC: #1, #2, #3, #4)
  - [x] 2.1: Create `tests/test_session.py`
  - [x] 2.2: Test `Session` can be instantiated empty
  - [x] 2.3: Test `add_turn` adds turn to session
  - [x] 2.4: Test turns are stored in order of addition
  - [x] 2.5: Test `turn(n)` returns correct turn by turn_number
  - [x] 2.6: Test `turn(n)` raises KeyError for non-existent turn
  - [x] 2.7: Test iteration yields turns in chronological order
  - [x] 2.8: Test `turns` property returns tuple (immutable)
  - [x] 2.9: Test validation rejects turn with wrong turn_number

- [x] Task 3: Export `Session` from package (AC: all)
  - [x] 3.1: Add `Session` to `afk/__init__.py` exports

- [x] Task 4: Run quality gate (all ACs)
  - [x] 4.1: Run `uv run ruff check afk/ tests/`
  - [x] 4.2: Run `uv run ruff format --check afk/ tests/`
  - [x] 4.3: Run `uv run pyright --threads`
  - [x] 4.4: Run `uv run pytest`

## Dev Notes

### Architecture Compliance

This story introduces the `Session` class per the architecture document:

From `docs/architecture.md#Project Structure`:
```
afk/
├── session.py            # Session tracking
```

From `docs/architecture.md#Requirements to Structure Mapping`:
```
FR6-9: Turn Management → turn.py, session.py
```

### Design Decision: Mutable Class vs Frozen Dataclass

Unlike `Turn` and `TurnResult` which are immutable frozen dataclasses, `Session` must be mutable because:
- Turns are added during execution, one at a time
- The session grows as the machine runs
- A frozen dataclass would require creating a new Session for each turn added

Use a regular class with a private `_turns` list and expose an immutable view via the `turns` property.

### Implementation Pattern

```python
from afk.turn import Turn


class Session:
    def __init__(self) -> None:
        self._turns: list[Turn] = []

    def add_turn(self, turn: Turn) -> None:
        expected = len(self._turns) + 1
        if turn.turn_number != expected:
            raise ValueError(
                f"Expected turn number {expected}, got {turn.turn_number}"
            )
        self._turns.append(turn)

    def turn(self, n: int) -> Turn:
        for t in self._turns:
            if t.turn_number == n:
                return t
        raise KeyError(f"No turn with number {n}")

    def __iter__(self):
        return iter(self._turns)

    @property
    def turns(self) -> tuple[Turn, ...]:
        return tuple(self._turns)
```

### Turn Number Validation

The `add_turn` method validates that turns are added in sequence:
- First turn must have `turn_number == 1`
- Second turn must have `turn_number == 2`
- And so on...

This enforces FR6: "System assigns sequential turn numbers starting from 1"

If a turn with wrong number is added, raise `ValueError` with clear message.

### Immutable View via `turns` Property

The `turns` property returns a `tuple[Turn, ...]` which is immutable:
- Caller cannot modify the session's internal list
- Caller cannot append, remove, or reorder turns
- Matches the AC: "immutable view of all turns"

### KeyError for Missing Turns

When `turn(n)` is called with a non-existent turn number:
- Raise `KeyError` (standard Python for "key not found")
- Message should include the turn number that wasn't found
- Matches AC: "raises KeyError if turn doesn't exist"

### What NOT to Build

This story is specifically about the `Session` **container**. The following are OUT OF SCOPE:

- **Log file naming** - Story 2.3
- **Turn execution** - Story 2.4 (`session.execute_turn()`)
- **Rewind functionality** - Epic 3 (Story 3.2)
- **Agent vs user commit tracking** - Epic 3 (Story 3.1)
- **Persistence** - Sessions are in-memory only for MVP

The `Session` class is a simple container that holds `Turn` instances. It doesn't know how to execute turns or create them - that's Story 2.4's responsibility.

### Testing Strategy

Simple unit tests using the `Turn` class from Story 2.1:

```python
from datetime import datetime, timezone

import pytest

from afk.session import Session
from afk.turn import Turn
from afk.turn_result import TurnResult


def make_turn(n: int, transition_type: str = "coding") -> Turn:
    """Helper to create Turn instances for testing."""
    return Turn(
        turn_number=n,
        transition_type=transition_type,
        result=TurnResult(outcome="success", message="test", commit_hash="abc123"),
        log_file=f"/logs/turn-{n:03d}.log",
        timestamp=datetime.now(timezone.utc),
    )


class TestSession:
    def test_empty_session(self):
        session = Session()
        assert session.turns == ()
        assert list(session) == []

    def test_add_single_turn(self):
        session = Session()
        turn = make_turn(1, "init")
        session.add_turn(turn)
        assert session.turns == (turn,)

    def test_add_multiple_turns_in_order(self):
        session = Session()
        t1 = make_turn(1, "init")
        t2 = make_turn(2, "coding")
        t3 = make_turn(3, "coding")
        session.add_turn(t1)
        session.add_turn(t2)
        session.add_turn(t3)
        assert session.turns == (t1, t2, t3)

    def test_turn_lookup_by_number(self):
        session = Session()
        t1 = make_turn(1)
        t2 = make_turn(2)
        session.add_turn(t1)
        session.add_turn(t2)
        assert session.turn(1) is t1
        assert session.turn(2) is t2

    def test_turn_lookup_raises_keyerror(self):
        session = Session()
        session.add_turn(make_turn(1))
        with pytest.raises(KeyError):
            session.turn(99)

    def test_iteration_chronological_order(self):
        session = Session()
        turns = [make_turn(i) for i in range(1, 4)]
        for t in turns:
            session.add_turn(t)
        assert list(session) == turns

    def test_turns_property_is_immutable(self):
        session = Session()
        session.add_turn(make_turn(1))
        turns = session.turns
        assert isinstance(turns, tuple)

    def test_add_turn_validates_sequence(self):
        session = Session()
        with pytest.raises(ValueError, match="Expected turn number 1"):
            session.add_turn(make_turn(2))  # Should start at 1

    def test_add_turn_validates_next_number(self):
        session = Session()
        session.add_turn(make_turn(1))
        with pytest.raises(ValueError, match="Expected turn number 2"):
            session.add_turn(make_turn(5))  # Should be 2
```

### Project Structure After This Story

```
afk/
├── __init__.py          # Exports: Driver, Git, TurnResult, execute_turn, Turn, Session
├── driver.py            # Driver class
├── executor.py          # execute_turn() function
├── git.py               # Git class
├── session.py           # NEW: Session class
├── turn.py              # Turn dataclass
└── turn_result.py       # TurnResult dataclass

tests/
├── test_driver.py
├── test_executor.py
├── test_git.py
├── test_session.py      # NEW: Session tests
└── test_turn.py
```

### Previous Story Learnings

From Story 2.1 (Turn Data Structure):
- Follow existing patterns in the codebase
- Keep tests focused on actual behavior
- Run quality gate (ruff, pyright, pytest) before marking complete
- Update `__init__.py` exports

### Dependencies

- **Turn** from Story 2.1 - the `Session` stores `Turn` instances
- **TurnResult** from Story 1.3 - needed for creating test Turn instances
- No other dependencies

### Epic 2 Context

This is the second story in Epic 2 (Turn Tracking & Session Management):

- **Story 2.1** (done): `Turn` data structure
- **Story 2.2** (this): `Session` class that tracks multiple turns
- **Story 2.3**: Log file naming by turn number and transition type
- **Story 2.4**: `execute_turn` integration that creates turns and adds to session

### Functional Requirements Covered

- **FR6**: System assigns sequential turn numbers starting from 1
  - Enforced by `add_turn` validation
- **FR9**: User can reference a specific turn by number for operations
  - Implemented by `turn(n)` method

### References

- [Source: docs/architecture.md#Project Structure] - `session.py` file location
- [Source: docs/architecture.md#Requirements to Structure Mapping] - FR6-9 mapping
- [Source: docs/epics.md#Story 2.2] - Acceptance criteria
- [Source: docs/prd.md#FR6] - Sequential turn numbers
- [Source: docs/prd.md#FR9] - Reference turns by number
- [Source: afk/turn.py] - Turn class to store
- [Source: docs/sprint-artifacts/2-1-turn-data-structure.md] - Previous story patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - no debug issues encountered

### Completion Notes List

- ✅ Implemented `Session` class as mutable container for `Turn` instances
- ✅ `add_turn()` validates sequential turn numbers (starting from 1)
- ✅ `turn(n)` returns Turn by number or raises `KeyError`
- ✅ `__iter__` provides chronological iteration
- ✅ `turns` property returns immutable `tuple[Turn, ...]`
- ✅ All 9 unit tests pass covering all 4 acceptance criteria
- ✅ Full test suite: 88 passed, 3 skipped
- ✅ Quality gate: ruff check, ruff format, pyright all pass

### File List

**New Files:**
- `afk/session.py` - Session class implementation
- `tests/test_session.py` - Unit tests for Session (9 tests)

**Modified Files:**
- `afk/__init__.py` - Added Session to exports
- `docs/sprint-artifacts/sprint-status.yaml` - Status updates
- `docs/sprint-artifacts/2-2-session-tracking.md` - Story completion
