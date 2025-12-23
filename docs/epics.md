---
stepsCompleted: [1, 2, 3, 4]
status: complete
completedAt: '2025-12-09'
inputDocuments:
  - docs/prd.md
  - docs/architecture.md
project_name: afk
user_name: Alex
date: '2025-12-09'
---

# afk - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for afk, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: User can execute a prompt against Claude Code CLI and receive structured results
- FR2: User can observe agent output in real-time as it streams to terminal
- FR3: System logs agent session to a file identified by turn number and transition type
- FR4: System detects git commits made by the agent during a session
- FR5: System returns what the agent produced (commits, documents) after session completes
- FR6: System assigns sequential turn numbers starting from 1
- FR7: Each turn is labeled with its transition type (init, coding, etc.)
- FR8: Logs and artifacts are named by turn number and transition type
- FR9: User can reference a specific turn by number for operations
- FR10: User can rewind repository to a specific previous turn's commit
- FR11: User can restart agent execution from a rewound state with fresh context
- FR12: System tracks which commits were made by agent vs user
- FR13: User can run a predefined trivial loop (Init → Coding → Coding...)
- FR14: User can define which prompt to run next based on previous results
- FR15: Loop terminates when state machine reaches a terminal state (no exits)
- FR16: User can interrupt a running loop
- FR17: User can manually set the state machine to a specific state after interruption
- FR18: User can configure maximum turns to limit loop execution
- FR19: User can run afk in interactive mode with menus for exploration
- FR20: User can run afk in headless mode with flags for automation
- FR21: User can specify configuration via command-line flags
- FR22: User can persist default configuration in `.afk` project file
- FR23: Command-line flags override `.afk` file settings
- FR24: User can clone the afk repo and run it directly
- FR25: User can scaffold a new project with predefined prompt locations
- FR26: System provides Init and Coding prompts as starting templates

### NonFunctional Requirements

- NFR1: Framework overhead is negligible compared to LLM latency
- NFR2: System gracefully handles Claude Code CLI unavailability (clear error message)
- NFR3: System adapts to Claude Code CLI output format changes with minimal code changes (driver abstraction)
- NFR4: System does not depend on specific Claude Code CLI version beyond documented minimum
- NFR5: System recovers cleanly from interrupted sessions (Ctrl+C leaves no orphan processes)
- NFR6: System preserves all logs and state even if session crashes mid-turn
- NFR7: System never corrupts git repository state (worst case: uncommitted changes, not broken repo)
- NFR8: On unrecoverable error during a turn, system rewinds to last committed state and halts cleanly
- NFR9: Adding a new transition type requires changes to < 3 files
- NFR10: Codebase is small enough for a single developer to hold in head (target: < 1000 LOC core)
- NFR11: System supports replaying from any previous turn state without side effects

### Additional Requirements

- No starter template - Project is minimal Python CLI; starts from scratch
- `script` command wrapper - Uses `script` to make Claude Code think it's in a terminal
- Post-commit hook termination - Hook kills agent on graceful completion
- Conventional commits with outcome footer - `outcome: success` or `outcome: failure` in commit message footer
- Exception vs Outcome distinction - Zero commits, multiple commits, timeout, process died are exceptions (halt machine), not outcomes
- Smart defaults philosophy - Framework has opinions, applications can override
- Flat structure - One file per domain entity: driver.py, machine.py, session.py, turn.py, transition.py, prompt.py, revision.py, commit.py, git.py
- TurnResult dataclass - Returns outcome, message, commit_hash
- Runs live outside repo - Agent workspaces in ~/runs/, never see framework source
- Fake CLI fixtures for testing - Python scripts simulate agent behavior for integration tests

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | Execute prompt against CLI |
| FR2 | Epic 1 | Real-time streaming |
| FR3 | Epic 1 | Session logging |
| FR4 | Epic 1 | Commit detection |
| FR5 | Epic 1 | Return TurnResult |
| FR6 | Epic 2, 3 | Create named Session |
| FR7 | Epic 3 | Tag session start |
| FR8 | Epic 2 | Sequential turn numbers |
| FR9 | Epic 3 | Tag completed turns |
| FR10 | Epic 3 | Rewind via tag checkout (git operation) |
| FR11 | Epic 4, 5 | Clone repo and import library |
| FR12 | Epic 5 | Example prompts with outcome signaling |

## Epic List

### Epic 1: Core Prompt Execution ✅
User can run a single prompt against Claude Code CLI and see what happens—real-time streaming, logging, and structured results back.
**FRs covered:** FR1, FR2, FR3, FR4, FR5
**Status:** Done

### Epic 2: Turn Tracking & Session Management ✅
User can run multiple prompts in sequence with each turn numbered, labeled, and logged separately—giving full observability into multi-turn sessions.
**FRs covered:** FR6, FR7, FR8, FR9
**Status:** Done

### Epic 3: Session Naming & Git Tagging ✅
Sessions have names, turns are tagged in git. Rewind = checkout tag + branch + new session.
**FRs covered:** FR6, FR7, FR8, FR9, FR10
**Status:** Done (Story 3.1 completed; Stories 3.2, 3.3 obsolete—git handles rewind)

### Epic 4: Tracer Bullet
Prove the driver actually works by running a minimal 1-turn session end-to-end against real Claude Code CLI.
**FRs covered:** FR1-5 (validation), FR11
**Status:** Backlog — IMMEDIATE PRIORITY

### Epic 5: Demo Recreation
Recreate the Anthropic autonomous-coding quickstart using afk, demonstrating full loop with git-recorded turn history.
**FRs covered:** FR11, FR12, all FRs validated end-to-end
**Status:** Backlog — MVP exit criterion

---

## Epic 1: Core Prompt Execution

User can run a single prompt against Claude Code CLI and see what happens—real-time streaming, logging, and structured results back.

### Story 1.1: Git Operations Foundation

As a framework developer,
I want a `Git` class that queries repo state and parses commit messages,
So that the framework can detect what the agent produced.

**Acceptance Criteria:**

**Given** a git repository exists in the target directory
**When** I instantiate `Git(repo_path)` and call `git.head_commit()`
**Then** I receive the current HEAD commit hash
**And** returns None if no commits exist

**Given** a commit with message following conventional format with `outcome:` footer
**When** I call `git.parse_commit_message(hash)`
**Then** I receive a tuple of (outcome, message) where outcome is the parsed value (e.g., "success")
**And** message is the full commit message text

**Given** a commit without an `outcome:` footer
**When** I call `git.parse_commit_message(hash)`
**Then** I receive a tuple of (None, message)
**And** message is the full commit message text

**Given** two commit hashes
**When** I call `git.commits_between(before, after)`
**Then** I receive a list of commit hashes made between those points
**And** the list is ordered oldest to newest

### Story 1.2: Driver - Execute Prompt via Script Wrapper

As a framework user,
I want a `Driver` class to execute prompts against Claude Code CLI with real-time streaming,
So that I can watch the agent work and have output logged.

**Acceptance Criteria:**

**Given** Claude Code CLI is available on PATH
**When** I instantiate `Driver(workspace)` or `Driver(workspace, model="model-name")` and call `driver.run(prompt, log_file)`
**Then** the prompt is passed to Claude Code CLI in the specified workspace
**And** if `model` was provided, the CLI is invoked with `--model <model>`
**And** output streams to terminal in real-time
**And** output is captured to the specified log file
**And** the method blocks until the process exits

**Given** the `script` command is used to wrap CLI execution
**When** the agent runs
**Then** Claude Code CLI behaves as if in a real terminal (proper streaming)
**And** all output including ANSI codes is captured to log

**Given** a prompt execution is in progress
**When** I send SIGINT (Ctrl+C)
**Then** the CLI process is terminated
**And** no orphan processes remain
**And** partial log output is preserved

### Story 1.3: Commit Detection and Result Extraction

As a framework user,
I want the framework to detect commits made during execution and return structured results,
So that I know what the agent produced.

**Acceptance Criteria:**

**Given** a prompt execution that results in exactly one commit
**When** the driver completes
**Then** I receive a `TurnResult` with outcome, message, and commit_hash
**And** the outcome is extracted from the `outcome:` footer

**Given** a prompt execution completes
**When** I check for commits made during execution
**Then** the framework compares HEAD before and after execution
**And** identifies all commits made in that window

**Given** the agent made a commit with footer `outcome: success`
**When** result extraction runs
**Then** `TurnResult.outcome` equals "success"
**And** `TurnResult.message` contains the full commit message
**And** `TurnResult.commit_hash` is the SHA of the commit

### Story 1.4: Exception Handling for Prompt Execution

As a framework user,
I want clear errors when prompt execution fails,
So that I can understand what went wrong and take corrective action.

**Acceptance Criteria:**

**Given** a prompt execution that produces zero commits
**When** the driver completes
**Then** a `RuntimeError` is raised with message indicating no commit was detected

**Given** a prompt execution that produces multiple commits
**When** the driver completes
**Then** a `RuntimeError` is raised with message listing the commit hashes

**Given** Claude Code CLI is not available on PATH
**When** I attempt to run a prompt
**Then** a `RuntimeError` is raised with message explaining how to install Claude Code CLI

**Given** the CLI process dies unexpectedly (non-zero exit, signal)
**When** the driver completes
**Then** a `RuntimeError` is raised with exit code or signal information
**And** the partial log file is preserved for debugging

---

## Epic 2: Turn Tracking & Session Management

User can run multiple prompts in sequence with each turn numbered, labeled, and logged separately—giving full observability into multi-turn sessions.

### Story 2.1: Turn Data Structure

As a framework developer,
I want a `Turn` class that captures all information about a single prompt execution,
So that I can track and reference individual turns in a session.

**Acceptance Criteria:**

**Given** a prompt execution completes
**When** I create a `Turn` instance
**Then** it contains turn_number (int, starting from 1)
**And** it contains transition_type (string, e.g., "init", "coding")
**And** it contains result (TurnResult or None if exception)
**And** it contains log_file path
**And** it contains timestamp of execution

**Given** a `Turn` instance exists
**When** I access its properties
**Then** all fields are immutable (dataclass frozen=True)

### Story 2.2: Session Tracking

As a framework user,
I want a `Session` class that tracks all turns in sequence,
So that I can review what happened across the entire run.

**Acceptance Criteria:**

**Given** a new `Session` is created
**When** I add turns to it
**Then** turn numbers are assigned sequentially starting from 1
**And** turns are stored in order

**Given** a `Session` with multiple turns
**When** I call `session.turn(n)`
**Then** I receive the `Turn` with turn_number == n
**And** raises KeyError if turn doesn't exist

**Given** a `Session` with turns
**When** I iterate over the session
**Then** I receive turns in chronological order

**Given** a `Session`
**When** I access `session.turns`
**Then** I receive an immutable view of all turns

### Story 2.3: Turn-Based Logging

As a framework user,
I want log files named by turn number and transition type,
So that I can easily find logs for specific turns.

**Acceptance Criteria:**

**Given** turn number 3 with transition type "coding"
**When** generating the log file name
**Then** the name follows pattern `turn-003-coding.log`
**And** the file is created in the session's log directory

**Given** a session log directory
**When** multiple turns execute
**Then** each turn has its own log file
**And** log files are never overwritten

**Given** a turn's log file path
**When** I want to review that turn
**Then** the path is accessible via `turn.log_file`

### Story 2.4: Turn Execution Integration

As a framework user,
I want to execute a turn that uses the `Driver` and records results in the `Session`,
So that turn tracking is automatic during prompt execution.

**Acceptance Criteria:**

**Given** a `Session` and a prompt with transition type
**When** I call `session.execute_turn(prompt, transition_type)`
**Then** the `Driver` is invoked with the prompt
**And** a `Turn` instance is created with the next turn number
**And** the `Turn` is added to the session
**And** the `Turn` is returned

**Given** a turn execution that raises an exception
**When** the exception occurs
**Then** a `Turn` instance is still created
**And** the `Turn`'s result is None
**And** the `Turn`'s log file is preserved
**And** the exception propagates after recording

---

## Epic 3: Session Naming & Git Tagging

Sessions have names, turns are tagged in git. Rewind = checkout tag + branch + new session.

### Story 3.1: Session Naming and Turn Tagging ✅

**Status:** Done

As a framework user,
I want each session to have a name and each turn to be tagged in git,
So that I can identify turn boundaries and rewind to any completed turn.

**Acceptance Criteria:**

1. **Given** I create a Session
   **When** I pass a name parameter
   **Then** the name is stored and accessible
   **And** validation rejects: empty string, whitespace-only, multi-line, leading/trailing whitespace

2. **Given** a turn completes successfully
   **When** the TurnResult is created
   **Then** HEAD is tagged with `afk-{session_name}-{turn_number}`
   **And** the tag points to the commit in TurnResult.commit_hash

3. **Given** a Session with completed turns
   **When** I want to rewind to turn N
   **Then** I can checkout tag `afk-{session_name}-{N}` and branch from it

### Stories 3.2 & 3.3: OBSOLETE

**Rationale:** The tag-based design implemented in Story 3.1 makes dedicated rewind/restart features unnecessary:
- Rewind to turn N: `git checkout afk-{session}-{N}`
- Restart from there: `git checkout -b new-branch && new Session("new_name")`

This is standard git workflow. The library provides tags; users do git operations.

---

## Epic 4: Tracer Bullet

Prove the driver actually works by running a minimal 1-turn session end-to-end against real Claude Code CLI.

### Story 4.1: Tracer Bullet — Hello World Session

As a framework developer,
I want to run a 1-turn session that creates a hello world script,
So that I can validate the driver works end-to-end with real Claude Code CLI.

**Acceptance Criteria:**

**Given** Claude Code CLI is installed and working
**When** I create a Session and execute one turn with a simple prompt ("create hello.py that prints hello world")
**Then** Claude Code runs, creates the file, commits with outcome
**And** TurnResult contains the commit hash and outcome
**And** Git tag `afk-{session}-1` exists pointing to the commit

**Given** the tracer bullet succeeds
**When** I inspect the workspace
**Then** hello.py exists and runs correctly
**And** git log shows the agent's commit with outcome footer
**And** git tag shows session-0 and session-1 tags

**Tasks:**
- [ ] Create `examples/tracer_bullet.py` script
- [ ] Create `examples/prompts/hello_world.md` with outcome signaling instructions
- [ ] Run against real Claude Code CLI (not fake)
- [ ] Document any driver issues discovered
- [ ] Fix driver issues if found
- [ ] Verify complete success before marking done

---

## Epic 5: Demo Recreation

Recreate the Anthropic autonomous-coding quickstart using afk, demonstrating full loop with git-recorded turn history.

### Story 5.1: Multi-Turn Demo Session

As a framework user,
I want to recreate the Anthropic autonomous-coding demo using afk,
So that I can validate the library works for real autonomous coding loops.

**Acceptance Criteria:**

**Given** the tracer bullet (Epic 4) succeeded
**When** I create a Session and run multiple turns mimicking the Anthropic demo flow
**Then** each turn produces a commit with outcome
**And** git tags mark every turn boundary
**And** the final result matches what the Anthropic demo produces

**Given** the demo completes
**When** I review the git history
**Then** I can see every turn's commit with its outcome
**And** I can checkout any turn tag and see the state at that point
**And** the history tells the story of what happened

**Tasks:**
- [ ] Study Anthropic quickstart (prompts/initializer_prompt.md, prompts/coding_prompt.md)
- [ ] Create `examples/anthropic_demo.py` that runs equivalent flow
- [ ] Create equivalent prompts with outcome signaling
- [ ] Run full demo, capture git history
- [ ] Document the session in README as proof of concept
- [ ] Verify git history is comprehensible and useful

### Story 5.2: README & Getting Started

As a potential user,
I want a README that shows afk working,
So that I can understand what it does and try it myself.

**Acceptance Criteria:**

**Given** someone visits the repo
**When** they read README.md
**Then** they see what afk is (library for autonomous coding turns)
**And** they see prerequisites (Python, Claude Code CLI, Claude Max)
**And** they see the tracer bullet example
**And** they see the demo recreation results (git history screenshot or log)

**Tasks:**
- [ ] Write README with clear value proposition
- [ ] Include tracer bullet quickstart (< 5 minutes)
- [ ] Show demo recreation results
- [ ] Link to examples/ directory
