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

### CLI Framework

**Decision:** `click`

Mature, widely used (since 2014), extensively documented, heavily represented in training data. Boring technology that works.

Rejected `typer` (type hints for CLI parsing don't solve a real problem—it's runtime conversion either way) and `argparse` (verbose, less ergonomic).

### Driver Interface

**Decision:** Use `script` command to wrap Claude Code CLI

- `script` makes Claude Code think it's in a terminal (streams properly)
- Tees output to log file (observability)
- Post-commit hook kills agent on graceful completion
- Framework waits for process exit, checks for commit, returns result or raises exception

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
├── afk/                          # Framework module
│   ├── __init__.py
│   ├── cli.py                    # Entry point (click)
│   ├── driver.py                 # Claude Code CLI wrapper (script, process mgmt)
│   ├── machine.py                # State machine execution logic
│   ├── session.py                # Session tracking
│   ├── turn.py                   # Turn execution
│   ├── transition.py             # Transition definitions
│   ├── prompt.py                 # Prompt loading and wrapping
│   ├── revision.py               # Git revision state
│   ├── commit.py                 # Commit parsing (conventional + outcome)
│   └── git.py                    # Git operations
├── tests/
│   ├── test_driver.py
│   ├── test_machine.py
│   ├── test_commit.py
│   ├── test_git.py
│   └── fixtures/
│       ├── cli_success.py        # Fake CLI: one commit, success
│       ├── cli_failure.py        # Fake CLI: one commit, failure
│       ├── cli_no_commit.py      # Fake CLI: exits without commit
│       ├── cli_multi_commit.py   # Fake CLI: multiple commits
│       └── cli_timeout.py        # Fake CLI: hangs
├── trivial-loop/                 # Experiment: trivial loop
│   ├── run.py                    # Loop implementation
│   └── prompts/
│       ├── init.md
│       └── coding.md
├── docs/                         # BMad artifacts
│   ├── prd.md
│   ├── domain-model.md
│   ├── architecture.md
│   ├── version-control-rules.md
│   └── project-context.md        # Generated after architecture
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
| FR1-5: Prompt Execution | `driver.py`, `prompt.py` |
| FR6-9: Turn Management | `turn.py`, `session.py` |
| FR10-12: State Management | `git.py`, `revision.py` |
| FR13-18: Loop Orchestration | `machine.py`, experiment's `run.py` |
| FR19-23: CLI Interface | `cli.py` |
| FR24-26: Project Setup | `pyproject.toml`, README |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All technology choices (Python, click, pytest, ruff) are standard, mature, and work together without conflicts.

**Pattern Consistency:** Standard Python conventions throughout. No exotic patterns or conflicting styles.

**Structure Alignment:** Flat module structure supports the "minimal framework" goal. Clear boundaries between framework, experiments, and runs.

### Requirements Coverage Validation ✅

**Functional Requirements:**
- FR1-5 (Prompt Execution): Covered by `driver.py`, `prompt.py`, `script` wrapper
- FR6-9 (Turn Management): Covered by `turn.py`, `session.py`
- FR10-12 (State Management): Covered by `git.py`, `revision.py`, runs as separate repos
- FR13-18 (Loop Orchestration): Covered by `machine.py`, experiment's `run.py`
- FR19-23 (CLI Interface): Covered by `cli.py` with click
- FR24-26 (Project Setup): Covered by `pyproject.toml`, README

**Non-Functional Requirements:**
- NFR1 (Performance): Framework is thin wrapper, negligible overhead
- NFR2-4 (Integration): Driver abstraction isolates CLI dependency
- NFR5-8 (Reliability): Exception propagation, git never corrupted, clean crash behavior
- NFR9-10 (Maintainability): Target < 1000 LOC, flat structure, one file per entity
- NFR11 (Replayability): Runs as separate git repos, rewind = git reset

### Implementation Readiness Validation ✅

**Decision Completeness:** All core decisions documented with rationale.

**Structure Completeness:** Every file named and mapped to requirements.

**Pattern Completeness:** Python conventions enforced by ruff. Commit schema and TurnResult defined.

### Gap Analysis Results

No critical or important gaps identified. Architecture covers MVP scope.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (low, intentionally minimal)
- [x] Technical constraints identified (Claude Code CLI, git)
- [x] Cross-cutting concerns mapped (logging, git ops, process mgmt)

**✅ Architectural Decisions**
- [x] Core model defined (state machine executor)
- [x] Technology stack specified (Python, click, pytest, ruff)
- [x] Driver interface designed (script wrapper, post-commit hook)
- [x] Smart defaults philosophy established

**✅ Implementation Patterns**
- [x] Python conventions (snake_case, PascalCase for classes)
- [x] Exception handling (RuntimeError, propagate with stack trace)
- [x] Result object (TurnResult dataclass)
- [x] Commit schema (conventional commits + [outcome] footer)

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established (framework / experiment / run)
- [x] Data flow mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Simple, boring technology choices
- Clear separation of concerns (framework vs experiment vs run)
- Git-centric state model eliminates sync complexity
- Smart defaults with application overrides
- Procedural code, no declarative config

**Areas for Future Enhancement:**
- Log file cleanup (strip ANSI codes)
- Config mechanism if others need it
- Additional experiments beyond trivial-loop

