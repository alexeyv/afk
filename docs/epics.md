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
| FR5 | Epic 1 | Return what agent produced |
| FR6 | Epic 2 | Sequential turn numbers |
| FR7 | Epic 2 | Transition type labeling |
| FR8 | Epic 2 | Artifact naming by turn/type |
| FR9 | Epic 2 | Reference turns by number |
| FR10 | Epic 3 | Rewind to previous turn |
| FR11 | Epic 3 | Restart from rewound state |
| FR12 | Epic 3 | Track agent vs user commits |
| FR13 | Epic 4 | Run trivial loop |
| FR14 | Epic 4 | Define next prompt from results |
| FR15 | Epic 4 | Terminal state handling |
| FR16 | Epic 4 | Interrupt running loop |
| FR17 | Epic 4 | Manual state setting |
| FR18 | Epic 4 | Max turn configuration |
| FR19 | Epic 5 | Interactive mode |
| FR20 | Epic 5 | Headless mode |
| FR21 | Epic 5 | Command-line flags |
| FR22 | Deferred | .afk config file (per Architecture decision) |
| FR23 | Deferred | Flags override file (per Architecture decision) |
| FR24 | Epic 6 | Clone and run |
| FR25 | Epic 6 | Scaffold new project |
| FR26 | Epic 6 | Bundled prompts |

## Epic List

### Epic 1: Core Prompt Execution
User can run a single prompt against Claude Code CLI and see what happens—real-time streaming, logging, and structured results back.
**FRs covered:** FR1, FR2, FR3, FR4, FR5

### Epic 2: Turn Tracking & Session Management
User can run multiple prompts in sequence with each turn numbered, labeled, and logged separately—giving full observability into multi-turn sessions.
**FRs covered:** FR6, FR7, FR8, FR9

### Epic 3: State Recovery & Rewind
User can rewind to any previous turn's commit and restart from a clean state—the core workflow for "that went off the rails, let me try again."
**FRs covered:** FR10, FR11, FR12

### Epic 4: State Machine Orchestration
User can define a state machine (states, outcomes, transitions) and let the framework run it—from trivial loops to sophisticated graphs.
**FRs covered:** FR13, FR14, FR15, FR16, FR17, FR18

### Epic 5: CLI & Configuration
User can run afk interactively (menus) or headless (flags), with all options specified via command-line flags.
**FRs covered:** FR19, FR20, FR21 (FR22, FR23 deferred per Architecture decision—no config files)

### Epic 6: Project Setup & Templates
User can clone-and-run or scaffold a new project, with bundled prompts ready to experiment.
**FRs covered:** FR24, FR25, FR26

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

## Epic 3: State Recovery & Rewind

User can rewind to any previous turn's commit and restart from a clean state—the core workflow for "that went off the rails, let me try again."

### Story 3.1: Agent vs User Commit Tracking

As a framework user,
I want the system to distinguish between commits made by the agent and commits made by me,
So that I can understand what changes came from where.

**Acceptance Criteria:**

**Given** a turn executes and the agent makes a commit
**When** the turn completes
**Then** the commit is recorded as agent-authored in the `Turn` instance

**Given** commits exist in the repo before a session starts
**When** the `Session` begins
**Then** those commits are recognized as pre-existing (not agent commits)

**Given** a `Session` with multiple turns
**When** I query which commits were made by the agent
**Then** I receive only commits made during turn executions
**And** each commit is associated with its turn number

### Story 3.2: Rewind to Previous Turn

As a framework user,
I want to rewind the repository to a specific turn's commit,
So that I can recover from bad agent output and try again.

**Acceptance Criteria:**

**Given** a `Session` with turns 1, 2, 3 and their commits
**When** I call `session.rewind_to_turn(2)`
**Then** the repository is reset to turn 2's commit (hard reset)
**And** turn 3's changes are discarded
**And** the working directory matches the state after turn 2

**Given** a rewind operation
**When** it completes
**Then** any uncommitted changes are discarded
**And** the git log shows only commits up to the target turn

**Given** an invalid turn number (e.g., turn 5 when only 3 exist)
**When** I call `session.rewind_to_turn(5)`
**Then** a `RuntimeError` is raised
**And** the repository state is unchanged

### Story 3.3: Restart from Rewound State

As a framework user,
I want to continue execution from a rewound state with fresh context,
So that I can iterate on prompts without accumulated garbage.

**Acceptance Criteria:**

**Given** the repository has been rewound to turn 2
**When** I execute a new turn
**Then** the new turn is numbered 3 (continuing sequence)
**And** the agent runs with fresh context (no memory of previous turn 3)
**And** the previous turn 3 data is preserved in session history (marked as superseded)

**Given** a rewound session
**When** I review session history
**Then** I can see the original turn 3 and the new turn 3
**And** they are distinguishable (e.g., turn 3a, 3b or timestamps)

**Given** multiple rewind-and-retry cycles
**When** reviewing the session
**Then** the full history of attempts is preserved
**And** the current state is clearly indicated

---

## Epic 4: State Machine Orchestration

User can define a state machine (states, outcomes, transitions) and let the framework run it—from trivial loops to sophisticated graphs.

### Story 4.1: State and Transition Definitions

As a framework developer,
I want to define states with prompts and transition maps,
So that I can describe how the machine should behave.

**Acceptance Criteria:**

**Given** I want to define a state
**When** I create a `State` instance
**Then** it has a name (string identifier)
**And** it has a prompt (or prompt path)
**And** it has a transition map (outcome → next state name)

**Given** a `State` with transitions `{"success": "coding", "failure": "halt"}`
**When** the outcome is "success"
**Then** the next state is "coding"

**Given** a `State` with no transitions defined (empty map)
**When** the `Machine` reaches this state
**Then** it is recognized as a terminal state

**Given** a transition map references an undefined state
**When** the `Machine` is validated
**Then** a `RuntimeError` is raised before execution begins

### Story 4.2: Machine Definition and Validation

As a framework user,
I want to define a complete `Machine` with multiple states,
So that I can orchestrate complex agent workflows.

**Acceptance Criteria:**

**Given** multiple `State` definitions
**When** I create a `Machine`
**Then** it contains all states indexed by name
**And** it has a designated start state

**Given** a `Machine` definition
**When** I call `machine.validate()`
**Then** all state transitions point to valid states
**And** the start state exists
**And** at least one terminal state exists (reachable or not)

**Given** the trivial loop (init → coding → coding...)
**When** I define it as a `Machine`
**Then** it has two states: "init" and "coding"
**And** init transitions to coding on success
**And** coding transitions to coding on success (self-loop)

### Story 4.3: Machine Execution Loop

As a framework user,
I want the `Machine` to execute states automatically based on outcomes,
So that I don't have to manually trigger each transition.

**Acceptance Criteria:**

**Given** a valid `Machine` and a `Session`
**When** I call `machine.run(session)`
**Then** execution starts at the start state
**And** each state's prompt is executed as a turn
**And** the outcome determines the next state
**And** execution continues until a terminal state is reached

**Given** a `Machine` running
**When** a terminal state is reached (no transitions)
**Then** execution stops
**And** the final `Turn` result is returned

**Given** a `Machine` execution
**When** an exception occurs during a turn
**Then** the `Machine` halts immediately
**And** the exception propagates
**And** all completed turns are preserved in the `Session`

### Story 4.4: Interrupt and Resume

As a framework user,
I want to interrupt a running `Machine` and optionally resume or change state,
So that I can intervene when something goes wrong.

**Acceptance Criteria:**

**Given** a `Machine` is running
**When** I send SIGINT (Ctrl+C)
**Then** the current turn is interrupted
**And** the `Machine` stops after the current turn completes (or fails)
**And** the `Session` state is preserved

**Given** an interrupted `Machine`
**When** I call `machine.resume(session)`
**Then** execution continues from the current state
**And** a new turn is started

**Given** an interrupted `Machine`
**When** I call `machine.set_state(session, "init")`
**Then** the current state is changed to "init"
**And** subsequent resume starts from "init"

### Story 4.5: Turn Limits

As a framework user,
I want to configure a maximum number of turns,
So that runaway loops don't execute forever.

**Acceptance Criteria:**

**Given** a `Machine` with max_turns=10
**When** execution reaches turn 10
**Then** execution halts after turn 10 completes
**And** a `RuntimeError` is raised with message indicating max turns reached
**And** all 10 turns are preserved in the `Session`

**Given** a `Machine` with no max_turns configured
**When** execution runs
**Then** it continues until a terminal state or exception

**Given** max_turns=5 and the `Machine` terminates at turn 3
**When** execution completes
**Then** no exception is raised (normal termination)
**And** only 3 turns exist in the `Session`

---

## Epic 5: CLI & Configuration

User can run afk interactively (menus) or headless (flags), with all options specified via command-line flags.

### Story 5.1: CLI Entry Point and Basic Structure

As a framework user,
I want a CLI entry point that parses arguments and routes to commands,
So that I can invoke afk from the terminal.

**Acceptance Criteria:**

**Given** afk is installed via `pip install -e .`
**When** I run `afk` in terminal
**Then** the CLI is invoked
**And** help is displayed if no command given

**Given** the CLI structure
**When** I run `afk --help`
**Then** I see available commands and global options

**Given** click is used for CLI parsing
**When** commands are defined
**Then** they follow click patterns (decorators, options, arguments)

### Story 5.2: Headless Run Command

As a framework user,
I want to run a machine headlessly with flags,
So that I can automate agent execution in scripts.

**Acceptance Criteria:**

**Given** a workspace directory and experiment module
**When** I run `afk run --workspace ~/runs/test-001 --experiment trivial-loop`
**Then** the experiment's machine is loaded
**And** execution proceeds automatically
**And** output streams to terminal
**And** exit code reflects success (0) or failure (non-zero)

**Given** headless mode
**When** execution completes or fails
**Then** no interactive prompts are shown
**And** all output goes to stdout/stderr

**Given** the `--max-turns` flag
**When** I run `afk run --max-turns 5 ...`
**Then** execution stops after 5 turns

### Story 5.3: Interactive Mode

As a framework user,
I want an interactive mode with menus for exploration,
So that I can experiment without memorizing flags.

**Acceptance Criteria:**

**Given** I run `afk` without commands
**When** the CLI starts
**Then** an interactive menu is displayed
**And** I can select options by number or name

**Given** interactive mode
**When** I select "run experiment"
**Then** I'm prompted for workspace path
**And** I'm prompted for experiment selection
**And** execution begins after confirmation

**Given** interactive mode during execution
**When** I press Ctrl+C
**Then** a menu appears with options: continue, rewind, change state, quit

### Story 5.4: Status and Inspection Commands

As a framework user,
I want commands to inspect session state,
So that I can understand what happened during a run.

**Acceptance Criteria:**

**Given** a session exists in a workspace
**When** I run `afk status --workspace ~/runs/test-001`
**Then** I see current state, turn count, last outcome

**Given** a session with turns
**When** I run `afk log --workspace ~/runs/test-001 --turn 3`
**Then** I see the log file contents for turn 3

**Given** a session with turns
**When** I run `afk history --workspace ~/runs/test-001`
**Then** I see a summary of all turns (number, type, outcome, timestamp)

---

## Epic 6: Project Setup & Templates

User can clone-and-run or scaffold a new project, with bundled prompts ready to experiment.

### Story 6.1: Package Structure and Installation

As a framework user,
I want to install afk and have the CLI available,
So that I can start using it immediately after clone.

**Acceptance Criteria:**

**Given** I clone the afk repository
**When** I run `pip install -e .`
**Then** the `afk` command is available on PATH
**And** the afk module is importable

**Given** pyproject.toml exists
**When** I inspect it
**Then** it defines project metadata (name, version, description)
**And** it defines dependencies (click, etc.)
**And** it defines the `afk` script entry point

**Given** a fresh clone
**When** I run `pip install -e . && afk --help`
**Then** the help message displays (no errors)

### Story 6.2: Trivial Loop Experiment

As a framework user,
I want a bundled trivial-loop experiment,
So that I can run my first experiment without writing any code.

**Acceptance Criteria:**

**Given** the afk repo is cloned
**When** I look in `trivial-loop/`
**Then** I find `run.py` (the experiment code)
**And** I find `prompts/init.md` (initialization prompt)
**And** I find `prompts/coding.md` (coding prompt)

**Given** the trivial-loop experiment
**When** I examine `run.py`
**Then** it imports from afk module
**And** it defines a Machine with init and coding states
**And** init transitions to coding on success
**And** coding transitions to coding on success (self-loop)

**Given** the bundled prompts
**When** I examine them
**Then** they include outcome signaling instructions (commit with `outcome: success` or `outcome: failure` footer)
**And** they include the commit message schema guidance

### Story 6.3: Workspace Initialization

As a framework user,
I want to initialize a fresh workspace for an experiment,
So that the agent works in isolation from the framework source.

**Acceptance Criteria:**

**Given** I want to run an experiment
**When** I run `afk init --workspace ~/runs/test-001`
**Then** the directory is created if it doesn't exist
**And** a git repository is initialized in it
**And** an initial commit is made (empty or with .gitignore)

**Given** a workspace path that already exists and has commits
**When** I run `afk init --workspace ~/runs/test-001`
**Then** an error is raised (won't overwrite existing workspace)

**Given** a fresh workspace
**When** I run an experiment in it
**Then** the agent only sees the workspace contents
**And** the agent cannot see or modify the afk source

### Story 6.4: README and Getting Started

As a potential user,
I want a README that explains what afk does and how to try it,
So that I can decide if it's useful and get started quickly.

**Acceptance Criteria:**

**Given** someone visits the repo
**When** they read README.md
**Then** they understand what afk is (autonomous coding agent framework)
**And** they understand the core concept (run_prompt → result)
**And** they see prerequisites (Python, Claude Code CLI, Claude Max)

**Given** the README
**When** I follow the quickstart
**Then** I can go from clone to running the trivial loop in < 5 minutes
**And** each step is explicit (no assumed knowledge)

**Given** the README
**When** I want to learn more
**Then** I find links to deeper documentation or examples
**And** I understand how to create my own experiments
