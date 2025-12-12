# Story 2.4: Turn Execution Integration

Status: ready-for-dev

## Story

As a framework user,
I want to execute a turn that uses the `Driver` and records results in the `Session`,
so that turn tracking is automatic during prompt execution.

## Acceptance Criteria

1. **Given** a `Session` and a prompt with transition type
   **When** I call `session.execute_turn(prompt, transition_type)`
   **Then** the `Driver` is invoked with the prompt
   **And** a `Turn` instance is created with the next turn number
   **And** the `Turn` is added to the session
   **And** the `Turn` is returned

2. **Given** a turn execution where `execute_turn()` raises (no commit, multiple commits, signal, non-zero exit)
   **When** the exception occurs
   **Then** a `Turn` instance is still created
   **And** the `Turn`'s result is None
   **And** the `Turn`'s log file is preserved
   **And** the exception propagates after recording

## Tasks / Subtasks

- [ ] Task 0: Create TransitionType value class (AC: #1, #2)
  - [ ] 0.1: Create `afk/transition_type.py` module
  - [ ] 0.2: Create `TransitionType` class with constructor validating pattern `^[a-z][a-z0-9_.-]*$`
  - [ ] 0.3: Make it a proper Python citizen: `__str__`, `__repr__`, `__eq__`, `__hash__`
  - [ ] 0.4: Update `Turn` to use `TransitionType` instead of `str`, remove `ALLOWED_TRANSITION_TYPES`
  - [ ] 0.5: Update `TurnLog` to use `TransitionType`, remove `_TRANSITION_TYPE_PATTERN`
  - [ ] 0.6: Export `TransitionType` from `afk/__init__.py`
  - [ ] 0.7: Update existing Turn and TurnLog tests
  - [ ] 0.8: Write unit tests for TransitionType (valid/invalid inputs, equality, hash)

- [ ] Task 1: Extend Session with root_dir and log_dir (AC: #1, #2)
  - [ ] 1.1: Add `root_dir: Path` parameter to `Session.__init__()`
  - [ ] 1.2: Add `log_dir` property returning `root_dir / "logs"`
  - [ ] 1.3: Store root_dir as private `_root_dir` attribute
  - [ ] 1.4: Update existing tests to pass root_dir to Session constructor

- [ ] Task 2: Add Driver injection to Session (AC: #1)
  - [ ] 2.1: Add `driver: Driver` parameter to `Session.__init__()`
  - [ ] 2.2: Store driver as private `_driver` attribute
  - [ ] 2.3: Update existing tests to pass mock/stub driver to Session constructor

- [ ] Task 3: Implement `session.execute_turn()` method (AC: #1, #2)
  - [ ] 3.1: Add `execute_turn(prompt: str, transition_type: str) -> Turn` method
  - [ ] 3.2: Compute next turn number as `len(self._turns) + 1`
  - [ ] 3.3: Create `TurnLog` instance for log file path
  - [ ] 3.4: Call `execute_turn(self._driver, prompt, str(turn_log.path))`
  - [ ] 3.5: Create `Turn` with result, log_file, timestamp
  - [ ] 3.6: Call `self.add_turn(turn)` to add to session
  - [ ] 3.7: Return the Turn

- [ ] Task 4: Handle exceptions in execute_turn (AC: #2)
  - [ ] 4.1: Wrap execution in try/except block
  - [ ] 4.2: On exception, create Turn with `result=None`
  - [ ] 4.3: Add Turn to session before re-raising
  - [ ] 4.4: Re-raise original exception after recording turn

- [ ] Task 5: Create fake CLI helpers for execute_turn tests (AC: #1, #2)
  - [ ] 5.1: Create `fake_claude_with_commit()` helper that writes a temp script making a commit with `outcome: success`
  - [ ] 5.2: Create `fake_claude_no_commit()` helper that writes a temp script exiting without commit
  - [ ] 5.3: Follow existing pattern in `test_driver.py:fake_claude()` - write temp bash scripts, return bin path for PATH injection

- [ ] Task 6: Write tests for execute_turn (AC: #1, #2)
  - [ ] 6.1: Test successful execution creates Turn with correct turn_number
  - [ ] 6.2: Test Turn has correct transition_type
  - [ ] 6.3: Test Turn has correct log_file path (follows TurnLog pattern)
  - [ ] 6.4: Test Turn is added to session
  - [ ] 6.5: Test sequential calls increment turn_number
  - [ ] 6.6: Test exception still creates Turn with result=None
  - [ ] 6.7: Test Turn is added to session even on exception
  - [ ] 6.8: Test original exception is re-raised

- [ ] Task 7: Run quality gate (all ACs)
  - [ ] 7.1: Run `uv run ruff check afk/ tests/`
  - [ ] 7.2: Run `uv run ruff format --check afk/ tests/`
  - [ ] 7.3: Run `uv run pyright --threads`
  - [ ] 7.4: Run `uv run pytest`

## Dev Notes

### TransitionType Value Class

Per `project_context.md`: "Domain classes must be good Python citizens."

TransitionType validates format once at construction using pattern `^[a-z][a-z0-9_.-]*$`. Implements:
- `__str__`: Returns the raw value
- `__repr__`: Returns `TransitionType('value')`
- `__eq__`: Value equality with other TransitionType
- `__hash__`: Hashable for use in sets/dicts

This replaces the hardcoded `ALLOWED_TRANSITION_TYPES` in Turn (which incorrectly restricted to only "init" and "coding") and `_TRANSITION_TYPE_PATTERN` in TurnLog with a single source of truth.

**IMPORTANT:** "init" and "coding" are examples, not an exhaustive list. Any lowercase identifier is valid.

### Breaking API Change: Session Constructor

Session changes from `Session()` to `Session(root_dir, driver)`. This breaks:

- `tests/test_session.py` - All existing tests use `Session()` with no args
- Any future code that constructs Session directly

**Migration:**
```python
# Before
session = Session()

# After
git = Git(repo_path)
driver = Driver(git)
session = Session(root_dir, driver)
```

For tests that don't need execute_turn, create minimal fixtures or use a test helper.

### Exception Handling Philosophy

AC #2 covers exceptions from prompt execution (no commit, multiple commits, signal termination, non-zero exit) - these record a Turn with `result=None` before re-raising.

Validation errors (invalid TransitionType, turn_number overflow, bad log_file path) are programmer errors. These propagate immediately and abort the experiment. No Turn is recorded. This is correct behavior - fail fast on bad inputs.

**Note:** `Turn.MAX_TURN_NUMBER` is 100,000. Exceeding this raises `ValueError`. In practice, no session will ever reach this limit.

### Architecture Compliance

This story implements FR6, FR7, and partially FR3 from the PRD:

> "FR6: System assigns sequential turn numbers starting from 1"
> "FR7: Each turn is labeled with its transition type (init, coding, etc.)"
> "FR3: System logs agent session to a file identified by turn number and transition type"

From `docs/architecture.md#Data Flow`:
> "1. Experiment's `run.py` calls `afk.run_prompt()`"
> "6. Framework parses commit, returns `TurnResult`"

This story bridges the gap between the existing `execute_turn()` function and the `Session` class by making execution session-aware.

### Design Decision: Session Method vs Standalone Function

**Option A: `session.execute_turn()` method** - Session owns turn creation and tracking.

**Option B: Standalone `session_execute_turn(session, driver, prompt, ...)` function**

**Recommendation: Option A (method)**
- Session already owns turn storage (`add_turn()`)
- Turn numbering is derived from session state
- Keeps session as the single coordination point
- Matches the AC: "I call `session.execute_turn()`"

### Design Decision: Driver Injection

The Session needs access to a Driver to execute prompts. Options:

**Option A: Constructor injection** - `Session(root_dir, driver)`
**Option B: Method injection** - `session.execute_turn(driver, prompt, type)`
**Option C: Global/singleton driver** - Not acceptable per project conventions

**Recommendation: Option A (constructor injection)**
- Follows `docs/project_context.md`: "Dependency injection via constructor only"
- Once constructed, dependencies don't change
- Session can execute multiple turns with same driver
- Simpler API: `session.execute_turn(prompt, type)` vs passing driver every call

### Implementation Pattern

```python
# afk/session.py - updated
from datetime import datetime, timezone
from pathlib import Path

from afk.driver import Driver
from afk.executor import execute_turn
from afk.transition_type import TransitionType
from afk.turn import Turn
from afk.turn_log import TurnLog


class Session:
    def __init__(self, root_dir: Path, driver: Driver) -> None:
        self._root_dir = root_dir
        self._driver = driver
        self._turns: list[Turn] = []

    @property
    def log_dir(self) -> Path:
        return self._root_dir / "logs"

    def execute_turn(self, prompt: str, transition_type: TransitionType) -> Turn:
        """Execute a turn and record it in the session.

        Creates the next sequential turn, executes via Driver, and adds
        to session. On exception, still records Turn with result=None
        before re-raising.
        """
        turn_number = len(self._turns) + 1
        turn_log = TurnLog(turn_number, transition_type, self.log_dir)
        timestamp = datetime.now(timezone.utc)

        try:
            result = execute_turn(self._driver, prompt, str(turn_log.path))
        except Exception:
            # Record failed turn before re-raising
            turn = Turn(
                turn_number=turn_number,
                transition_type=transition_type,
                result=None,
                log_file=turn_log.path,
                timestamp=timestamp,
            )
            self.add_turn(turn)
            raise

        turn = Turn(
            turn_number=turn_number,
            transition_type=transition_type,
            result=result,
            log_file=turn_log.path,
            timestamp=timestamp,
        )
        self.add_turn(turn)
        return turn

    # ... existing methods unchanged ...
```

### Testing Strategy

Per `project_context.md`: **No mocks.** Use fake CLI scripts to simulate Claude.

Follow the existing pattern in `test_driver.py:fake_claude()`:
1. Write a temp bash script in `tmp_path` that acts as `claude`
2. Script makes a git commit with `outcome: success` footer
3. Return the bin directory path, inject into PATH
4. Real code runs; only the external process is faked

```python
# tests/test_session.py - execute_turn tests
import os
import subprocess
from pathlib import Path

from afk.driver import Driver
from afk.git import Git
from afk.session import Session


def fake_claude_with_commit(tmp_path: Path, repo_path: Path) -> Path:
    """Create fake claude that makes a commit. Returns bin dir for PATH."""
    fake_bin = tmp_path / "fake_bin"
    fake_bin.mkdir(exist_ok=True)
    script = fake_bin / "claude"
    script.write_text(f"""#!/bin/bash
cd {repo_path}
git commit --allow-empty -m "feat: test commit

outcome: success"
""")
    script.chmod(0o755)
    return fake_bin


class TestSessionExecuteTurn:
    def test_creates_turn_with_correct_number(self, tmp_path):
        # Set up git repo
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "initial"], cwd=repo, check=True)

        # Inject fake claude into PATH
        fake_bin = fake_claude_with_commit(tmp_path, repo)
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env['PATH']}"

        git = Git(repo)
        driver = Driver(git)
        session = Session(repo, driver)

        turn = session.execute_turn("prompt", "init")

        assert turn.turn_number == 1
```

### Import Considerations

Adding `execute_turn` import to `session.py` creates a new dependency:
- `session.py` currently imports only `Turn`
- Will now also import `Driver`, `execute_turn`, `TurnLog`
- No circular dependency issues: dependency graph is acyclic

### What NOT to Build

- **Machine integration** - Story 4.3 (Machine Execution Loop) will call `session.execute_turn()`
- **Log directory creation** - Already handled by `Driver.run()` which calls `log_path.parent.mkdir()`
- **ANSI cleanup** - Architecture says "clean up later if needed"
- **Session persistence** - Not in scope for Epic 2

### Existing Code Integration Points

The new method integrates with existing code:

1. **TurnLog** (`afk/turn_log.py`): Generates log file path
2. **execute_turn** (`afk/executor.py`): Runs prompt via Driver, returns TurnResult
3. **Turn** (`afk/turn.py`): Immutable record of execution
4. **Session.add_turn()**: Existing method validates and stores turn

### Run Directory Structure

After this story, run workspaces will have:
```
~/runs/trivial-001/        # root_dir (Session constructor arg)
├── logs/                  # session.log_dir (auto-created by Driver)
│   ├── turn-00001-init.log
│   ├── turn-00002-coding.log
│   └── ...
└── ...                    # Other workspace files
```

### Previous Story Learnings

From Story 2.3 (Turn-Based Logging):
- TurnLog class handles filename generation with 5-digit zero-padding
- Transition type validation uses regex pattern `^[a-z][a-z0-9_.-]*$`
- Turn validation is strict (must be lowercase identifier)
- Log file creation is Driver's responsibility, not TurnLog's

From Story 2.2 (Session Tracking):
- Session validates turn numbers are sequential
- `add_turn()` raises ValueError for non-sequential turn numbers
- Session is iterable and supports `__getitem__`

From code review patterns:
- Constructor injection is mandatory per project_context.md
- No inline comments - put comments on line above
- All assertions are hard (no `if __debug__:`)

### Git Intelligence from Recent Commits

Recent commits show the established pattern:
```
ac0af72 feat: add TurnLog class for log file naming (Story 2.3)
5d4dc42 feat: add Session class for turn tracking (Story 2.2)
f0adcab feat: add Turn dataclass for tracking prompt executions (Story 2.1)
```

Expected commit for this story:
```
feat: add Session.execute_turn() for turn execution integration (Story 2.4)
```

### Project Structure After This Story

```
afk/
├── transition_type.py   # NEW: TransitionType value class
├── session.py           # MODIFIED: Add root_dir, driver, execute_turn()
├── turn.py              # MODIFIED: Use TransitionType instead of str
├── turn_log.py          # MODIFIED: Use TransitionType instead of str
└── __init__.py          # MODIFIED: Export TransitionType

tests/
├── test_transition_type.py  # NEW: TransitionType tests
├── test_session.py      # MODIFIED: Add execute_turn tests, update constructor calls
├── test_turn.py         # MODIFIED: Update for TransitionType
└── test_turn_log.py     # MODIFIED: Update for TransitionType
```

### Dependencies

**Inputs (must exist):**
- `afk/session.py` - Session class to extend
- `afk/executor.py` - `execute_turn()` function to call
- `afk/turn_log.py` - TurnLog for log file naming
- `afk/driver.py` - Driver class for execution
- `afk/turn.py` - Turn dataclass for recording

**Outputs (will enable):**
- Story 4.3 (Machine Execution Loop) can use `session.execute_turn()` directly
- Epic 3 (State Recovery) can access turn history with log paths

### Epic 2 Context

This is the final story in Epic 2 (Turn Tracking & Session Management):

- **Story 2.1** (done): `Turn` data structure
- **Story 2.2** (done): `Session` class that tracks multiple turns
- **Story 2.3** (done): Log file naming by turn number and transition type
- **Story 2.4** (this): `execute_turn` integration that creates turns and adds to session

Completing this story finishes Epic 2 and unblocks:
- Epic 3: State Recovery & Rewind (needs session with turns)
- Epic 4: State Machine Orchestration (needs session.execute_turn())

### Functional Requirements Covered

- **FR6**: System assigns sequential turn numbers starting from 1
  - Implemented by `execute_turn()` computing `len(self._turns) + 1`
- **FR7**: Each turn is labeled with its transition type
  - Passed through to Turn constructor
- **FR3**: System logs agent session to file identified by turn number and type
  - TurnLog generates path, Driver creates file

### References

- [Source: docs/architecture.md#Data Flow] - Execution model
- [Source: docs/epics.md#Story 2.4] - Acceptance criteria
- [Source: docs/prd.md#FR6, FR7, FR3] - Turn numbering, labeling, logging
- [Source: docs/project_context.md#Python Conventions] - Code style requirements
- [Source: docs/project_context.md#Critical Rules] - "Dependency injection via constructor only"
- [Source: afk/session.py] - Existing Session class to extend
- [Source: afk/executor.py] - execute_turn() function to integrate
- [Source: afk/turn_log.py] - TurnLog for path generation
- [Source: docs/sprint-artifacts/2-3-turn-based-logging.md] - Previous story patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
