# Sprint Change Proposal - Commit Message Format Correction

**Date:** 2025-12-10
**Author:** Bob (Scrum Master)
**Status:** Approved

## Issue Summary

The commit message outcome format `[outcome] comment` specified in Architecture violates the Conventional Commits specification. The spec requires footers to follow `token: value` or `token #value` format.

**Issue Type:** Misunderstanding of original requirements (Conventional Commits spec)

**Discovered:** During architecture review, before significant implementation

## Impact Analysis

### Epic Impact
- **Epic 1 (Core Prompt Execution):** Can continue with minor acceptance criteria updates
- **Story 1-1:** Done - parsing logic update needed (trivial regex change)
- **Story 1-3:** Backlog - acceptance criteria wording update
- **All other epics:** Unaffected structurally

### Artifact Changes Required

| Artifact | Section | Change |
|----------|---------|--------|
| architecture.md | Commit Message Schema | Update format and example |
| project-context.md | Commit Message Schema | Update format and example |
| epics.md | Story 1-1, 1-3, 6-2 acceptance criteria | Update format references |
| afk/git.py | parse_commit_message() | Update regex if implemented |

## Recommended Approach

**Direct Adjustment** - Update all references from `[outcome]` bracket format to `outcome: value` Conventional Commits compliant footer format.

- **Effort:** Low
- **Risk:** Low
- **Timeline Impact:** None

## Detailed Edit Proposals

### Edit 1: architecture.md - Commit Message Schema

**OLD:**
```
feat: implement user authentication

Added login flow with session management.
Refactored the auth module for clarity.

[success] completed as specified
```

**NEW:**
```
feat: implement user authentication

Added login flow with session management.
Refactored the auth module for clarity.

outcome: success
```

Also update description from `[outcome] comment` to `outcome: value`.

### Edit 2: project-context.md - Commit Message Schema

**OLD:**
```
[success] completed as specified
```
and
```
Footer contains `[outcome] comment` for machine parsing
```

**NEW:**
```
outcome: success
```
and
```
Footer contains `outcome: value` for machine parsing (Conventional Commits compliant)
```

### Edit 3: epics.md - Multiple locations

Update all references:
- Line 69: `[success]` or `[failure]` → `outcome: success` or `outcome: failure`
- Line 153: `[outcome]` footer → `outcome:` footer
- Line 158: `[outcome]` footer → `outcome:` footer
- Line 205: `[outcome]` footer → `outcome:` footer
- Line 212: `[success] task completed` → footer with `outcome: success`
- Line 690: `[success]` or `[failure]` → `outcome: success` or `outcome: failure`

## Scope Classification

**Minor** - Direct implementation by development team / SM

## Handoff Plan

| Role | Responsibility |
|------|----------------|
| SM | Update architecture.md, project-context.md, epics.md |
| Dev | Update git.py parsing if already implemented |

## Approval

- [x] User approved proposal
- [x] Changes are actionable and specific
- [x] Handoff responsibilities clear
