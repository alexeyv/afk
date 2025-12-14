# Domain Refactoring: Turn State Machine

## Problem Statement

The current domain model has an awkward representation of turns:

- **TurnLog** was originally just a path generator, but now represents the "turn in progress" (owns turn number, logs lifecycle events)
- **Turn** is a frozen dataclass that only exists after successful execution
- Failed turns leave no Turn record - only a log file with ABORT

This naming is confusing: TurnLog sounds like a logging utility but actually represents the active turn.

## Current Design

```
Session.execute_turn():
    turn_number = Turn.next_turn_number()
    turn_log = TurnLog(number, type, root)   # Creates log, writes START

    try:
        result = executor_execute_turn(...)
    except:
        turn_log.log(ABORT)                   # Log failure
        raise                                  # No Turn created

    turn_log.log(END)
    turn = Turn(frozen dataclass)             # Only on success
    session.add_turn(turn)
```

**Problems:**
1. TurnLog is doing Turn's job (representing the active turn)
2. Turn only exists for successful executions
3. Session orchestrates everything instead of Turn owning its lifecycle
4. Naming doesn't reflect responsibilities

## Proposed Design

### Turn (Mutable State Machine)

The active turn. Owns its lifecycle and logging.

**States:**
- `Initial` - just created, nothing logged
- `InProgress` - started, executing
- `Finished` - completed successfully
- `Aborted` - failed with exception

**Transitions:**
```
         ┌─────────┐
         │ Initial │
         └────┬────┘
              │ start()
              ▼
         ┌──────────┐
    ┌───►│InProgress│◄───┐
    │    └────┬─────┘    │
    │         │          │
    │  execute()    execute()
    │    (n times)       │
    │         │          │
    └─────────┴──────────┘
              │
       ┌──────┴──────┐
       │             │
  finish()        abort()
       │             │
       ▼             ▼
  ┌────────┐   ┌─────────┐
  │Finished│   │ Aborted │
  └────────┘   └─────────┘
```

**Interface:**
```python
class Turn:
    def __init__(self, driver: Driver, session_root: Path) -> None:
        # State = Initial, no logging yet

    def start(self, transition_type: TransitionType) -> None:
        # Initial -> InProgress
        # Creates TurnLog, logs START with transition_type

    def execute(self, prompt: str, description: str) -> ...:
        # Requires InProgress
        # Logs description (what we're asking driver to do)
        # Calls driver.run()
        # Returns result or raises

    def finish(self, outcome: str, commit_hash: str, message: str) -> TurnResult:
        # InProgress -> Finished
        # Logs END with outcome
        # Creates and returns frozen TurnResult

    def abort(self, exception: Exception) -> None:
        # InProgress -> Aborted
        # Logs ABORT with exception type, message, traceback
        # Re-raises the exception
```

### TurnLog (Logging Only)

Owned by Turn. Just file I/O.

```python
class TurnLog:
    def __init__(self, turn_number: int, transition_type: TransitionType, session_root: Path) -> None:
        # Creates fresh log file with START marker

    def log(self, message: str) -> None:
        # Appends message to log file

    @property
    def path(self) -> Path:
        # Returns log file path
```

### TurnResult (Frozen Record)

Created by `Turn.finish()`. Stored in Session history.

```python
@dataclass(frozen=True)
class TurnResult:
    turn_number: int
    transition_type: TransitionType
    outcome: str
    commit_hash: str
    message: str
    log_file: Path
    timestamp: datetime
```

### Session

Creates turns, stores results.

```python
class Session:
    def execute_turn(self, prompt: str, transition_type: TransitionType) -> TurnResult:
        turn = Turn(self._driver, self.root_dir)
        turn.start(transition_type)

        try:
            turn.execute(prompt, f"Turn {turn.number}: {transition_type}")
            # ... extract outcome, commit_hash, message from git ...
            result = turn.finish(outcome, commit_hash, message)
        except Exception as e:
            turn.abort(e)  # logs and re-raises

        self._history.append(result)
        return result
```

## Key Changes

| Current | Proposed |
|---------|----------|
| Turn is frozen dataclass | Turn is mutable state machine |
| Turn only exists on success | Turn exists throughout lifecycle |
| TurnLog represents active turn | TurnLog is just logging |
| Session orchestrates logging | Turn owns its lifecycle |
| No record of failed turns | TurnResult could include failures (optional) |

## Files Affected

- `afk/turn.py` - Rewrite as state machine
- `afk/turn_log.py` - Simplify to just logging (already close)
- `afk/turn_result.py` - New file, frozen dataclass (extract from current Turn)
- `afk/session.py` - Update to use new Turn API
- `afk/executor.py` - May be absorbed into Turn.execute() or simplified
- Tests for all above

## Open Questions

1. Should TurnResult include aborted turns? (Could have `outcome: "aborted"` with exception info)
2. Should Turn.execute() return something or just mutate internal state?
3. Where does git commit detection live - in Turn.execute() or Session?
4. Turn number allocation - Turn class method or Session responsibility?
