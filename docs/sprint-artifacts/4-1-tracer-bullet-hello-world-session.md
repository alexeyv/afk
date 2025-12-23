# Story 4.1: Tracer Bullet — Hello World Session

Status: ready-for-dev

## Story

As a framework developer,
I want to run a 1-turn session that creates a hello world script,
so that I can validate the driver works end-to-end with real Claude Code CLI.

## Acceptance Criteria

1. **Given** Claude Code CLI is installed and working
   **When** I create a Session and execute one turn with a simple prompt ("create hello.py that prints hello world")
   **Then** Claude Code runs, creates the file, commits with outcome
   **And** TurnResult contains the commit hash and outcome
   **And** Git tag `afk-{session}-1` exists pointing to the commit

2. **Given** the tracer bullet succeeds
   **When** I inspect the workspace
   **Then** hello.py exists and runs correctly
   **And** git log shows the agent's commit with outcome footer
   **And** git tag shows `afk-{session}-0` (session start) and `afk-{session}-1` (turn 1) tags

## Tasks / Subtasks

- [ ] Task 1: Create examples directory structure (AC: #1, #2)
  - [ ] 1.1: Create `examples/` directory
  - [ ] 1.2: Create `examples/prompts/` subdirectory

- [ ] Task 2: Create hello_world.md prompt with outcome signaling (AC: #1)
  - [ ] 2.1: Write prompt that instructs Claude to create hello.py (see example below)
  - [ ] 2.2: Include explicit outcome signaling instructions (conventional commit with `outcome: success` footer)
  - [ ] 2.3: Include constraint for single commit

  **Example prompt structure:**
  ```
  Create a file called hello.py that prints "hello world" to stdout.

  When complete, commit with:
  - Conventional commit format (e.g., "feat: add hello world script")
  - Add "outcome: success" in the commit message footer
  - Use exactly ONE commit for all changes
  ```

- [ ] Task 3: Create tracer_bullet.py script (AC: #1, #2)
  - [ ] 3.1: Create script skeleton (imports, create workspace dir if not exists)
  - [ ] 3.2: Instantiate Driver, Git, Session (workspace dir must exist first!)
  - [ ] 3.3: Read prompt from `examples/prompts/hello_world.md`
  - [ ] 3.4: Execute one turn with `TransitionType("init")` (NOT enum-style)
  - [ ] 3.5: Print TurnResult showing outcome, commit_hash, message
  - [ ] 3.6: Verify git tags exist
  - [ ] 3.7: Handle expected errors (CLI unavailable, no commit, etc.)

- [ ] Task 4: Run end-to-end validation (AC: #1, #2)
  - [ ] 4.1: Create fresh workspace directory (e.g., `~/runs/tracer-001/`) — use unique name
  - [ ] 4.2: Run tracer_bullet.py against real Claude Code CLI
  - [ ] 4.3: Verify hello.py exists and runs (`python hello.py` → outputs "hello world")
  - [ ] 4.4: Verify git log shows commit with `outcome: success` footer
  - [ ] 4.5: Verify `git tag` shows both `afk-{session}-0` and `afk-{session}-1`
  - [ ] 4.6: Check `workspace/logs/` for turn log files (useful for debugging)

- [ ] Task 5: Document any driver issues discovered (AC: #1)
  - [ ] 5.1: If issues found, document in story completion notes
  - [ ] 5.2: If fixes needed, create follow-up tasks

- [ ] Task 6: Verify complete success (AC: #1, #2)
  - [ ] 6.1: All acceptance criteria validated
  - [ ] 6.2: No driver issues blocking success

## Dev Notes

### Library API

The public API from `afk/__init__.py`:

```python
from afk import Driver, Git, Session, TransitionType, TurnResult
```

**Git instantiation** (`afk/git.py:10`):
```python
Git(repo_path: str)  # NOTE: Takes str, NOT Path!
```

- `repo_path`: String path to existing directory (Git validates directory exists)

**Driver instantiation** (`afk/driver.py:42`):
```python
Driver(working_dir: Path, *, model: str | None = None)
```

- `working_dir`: Must be absolute Path
- Checks environment on init: git, script, claude commands must be on PATH
- Raises RuntimeError if any command missing

**Session instantiation** (`afk/session.py:130`):
```python
Session(root_dir: Path, name: str, driver: Driver, git: Git)
```

- `root_dir`: Absolute Path to workspace directory (must exist!)
- `name`: Alphanumeric + underscores only, max 64 chars, no empty strings
- Session workspace initialization:
  - If directory is **empty**: creates git repo with initial commit
  - If directory is **already a git repo**: uses it (must have at least one commit)
  - If directory has **files but no repo**: raises RuntimeError
- Tags session start as `afk-{name}-0`

**CRITICAL: Git and Driver must point to same directory!**
```python
workspace = Path("/Users/alex/runs/tracer-001")
driver = Driver(workspace)          # Path
git = Git(str(workspace))           # str - MUST match driver path!
session = Session(workspace, "tracer", driver, git)
```

**TransitionType instantiation** (`afk/transition_type.py:19`):
```python
TransitionType(value: str)  # NOT enum-style!
```

- Constructed with string, not enum: `TransitionType("init")` ✓
- NOT `TransitionType.INIT` ✗
- Pattern: `^[a-z][a-z0-9_.-]*$` (lowercase letters, digits, underscore, dot, dash)

**Execute turn** (`afk/session.py:290`):
```python
result = session.execute_turn(prompt: str, transition_type: TransitionType) -> TurnResult
```

- Tags commit as `afk-{session_name}-{turn_number}` after completion

**TurnResult** (`afk/turn_result.py`):
```python
result.outcome      # str: "success", "failure", or custom
result.commit_hash  # str: Git SHA
result.message      # str: Full commit message
result.turn_number  # int: Sequential turn number
```

### Complete Minimal Example

```python
from pathlib import Path
from afk import Driver, Git, Session, TransitionType

# 1. Create workspace directory (MUST exist before Git/Session)
workspace = Path.home() / "runs" / "tracer-001"
workspace.mkdir(parents=True, exist_ok=True)

# 2. Instantiate components (Git takes str, Driver takes Path)
driver = Driver(workspace)
git = Git(str(workspace))  # Note: str, not Path!

# 3. Create session (will init git if empty, tag as afk-tracer-0)
session = Session(workspace, "tracer", driver, git)

# 4. Execute turn (TransitionType takes string, not enum)
prompt = open("examples/prompts/hello_world.md").read()
result = session.execute_turn(prompt, TransitionType("init"))

# 5. Check result
print(f"Outcome: {result.outcome}")
print(f"Commit: {result.commit_hash[:7]}")
```

### Commit Message Schema

The prompt must instruct Claude to commit with conventional format + outcome footer:

```
feat: description

Body text.

outcome: success
```

The framework parses `outcome:` from the commit message footer. [Source: docs/architecture.md#Commit-Message-Schema]

### Run Workspace Pattern

Tracer bullet runs in a fresh workspace OUTSIDE the afk repo:

```
~/runs/tracer-001/      # Fresh git repo, agent works here
```

**CRITICAL: Workspace must NOT be inside /Users/alex/src/afk!**

The script should:
1. Create workspace directory (must exist before Git/Session instantiation)
2. Instantiate Driver(workspace) and Git(str(workspace)) pointing to SAME directory
3. Create Session which initializes the workspace (empty → init git, existing repo → use it)
4. Use unique session name to avoid tag collisions (e.g., include timestamp)

### Testing Philosophy

This is NOT a unit test - it's end-to-end validation with real Claude Code CLI. No mocks, no fakes. [Source: docs/architecture.md#Test-Strategy]

### Project Structure Notes

New files to create:
```
examples/
├── tracer_bullet.py          # Main script
└── prompts/
    └── hello_world.md        # Prompt with outcome signaling
```

This matches the documented structure. [Source: docs/architecture.md#Project-Structure]

### Critical Constraints

- **Single commit per turn**: Framework expects exactly 1 commit (`session.py:282` raises if multiple)
- **Outcome in footer**: Must be parseable from commit message (`git.py` parses `outcome:` token)
- **No absolute paths in code**: Compute from `__file__` or use Path operations [Source: docs/project-context.md]
- **Script command**: Driver uses `script` to wrap Claude CLI for terminal emulation (`driver.py:109-113`)

### References

- [Source: docs/architecture.md:288-312] - examples/ directory structure
- [Source: docs/architecture.md:216-229] - Conventional commits + outcome footer
- [Source: docs/architecture.md:162-179] - Test strategy: real CLI, not mocks
- [Source: docs/project-context.md:55-72] - Python conventions
- [Source: afk/session.py:290-321] - execute_turn implementation
- [Source: afk/driver.py:63-101] - run() method with script wrapper
- [Source: afk/git.py:10-18] - Git constructor (takes str, not Path)
- [Source: afk/transition_type.py:19-34] - TransitionType constructor
- [Source: docs/epics.md:371-398] - Original story definition

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
