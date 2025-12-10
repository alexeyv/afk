# Project Context - afk

**Project:** afk - Python framework for autonomous coding agent loops
**Date:** 2025-12-09

This file contains critical rules and patterns for AI agents implementing this codebase.

## Core Concept

afk is a **state machine executor**, not a loop orchestrator. The framework executes prompts and reports results. Loop logic lives in experiment code, not the framework.

- Git is the state machine. Revision = state. Commit = transition result.
- The framework is stateless—everything it needs is in git.
- Each turn executes one prompt, produces one commit, extracts the outcome.
- Runs live in separate git repos outside the afk codebase.

## Technology Stack

- **Language:** Python 3.x
- **System:** git (must be on PATH)
- **CLI Framework:** click
- **Testing:** pytest
- **Linting/Formatting:** ruff
- **Package Format:** pyproject.toml

## Critical Rules

### Version Control

- **Agents never push.** Human reviews and pushes.
- Planning workflows (PRD, architecture, epics): commit at workflow completion
- Dev workflow (dev-story): commit after each step
- Commit messages: `docs:` prefix for planning artifacts, conventional commits for code
- Keep docs on main, no branch ceremony for planning
- Amend only for typos, new commit for substantive changes

### Commit Message Schema

Conventional commits with outcome in footer:

```
feat: implement feature X

Description of changes.

[success] completed as specified
```

- Footer contains `[outcome] comment` for machine parsing
- Default outcomes: `success`, `failure`
- Applications can define additional outcomes

### Python Conventions

- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- No exception hierarchy—use `RuntimeError` for explicit errors
- Never wrap library exceptions—let them propagate with full stack trace
- Skip docstrings unless genuinely clarifying

### Project Structure

```
afk/                          # Framework module
├── cli.py                    # Entry point (click)
├── driver.py                 # Claude Code CLI wrapper
├── machine.py                # State machine execution
├── git.py                    # Git operations
└── ...                       # One file per domain entity

tests/                        # Framework tests only
├── test_*.py                 # Mirror afk/*.py
└── fixtures/                 # Fake CLI scripts

trivial-loop/                 # Experiments live alongside framework
├── run.py
└── prompts/

docs/                         # BMad artifacts
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

### What NOT to Do

- Don't create config files (YAML, TOML, etc.)—everything in Python code
- Don't create exception hierarchies—just use RuntimeError
- Don't add docstrings to obvious functions
- Don't over-engineer—keep < 1000 LOC in framework core
- Don't touch files outside the current task scope
