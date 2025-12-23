# AFK Domain Model

Generated: 2025-12-14
Updated: 2025-12-16 (scope change - library, not framework)

This diagram shows the core entities of the AFK library, their attributes, and relationships.

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
        +is_repo() bool
        +init() void
        +commit_empty(message) str
        +is_empty_directory() bool
        +tag_exists(name) bool
        +tag(name, commit_hash) void
    }

    class Driver {
        +Path working_dir
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
        -Git _git
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
        -str _name
        -Driver _driver
        -Git _git
        -list~TurnResult~ _turns
        -int _next_turn_number
        +root_dir Path
        +name str
        +log_dir Path
        +turns tuple~TurnResult~
        +allocate_turn_number() int
        +execute_turn(prompt, transition_type) TurnResult
        +build_turn_result(turn, exit_code) TurnResult
        +add_turn(result)
        +turn(n) TurnResult
        +__iter__() Iterator~TurnResult~
        +__len__() int
        +__getitem__(n) TurnResult
        +MAX_TURN_NUMBER$ int
    }

    %% Composition (ownership)
    Session *-- Git : owns
    Session *-- Driver : owns
    Turn *-- TurnLog : creates on start()
    Turn --> TurnResult : creates on finish()

    %% Association (references)
    Turn --> TurnState : has current
    Turn o-- TransitionType : has
    Turn o-- Git : references
    TurnResult o-- TransitionType : has
    TurnLog o-- TransitionType : references
    Session *-- TurnResult : stores 0..*

    %% Dependencies (uses)
    Session ..> Turn : creates & orchestrates
    Session ..> Git : queries commits via current_turn_result()
    Turn ..> Driver : invokes run()
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
| **Session** | Orchestrates turns, owns driver, git, and stores TurnResult history. Named sessions with git tagging for rewind support. `build_turn_result()` is an extension point for custom validation policies. | No |

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
    +-> allocate_turn_number()         // get next turn number
    |
    +-> pre-check tag afk-{name}-{N}   // fail fast if tag exists
    |
    +-> Turn(driver, git, session_root)  // creates in INITIAL state
    |
    +-> turn.start(turn_number, transition_type)  // INITIAL -> IN_PROGRESS
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
    +-> session.build_turn_result(turn, exit_code)
    |       |
    |       +-> checks exit code
    |       +-> Git.head_commit()      // after
    |       +-> Git.commits_between()
    |       +-> Git.parse_commit_message()
    |       +-> returns TurnResult
    |
    +-> Session._add_result(result)    // stores in history
    |
    +-> Git.tag(afk-{name}-{N}, commit_hash)  // tag turn boundary
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
| **Turn** | Construction: Driver type, Git type, Path type, absolute path |
| **Turn.start()** | TransitionType type |
| **Turn.execute/finish/abort()** | State is IN_PROGRESS |
| **TurnLog** | Construction: number range, type, Path for session_root |
| **Session** | Construction: absolute directory path, name (alphanumeric+underscore, max 64 chars), valid Driver, valid Git |
| **Session.build_turn_result()** | Runtime: exactly one commit, zero exit code, ancestry path |
