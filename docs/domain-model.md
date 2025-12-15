# AFK Domain Model

Generated: 2025-12-14

This diagram shows the core entities of the AFK framework, their attributes, and relationships.

## Class Diagram

```mermaid
classDiagram
    direction TB

    class Git {
        +str repo_path
        +head_commit() str|None
        +commit_message(hash) str
        +commit_summary(hash) str
        +parse_commit_message(hash) tuple
        +root_commit() str
        +commits_between(since, until) list
    }

    class Driver {
        +Git git
        +str|None model
        +run(prompt, log_file) int
    }

    class TurnState {
        <<enumeration>>
        INITIAL
        IN_PROGRESS
        FINISHED
        ABORTED
    }

    class TurnResult {
        <<frozen dataclass>>
        +int turn_number
        +TransitionType transition_type
        +str|None outcome
        +str message
        +str commit_hash
        +Path log_file
        +datetime timestamp
        +MAX_TURN_NUMBER$ int
    }

    class TransitionType {
        <<value object>>
        -str _value
        +__str__() str
        +__repr__() str
        +__eq__() bool
        +__hash__() int
    }

    class Turn {
        <<mutable state machine>>
        -Driver _driver
        -Path _session_root
        -int|None _number
        -TurnState _state
        -TurnLog|None _turn_log
        -TransitionType|None _transition_type
        -datetime|None _timestamp
        -str|None _head_before
        +number int
        +state TurnState
        +log_file Path
        +head_before str|None
        +start(transition_type) void
        +execute(prompt) int
        +finish(outcome, commit_hash, message) TurnResult
        +abort(exception) void
        +next_turn_number(resume_from)$ int
        +reset_turn_counter()$ void
        +MAX_TURN_NUMBER$ int
    }

    class TurnLog {
        -int _turn_number
        -TransitionType _transition_type
        -Path _session_root
        +filename str
        +log_dir Path
        +path Path
        +log(message) void
        +__repr__() str
    }

    class Session {
        -Path _root_dir
        -Driver _driver
        -list~TurnResult~ _turns
        +root_dir Path
        +log_dir Path
        +turns tuple~TurnResult~
        +execute_turn(prompt, transition_type) TurnResult
        +add_turn(result)
        +turn(n) TurnResult
        +__iter__() Iterator~TurnResult~
        +__len__() int
        +__getitem__(n) TurnResult
    }

    class validate_turn_execution {
        <<function>>
        validate_turn_execution(git, exit_code, log_file, head_before) tuple
    }

    %% Composition (ownership)
    Driver *-- Git : owns
    Session *-- Driver : owns
    Turn *-- TurnLog : creates on start()
    Turn --> TurnResult : creates on finish()

    %% Association (references)
    Turn --> TurnState : has current
    Turn o-- TransitionType : has
    TurnResult o-- TransitionType : has
    TurnLog o-- TransitionType : references
    Session *-- TurnResult : stores 0..*

    %% Dependencies (uses)
    Session ..> Turn : creates & orchestrates
    Session ..> validate_turn_execution : calls
    Turn ..> Driver : invokes run()
    validate_turn_execution ..> Git : queries commits
```

## Relationship Legend

| Symbol | Meaning |
|--------|---------|
| `*--` | Composition (owns lifecycle) |
| `o--` | Association (references) |
| `..>` | Dependency (uses/calls) |
| `-->` | Creates (factory relationship) |

## Entity Descriptions

### Core Entities

| Entity | Role | Immutable |
|--------|------|-----------|
| **Git** | Repository operations - queries commits, parses messages | No |
| **Driver** | Executes prompts via Claude Code CLI with script wrapper | No |
| **TurnState** | Enum of Turn lifecycle states: INITIAL, IN_PROGRESS, FINISHED, ABORTED | Yes (enum) |
| **TurnResult** | Complete frozen record of a finished turn - all data needed for history | Yes (frozen) |
| **TransitionType** | Validated state label (e.g., "init", "coding") | Yes (value object) |
| **Turn** | Mutable state machine for active turn execution | No (state machine) |
| **TurnLog** | Manages log file paths and writes turn lifecycle events | No |
| **Session** | Orchestrates turns, owns driver and stores TurnResult history | No |

### Function

| Function | Purpose |
|----------|---------|
| **validate_turn_execution** | Post-execution validation - checks exit code, detects commits, returns result tuple |

## Turn State Machine

```
    +---------+
    | INITIAL |
    +---------+
         |
         | start(transition_type)
         | - captures HEAD
         | - creates TurnLog
         v
    +-------------+
    | IN_PROGRESS |
    +-------------+
         |
    +----+----+
    |         |
    | finish()| abort(exception)
    |         |
    v         v
+----------+ +----------+
| FINISHED | | ABORTED  |
+----------+ +----------+
     |
     +-> returns TurnResult
```

## Lifecycle Flow

```
Session.execute_turn(prompt, transition_type)
    |
    +-> Turn(driver, session_root)     // creates in INITIAL state
    |       |
    |       +-> allocates turn number
    |
    +-> turn.start(transition_type)    // INITIAL -> IN_PROGRESS
    |       |
    |       +-> captures HEAD before
    |       +-> creates TurnLog
    |       +-> logs START marker
    |
    +-> turn.execute(prompt)
    |       |
    |       +-> Driver.run()           // execute prompt
    |       +-> returns exit code
    |
    +-> validate_turn_execution(git, exit_code, log_file, head_before)
    |       |
    |       +-> checks exit code
    |       +-> Git.head_commit()      // after
    |       +-> Git.commits_between()
    |       +-> Git.parse_commit_message()
    |       +-> returns (outcome, commit_hash, message)
    |
    +-> turn.finish(outcome, commit_hash, message) // IN_PROGRESS -> FINISHED
    |       |
    |       +-> logs END marker
    |       +-> returns TurnResult
    |
    +-> Session._add_result(result)    // stores in history
```

### On Error

```
Session.execute_turn(prompt, transition_type)
    |
    +-> Turn(...), start(...), execute(...)
    |
    +-> exception raised
    |
    +-> turn.abort(exception)          // IN_PROGRESS -> ABORTED
            |
            +-> logs ABORT marker with traceback
            +-> re-raises exception
```

## Validation Summary

| Entity | Validates At |
|--------|-------------|
| **TransitionType** | Construction: pattern `^[a-z][a-z0-9_.-]*$` |
| **TurnResult** | Construction: number range 1-99999, types, absolute path, timezone-aware timestamp |
| **Turn** | Construction: Driver type, Path type, absolute path |
| **Turn.start()** | TransitionType type |
| **Turn.execute/finish/abort()** | State is IN_PROGRESS |
| **TurnLog** | Construction: number range, type, Path for session_root |
| **Session** | Construction: absolute directory path, valid Driver |
| **validate_turn_execution** | Runtime: exactly one commit, zero exit code, ancestry path |
