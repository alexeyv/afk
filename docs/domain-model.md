# AFK Domain Model

Generated: 2025-12-13

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

    class TurnResult {
        <<frozen dataclass>>
        +str|None outcome
        +str message
        +str commit_hash
    }

    class TransitionType {
        <<value object>>
        -str _value
        +__str__() str
        +__eq__()
        +__hash__()
    }

    class Turn {
        <<frozen dataclass>>
        +int turn_number
        +TransitionType transition_type
        +TurnResult result
        +Path log_file
        +datetime timestamp
        +next_turn_number()$ int
        +reset_turn_counter()$
    }

    class TurnLog {
        -int _turn_number
        -TransitionType _transition_type
        -Path _log_dir
        +filename str
        +path Path
    }

    class Session {
        -Path _root_dir
        -Driver _driver
        -list~Turn~ _turns
        +root_dir Path
        +log_dir Path
        +execute_turn(prompt, type) Turn
        +add_turn(turn)
        +turn(n) Turn
        +turns tuple
    }

    class execute_turn {
        <<function>>
        execute_turn(driver, prompt, log_file) TurnResult
    }

    %% Composition (ownership)
    Driver *-- Git : owns
    Session *-- Driver : owns
    Session *-- Turn : owns 0..*
    Turn *-- TurnResult : contains

    %% Association (references)
    Turn o-- TransitionType : has
    TurnLog o-- TransitionType : references

    %% Dependencies (uses)
    Session ..> TurnLog : uses for paths
    Session ..> execute_turn : calls
    execute_turn ..> Driver : invokes run()
    execute_turn ..> Git : queries commits
    execute_turn ..> TurnResult : returns
```

## Relationship Legend

| Symbol | Meaning |
|--------|---------|
| `*--` | Composition (owns lifecycle) |
| `o--` | Association (references) |
| `..>` | Dependency (uses/calls) |

## Entity Descriptions

### Core Entities

| Entity | Role | Immutable |
|--------|------|-----------|
| **Git** | Repository operations - queries commits, parses messages | No |
| **Driver** | Executes prompts via Claude Code CLI with script wrapper | No |
| **TurnResult** | Outcome of a single turn - outcome, message, commit hash | Yes (frozen) |
| **TransitionType** | Validated state label (e.g., "init", "coding") | Yes (value object) |
| **Turn** | Complete record of one execution - number, type, result, log | Yes (frozen) |
| **TurnLog** | Generates log file paths from turn number and type | No |
| **Session** | Orchestrates turns, owns driver and turn history | No |

### Function

| Function | Purpose |
|----------|---------|
| **execute_turn** | Core execution logic - runs driver, detects commits, returns result |

## Lifecycle Flow

```
Session.execute_turn(prompt, type)
    │
    ├─► TurnLog(number, type, log_dir)  // determine log path
    │
    ├─► execute_turn(driver, prompt, log_file)
    │       │
    │       ├─► Git.head_commit()  // before
    │       ├─► Driver.run()       // execute
    │       ├─► Git.commits_between()
    │       ├─► Git.parse_commit_message()
    │       └─► return TurnResult
    │
    └─► Turn(number, type, result, log, timestamp)
            │
            └─► added to Session._turns
```
