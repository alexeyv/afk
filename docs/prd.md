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

afk is a Python library for running autonomous coding agent turns. At its core: `session.execute_turn(prompt)` sends a prompt to Claude Code CLI, streams output, and returns what the agent produced (a git commit with outcome).

The insight: Claude Code CLI on Claude Max ($100/month flat rate) makes extended autonomous coding economically viable. But there's no minimal harness to run prompts and track what happened. afk handles the plumbing—you write whatever loop or state machine logic you want on top.

Git is the database. Each turn produces a commit. Git tags mark turn boundaries. Rewind = checkout a tag and branch. The framework is stateless—everything it needs is in git.

### What Makes This Special

- **Simple core** - `session.execute_turn(prompt) → TurnResult`. You decide what to run next.
- **Git as source of truth** - Every turn tagged. Full history. Rewind by checkout.
- **Transparent execution** - Real-time streaming, logging, full observability.
- **Flat-rate economics** - Runs on Claude Max via Claude Code CLI, not metered API calls.
- **Library, not framework** - No state machine abstraction. No CLI. Just turns.

## Project Classification

**Technical Type:** Python Library
**Domain:** General (developer tooling)
**Complexity:** Low
**Project Context:** Greenfield - new project

Target users are experienced developers with Claude Max subscriptions who want to run autonomous coding turns without building the execution plumbing themselves. Loop logic, state machines, orchestration—that's user code, not library concern.

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

1. `session.execute_turn(prompt) → TurnResult` with real-time streaming and logging
2. Git commit detection with outcome extraction from commit message
3. Git tagging of session start and turn boundaries (rewind = checkout tag + branch)
4. Tracer bullet: trivial 1-turn session proves driver works end-to-end
5. Demo recreation: reproduce Anthropic autonomous-coding quickstart with full git history
6. README that makes developers want to try it

### Growth Features (Post-MVP)

- Structured commit message schema enforcement (beyond basic outcome parsing)
- Pre-commit hooks for invariant validation
- Additional example experiments

### Vision (Future)

- Dependency-graph walking experiments (lifecycle and cooperation graphs)
- Context scoping (graph-neighborhood, ~2 layers)
- Escalation logic (agent signals "I need help")

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

## Project Scoping & Phased Development

### MVP Strategy

**Approach:** Tracer bullet MVP - prove the core works end-to-end before anything else. Session executes turn, driver talks to Claude, commit comes back with outcome.

**Resource:** Solo project. Scope must stay minimal.

### MVP Feature Set (Phase 1)

1. `session.execute_turn(prompt) → TurnResult` with real-time streaming
2. Git commit detection with outcome extraction
3. Git tagging of session and turn boundaries
4. Tracer bullet validation (1-turn hello world session)
5. Demo recreation (Anthropic quickstart with git history)
6. README that makes developers want to try it

### Post-MVP Features (Phase 2)

- Pre-commit hooks for commit format enforcement
- Structured commit schema beyond basic outcome
- Additional example experiments

### Vision (Phase 3)

- Dependency-graph walking experiments (lifecycle and cooperation graphs)
- Context scoping (graph-neighborhood, ~2 layers)
- Escalation logic (agent signals "I need help")

### Risk Assessment

**Technical Risks:**
- Claude Code CLI changes - mitigate by keeping driver abstraction clean
- Driver never actually tested - mitigate with tracer bullet as first priority

**Market Risks:** N/A - personal experimentation tool

**Resource Risks:** Solo project - scope creep was the main danger. Now fixed.

## Functional Requirements

### Prompt Execution

- FR1: User can execute a prompt against Claude Code CLI and receive structured results
- FR2: User can observe agent output in real-time as it streams to terminal
- FR3: System logs agent session to a file identified by session name and turn number
- FR4: System detects git commits made by the agent during a turn
- FR5: System returns TurnResult with outcome, message, and commit hash

### Session & Turn Management

- FR6: User can create a named Session in a git repository
- FR7: System tags session start as `afk-{session_name}-0`
- FR8: System assigns sequential turn numbers starting from 1
- FR9: System tags each completed turn as `afk-{session_name}-{turn_number}`
- FR10: User can checkout any turn tag to rewind (standard git operation)

### Project Setup

- FR11: User can clone the afk repo and import the library
- FR12: System provides example prompts demonstrating outcome signaling

## Non-Functional Requirements

### Performance

- NFR1: Library overhead is negligible compared to LLM latency

### Integration

- NFR2: System gracefully handles Claude Code CLI unavailability (clear error message)
- NFR3: Driver abstraction isolates CLI interface changes
- NFR4: No dependency on specific Claude Code CLI version beyond documented minimum

### Reliability

- NFR5: Clean interrupt handling (Ctrl+C leaves no orphan processes)
- NFR6: Logs preserved even if session crashes mid-turn
- NFR7: Never corrupts git repository state (worst case: uncommitted changes, not broken repo)

### Maintainability

- NFR8: Codebase small enough for single developer to hold in head (target: < 500 LOC core)

