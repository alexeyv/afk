# Story 1.3: Commit Detection and Result Extraction

Status: Done

## Story

As a framework user,
I want the framework to detect commits made during execution and return structured results,
so that I know what the agent produced.

## Acceptance Criteria

1. **Given** a prompt execution that results in exactly one commit
   **When** the driver completes
   **Then** I receive a `TurnResult` with outcome, message, and commit_hash
   **And** the outcome is extracted from the `outcome:` footer

2. **Given** a prompt execution completes
   **When** I check for commits made during execution
   **Then** the framework compares HEAD before and after execution
   **And** identifies all commits made in that window

3. **Given** the agent made a commit with footer `outcome: success`
   **When** result extraction runs
   **Then** `TurnResult.outcome` equals "success"
   **And** `TurnResult.message` contains the full commit message
   **And** `TurnResult.commit_hash` is the SHA of the commit

## Tasks / Subtasks

- [x] Task 1: Create `TurnResult` dataclass (AC: #1, #3)
  - [x] 1.1: Create `afk/turn_result.py` with frozen dataclass
  - [x] 1.2: Fields: `outcome: str`, `message: str`, `commit_hash: str`
  - [x] 1.3: Export from `afk/__init__.py`

- [x] Task 2: Implement commit detection logic (AC: #2)
  - [x] 2.1: Create function to capture HEAD before execution
  - [x] 2.2: Use existing `git.commits_between()` to find new commits after execution
  - [x] 2.3: Handle edge case: no prior commits (None as `before`)

- [x] Task 3: Integrate result extraction with Driver (AC: #1, #3)
  - [x] 3.1: Create `execute_turn()` orchestration function in `afk/executor.py` (Option B per Dev Notes)
  - [x] 3.2: Capture HEAD before calling Claude Code
  - [x] 3.3: After process exits, get HEAD after and find commits between
  - [x] 3.4: For exactly one commit: parse outcome via `git.parse_commit_message()`
  - [x] 3.5: Return `TurnResult` with extracted data

- [x] Task 4: Write tests (AC: all)
  - [x] 4.1: Test `TurnResult` dataclass frozen behavior
  - [x] 4.2: Test commit detection with one commit (happy path)
  - [x] 4.3: Test outcome extraction from commit message
  - [x] 4.4: Test with empty repo (no prior commits)

## Dev Notes

### Architecture Compliance

This story introduces `TurnResult`, the core result object defined in the architecture:

```python
@dataclass(frozen=True)
class TurnResult:
    outcome: str           # "success", "failure", or custom outcome
    message: str           # Full commit message
    commit_hash: str       # Git SHA
```

**Key architectural points:**
- Use `frozen=True` for immutability (per architecture: "all fields are immutable")
- File location: `afk/turn_result.py` (flat structure, one file per entity)
- No exception hierarchy—use `RuntimeError` with descriptive messages

### Implementation Pattern

The story establishes the pattern for extracting structured results from agent execution:

1. **Before execution:** Capture current HEAD (may be None for empty repos)
2. **During execution:** Agent runs, streams, commits
3. **After execution:**
   - Get new HEAD
   - Find commits between old and new HEAD via `git.commits_between()`
   - For single commit: parse message, extract outcome
   - Return `TurnResult`

### Dependencies on Completed Work

**Story 1.1 (done)** provided:
- `Git.head_commit()` - returns current HEAD or None
- `Git.parse_commit_message(hash)` - returns `(outcome, message)` tuple
- `Git.commits_between(before, after)` - returns list of commit hashes

**Story 1.2 (in review)** provided:
- `Driver.run(prompt, log_file)` - executes prompt, streams output, returns exit code

This story bridges these: wrap Driver execution with commit detection to produce `TurnResult`.

### Integration Design Choice

Two implementation options:

**Option A: Modify `Driver.run()` to return `TurnResult`**
- Pros: Single call does everything
- Cons: Couples driver to git operations, complicates error cases

**Option B: Create separate orchestration function**
- Pros: Clean separation, driver stays focused on execution
- Cons: Caller must coordinate

**Recommended: Option B** - Create a function (possibly in a new module or as a classmethod) that:
1. Takes driver + git instance
2. Captures HEAD before
3. Calls `driver.run()`
4. Captures HEAD after
5. Detects commits
6. Returns `TurnResult`

This preserves the flat architecture while keeping concerns separated. Story 1.4 will handle the exception cases (zero commits, multiple commits, process failures).

### What This Story Does NOT Cover

Per the epic breakdown, this story focuses on the **happy path** (exactly one commit):

**Covered here:**
- `TurnResult` dataclass
- Commit detection (HEAD before/after comparison)
- Outcome extraction from single commit
- Return structured result

**Deferred to Story 1.4 (Exception Handling):**
- Zero commits → raise `RuntimeError`
- Multiple commits → raise `RuntimeError`
- CLI not available → raise `RuntimeError`
- Process died unexpectedly → raise `RuntimeError`

For now, the implementation may simply assert exactly one commit and not handle exceptions gracefully—that's 1.4's job.

### Project Structure Notes

Current codebase structure:
```
afk/
├── __init__.py          # Exports public API
├── driver.py            # Driver class (Story 1.2)
├── git.py               # Git class (Story 1.1)
└── turn_result.py       # NEW: TurnResult dataclass (this story)
```

Files to create:
- `afk/turn_result.py` - TurnResult dataclass

Files to modify:
- `afk/__init__.py` - Export TurnResult
- Possibly `afk/driver.py` or new orchestration module

### Testing Strategy

Use real git repos in temp directories (like Story 1.1 likely does). No mocking of git operations—test against real git behavior.

Test scenarios:
1. Create temp git repo
2. Make a commit with `outcome: success` footer
3. Verify `TurnResult` contains correct outcome, message, hash
4. Test with no prior commits (initial commit scenario)

### References

- [Source: docs/architecture.md#result-object] - TurnResult specification
- [Source: docs/architecture.md#execution-model] - Normal operation flow
- [Source: docs/epics.md#story-13] - Story requirements
- [Source: afk/git.py] - Existing Git class methods
- [Source: afk/driver.py] - Existing Driver class

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5

### Debug Log References

N/A - implementation completed without issues

### Completion Notes List

- Created `TurnResult` frozen dataclass with `outcome`, `message`, `commit_hash` fields
- Implemented `execute_turn()` orchestration function following Option B (separate orchestration)
- Function captures HEAD before/after execution, detects commits, parses outcome
- Uses `DriverProtocol` for type safety without coupling to concrete Driver
- Happy path implementation with assert for exactly one commit (per Dev Notes, exception handling deferred to Story 1.4)
- All tests pass (41 passed, 2 skipped) - test suite covers frozen behavior, commit detection, outcome extraction, empty repo case

### File List

- `afk/turn_result.py` (new) - TurnResult dataclass
- `afk/executor.py` (new) - execute_turn() orchestration function
- `afk/__init__.py` (modified) - exports TurnResult and execute_turn
- `tests/test_turn_result.py` (new) - TurnResult unit tests
- `tests/test_executor.py` (new) - execute_turn integration tests

### Change Log

- 2025-12-10: Story 1.3 implemented - TurnResult dataclass and execute_turn orchestration function
- 2025-12-11: Code review completed (parallel reviews with custom deduplication - no formal review artifact generated)
