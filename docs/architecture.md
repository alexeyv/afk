---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - docs/prd.md
  - docs/domain-model.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2025-12-09'
project_name: 'afk'
user_name: 'Alex'
date: '2025-12-09'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Core Architectural Insight

**The framework is a state machine executor, not a loop orchestrator.**

First principles analysis revealed:
- Git is the state machine. Revision = state. Commit = transition result.
- The framework is stateless—everything it needs is in git.
- Each turn executes one prompt, produces one commit, extracts the outcome.
- Outcome determines the next state via machine definition.
- The "trivial loop" is just the simplest possible machine (init → coding → coding...).

### Execution Model

**Normal operation:**
- Machine defines states, each with a prompt and transition map (outcome → next state)
- Agent runs current state's prompt, produces exactly one commit
- Commit message follows schema with outcome signal (success, failure, or custom outcomes)
- Framework parses commit message, looks up transition, moves to next state

**Exceptions (not outcomes):**
- Zero commits — turn didn't complete
- Multiple commits — turn violated invariant
- Timeout — agent took too long
- Process died — CLI crashed
- CLI unavailable — can't execute

Exceptions halt the machine. No transition, no next state. Human intervention required.

### Design Philosophy

**Smart defaults, application-overridable.**

The framework ships with sensible opinions. Applications override when they know better:

| Concern | Default | Override |
|---------|---------|----------|
| Commits per turn | Exactly 1 | Application can expect 0, N, or "any" |
| Commit message schema | Standard success/failure | Custom outcomes, custom fields |
| Success criteria | One commit + success outcome | Custom validation logic |
| Machine definition | Trivial loop | Custom state graph |
| Timeouts, logging, etc. | Sensible values | Per-prompt or global config |

This keeps the trivial loop trivial while enabling sophisticated applications.

### Requirements Overview

**Functional Requirements:**

18 functional requirements across 6 categories:
- **Prompt Execution (FR1-5):** Core `run_prompt(prompt) → result` with real-time streaming, session logging, commit detection, and structured result return.
- **Turn Management (FR6-9):** Sequential turn numbering, transition type labeling, artifact naming by turn/type.
- **State Management (FR10-12):** Rewind to previous turn's commit, restart from rewound state with fresh context, track agent vs user commits.
- **Loop Orchestration (FR13-18):** Machine definition (states + transitions), outcome-based next-state lookup, terminal state handling, interrupt/resume, max turn limits.
- **CLI Interface (FR19-23):** Dual-mode (interactive menus + headless flags), config via flags and `.afk` file, flags override file.
- **Project Setup (FR24-26):** Clone-and-run or scaffold install, bundled Init and Coding prompts.

**Non-Functional Requirements:**

11 non-functional requirements that shape the architecture:
- **Performance (NFR1):** Framework overhead negligible vs LLM latency.
- **Integration (NFR2-4):** Graceful CLI unavailability handling, driver abstraction for CLI changes, no version pinning beyond minimum.
- **Reliability (NFR5-8):** Clean interrupt handling (no orphans), preserve logs on crash, never corrupt git state, halt cleanly on exception.
- **Maintainability (NFR9-10):** New transition < 3 files, < 1000 LOC core.
- **Replayability (NFR11):** Rewind/retry without side effects is a core workflow.

### Technical Constraints & Dependencies

- **Claude Code CLI:** External dependency. Framework wraps but doesn't control. Unavailability = exception.
- **Git:** Required in target project. All state flows through git. Framework must never corrupt repo state.
- **Python:** Implementation language.
- **Flat-rate economics:** Designed for Claude Max subscription, not metered API calls.

### Cross-Cutting Concerns

- **Process management:** Spawning CLI, streaming output, handling signals (SIGINT, SIGTERM).
- **Logging:** Every turn logged. Logs preserved even on crash. Named by turn number and transition type.
- **Git operations:** Commit detection, message parsing, rewind, state queries.
- **Configuration:** Layered (flags override file). Smart defaults throughout.
- **Exception handling:** Exceptions halt machine cleanly. No partial state. Human intervenes.

## Starter Template & Project Structure

### Starter Template Decision

**Decision:** No starter template. Project is a minimal Python CLI framework—starters add ceremony without value.

### Project Structure

```
afk/                          # Main repo
├── afk/                      # Framework module
│   ├── __init__.py
│   ├── cli.py                # Entry point
│   ├── driver.py             # Claude Code CLI wrapper
│   ├── machine.py            # Machine execution
│   ├── session.py            # Session (sequence of turns)
│   ├── turn.py               # Turn (transition + commit + log)
│   ├── transition.py         # Transition (prompt + conditions)
│   ├── prompt.py             # Prompt (content + location)
│   ├── revision.py           # Revision (repo at commit)
│   ├── commit.py             # Commit (hash + message + changes)
│   └── git.py                # Git operations
├── tests/                    # Framework tests
│   ├── test_driver.py
│   ├── test_machine.py
│   ├── test_git.py
│   └── fixtures/             # Fake CLI scripts (Python)
│       ├── cli_success.py
│       ├── cli_failure.py
│       ├── cli_no_commit.py
│       ├── cli_multi_commit.py
│       └── cli_timeout.py
├── trivial-loop/             # Experiment: trivial loop
│   ├── run.py                # Loop code (imports afk)
│   └── prompts/
│       ├── init.md
│       └── coding.md
├── pyproject.toml
└── README.md
```

**Runs live outside the repo:**
```
~/runs/                       # Separate from afk source
├── trivial-001/              # Each run is its own git repo
├── trivial-002/              # Agent works here, never sees afk/
└── ...
```

### Tooling Decisions

| Tool | Choice | Rationale |
|------|--------|-----------|
| Package format | `pyproject.toml` | Modern Python standard |
| CLI entry point | `[project.scripts]` in pyproject.toml | `pip install -e .` creates `afk` command |
| Testing | `pytest` | Simple, no boilerplate |
| Linting/Formatting | `ruff` | Fast, replaces black + isort + flake8 |
| CLI framework | TBD | `click`, `typer`, or `argparse` |

### Test Strategy

**Unit tests:** Git operations, commit parsing, outcome extraction, machine logic. No external dependencies.

**Integration tests:** Mandatory. Use fake CLI scripts (Python) that simulate agent behavior:
- Predictable output to stdout
- Controlled commit behavior (one, none, multiple)
- Configurable exit codes
- Controllable timing (for timeout tests)

The driver calls the fake CLI exactly as it would call the real one. Tests verify real behavior without mocking.

### Structure Philosophy

- Flat until it hurts. One file per domain entity, no subdirectories yet.
- Experiments live alongside framework in same repo (e.g., `trivial-loop/`)
- Each experiment has its own prompts
- Prompt templates: framework provides scaffolding (outcome signaling, commit schema), experiment provides task content
- Run workspaces live outside afk repo entirely—agents never see framework source

## Core Architectural Decisions

### No CLI

**Decision:** Library only, no CLI

afk is a Python library, not a command-line tool. Users import `afk` and write their own scripts. No click, no argparse, no interactive menus.

Rationale: CLI adds complexity without value. User code decides how to invoke the library.

### Driver Interface

**Decision:** Use `script` command to wrap Claude Code CLI

- `script` makes Claude Code think it's in a terminal (streams properly)
- Tees output to log file (observability)
- Post-commit hook kills agent on graceful completion
- Library waits for process exit, checks for commit, returns result or raises exception

**Graceful completion:** Agent commits with outcome in message → post-commit hook kills process → framework reads outcome.

**Exception:** Process exits without commit, or signal/non-zero exit. Human investigates.

### Streaming

**Decision:** `script` handles it

- Pass-through to terminal (user sees live)
- Captured to log file (via `script`)
- Log files will have ANSI escape codes and terminal control noise
- Clean up later if needed; functional for MVP

### Commit Message Schema

**Decision:** Conventional commits with outcome in footer

```
feat: implement user authentication

Added login flow with session management.
Refactored the auth module for clarity.

outcome: success
```

- Standard conventional commits format (type: subject, body)
- Footer contains `outcome: value` for machine parsing (Conventional Commits compliant)
- Framework parses footer for `outcome:` token
- Default outcomes: `success`, `failure`
- Applications can define additional outcomes

### Configuration

**Decision:** None

- No `.afk` config files, no YAML, no declarations
- Everything in Python code
- Experiment's `run.py` is the configuration
- Add config mechanism later if real need emerges

### Error/Exception Handling

**Decision:** Standard Python exception propagation

- Exceptions bubble up naturally, no catching unless adding value
- Stack trace prints to stderr (Python default)
- Process exits non-zero on uncaught exception (Python default)
- Don't swallow stack traces
- Framework raises exceptions for its failure modes (no commit, multiple commits, process died)
- Crash with full context is the right behavior for a lab tool

## Implementation Patterns & Consistency Rules

### Python Conventions

Standard Python conventions enforced by `ruff`:
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- No exception hierarchy—use `RuntimeError` with descriptive messages
- Dispatch on exception types is a code smell; just let them propagate

### Result Object

```python
@dataclass
class TurnResult:
    outcome: str           # "success", "failure", or custom outcome
    message: str           # Full commit message
    commit_hash: str       # Git SHA
```

### Test Organization

- Framework tests in `tests/` directory
- Files mirror source: `afk/driver.py` → `tests/test_driver.py`
- Standard pytest discovery
- Experiments handle their own testing—not the framework's concern

### Docstrings

- Skip unless genuinely clarifying
- Prefer clear naming over documentation
- `ruff` does not enforce docstring presence

## Project Structure & Boundaries

### Complete Project Directory Structure

```
afk/                              # Main repo
├── afk/                          # Library module
│   ├── __init__.py               # Public API: Session, TurnResult
│   ├── driver.py                 # Claude Code CLI wrapper (script, process mgmt)
│   ├── session.py                # Session with turns and git tagging
│   ├── turn.py                   # Turn execution and state
│   └── git.py                    # Git operations (commits, tags, queries)
├── tests/
│   ├── test_driver.py
│   ├── test_session.py
│   ├── test_turn.py
│   ├── test_git.py
│   └── fixtures/
│       ├── fake_claude.py        # Fake CLI: configurable behavior
│       └── prompts/              # Test prompts
├── examples/
│   ├── tracer_bullet.py          # Minimal 1-turn validation
│   └── prompts/
│       └── hello_world.md        # Simple prompt for tracer bullet
├── docs/                         # Project artifacts
├── pyproject.toml
├── README.md
└── CLAUDE.md                     # Points to docs/project-context.md
```

### Run Workspaces

Run workspaces live outside the repo entirely:

```
~/runs/
├── trivial-001/                  # Each run is its own git repo
├── trivial-002/                  # Agent works here, never sees afk/
└── ...
```

### Architectural Boundaries

| Boundary | Inside | Outside |
|----------|--------|---------|
| Framework | `afk/` module | Experiments, runs |
| Experiment | `trivial-loop/` etc. | Framework internals, other experiments |
| Run workspace | `~/runs/xxx/` | Everything else—agent never sees framework |

### Data Flow

1. Experiment's `run.py` calls `afk.run_prompt()`
2. Framework spawns Claude Code CLI via `script` in target workspace
3. CLI streams to terminal + log file
4. Agent commits with outcome in message
5. Post-commit hook kills process
6. Framework parses commit, returns `TurnResult`
7. Experiment decides next action

### Requirements to Structure Mapping

| PRD Requirement | Implementation Location |
|-----------------|------------------------|
| FR1-5: Prompt Execution | `driver.py`, `turn.py` |
| FR6-9: Session & Turn Management | `session.py`, `turn.py`, `git.py` |
| FR10: Rewind via Tags | `git.py` (user does checkout) |
| FR11-12: Project Setup | `pyproject.toml`, README, `examples/` |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All technology choices (Python, pytest, ruff) are standard, mature, and work together without conflicts.

**Pattern Consistency:** Standard Python conventions throughout. No exotic patterns or conflicting styles.

**Structure Alignment:** Flat module structure supports the "minimal library" goal. Clear boundaries between library and user code.

### Requirements Coverage Validation ✅

**Functional Requirements:**
- FR1-5 (Prompt Execution): Covered by `driver.py`, `turn.py`, `script` wrapper
- FR6-9 (Session & Turn Management): Covered by `session.py`, `turn.py`, `git.py`
- FR10 (Rewind via Tags): Covered by `git.py` tagging; user does checkout
- FR11-12 (Project Setup): Covered by `pyproject.toml`, README, `examples/`

**Non-Functional Requirements:**
- NFR1 (Performance): Library is thin wrapper, negligible overhead
- NFR2-4 (Integration): Driver abstraction isolates CLI dependency
- NFR5-7 (Reliability): Exception propagation, git never corrupted, clean crash behavior
- NFR8 (Maintainability): Target < 500 LOC, flat structure

### Implementation Readiness Validation ✅

**Decision Completeness:** All core decisions documented with rationale.

**Structure Completeness:** Every file named and mapped to requirements.

**Pattern Completeness:** Python conventions enforced by ruff. Commit schema and TurnResult defined.

### Gap Analysis Results

**Critical gap identified and addressed:** Driver never validated end-to-end. Tracer bullet epic added to MVP to close this gap.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (low, intentionally minimal)
- [x] Technical constraints identified (Claude Code CLI, git)
- [x] Cross-cutting concerns mapped (logging, git ops, process mgmt)

**✅ Architectural Decisions**
- [x] Core model defined (session executes turns, git stores state)
- [x] Technology stack specified (Python, pytest, ruff)
- [x] Driver interface designed (script wrapper, post-commit hook)
- [x] No CLI decision documented

**✅ Implementation Patterns**
- [x] Python conventions (snake_case, PascalCase for classes)
- [x] Exception handling (RuntimeError, propagate with stack trace)
- [x] Result object (TurnResult dataclass)
- [x] Commit schema (conventional commits + outcome footer)

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established (library / user code / workspace)
- [x] Data flow mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION (pending tracer bullet validation)

**Confidence Level:** Medium-High (driver untested)

**Key Strengths:**
- Simple, boring technology choices
- Git-centric state model eliminates sync complexity
- Library, not framework — user controls flow
- Minimal surface area (4 source files)

**Immediate Priority:**
- Tracer bullet to validate driver actually works
- Then demo recreation to prove end-to-end value

