# Epic 1 Retrospective - Action Items

Generated: 2025-12-11

---

## Action Item 1: Resolved Review Findings Registry

**Problem Statement:**

During Epic 1 code reviews, the same findings kept recurring across stories - particularly around macOS `script` command not propagating exit codes/signals. Reviewers would flag "you should handle exit codes more carefully" 4-5 times, even though we'd already decided: commit presence = success, no commit = exception, check the log.

**Root Cause:**

Reviewers don't have visibility into previous architectural decisions. They rediscover the same "problems" that are actually intentional design choices.

**Solution:**

Create a registry of resolved review findings that the dedup step can filter against:

```
docs/resolved-review-findings.md

## Exit Code / Signal Handling on macOS

- **Finding pattern:** "exit codes not handled", "signal handling incomplete", "should check return codes"
- **Decision:** Commit presence is the success signal, not exit codes
- **Rationale:** macOS `script` command eats signals and doesn't propagate exit codes reliably
- **First resolved:** Epic 1, Story 1.4
- **Status:** Won't fix - intentional design
```

**Integration with Review Workflow:**

This registry feeds into the "Dedupe" phase of the multi-LLM review workflow (Action Item 2). After collecting findings from all reviewers, the dedup step:
1. Merges overlapping findings
2. Filters against resolved-review-findings.md
3. Presents remaining findings for human review

**Owner:** SM (create initial file, seed with exit code finding)

**Priority:** High - reduces review noise immediately

**Acceptance Criteria:**
- [x] Create `docs/resolved-review-findings.md`
- [x] Seed with macOS exit code/signal finding
- [x] Document format for adding new resolved findings
- [ ] Reference in review dedup workflow (when implemented)

**Status:** ✅ Complete (2025-12-13) - Created `docs/resolved-review-findings.md` with exit code finding and format documentation.

---

## Action Item 2: Domain Model Diagram

**Problem Statement:**

As the codebase grows, there's no visual reference for:
- Who owns whom (lifecycle relationships)
- Who calls whom (cooperation/dependency relationships)
- What state each entity holds

This makes it harder to onboard, reason about architecture, and prevent drift.

**Desired Output:**

A diagram (Excalidraw or Mermaid) showing:

1. **Entities:** `Git`, `Driver`, `TurnResult`, `execute_turn`, and upcoming `Turn`, `Session`

2. **Lifecycle ownership (who creates/destroys whom):**
   - e.g., `execute_turn` creates `TurnResult`
   - e.g., `Session` will own `Turn` instances

3. **Cooperation (who calls whom):**
   - e.g., `execute_turn` calls `Driver.run()` and `Git.head_commit()`
   - e.g., `Driver` calls subprocess (`script` + `claude`)

4. **State attributes per entity:**
   - `Git`: `repo_path`
   - `Driver`: `workspace`, `model`
   - `TurnResult`: `outcome`, `message`, `commit_hash` (frozen)
   - `Turn`: `turn_number`, `transition_type`, `result`, `log_file`, `timestamp` (frozen)

**Owner:** Architect or Tech Writer

**Priority:** Medium - valuable reference, not blocking

**Acceptance Criteria:**
- [x] Create domain model diagram in `docs/`
- [x] Show lifecycle ownership arrows
- [x] Show cooperation/call arrows
- [x] List state attributes for each entity
- [x] Update as Epic 2 entities are implemented

**Status:** ✅ Complete (2025-12-13) - Created `docs/domain-model.md` with Mermaid class diagram showing all 7 domain classes including Epic 2 entities (Turn, TurnLog, TransitionType, Session).

---

## Action Item 3: Quality Gate & Commit Step in Stories

**Problem Statement:**

Dev workflow currently has quality gate mentioned but not enforced as a final step with commit. Result: Alex has to spend a turn to get the commit done after reviewing.

**Desired State:**

Dev turn ends with commit already done. Flow is:
1. Implement all tasks
2. Run quality gate (ruff, pyright, pytest)
3. All must pass - if failures, fix and re-run
4. Commit with conventional commit message

**Solution:**

Add section to `project_context.md` with explicit dev workflow:

```markdown
## Dev Workflow: Quality Gate & Commit

Before marking a story complete, the dev agent MUST:

1. Run quality gate - ALL must pass:
   - `uv run ruff check afk/ tests/`
   - `uv run ruff format --check afk/ tests/`
   - `uv run pyright --threads`
   - `uv run pytest`

2. If any failures: fix issues and re-run from step 1

3. Commit with conventional commit message:
   - Format: `feat|fix|refactor|docs|chore: description`
   - Reference story number in commit body if helpful

4. Only then mark story tasks complete
```

**Owner:** SM (add to project_context.md, apply to future story creation)

**Priority:** High - saves turns, reduces friction

**Acceptance Criteria:**
- [ ] Add "Dev Workflow: Quality Gate & Commit" section to project_context.md
- [ ] Future stories reference this workflow in Dev Notes
- [ ] Dev turns end with commit, not pending commit

---

## Action Item 4: Enhanced Multi-LLM Code Review Workflow

**Problem Statement:**

Current code-review workflow is single-LLM, linear. During Epic 1, value was discovered in:
1. Running parallel reviews across different LLMs
2. Leveraging information asymmetry (reviewers without full story context find different issues)
3. Deduplicating and prioritizing findings from multiple sources

**Current Gap:**

- No workflow to fan-out reviews to multiple sources
- No mechanism to collect and dedupe findings
- Going off-workflow loses status tracking and traceability (Stories 1-2, 1-3, 1-4 had no formal review artifacts)
- Reviews requiring "fresh eyes" (no context) need shell wrapper invocation to isolate context

**Desired Capabilities:**

1. **Fan-out**: Invoke multiple review agents (different LLMs, different context levels)
2. **Collect**: Gather findings from all sources
3. **Dedupe**: Merge overlapping findings intelligently
4. **Integrate**: Feed external review findings into the standard workflow
5. **Track**: Maintain status transitions and artifacts regardless of review path

**Technical Considerations:**

- Some reviews need full context (story + code)
- Some reviews need information asymmetry (code only, no story context) → requires shell wrapper to prevent context leakage
- Cross-LLM invocation may need MCP or external orchestration
- Task tool doesn't exist in all LLMs

**Owner:** TBD (Architecture decision needed)

**Priority:** Medium - enhances quality process

---

## Process Learning: Off-Workflow Reviews Lose Traceability

**What Happened:**

Stories 1-2, 1-3, and 1-4 were reviewed using a custom parallel review process outside the standard `*code-review` workflow. The review work was thorough, but:
- Status remained stuck at `review` (workflow auto-marks `done` only if it runs to completion)
- No review artifacts were generated
- Change logs only have a one-liner noting reviews happened

**Lesson:**

When going off-workflow for good reasons (better quality), we lose:
- Automatic status transitions
- Review finding documentation
- Traceability of what was found and fixed

**Mitigation Applied:**

- Manually updated statuses to `done`
- Added notes to Change Logs documenting the gap
- Created this action item for workflow improvement
