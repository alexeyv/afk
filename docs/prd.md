---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
inputDocuments:
  - docs/analysis/product-brief-afk-2025-12-09.md
  - ~/src/claude-quickstarts/autonomous-coding/agent.py
  - ~/src/claude-quickstarts/autonomous-coding/client.py
  - ~/src/claude-quickstarts/autonomous-coding/autonomous_agent_demo.py
  - ~/src/claude-quickstarts/autonomous-coding/prompts.py
  - ~/src/claude-quickstarts/autonomous-coding/security.py
  - ~/src/claude-quickstarts/autonomous-coding/prompts/initializer_prompt.md
  - ~/src/claude-quickstarts/autonomous-coding/prompts/coding_prompt.md
  - ~/src/claude-quickstarts/autonomous-coding/README.md
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 8
workflowType: 'prd'
lastStep: 11
project_name: 'afk'
user_name: 'Alex'
date: '2025-12-09'
---

# Product Requirements Document - afk

**Author:** Alex
**Date:** 2025-12-09

## Executive Summary

afk is a Python framework for autonomous coding agent loops. At its core: `run_prompt(prompt)` sends a prompt to Claude Code CLI, monitors the session in real-time, logs everything, and returns what the agent produced (a git commit, a document, or both).

The insight: Claude Code CLI on Claude Max ($100/month flat rate) makes extended autonomous coding economically viable. But there's no minimal harness to experiment with different loop shapes. You write the loop logic - which prompt to run next based on what came back. The framework handles the plumbing.

MVP ships with two prompts (Init and Coding) wired into a trivial loop. The framework's value is making it trivial to run any prompt and get structured output back.

### What Makes This Special

- **Simple core** - `run_prompt(prompt) → result`. You decide what to run next.
- **Transparent execution** - Real-time streaming, logging, full observability of what the agent is doing.
- **Structured output** - Agent work produces commits and/or documents. You get back what was created.
- **Flat-rate economics** - Runs on Claude Max via Claude Code CLI, not metered API calls.
- **Your loop, your logic** - Framework handles execution; you control the flow.

## Project Classification

**Technical Type:** CLI Tool / Developer Tool
**Domain:** General (developer tooling)
**Complexity:** Low
**Project Context:** Greenfield - new project

Target users are experienced developers with Claude Max subscriptions who want to experiment with autonomous coding loops without building the execution plumbing themselves.

## Success Criteria

### User Success

The user runs the trivial loop, watches the agent work in real-time, reviews the commits and logged reasoning, and it makes sense. They understand what happened and why.

Success is not "the agent built something useful" - that's on the prompts. The framework succeeds when execution is transparent and comprehensible.

### Business Success

**Did I learn something?**

After running experiments with the framework:
- Have data points: "Review every commit worked better than review every 5"
- Have anecdotes: "It went off the rails here, stopped correctly there"
- Formed opinions about where human checkpoints belong
- Ready to build the next iteration based on what was learned

The framework succeeds if it produces learning, not just code.

### Technical Success

- **Clone to first run:** < 5 minutes
- **Abstractions:** Clean enough that adding a third transition is obviously easy
- **Observability:** Real-time streaming, logging, commit detection all work reliably

### Measurable Outcomes

- Ran the trivial loop end-to-end
- Watched agent output stream in real-time
- Reviewed commits and reasoning logs
- Understood what the agent did and why

## Product Scope

### MVP - Minimum Viable Product

1. `run_prompt(prompt) → result` with real-time streaming and logging
2. Git commit detection (return what the agent produced)
3. Rewind to last good commit (recover from garbage, retry from clean state)
4. Two prompts (Init, Coding) wired into a trivial loop
5. Dual-mode CLI: interactive menus for exploration, headless flags for automation
6. README that makes developers want to try it

### Growth Features (Post-MVP)

- Review transitions
- Human checkpoint transitions
- Additional prompt templates

### Vision (Future)

- Context scoping (control what each transition sees)
- Structured commit message schema and enforcement
- Escalation logic (agent signals "I need help")
- BMAD integration

## User Journeys

### Journey 1: Alex - Recalibrating for a Moving Target

Alex is a senior developer who's spent months using Claude Code for real work. Six months ago, he learned the hard way that letting an LLM run unchecked produces plausible-looking garbage. He developed a personal rule: never let Claude run for more than two minutes without checking in. It worked then.

But the tools have changed. Claude's gotten better. Claude Code has new capabilities. Alex suspects his two-minute rule might be stale - a defensive habit from an earlier era that's now costing him productivity. He needs fresh data, not old instincts.

One evening, Alex clones afk and runs the trivial loop on a throwaway project. The terminal streams the agent's output in real-time. He watches the first iteration with mild curiosity, then the second. By the third, he's skimming commits instead of watching.

An hour later, he reviews the git log. Garbage starts showing up around the five-minute mark. Not two minutes - five. His old rule was too conservative by a factor of 2.5. That's not a vibe; that's a data point.

He rewinds to the last good commit and tweaks the prompt. The agent picks up from that state with fresh context. Second run: garbage at six minutes. He's iterating on the loop itself now, not just watching it run.

The framework gave him a lab to find out.

### Journey Requirements Summary

- Real-time streaming (watch what's happening)
- Commit detection and reporting (know what changed)
- Rewind to last good commit (recover from garbage, retry from clean state)
- Easy prompt modification (experiment with different loop shapes)
- Clear logging (review the session after the fact)
- Low friction to run experiments (test assumptions quickly)

## Innovation & Novel Patterns

### Why Build This

The trivial loop (init → coding → coding) isn't the point. It's scaffolding for experiments that don't exist yet.

**One experiment worth running:** A slow agent that walks a codebase's dependency graphs - lifecycle (who owns whom) and cooperation (who calls whom) - examining nodes with a couple layers of context in each direction.

- Lifecycle traversal might find memory leaks
- Cooperation traversal might find stale invariants - assumptions that held when code was written but broke as the codebase evolved

These are bugs almost impossible to find otherwise. Static analysis can't reason about intent. Tests only cover what you thought to test. One-shot LLM can't hold enough context.

A slow walk with accumulated context might.

**MVP doesn't build this.** MVP builds the scaffolding that makes experiments like this possible to try.

## CLI Tool / Developer Tool Requirements

### Command Interface

**Dual-mode CLI:**
- Interactive menus for exploration
- Headless flags for automation

**Configuration:**
- Command-line flags for everything
- `.afk` file in project root for persistent defaults
- Flags override file settings

### Installation & Setup

- Clone the repo, or
- Install and run scaffolding command to generate project skeleton
- Prompts live in predefined location within project

### Output Artifacts

- **Terminal streaming:** Pass-through from Claude Code CLI (not controlled by afk)
- **Log file:** One per session, agent writes whatever it wants, afk provides the filename
- **Git commits:** Format guided by prompts (may use JSON-structured messages)
- **Documents:** Agents exchange documents (likely JSON, possibly MD)

### Post-MVP Considerations

- Pre-commit hooks for commit format enforcement and invariant validation
- Back pressure on agent at commit time - when it thinks it's done

## Project Scoping & Phased Development

### MVP Strategy

**Approach:** Platform MVP - build the foundation for future experiments. The trivial loop proves the scaffolding works; it's not the product itself.

**Resource:** Solo project. Scope must stay minimal.

### MVP Feature Set (Phase 1)

1. `run_prompt(prompt) → result` with real-time streaming
2. Git commit detection (return what the agent produced)
3. Rewind to last good commit (recover from garbage, retry from clean state)
4. Two prompts (Init, Coding) wired into trivial loop
5. Dual-mode CLI (interactive menus + headless flags)
6. `.afk` config file support
7. Clone or scaffold install
8. README that makes developers want to try it

### Post-MVP Features (Phase 2)

- Pre-commit hooks for format enforcement and invariant validation
- Review transitions
- Human checkpoint transitions
- Additional prompt templates

### Vision (Phase 3)

- Dependency-graph walking experiments (lifecycle and cooperation graphs)
- Context scoping (graph-neighborhood, ~2 layers)
- Structured commit schema enforcement
- Escalation logic (agent signals "I need help")

### Risk Assessment

**Technical Risks:**
- Claude Agent SDK stability - mitigate by keeping driver abstraction clean
- Claude Code CLI changes - same mitigation

**Market Risks:** N/A - personal experimentation tool

**Resource Risks:** Solo project - scope creep is the main danger. Stay minimal.

## Functional Requirements

### Prompt Execution

- FR1: User can execute a prompt against Claude Code CLI and receive structured results
- FR2: User can observe agent output in real-time as it streams to terminal
- FR3: System logs agent session to a file identified by turn number and transition type
- FR4: System detects git commits made by the agent during a session
- FR5: System returns what the agent produced (commits, documents) after session completes

### Turn Management

- FR6: System assigns sequential turn numbers starting from 1
- FR7: Each turn is labeled with its transition type (init, coding, etc.)
- FR8: Logs and artifacts are named by turn number and transition type
- FR9: User can reference a specific turn by number for operations

### State Management

- FR10: User can rewind repository to a specific previous turn's commit
- FR11: User can restart agent execution from a rewound state with fresh context
- FR12: System tracks which commits were made by agent vs user

### Loop Orchestration

- FR13: User can run a predefined trivial loop (Init → Coding → Coding...)
- FR14: User can define which prompt to run next based on previous results
- FR15: Loop terminates when state machine reaches a terminal state (no exits)
- FR16: User can interrupt a running loop
- FR17: User can manually set the state machine to a specific state after interruption
- FR18: User can configure maximum turns to limit loop execution

### CLI Interface

- FR19: User can run afk in interactive mode with menus for exploration
- FR20: User can run afk in headless mode with flags for automation
- FR21: User can specify configuration via command-line flags
- FR22: User can persist default configuration in `.afk` project file
- FR23: Command-line flags override `.afk` file settings

### Project Setup

- FR24: User can clone the afk repo and run it directly
- FR25: User can scaffold a new project with predefined prompt locations
- FR26: System provides Init and Coding prompts as starting templates

## Non-Functional Requirements

### Performance

- NFR1: Framework overhead is negligible compared to LLM latency (framework should never be the bottleneck)

### Integration

- NFR2: System gracefully handles Claude Code CLI unavailability (clear error message)
- NFR3: System adapts to Claude Code CLI output format changes with minimal code changes (driver abstraction)
- NFR4: System does not depend on specific Claude Code CLI version beyond documented minimum

### Reliability

- NFR5: System recovers cleanly from interrupted sessions (Ctrl+C leaves no orphan processes)
- NFR6: System preserves all logs and state even if session crashes mid-turn
- NFR7: System never corrupts git repository state (worst case: uncommitted changes, not broken repo)
- NFR8: On unrecoverable error during a turn, system rewinds to last committed state and halts cleanly

### Maintainability

- NFR9: Adding a new transition type requires changes to < 3 files
- NFR10: Codebase is small enough for a single developer to hold in head (target: < 1000 LOC core)

### Replayability

- NFR11: System supports replaying from any previous turn state without side effects (rewind and retry is a core workflow)

