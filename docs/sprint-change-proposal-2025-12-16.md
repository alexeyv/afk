# Sprint Change Proposal - 2025-12-16

**Project:** afk
**Author:** Alex (via SM Agent)
**Status:** APPROVED
**Scope:** Major - Fundamental replan

---

## Section 1: Issue Summary

### Problem Statement

During Story 3.1 implementation (Session Naming and Turn Tagging), it became clear that:

1. **The tag-based design makes dedicated rewind/restart features unnecessary.** Checkout a tag, branch, start new session. That's git, not framework code.

2. **The driver has never been validated.** Zero tracer bullets. No confidence it actually works.

3. **The PRD scope drifted toward framework complexity** (state machines, CLI, interactive menus) when the real need is a **simple library for executing turns**.

4. **MVP exit criterion was unclear.** New clarity: recreate Anthropic demo with git-recorded history.

### Discovery Context

- **Triggering story:** 3.1 (Agent vs User Commit Tracking, renamed to Session Naming and Turn Tagging)
- **When discovered:** Mid-sprint, during implementation
- **Category:** Strategic pivot + requirements misunderstanding

### Evidence

1. Story 3.1 proves tags work — rewind is just `git checkout afk-{session}-{N}`
2. Driver code exists but has never run against real Claude Code CLI
3. PRD had 26 FRs, 6 epics — now reduced to 12 FRs, 5 epics
4. Anthropic quickstart is simple loops, not state machine frameworks

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Original | New Status |
|------|----------|------------|
| Epic 1: Core Prompt Execution | Done | **Unchanged** |
| Epic 2: Turn Tracking & Session | Done | **Unchanged** |
| Epic 3: State Recovery & Rewind | In Progress | **Done** (3.1 complete, 3.2/3.3 obsolete) |
| Epic 4: State Machine Orchestration | Backlog | **Deleted** — out of scope |
| Epic 5: CLI & Configuration | Backlog | **Deleted** — out of scope |
| Epic 6: Project Setup & Templates | Backlog | **Deleted** — replaced |
| **NEW** Epic 4: Tracer Bullet | — | **Added** — validate driver |
| **NEW** Epic 5: Demo Recreation | — | **Added** — MVP exit criterion |

### Story Impact

**Obsolete stories (removed):**
- 3.2: Rewind to Previous Turn — git checkout handles this
- 3.3: Restart from Rewound State — new session handles this
- 4.1-4.5: All State Machine stories (5 stories)
- 5.1-5.4: All CLI stories (4 stories)
- 6.1-6.4: All Setup & Templates stories (4 stories)

**New stories (added):**
- 4.1: Tracer Bullet — Hello World Session
- 5.1: Multi-Turn Demo Session
- 5.2: README & Getting Started

**Net change:** 17 stories removed, 3 stories added = **14 fewer stories**

### Artifact Conflicts

| Artifact | Impact | Changes Required |
|----------|--------|------------------|
| PRD | Major | Rewrite scope, FRs (26→12), remove CLI sections |
| Architecture | Major | Remove CLI decision, simplify structure, update validation |
| Epics | Major | Delete Epics 4-6, add new 4-5, mark 3 done |
| Sprint Status | Major | Reset with new epic structure |
| Project Context | Moderate | Update core concept, structure |
| Domain Model | Minor | Header terminology update |

### Technical Impact

**Code changes:** None required for scope change. Existing code (Epics 1-2, Story 3.1) remains valid.

**Files to NOT create:**
- `cli.py` — no CLI
- `machine.py` — no state machine
- `transition.py` — no transitions
- `revision.py` — no revision tracking beyond git
- `commit.py` — outcome parsing stays in git.py

**Files to create (future epics):**
- `examples/tracer_bullet.py`
- `examples/prompts/hello_world.md`
- `examples/anthropic_demo.py`

---

## Section 3: Recommended Approach

### Selected Path: PRD MVP Redefinition

**Rationale:**
- Epics 1-2 and Story 3.1 are solid foundation — no wasted work
- Removing Epics 4-6 dramatically reduces scope
- New Epics 4-5 (Tracer Bullet + Demo) are small and prove value
- Clear exit criterion: "Recreate Anthropic demo with git history"

### Effort Estimate: Low
- Document updates: ~1 hour
- Tracer Bullet (Epic 4): ~2-4 hours
- Demo Recreation (Epic 5): ~4-8 hours

### Risk Assessment: Low
- Removing scope, not adding
- Existing code unaffected
- Driver risk addressed explicitly with tracer bullet

### Timeline Impact
- **Faster to MVP** — fewer stories, clearer goal
- Original: 6 epics, 23+ stories
- New: 5 epics, 14 stories (Epics 1-3 done = 11 stories complete)
- Remaining: 3 stories

---

## Section 4: Detailed Change Proposals

### 4.1 PRD Changes

1. **Executive Summary:** "State machine framework" → "Library for autonomous coding turns"
2. **Classification:** "CLI Tool" → "Python Library"
3. **MVP:** Remove CLI, add tracer bullet + demo recreation
4. **Functional Requirements:** 26 → 12 FRs
5. **Non-Functional Requirements:** 11 → 8 NFRs
6. **Delete:** CLI Tool Requirements section entirely
7. **Update:** Phased Development with tracer bullet strategy

### 4.2 Architecture Changes

1. **CLI Decision:** "click" → "No CLI - library only"
2. **Project Structure:** Remove cli.py, machine.py, etc.
3. **Requirements Mapping:** Update to new 12 FRs
4. **Validation:** Note driver gap, tracer bullet as fix
5. **Confidence:** "High" → "Medium-High (driver untested)"

### 4.3 Epics Changes

1. **Epic 3:** Rename, mark done, obsolete 3.2/3.3
2. **Epic 4:** DELETE State Machine → NEW Tracer Bullet
3. **Epic 5:** DELETE CLI → NEW Demo Recreation
4. **Epic 6:** DELETE entirely
5. **FR Coverage Map:** Update to new FRs

### 4.4 Sprint Status Changes

1. Reset development_status with new epic structure
2. Add scope change note with date reference

### 4.5 Project Context Changes

1. Core concept: "state machine executor" → "library for turns"
2. Structure: Remove deleted files, add examples/

### 4.6 Domain Model Changes

1. Header: "framework" → "library"
2. Add update timestamp

---

## Section 5: Implementation Handoff

### Scope Classification: Major

This is a fundamental replan requiring PM/Architect-level decisions. However, the changes are **scope reduction**, not expansion, so implementation risk is low.

### Handoff Plan

| Role | Responsibility |
|------|----------------|
| **Alex (User)** | Approve proposal, apply document changes |
| **SM Agent** | Generate this proposal, assist with document updates |
| **Dev Agent** | Implement Epic 4 (Tracer Bullet), Epic 5 (Demo Recreation) |

### Success Criteria

1. All 15 document edits applied cleanly
2. Sprint status reflects new epic structure
3. Epic 4 (Tracer Bullet) validates driver works
4. Epic 5 (Demo Recreation) proves MVP value
5. README demonstrates working example

### Next Steps

1. **Immediate:** Apply all document changes (SM or user)
2. **Next sprint work:** Epic 4 — Tracer Bullet (Story 4.1)
3. **Then:** Epic 5 — Demo Recreation (Stories 5.1, 5.2)
4. **MVP complete:** When README shows working Anthropic demo recreation

---

## Approval

**Proposal Status:** ✅ APPROVED

**Changes Summary:**
- 17 stories removed
- 3 stories added
- 6 epics → 5 epics (3 done, 2 new)
- 26 FRs → 12 FRs
- CLI tool → Python library

**User Approval:** Alex

**Date:** 2025-12-16

**Implementation Status:** All document changes applied
