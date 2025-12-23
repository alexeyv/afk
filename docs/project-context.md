# Project Context - afk

**Project:** afk - Python framework for autonomous coding agent loops
**Date:** 2025-12-09

This file contains critical rules and patterns for AI agents implementing this codebase.

## Core Concept

afk is a **Python library for autonomous coding turns**. The library executes prompts via Claude Code CLI and returns results. Loop logic, state machines, orchestration—that's user code, not library concern.

- Git is the database. Commit = turn result. Tags = turn boundaries.
- The library is stateless—everything it needs is in git.
- Each turn executes one prompt, produces one commit, extracts the outcome.
- Sessions have names. Turns are tagged: `afk-{session}-{turn_number}`.
- Rewind = checkout a tag, branch, start new session. Standard git workflow.
- Runs live in separate git repos outside the afk codebase.

## Technology Stack

- **Language:** Python 3.x
- **System:** git (must be on PATH)
- **CLI Framework:** click
- **Testing:** pytest
- **Linting/Formatting:** ruff
- **Type Checking:** pyright (strict mode)
- **Package Format:** pyproject.toml

## Critical Rules

### Version Control

**Note:** Dev agent ignores non-coding-style rules from this file. Git/commit rules live in:
- `_bmad/_cfg/agents/bmm-dev.customize.yaml` — commit per task
- `_bmad/_cfg/agents/bmm-sm.customize.yaml` — commit per workflow

### Commit Message Schema

Conventional commits with outcome in footer:

```
feat: implement feature X

Description of changes.

outcome: success
```

- Footer contains `outcome: value` for machine parsing (Conventional Commits compliant)
- Default outcomes: `success`, `failure`
- Applications can define additional outcomes

### Python Conventions

- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- **Class method ordering:** (1) class attributes, (2) `__init__`, (3) other dunders (`__repr__`, `__iter__`, etc.), (4) `@classmethod`s, (5) `@staticmethod`s, (6) `@property` methods, (7) public methods, (8) private methods (`_underscore`)
- No circular dependencies—fix the design, don't work around with `TYPE_CHECKING` hacks
- No exception hierarchy—use `RuntimeError` for explicit errors
- Never wrap library exceptions—let them propagate with full stack trace
- Never dispatch on error type (no `except SomeError`)—catch-all or let it crash
- Skip docstrings unless genuinely clarifying
- No inline comments—put comments on the line above
- **No assert statements.** Use explicit runtime checks. `python -O` removes asserts.
- **Think through invariants.** When designing classes, identify what must always be true and make violations impossible or check them explicitly.
- **Domain classes validate at boundaries.** Strict runtime type and value validation on all inputs to mutating methods (including constructors). Enforce class invariants at the end of every mutating method. Static type checking (pyright) doesn't run at runtime—domain classes must protect themselves.
- **Dependency injection via constructor only.** No setter injection. Once constructed, dependencies don't change.
- **Never iterate through live mutable collections.** Return a snapshot (tuple/copy) to prevent mid-iteration surprises.
- **Domain classes must be good Python citizens.** Implement `__repr__` (always), plus `__iter__`, `__len__`, `__getitem__`, `__contains__` where semantically meaningful.
- **All classes use `__slots__`.** Saves memory, catches typos, signals fixed structure.
- **LLM output vs Python output.** LLM-generated values: treat as human input, be lenient. Python-generated values: validate at creation, throw if invalid.

### Project Structure

```
afk/                          # Library module
├── __init__.py               # Public API: Session, TurnResult
├── driver.py                 # Claude Code CLI wrapper
├── session.py                # Session with turns and tagging
├── turn.py                   # Turn execution
└── git.py                    # Git operations

tests/                        # Library tests only
├── test_*.py                 # Mirror afk/*.py
└── fixtures/                 # Fake CLI scripts

examples/                     # Usage examples
├── tracer_bullet.py          # Minimal 1-turn validation
└── prompts/

docs/                         # Project artifacts
```

### Architectural Boundaries

| Boundary | Inside | Outside |
|----------|--------|---------|
| Framework | `afk/` module | Experiments, runs |
| Experiment | `trivial-loop/` etc. | Framework internals |
| Run workspace | `~/runs/xxx/` | Everything—agent never sees framework |

### Design Philosophy

**Smart defaults, application-overridable.**

The framework ships with sensible opinions. Applications override when they know better:
- Commits per turn: default 1, overridable
- Commit message schema: default success/failure, overridable
- Success criteria: default one commit, overridable

### Linting and Code Quality Checks

All three must pass before committing:

```bash
uv run ruff check afk/ tests/      # Linting
uv run ruff format --check afk/ tests/  # Formatting
uv run pyright --threads           # Type checking (strict)
uv run pytest                      # Tests
```

Type errors are bugs. Fix them, don't suppress them.

### Testing Philosophy

**No mocks.** Use fake CLI scripts in `tests/fixtures/` to simulate Claude. Real code runs; only the external process is faked.

### What NOT to Do

- Don't create config files (YAML, TOML, etc.)—everything in Python code
- Don't create exception hierarchies—just use RuntimeError
- **No frozen dataclasses.** Plain classes with `__slots__` and read-only properties.
- Don't add docstrings to obvious functions
- Don't over-engineer—keep < 1000 LOC in framework core
- Don't touch files outside the current task scope
- **No absolute paths**—compute from `__file__`
- Don't suppress type errors with `# type: ignore`—fix the underlying issue
- **No flaky tests. No "unrelated" failing tests.** Fix them. Deleting requires human approval.
- **Never name a module after stdlib**—no `logging.py`, `typing.py`, `collections.py`, etc.
- **Never hardcode paths in tests**—use pytest's `tmp_path` fixture
- **KeyError/IndexError take the key/index value, not a message string**—`raise KeyError(n)` not `raise KeyError(f"not found: {n}")`

Project artifacts use formal technical English.
