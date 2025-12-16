# Story 3.1: Session Naming and Turn Tagging

Status: ready-for-dev

## Story

As a framework user,
I want each session to have a name and each turn to be tagged in git,
So that I can identify turn boundaries and rewind to any completed turn.

## Acceptance Criteria

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
   (Note: actual rewind implementation is Story 3.2; this story creates the tags)

## Tasks / Subtasks

- [x] Task 1: Add session name and tag session start (AC: #1, #2)
  - [x] Add `_name: str` to Session `__slots__`
  - [x] Add `name` parameter to `__init__` (required, positional after root_dir)
  - [x] Add `_validate_name()` static method:
    - Reject if not str
    - Reject if empty
    - Reject if length > 64 characters
    - Reject if not matching `^[a-zA-Z0-9_]+$` (alphanumerics and underscore only)
    - This ensures valid git tag names and simple, predictable session identifiers
  - [x] In `__init__`, after validation, initialize workspace:
    - Check if root_dir is a git repo via `git rev-parse --git-dir`
    - If NOT a git repo:
      - If directory is empty → `git init` + `git commit --allow-empty -m "afk: session {name} initialized"`
      - If directory has content → RuntimeError("Directory is not a git repo and not empty")
    - Get current HEAD via `self._git.head_commit()`
    - If None (empty repo but somehow no commit) → RuntimeError("Session requires at least one commit")
    - Tag HEAD as `afk-{name}-0` via `self._git.tag()` (uses pre-check)
    - If tag exists → RuntimeError (enforces unique session name per repo)
  - [x] Add `@property name` (read-only)
  - [x] Update `__repr__` to include name
  - [x] Add tests for all validation cases
  - [x] Add test: empty repo raises RuntimeError
  - [x] Add test: session creation tags HEAD as `afk-{name}-0`

- [ ] Task 2: Add Git methods for repo initialization and tagging (AC: #2)
  - [ ] Implement `is_repo() -> bool`
    - Use `git rev-parse --git-dir`, return True if exit code 0
  - [ ] Implement `init() -> None`
    - Use `git init`
  - [ ] Implement `commit_empty(message: str) -> str`
    - Use `git commit --allow-empty -m {message}`
    - Return the new commit hash
  - [ ] Implement `is_empty_directory() -> bool`
    - Check if repo_path has no files/subdirs (excluding .git)
  - [ ] Implement `tag_exists(name: str) -> bool`
    - Use `git tag -l {name}` and check if output is non-empty
  - [ ] Implement `tag(name: str, commit_hash: str) -> None`
    - First call `tag_exists(name)` — if True, raise RuntimeError with clear message
    - Then `git tag {name} {commit_hash}`
    - Raise RuntimeError if git command fails
  - [ ] Add tests for all new methods

- [ ] Task 3: Tag commit after turn completion (AC: #2)
  - [ ] In `Session.execute_turn()`, new flow:
    ```
    1. turn_number = allocate_turn_number()
    2. tag_name = f"afk-{self._name}-{turn_number}"
    3. if self._git.tag_exists(tag_name): raise RuntimeError(f"Tag already exists: {tag_name}")
    4. turn.start(turn_number, transition_type)
    5. exit_code = turn.execute(prompt)
    6. result = build_turn_result(turn, exit_code)  # inside try/except with turn.abort()
    7. _add_result(result)
    8. self._git.tag(tag_name, result.commit_hash)  # AFTER _add_result
    9. return result
    ```
  - [ ] Pre-check tag existence BEFORE turn.start() — fail fast, no wasted work
  - [ ] Tag AFTER _add_result() — if tagging fails, session still knows about the turn
  - [ ] Add integration test: execute turn, verify tag exists pointing to correct commit
  - [ ] Add test: pre-existing tag causes immediate RuntimeError before turn starts

- [ ] Task 4: Remove `resume_from` parameter from allocate_turn_number()
  - [ ] Delete `resume_from` parameter and all related logic
  - [ ] Simplify to just sequential allocation: return N, increment to N+1
  - [ ] Remove any tests for resume_from behavior
  - [ ] Rationale: Invalid for tagging design. MVP has no resume — start fresh sessions.

- [ ] Task 5: Update all existing tests
  - [ ] Update all Session instantiations to include name parameter
  - [ ] Use descriptive test names like "test_session" or similar

## Dev Notes

### Design Rationale

**Why tags instead of commit tracking?**
- Tags are permanent markers for "end of turn N"
- Git does the heavy lifting for history
- Rewind = `git checkout afk-{session}-{turn}` (trivial)
- Human commits between turns don't matter — framework only cares about turn boundaries
- No need to distinguish agent vs user commits explicitly

**Tag naming: `afk-{session_name}-{N}`**
- `afk-` prefix prevents collision with user tags
- Session name allows multiple sessions in same repo
- N gives chronological ordering

**Turn numbering (important):**
- Turn numbers are **1-indexed** (first turn is turn 1, not turn 0)
- **Tag 0** = session start (before any turns run)
- **Tag N** = end of turn N (where N >= 1)
- Example: `afk-experiment-0` (start), `afk-experiment-1` (end of turn 1), `afk-experiment-2` (end of turn 2)

### Session Name Validation

```python
import re

@staticmethod
def _validate_name(name: str) -> None:
    if not isinstance(name, str):
        raise TypeError(f"expected str for name, got {name!r}")
    if not name:
        raise ValueError("name cannot be empty")
    if len(name) > 64:
        raise ValueError("name cannot exceed 64 characters")
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValueError("name must contain only alphanumerics and underscores")
```

### Git Tagging Implementation

```python
def tag_exists(self, name: str) -> bool:
    """Check if a tag with the given name exists."""
    output = self._run("tag", "-l", name)
    return bool(output.strip())

def tag(self, name: str, commit_hash: str) -> None:
    """Create a lightweight tag pointing to the specified commit.

    Raises RuntimeError if tag already exists (checked before attempting).
    """
    if self.tag_exists(name):
        raise RuntimeError(f"Tag already exists: {name}")
    self._run("tag", name, commit_hash)
```

### Architecture Compliance

From project-context.md:
- **`__slots__`**: Add `_name` to Session's `__slots__`
- **Domain validation at boundaries**: Validate name in constructor
- **No assert statements**: Use explicit runtime checks
- **KeyError/ValueError take values**: `raise ValueError("name cannot be empty...")`

From architecture.md:
- **Flat structure**: Changes go in `session.py` and `git.py`
- **Git-centric model**: Tags are first-class git objects — fits the model perfectly

### File Structure Requirements

| File | Changes |
|------|---------|
| `afk/session.py` | Add `_name` slot, validation, property, tagging in execute_turn |
| `afk/git.py` | Add `tag()` method |
| `tests/test_session.py` | Add name validation tests, update all Session instantiations |
| `tests/test_git.py` | Add tag() tests |

### Testing Requirements

- **No mocks**: Use real git operations with tmp_path fixture
- **pytest's tmp_path**: Never hardcode paths

Test cases needed:
1. Session rejects empty name
2. Session rejects name with spaces (`"my session"`)
3. Session rejects name with special chars (`"test:1"`, `"test-1"`, `"test.1"`)
4. Session rejects name longer than 64 characters
5. Session accepts valid name (alphanumerics + underscore, <= 64 chars), accessible via property
6. Empty directory → git init + empty commit + tag `afk-{name}-0`
7. Non-empty directory, not a git repo → RuntimeError
8. Git repo with commits → tags HEAD as `afk-{name}-0`
9. Git.is_repo() returns True/False correctly
10. Git.init() creates a new repo
11. Git.commit_empty() creates commit and returns hash
12. Git.tag_exists() returns False for non-existent tag
13. Git.tag_exists() returns True for existing tag
14. Git.tag() creates tag pointing to correct commit
15. Git.tag() raises RuntimeError before git call if tag exists (pre-check)
16. execute_turn() checks tag exists BEFORE turn.start() — pre-existing tag = immediate error
17. execute_turn() creates tag `afk-{name}-{turn_number}` AFTER _add_result()
18. Second session with same name fails at creation (tag 0 already exists)

### Previous Epic Learnings

From Epic 2 retrospective:
- **Update all existing tests**: When adding constructor params, every test instantiation needs updating
- **Validation at boundaries**: Session already validates root_dir, driver, git — follow same pattern

### Impact on Story 3.2 (Rewind)

Story 3.2 becomes simpler:
- Find tag `afk-{session_name}-{turn_number}`
- `git checkout {tag}`
- `git checkout -b {new_branch_name}` (or let user decide)

No need to track commits between turns or worry about human commits.

### What This Story Does NOT Do

- Track human commits (out of scope — framework doesn't care)
- Track agent vs user commit distinction (replaced by tag-based approach)
- Implement rewind (Story 3.2)
- Delete old session tags (user's responsibility to clean up if reusing names)

### Tag Collision Behavior

**Tag collision is a hard error.** If `afk-{session_name}-{N}` already exists:
- `Git.tag_exists()` returns True
- `Git.tag()` raises `RuntimeError("Tag already exists: {name}")`

**This enforces unique session names per repo:**
- Session creation tries to tag `afk-{name}-0`
- If that tag exists → another session with that name already ran → fail immediately
- No duplicate session names, no ambiguous tags

User picks unique names. Framework enforces via tag-0 check at creation time.

### References

- Epic 3 definition: [Source: docs/epics.md#Epic 3: State Recovery & Rewind]
- Architecture patterns: [Source: docs/architecture.md#Implementation Patterns & Consistency Rules]
- Python conventions: [Source: docs/project-context.md#Python Conventions]
- Session class: [Source: afk/session.py:117-338]
- Git class: [Source: afk/git.py:7-134]
- Epic 2 retrospective: [Source: docs/archive/epic-2/epic-2-retro-2025-12-13.md]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
