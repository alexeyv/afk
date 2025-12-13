# Epic 2 Retrospective - Action Items

Generated: 2025-12-13

---

## Action Item 1: Propagate Review Changes to Quick Dev Workflow

**Problem Statement:**

Code review improvements discovered during Epic 2 (better review checklists, improved dedup guidance) need to be reflected in the Quick Dev workflow for use in Epic 2.5.

**Owner:** Alex

**Timeline:** Before Epic 2.5

**Acceptance Criteria:**
- [ ] Update Quick Dev workflow with review improvements from Epic 2
- [ ] Test workflow with domain model cleanup stories

**Status:** Pending

---

## Action Item 2: Epic 2.5 - Domain Model Cleanup (Quick Flow)

**Problem Statement:**

Design smells identified during Epic 2 that need cleanup before Epic 3:

| Issue | Current State | Problem |
|-------|---------------|---------|
| `Turn.log_file` | Raw `Path` | Should reference `TurnLog` instance |
| `TurnLog` naming | Does path math, not logging | Misleading name |
| Two `execute_turn`s | Function + method with same name | Confusing API |
| Naked paths | `str`/`Path` everywhere | Should pass structured objects |
| Naked turn numbers | Raw `int` scattered | Should be `TurnNumber` value class |

**Decision:** Execute domain model cleanup via Quick Flow before Epic 3.

**Owner:** Alex

**Timeline:** Before Epic 3

**Acceptance Criteria:**
- [ ] `Turn.log_file` references `TurnLog` instance
- [ ] `TurnLog` renamed or refactored for clarity
- [ ] Resolve `execute_turn` naming collision
- [ ] Replace naked paths with structured objects where appropriate
- [ ] Introduce `TurnNumber` value class

**Status:** Pending

---

## Action Item 3: Validate Multi-LLM Code Review Workflow

**Problem Statement:**

Enhanced multi-LLM code review workflow (Action Item 4 from Epic 1) exists in BMAD fork branch but hasn't been validated in production use.

**Owner:** Alex

**Timeline:** During Epic 3

**Acceptance Criteria:**
- [ ] Test multi-LLM review workflow on Epic 3 stories
- [ ] Document any issues or improvements needed
- [ ] Decide on adoption for standard workflow

**Status:** Pending

---

## Action Item 4: Add 3 Lessons to project-context.md

**Problem Statement:**

"Holy crap" moments from Epic 2 code review need to be permanently documented:

1. **Named file `logging.py`** - Shadows Python stdlib
2. **Hardcoded `/tmp` in tests** - Fails on Windows
3. **`raise KeyError(f"msg")`** - KeyError takes key, not message

**Owner:** Alex

**Timeline:** Retrospective

**Acceptance Criteria:**
- [x] Add stdlib shadowing rule to "What NOT to Do"
- [x] Add hardcoded paths rule to "What NOT to Do"
- [x] Add KeyError format rule to "What NOT to Do"

**Status:** Complete (2025-12-13) - All three rules added to `docs/project-context.md` "What NOT to Do" section.
