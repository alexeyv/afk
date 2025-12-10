---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - /Users/alex/src/claude-quickstarts/autonomous-coding/project_inception.md
  - /Users/alex/src/claude-quickstarts/autonomous-coding/implementation_plan.md
  - /Users/alex/src/claude-quickstarts/autonomous-coding/agent.py
  - /Users/alex/src/claude-quickstarts/autonomous-coding/client.py
  - /Users/alex/src/claude-quickstarts/autonomous-coding/prompts/initializer_prompt.md
  - /Users/alex/src/claude-quickstarts/autonomous-coding/prompts/coding_prompt.md
workflowType: 'product-brief'
lastStep: 2
project_name: 'afk'
user_name: 'Alex'
date: '2025-12-09'
---

# Product Brief: afk

**Date:** 2025-12-09
**Author:** Alex

---

## Executive Summary

AFK is an experimentation framework for autonomous coding agent loops. Rather than prescribing a fixed workflow, it provides well-factored scaffolding - a Python state machine that orchestrates Claude Code CLI sessions through configurable states (initialization, coding, review, human checkpoints).

The key enabler: Claude Code CLI runs on Claude Max subscriptions ($100/month flat rate), not metered API calls. This makes extended autonomous coding sessions economically viable, opening up experimentation that would otherwise cost $50-200+ per run via API.

The goal is to enable rapid experimentation with different feedback loop shapes, moving beyond the naive "static test list → tick boxes" pattern toward adaptive, reflective autonomous coding workflows.

---

## Core Vision

### Problem Statement

Current autonomous coding approaches assume perfect upfront knowledge: define all features and tests, then execute linearly. This mirrors waterfall methodology and fails for the same reasons - requirements evolve, discoveries happen mid-build, and the "source of truth" becomes a fiction.

### Problem Impact

The existing bash-based prototype demonstrates the concept works but is:

- **Opaque** - Agent reasoning buried in logs, no real-time observability
- **Rigid** - Adding new workflow steps means hacking a while-loop
- **Stateless** - No formal tracking of "where are we" beyond file existence checks
- **Brittle** - Human intervention via Ctrl+C is fragile and error-prone

Additionally, the metered API model makes extended autonomous coding sessions economically impractical for many developers. A 10-hour autonomous coding run could cost $50-200+ in API calls, creating a barrier to experimentation.

### Why Existing Solutions Fall Short

The current demo works but isn't designed for experimentation. Changing the loop shape requires rewriting, not configuring. It's a proof-of-concept, not a lab bench.

### Proposed Solution

A Python state machine framework that makes the loop explicit and extensible.

**The core insight:** Instead of a bash `while true` loop with hidden control flow, you get:

```python
while not done(repo):
    transition(repo)  # agent session: reads state, does work, commits
    # state is now the new commit
```

**State = the repo.** Each commit is a state snapshot. Git history is transition history. No separate state tracking - Git already does it.

**Transitions = agent sessions.** An agent reads the current state (repo contents), does work, commits. The commit *is* the state change.

When you want to add a review step, you add a transition. The loop just orchestrates which transition runs next.

**MVP scope:** The trivial loop (init transition → coding transition → coding transition → ...) - just well-factored. The scaffolding makes adding transitions trivial; it doesn't ship with transitions we haven't validated.

**The framework provides:**

- Orchestration of Claude Code CLI sessions as transitions
- Git as the state store (commits = state snapshots)
- Real-time observability (streaming output, structured logs)
- Easy transition addition/modification for experimentation
- Clean driver abstraction (loop doesn't know it's talking to Claude Code CLI specifically)

**Not in MVP:** Review transitions, human checkpoint transitions, escalation logic. These are future experiments enabled by the scaffolding.

### Design Principles (First Principles)

Built from fundamental truths about LLMs and autonomous coding:

1. **LLMs have limited context windows** - Sessions must end; state must persist externally
2. **LLMs produce plausible garbage at scale** - Unconstrained autonomy is a losing strategy; the question is where to checkpoint
3. **Claude Code CLI on Max is the economic enabler** - Driver abstraction is insurance against platform changes
4. **Developers understand loops** - No hidden magic; the code IS the documentation
5. **Experimentation requires low friction** - If adding a state takes an hour, nobody experiments; if it takes 5 minutes, they will

**Core success metrics:**
- How easy is it to add a new state? That's the UX that matters.
- Is the README not just clear, but *engaging*? This is a tool for curious developers - it should make them want to try it.
- Can someone else clone, run, and understand what's happening without reading the source?
- Is the CLI a pleasure to use? Two modes: interactive menus for exploration (guiding choices, not overwhelming), AND headless with flags for automation/scripts. Both matter.

### Competitive Landscape

Evaluated existing autonomous agent frameworks:

- **[OpenHands](https://github.com/OpenHands/OpenHands)**: 5,600+ commits, enterprise platform with cloud deployment, React frontend, Docker infrastructure. Orders of magnitude more complex than needed.
- **[Swarm](https://github.com/openai/swarm)**, **[CrewAI](https://crewai.com)**, **[AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)**: All built around API calls to LLMs, not interactive CLI sessions. Can't easily adapt to Claude Code CLI's PTY/session model.
- **Tutorial content**: Mostly SEO-optimized content marketing for consulting gigs, not production-tested code.

**Conclusion:** No minimal, cloneable project exists that wraps Claude Code CLI with a state machine. The existing demo code (`agent.py`, `client.py`) is the starting point - needs cleanup into explicit state machine shape. Estimated ~500 lines of Python.

### Key Differentiators

- **No API costs** - Runs on Claude Max subscription via Claude Code CLI, not metered API calls
- **Git is the state store** - Commits are state snapshots; structured commit messages are the agent's lab notebook
- **Lab bench, not prescription** - Framework for experimenting with loop shapes, not a fixed workflow
- **Transitions, not states** - States are repo contents; transitions are agent sessions that transform state via commits
- **Observable by design** - Agent reasoning lives in Git history, not separate logs
- **Built on Claude Agent SDK** - Native orchestration of Claude Code CLI sessions

---

## Target Users

### Primary Users

**Segment A: The Skeptical Practitioner**

Developers with real LLM-assisted coding experience who've learned the hard way that autonomous = tech debt. They're deeply suspicious of "let it cook" approaches and won't let Claude run for more than 2 minutes without review.

**Profile:**
- Has used Cursor, Claude Code, Copilot extensively in production
- Knows that LLMs left unchecked produce plausible-looking garbage
- Already has Claude Max subscription
- Comfortable with Python and CLI tools

**Root Motivation (5 Whys):**
Not "I don't want to code" but **"I want to think at a higher level while the AI handles the lower level."** They want leverage - to operate as technical director, not typist.

**What they actually want:**
- Tighter feedback loops, not longer ones
- Adversarial review baked into the process
- Clear escalation signals before things go off-rails
- A lab to experiment with **constraining** autonomy intelligently
- The question they're asking: *"Can we make autonomous loops that don't produce garbage?"*

**Current Experience:**
- Manually babysitting Claude Code sessions (exhausting context-switching)
- Writing one-off scripts that aren't reusable
- Limiting exploration because tooling friction is too high

**Success Looks Like:**
- Operate as technical director - think at architecture/strategy level while Claude handles implementation
- Right-level engagement - step in for steering decisions, not rubber-stamping every action
- Trivially add/modify states (reviewer, checkpoint) without rewriting the loop
- Leave it running, come back to meaningful progress or a clear "I need help" signal

---

**Segment B: The Enthusiast (Education Path)**

Developers who've seen the "built a SaaS in 10 minutes" viral demos and want to try autonomous coding. Rather than letting them fail and blame the tool, afk should steer them toward appropriate human-in-the-loop patterns.

**Profile:**
- Excited about autonomous coding potential
- Limited experience with LLM failure modes at scale
- Will discover the tech debt problem firsthand if left unconstrained

**How afk should serve them (future considerations beyond MVP):**
- Sensible defaults: review steps and checkpoints enabled out of the box
- Visible feedback: see what the adversarial reviewer catches, learn the failure patterns
- Progressive trust: loosen constraints intentionally as understanding grows
- Education through structure, not failure

*Note: These are design principles for future development. MVP scope is the scaffolding that enables building toward these patterns.*

### Secondary Users

N/A for MVP - single-user experimentation tool.

### User Journey

1. **Discovery:** Finds afk while exploring autonomous coding tools (or learns the hard way that raw loops = tech debt)
2. **Onboarding:** Clones repo, has Claude Max, runs the harness on a test project
3. **First Value:** Watches Claude work autonomously with review checkpoints - sees both progress and catches
4. **Experimentation:** Modifies states, adjusts checkpoint frequency, tries different loop shapes
5. **Integration:** Becomes their go-to harness for controlled autonomous coding experiments

### Future Consideration: BMAD Integration

afk may eventually become a module within the BMAD ecosystem. Three potential paths were considered:

1. **BMAD Workflow** (`/bmad:bmm:workflows:autonomous-coding`) - Deep integration, speaks BMAD artifact language
2. **BMAD Agent** (`bmm:agents:autonomous-coder`) - Lives alongside analyst, architect, dev agents
3. **Standalone but BMAD-compatible** - Independent tool that can consume BMAD artifacts

**Decision: Scenario 3 for MVP** - Stay standalone but design clean interfaces:
- State machine reads a generic "task" format (could be BMAD story, could be anything)
- Outputs are standard artifacts (commits, PRs, status files)
- No BMAD-specific dependencies in core
- Later integration paths remain open without coupling now

### Future Direction: Context Scoping

A key evolution beyond MVP: controlling what each agent/state *sees*, not just what it *does*.

**The problem:** If every agent sees the same context, they converge on the same conclusions. An "adversarial reviewer" that read the coder's reasoning just rubber-stamps it.

**The solution (future):** Information asymmetry by design. Each state declares its context:
- Coder sees: full repo, current story, feature list
- Reviewer sees: last commit diff, story spec, test results (NOT coder's reasoning)

**For MVP:** Not implemented. But worth noting that the framework may eventually need an abstraction for "what an agent sees" - context scoping as a first-class concept.

---

## Architecture Decision Records

### ADR-001: Build vs Clone

**Decision:** Build from existing demo code, not fork/clone an existing framework.

**Context:** Evaluated OpenHands, Swarm, CrewAI, AutoGPT, and various tutorials.

**Rationale:**
- Existing frameworks are orders of magnitude more complex than needed
- All are built around LLM API calls, not interactive CLI sessions
- Claude Code CLI requires PTY/session management that doesn't fit their architecture

**Consequences:** More control, less baggage. Must build state machine ourselves (~500 lines). No community/ecosystem to lean on.

---

### ADR-002: Claude Code CLI via Agent SDK

**Decision:** Use Claude Agent SDK to drive Claude Code CLI, not direct API calls.

**Context:** Could call Anthropic API directly, or wrap Claude Code CLI.

**Rationale:**
- Claude Code CLI runs on Max subscription (flat rate)
- API calls are per-token (expensive for long-running experiments)
- Agent SDK provides session management, PTY handling, streaming

**Consequences:** Dependent on Claude Code CLI continuing to exist. Must maintain driver abstraction as insurance. Unlocks flat-rate autonomous experiments.

---

### ADR-003: Git as the Agent's Lab Notebook

**Decision:** Git is the state store AND the observability layer. Structured commit messages are first-class.

**Context:** Could build custom state persistence and logging, or use Git for both.

**Rationale:**
- Each commit = a state snapshot
- Commit history = transition history
- Diff between commits = what a transition did
- Current working tree = current state
- Git already solves persistence, history, branching, rollback
- **Structured commit messages encode agent reasoning** - not just what changed, but what the agent was trying to do, what it decided, what it's uncertain about

**Commit message schema example:**
```
[CODING] Implemented user auth flow

CHANGES: Added login/logout endpoints, JWT middleware
TESTS: 3 passing, 2 new failures (session timeout edge cases)
CONFIDENCE: High on core flow, uncertain on token refresh
DEFERRED: Rate limiting (out of scope for this story)
NEXT: Fix session timeout tests
```

**Why this matters:**
- A review transition (or human) can read the log and understand *what the agent was thinking*
- Enables debugging why it went off the rails
- Trains you on agent failure modes
- Future transitions can read previous commits to make smarter decisions
- Git isn't just version control - it's the agent's lab notebook

**Documentation artifacts as state:**

Transitions don't just produce code - they produce documentation:
- Review transition → `review-findings.md`
- Address-review transition → code changes + `review-response.md`
- All committed to Git

These artifacts are three things at once:
1. **State** - influences what the next transition does
2. **Short-lived context** - needs archiving after it's served its purpose (out of agent's active context)
3. **Experimentation record** - the permanent log for post-run analysis

Archive isn't cleanup - it's science. The archived docs are experiment results you analyze to form opinions about what works.

**Consequences:** Agents must commit with structured messages. The schema is part of the experiment (what metadata is useful?). Observability comes from Git, not a separate logging system. Documentation artifacts are first-class state with a lifecycle (active → archived).

---

### ADR-004: Explicit Loop with Transitions

**Decision:** Loop structure must be explicit in code. Transitions transform state, not "execute states."

**Context:** Current demo uses implicit while-loop in Python.

**Rationale:**
- States are project artifacts (repo at a point in time)
- Transitions are agent sessions that mutate state
- "Make the loop obvious" is the core product insight
- `while not done: state = transition(state)` is the whole thing

**Consequences:** Transitions are first-class. Each transition is an agent run that reads state, does work, commits. The loop just orchestrates transitions.

---

### ADR-005: MVP is the Trivial Loop

**Decision:** MVP ships with INIT → CODING → CODING → ... only.

**Context:** Could build REVIEW, HUMAN_CHECKPOINT, etc. upfront.

**Rationale:**
- Don't ship states we haven't validated
- Scaffolding makes adding states trivial
- Experimentation will reveal which states matter

**Consequences:** MVP is minimal but complete. Future states are experiments, not features. Avoids premature abstraction.

---

### ADR-006: Dual-Mode CLI

**Decision:** CLI supports both interactive menus AND headless flags.

**Context:** Could do one or the other.

**Rationale:**
- Interactive for exploration/onboarding
- Headless for automation/scripts
- Both are real use cases

**Consequences:** Slightly more CLI code. Better UX for both modes. First impression matters.

---

### ADR-007: Generic Task Format

**Decision:** State machine reads generic "task" input, not BMAD-specific.

**Context:** Could tightly couple to BMAD story format.

**Rationale:**
- Standalone but BMAD-compatible (Scenario 3)
- Clean interfaces enable future integration
- No BMAD dependencies in core

**Consequences:** Must define task format. BMAD integration is a wrapper, not core. Other inputs possible (plain markdown, JSON, etc.).

---

## Success Metrics

### User Success (Scaffolding Phase)

**Primary objective:** Run experiments with autonomous coding loops and develop informed opinions based on personal experience.

Not "the loop works perfectly" but "I learned what works and what doesn't."

Success looks like:
- Ran multiple experiments with different loop shapes
- Have data points: "Review every commit worked better than review every 5"
- Have anecdotes: "It went off the rails here, stopped correctly there"
- Formed opinions about where HITL checkpoints belong
- Ready to build the next iteration based on what was learned

### Business Objectives

N/A - experimentation scaffold, not a product.

### Key Performance Indicators

For the scaffolding itself:

- **Time to add a new state:** < 10 minutes
- **Time from clone to first run:** < 5 minutes
- **Experiments run:** Have I actually used this to try things?
- **Opinions formed:** Can I now articulate what works and why?

---

## MVP Scope

### Core Features

1. **The loop** - Explicit orchestration: `while not done(repo): transition(repo)`
2. **Two transitions** - Init (creates feature list + tests) and Coding (makes tests green, commits)
3. **Git as state store** - Each transition commits; structured commit messages with schema
4. **Claude Code CLI driver** - Via Agent SDK, wrapping existing demo code
5. **Real-time streaming** - See agent output as it happens
6. **Dual-mode CLI** - Interactive menus for exploration, headless flags for automation
7. **Engaging README** - Makes developers want to try it

### Out of Scope for MVP

- Review transitions
- Human checkpoint transitions
- Automatic escalation/stop logic (beyond max iterations)
- Context scoping (controlling what each transition sees)
- Documentation artifact archiving
- Custom state schemas (use demo's feature list pattern)
- BMAD integration
- Web dashboard

### What's Experimental (varies per run)

- The commit message schema (what metadata is useful?)
- Transition prompts (what instructions work?)
- State schema (feature list? stories? something else?)
- Stop conditions (iteration count? test status? agent signal?)

### MVP Success Criteria

- Can run the trivial loop end-to-end
- Can add a new transition in < 10 minutes
- Git history shows structured commits with agent reasoning
- Someone else can clone and run in < 5 minutes
- After running experiments, have informed opinions about autonomous loops
